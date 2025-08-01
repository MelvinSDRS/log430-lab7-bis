import os
import uuid
import json
import threading
import structlog
from datetime import datetime
from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from event_publisher import EventPublisher
from event_consumer import EventConsumer
from refund_calculator import RefundCalculator

# Configuration de logging structuré
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Métriques Prometheus
SAGA_EVENTS_PROCESSED = Counter('saga_events_processed_total', 'Total saga events processed', ['event_type', 'status'])
REFUNDS_CALCULATED = Counter('refunds_calculated_total', 'Total refunds calculated')
REFUNDS_CANCELLED = Counter('refunds_cancelled_total', 'Total refunds cancelled')
PROCESSING_DURATION = Histogram('refund_processing_duration_seconds', 'Refund processing duration')

app = Flask(__name__)
api = Api(app, version='1.0', title='Refund Payment Service API',
          description='Service de calcul de remboursement pour saga chorégraphiée',
          doc='/docs/')

# Configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6381/0')
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')

# Initialiser les composants
event_publisher = EventPublisher(redis_url, mongo_url)
event_consumer = EventConsumer(redis_url, mongo_url, 'refund-payment-group', 'refund-payment-consumer')
refund_calculator = RefundCalculator()

# Stockage des processus en cours (idempotence)
processing_sagas = {}

def handle_saga_remboursement_demarree(event_data):
    """Traite l'événement de démarrage de saga de remboursement"""
    correlation_id = event_data.get('correlation_id')
    
    # Vérifier l'idempotence
    if correlation_id in processing_sagas:
        logger.info("Saga already processed", correlation_id=correlation_id)
        return
    
    processing_sagas[correlation_id] = {'status': 'processing', 'timestamp': datetime.utcnow()}
    
    try:
        with PROCESSING_DURATION.time():
            # Extraire les données du panier
            data = json.loads(event_data.get('data', '{}'))
            claim_id = data.get('claim_id')
            customer_id = data.get('customer_id')
            product_id = data.get('product_id')
            
            # Calculer le remboursement
            refund_amount = refund_calculator.calculate_refund(
                product_id=product_id,
                claim_type=data.get('claim_type', 'product_defect')
            )
            
            # Publier l'événement de remboursement calculé
            refund_data = {
                'claim_id': claim_id,
                'customer_id': customer_id,
                'product_id': product_id,
                'refund_amount': refund_amount,
                'currency': 'CAD',
                'payment_method': 'credit_card',
                'processed_at': datetime.utcnow().isoformat(),
                'saga_step': 'payment_calculated'
            }
            
            event_publisher.publish_event(
                event_type='RemboursementCalcule',
                aggregate_id=claim_id,
                data=refund_data,
                correlation_id=correlation_id
            )
            
            processing_sagas[correlation_id]['status'] = 'completed'
            SAGA_EVENTS_PROCESSED.labels(event_type='SagaRemboursementDemarree', status='success').inc()
            REFUNDS_CALCULATED.inc()
            
            logger.info(
                "Refund calculated successfully",
                claim_id=claim_id,
                customer_id=customer_id,
                refund_amount=refund_amount,
                correlation_id=correlation_id
            )
            
    except Exception as e:
        processing_sagas[correlation_id]['status'] = 'failed'
        
        # Publier l'événement d'échec
        error_data = {
            'claim_id': data.get('claim_id'),
            'error': str(e),
            'failed_at': datetime.utcnow().isoformat(),
            'saga_step': 'payment_calculation_failed'
        }
        
        event_publisher.publish_event(
            event_type='RemboursementAnnule',
            aggregate_id=data.get('claim_id'),
            data=error_data,
            correlation_id=correlation_id
        )
        
        SAGA_EVENTS_PROCESSED.labels(event_type='SagaRemboursementDemarree', status='failed').inc()
        REFUNDS_CANCELLED.inc()
        
        logger.error(
            "Refund calculation failed",
            claim_id=data.get('claim_id'),
            error=str(e),
            correlation_id=correlation_id
        )

def handle_saga_remboursement_echouee(event_data):
    """Traite l'événement d'échec de saga pour compensation"""
    correlation_id = event_data.get('correlation_id')
    
    try:
        data = json.loads(event_data.get('data', '{}'))
        claim_id = data.get('claim_id')
        
        # Annuler toute transaction de remboursement en cours
        if correlation_id in processing_sagas:
            processing_sagas[correlation_id]['status'] = 'compensated'
            
            # Publier l'événement de compensation
            compensation_data = {
                'claim_id': claim_id,
                'compensated_at': datetime.utcnow().isoformat(),
                'saga_step': 'payment_compensated'
            }
            
            event_publisher.publish_event(
                event_type='RemboursementAnnule',
                aggregate_id=claim_id,
                data=compensation_data,
                correlation_id=correlation_id
            )
            
            SAGA_EVENTS_PROCESSED.labels(event_type='SagaRemboursementEchouee', status='compensated').inc()
            
            logger.info(
                "Refund compensation completed",
                claim_id=claim_id,
                correlation_id=correlation_id
            )
            
    except Exception as e:
        logger.error(
            "Refund compensation failed",
            error=str(e),
            correlation_id=correlation_id
        )

# Enregistrer les handlers d'événements
event_consumer.register_handler('SagaRemboursementDemarree', handle_saga_remboursement_demarree)
event_consumer.register_handler('SagaRemboursementEchouee', handle_saga_remboursement_echouee)

@api.route('/refunds/<string:claim_id>')
class RefundResource(Resource):
    @api.doc('get_refund_status')
    def get(self, claim_id):
        """Obtenir le statut du remboursement"""
        # Rechercher dans les sagas en cours
        for correlation_id, saga_info in processing_sagas.items():
            if saga_info.get('claim_id') == claim_id:
                return {
                    'claim_id': claim_id,
                    'status': saga_info['status'],
                    'correlation_id': correlation_id,
                    'timestamp': saga_info['timestamp'].isoformat()
                }
        
        return {'error': 'Refund not found'}, 404

@api.route('/refunds/stats')
class RefundStatsResource(Resource):
    @api.doc('get_refund_stats')
    def get(self):
        """Obtenir les statistiques des remboursements"""
        stats = {
            'total_processing': len([s for s in processing_sagas.values() if s['status'] == 'processing']),
            'total_completed': len([s for s in processing_sagas.values() if s['status'] == 'completed']),
            'total_failed': len([s for s in processing_sagas.values() if s['status'] == 'failed']),
            'total_compensated': len([s for s in processing_sagas.values() if s['status'] == 'compensated'])
        }
        return stats

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {"status": "healthy", "service": "refund-payment-service"}

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def start_event_consumer():
    """Démarre le consommateur d'événements"""
    streams = [
        'events:sagaremboursementdemarree',
        'events:sagaremboursementechouee'
    ]
    event_consumer.start_consuming(streams)

if __name__ == '__main__':
    # Démarrer le consommateur d'événements dans un thread séparé
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    
    logger.info("Starting Refund Payment Service", port=8108)
    app.run(host='0.0.0.0', port=8108, debug=False)