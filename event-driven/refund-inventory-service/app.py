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
from inventory_manager import InventoryManager

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
STOCK_ADJUSTMENTS = Counter('stock_adjustments_total', 'Total stock adjustments')
STOCK_RESTORATIONS = Counter('stock_restorations_total', 'Total stock restorations')
PROCESSING_DURATION = Histogram('inventory_processing_duration_seconds', 'Inventory processing duration')

app = Flask(__name__)
api = Api(app, version='1.0', title='Refund Inventory Service API',
          description='Service de gestion d\'inventaire pour saga chorégraphiée',
          doc='/docs/')

# Configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6381/0')
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')

# Initialiser les composants
event_publisher = EventPublisher(redis_url, mongo_url)
event_consumer = EventConsumer(redis_url, mongo_url, 'refund-inventory-group', 'refund-inventory-consumer')
inventory_manager = InventoryManager()

# Stockage des processus en cours (idempotence)
processing_sagas = {}

def handle_remboursement_calcule(event_data):
    """Traite l'événement de remboursement calculé"""
    correlation_id = event_data.get('correlation_id')
    
    # Vérifier l'idempotence
    if correlation_id in processing_sagas:
        logger.info("Saga already processed", correlation_id=correlation_id)
        return
    
    processing_sagas[correlation_id] = {'status': 'processing', 'timestamp': datetime.utcnow()}
    
    try:
        with PROCESSING_DURATION.time():
            # Extraire les données
            data = json.loads(event_data.get('data', '{}'))
            claim_id = data.get('claim_id')
            product_id = data.get('product_id')
            refund_amount = data.get('refund_amount')
            
            # Calculer la quantité à remettre en stock
            # Pour les remboursements, on remet 1 unité en stock
            quantity_to_restore = 1
            
            # Effectuer l'ajustement de stock
            stock_adjustment = inventory_manager.adjust_stock(
                product_id=product_id,
                quantity_change=quantity_to_restore,
                reason='refund_return',
                claim_id=claim_id
            )
            
            # Publier l'événement de stock mis à jour
            stock_data = {
                'claim_id': claim_id,
                'product_id': product_id,
                'quantity_adjusted': quantity_to_restore,
                'new_stock_level': stock_adjustment['new_stock_level'],
                'adjustment_reason': 'refund_return',
                'refund_amount': refund_amount,
                'adjusted_at': datetime.utcnow().isoformat(),
                'saga_step': 'inventory_adjusted'
            }
            
            event_publisher.publish_event(
                event_type='StockMisAJour',
                aggregate_id=claim_id,
                data=stock_data,
                correlation_id=correlation_id
            )
            
            processing_sagas[correlation_id]['status'] = 'completed'
            SAGA_EVENTS_PROCESSED.labels(event_type='RemboursementCalcule', status='success').inc()
            STOCK_ADJUSTMENTS.inc()
            
            logger.info(
                "Stock adjustment completed",
                claim_id=claim_id,
                product_id=product_id,
                quantity_adjusted=quantity_to_restore,
                new_stock_level=stock_adjustment['new_stock_level'],
                correlation_id=correlation_id
            )
            
    except Exception as e:
        processing_sagas[correlation_id]['status'] = 'failed'
        
        # Publier l'événement d'échec
        error_data = {
            'claim_id': data.get('claim_id'),
            'product_id': data.get('product_id'),
            'error': str(e),
            'failed_at': datetime.utcnow().isoformat(),
            'saga_step': 'inventory_adjustment_failed'
        }
        
        event_publisher.publish_event(
            event_type='SagaRemboursementEchouee',
            aggregate_id=data.get('claim_id'),
            data=error_data,
            correlation_id=correlation_id
        )
        
        SAGA_EVENTS_PROCESSED.labels(event_type='RemboursementCalcule', status='failed').inc()
        
        logger.error(
            "Stock adjustment failed",
            claim_id=data.get('claim_id'),
            product_id=data.get('product_id'),
            error=str(e),
            correlation_id=correlation_id
        )

def handle_saga_remboursement_echouee(event_data):
    """Traite l'événement d'échec de saga pour compensation"""
    correlation_id = event_data.get('correlation_id')
    
    try:
        data = json.loads(event_data.get('data', '{}'))
        claim_id = data.get('claim_id')
        product_id = data.get('product_id')
        
        # Vérifier si on a effectué un ajustement à compenser
        if correlation_id in processing_sagas and processing_sagas[correlation_id]['status'] == 'completed':
            # Reverser l'ajustement de stock
            inventory_manager.adjust_stock(
                product_id=product_id,
                quantity_change=-1,  # Enlever la quantité qu'on avait ajoutée
                reason='refund_compensation',
                claim_id=claim_id
            )
            
            processing_sagas[correlation_id]['status'] = 'compensated'
            STOCK_RESTORATIONS.inc()
            
            logger.info(
                "Stock compensation completed",
                claim_id=claim_id,
                product_id=product_id,
                correlation_id=correlation_id
            )
            
    except Exception as e:
        logger.error(
            "Stock compensation failed",
            error=str(e),
            correlation_id=correlation_id
        )

# Enregistrer les handlers d'événements
event_consumer.register_handler('RemboursementCalcule', handle_remboursement_calcule)
event_consumer.register_handler('SagaRemboursementEchouee', handle_saga_remboursement_echouee)

@api.route('/inventory/<string:product_id>')
class InventoryResource(Resource):
    @api.doc('get_inventory_level')
    def get(self, product_id):
        """Obtenir le niveau de stock d'un produit"""
        stock_level = inventory_manager.get_stock_level(product_id)
        return {
            'product_id': product_id,
            'stock_level': stock_level,
            'timestamp': datetime.utcnow().isoformat()
        }

@api.route('/inventory/adjustments/<string:claim_id>')
class InventoryAdjustmentResource(Resource):
    @api.doc('get_adjustment_status')
    def get(self, claim_id):
        """Obtenir le statut d'ajustement de stock"""
        # Rechercher dans les sagas en cours
        for correlation_id, saga_info in processing_sagas.items():
            if saga_info.get('claim_id') == claim_id:
                return {
                    'claim_id': claim_id,
                    'status': saga_info['status'],
                    'correlation_id': correlation_id,
                    'timestamp': saga_info['timestamp'].isoformat()
                }
        
        return {'error': 'Adjustment not found'}, 404

@api.route('/inventory/stats')
class InventoryStatsResource(Resource):
    @api.doc('get_inventory_stats')
    def get(self):
        """Obtenir les statistiques d'inventaire"""
        stats = {
            'total_adjustments': len(processing_sagas),
            'processing': len([s for s in processing_sagas.values() if s['status'] == 'processing']),
            'completed': len([s for s in processing_sagas.values() if s['status'] == 'completed']),
            'failed': len([s for s in processing_sagas.values() if s['status'] == 'failed']),
            'compensated': len([s for s in processing_sagas.values() if s['status'] == 'compensated']),
            'total_stock_levels': inventory_manager.get_all_stock_levels()
        }
        return stats

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {"status": "healthy", "service": "refund-inventory-service"}

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def start_event_consumer():
    """Démarre le consommateur d'événements"""
    streams = [
        'events:remboursementcalcule',
        'events:sagaremboursementechouee'
    ]
    event_consumer.start_consuming(streams)

if __name__ == '__main__':
    # Démarrer le consommateur d'événements dans un thread séparé
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    
    logger.info("Starting Refund Inventory Service", port=8109)
    app.run(host='0.0.0.0', port=8109, debug=False)