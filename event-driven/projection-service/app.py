import os
import time
import threading
import json
from datetime import datetime
from typing import Dict, Any

import structlog
from flask import Flask, jsonify
from flask_restx import Api, Resource
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from event_consumer import EventConsumer
from read_models import ReadModelRepository

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
PROJECTIONS_UPDATED = Counter('projections_updated_total', 'Total number of projections updated', ['projection_type'])
EVENTS_PROCESSED = Counter('projection_events_processed_total', 'Total number of events processed', ['event_type'])
PROCESSING_DURATION = Histogram('projection_processing_duration_seconds', 'Projection processing duration', ['event_type'])

app = Flask(__name__)
api = Api(app, version='1.0', title='Projection Service API',
          description='Service de projections CQRS pour read models',
          doc='/docs/')

# Configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6381/0')
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')
postgres_url = os.getenv('POSTGRES_URL', 'postgresql://localhost:5439/read_models_db')

# Initialiser le repository des read models
read_model_repo = ReadModelRepository(postgres_url)

def handle_reclamation_creee(event_data: Dict[str, Any]):
    """Traite l'événement ReclamationCreee pour mettre à jour les projections"""
    with PROCESSING_DURATION.labels(event_type='ReclamationCreee').time():
        try:
            claim_id = event_data.get('aggregate_id')
            data = event_data.get('data', {})
            
            # Parser les données si elles sont en string JSON
            if isinstance(data, str):
                data = json.loads(data)
            
            # Créer/mettre à jour le read model de la réclamation
            claim_data = {
                'claim_id': claim_id,
                'customer_id': data.get('customer_id'),
                'claim_type': data.get('claim_type'),
                'description': data.get('description'),
                'product_id': data.get('product_id'),
                'status': 'created',
                'created_at': datetime.fromisoformat(event_data.get('timestamp')),
                'updated_at': datetime.fromisoformat(event_data.get('timestamp'))
            }
            
            read_model_repo.upsert_claim(claim_data)
            
            # Mettre à jour les statistiques client
            read_model_repo.update_customer_stats(
                customer_id=data.get('customer_id'),
                operation='created',
                claim_date=datetime.fromisoformat(event_data.get('timestamp'))
            )
            
            # Mettre à jour les statistiques par type
            read_model_repo.update_claim_type_stats(
                claim_type=data.get('claim_type'),
                status='created',
                operation='created'
            )
            
            # Métriques
            PROJECTIONS_UPDATED.labels(projection_type='claim').inc()
            PROJECTIONS_UPDATED.labels(projection_type='customer_stats').inc()
            PROJECTIONS_UPDATED.labels(projection_type='claim_type_stats').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationCreee').inc()
            
            logger.info(
                "Projections updated for ReclamationCreee",
                claim_id=claim_id,
                customer_id=data.get('customer_id'),
                claim_type=data.get('claim_type')
            )
            
        except Exception as e:
            logger.error(
                "Error handling ReclamationCreee event",
                error=str(e),
                event_data=event_data
            )

def handle_reclamation_affectee(event_data: Dict[str, Any]):
    """Traite l'événement ReclamationAffectee"""
    with PROCESSING_DURATION.labels(event_type='ReclamationAffectee').time():
        try:
            claim_id = event_data.get('aggregate_id')
            data = event_data.get('data', {})
            
            if isinstance(data, str):
                data = json.loads(data)
            
            # Mettre à jour le statut de la réclamation
            claim_data = {
                'claim_id': claim_id,
                'status': 'assigned',
                'assigned_agent': data.get('agent_id'),
                'assigned_at': datetime.fromisoformat(event_data.get('timestamp')),
                'updated_at': datetime.fromisoformat(event_data.get('timestamp'))
            }
            
            read_model_repo.upsert_claim(claim_data)
            
            # Mettre à jour les statistiques agent
            read_model_repo.update_agent_stats(
                agent_id=data.get('agent_id'),
                operation='assigned',
                assignment_date=datetime.fromisoformat(event_data.get('timestamp'))
            )
            
            # Mettre à jour les statistiques par type (changement de statut)
            # On a besoin du claim_type, on peut le récupérer depuis la base
            claim = read_model_repo.session.query(read_model_repo.ClaimReadModel).filter_by(claim_id=claim_id).first()
            if claim:
                read_model_repo.update_claim_type_stats(
                    claim_type=claim.claim_type,
                    status='assigned',
                    operation='status_change'
                )
            
            # Métriques
            PROJECTIONS_UPDATED.labels(projection_type='claim').inc()
            PROJECTIONS_UPDATED.labels(projection_type='agent_stats').inc()
            PROJECTIONS_UPDATED.labels(projection_type='claim_type_stats').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationAffectee').inc()
            
            logger.info(
                "Projections updated for ReclamationAffectee",
                claim_id=claim_id,
                agent_id=data.get('agent_id')
            )
            
        except Exception as e:
            logger.error(
                "Error handling ReclamationAffectee event",
                error=str(e),
                event_data=event_data
            )

def handle_reclamation_en_cours(event_data: Dict[str, Any]):
    """Traite l'événement ReclamationEnCours"""
    with PROCESSING_DURATION.labels(event_type='ReclamationEnCours').time():
        try:
            claim_id = event_data.get('aggregate_id')
            
            # Mettre à jour le statut
            claim_data = {
                'claim_id': claim_id,
                'status': 'in_progress',
                'started_at': datetime.fromisoformat(event_data.get('timestamp')),
                'updated_at': datetime.fromisoformat(event_data.get('timestamp'))
            }
            
            read_model_repo.upsert_claim(claim_data)
            
            # Mettre à jour les statistiques par type
            claim = read_model_repo.session.query(read_model_repo.ClaimReadModel).filter_by(claim_id=claim_id).first()
            if claim:
                read_model_repo.update_claim_type_stats(
                    claim_type=claim.claim_type,
                    status='in_progress',
                    operation='status_change'
                )
            
            # Métriques
            PROJECTIONS_UPDATED.labels(projection_type='claim').inc()
            PROJECTIONS_UPDATED.labels(projection_type='claim_type_stats').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationEnCours').inc()
            
        except Exception as e:
            logger.error(
                "Error handling ReclamationEnCours event",
                error=str(e),
                event_data=event_data
            )

def handle_reclamation_resolue(event_data: Dict[str, Any]):
    """Traite l'événement ReclamationResolue"""
    with PROCESSING_DURATION.labels(event_type='ReclamationResolue').time():
        try:
            claim_id = event_data.get('aggregate_id')
            data = event_data.get('data', {})
            
            if isinstance(data, str):
                data = json.loads(data)
            
            # Mettre à jour la réclamation
            claim_data = {
                'claim_id': claim_id,
                'status': 'resolved',
                'resolution': data.get('resolution'),
                'resolved_at': datetime.fromisoformat(event_data.get('timestamp')),
                'updated_at': datetime.fromisoformat(event_data.get('timestamp'))
            }
            
            read_model_repo.upsert_claim(claim_data)
            
            # Mettre à jour les statistiques client
            claim = read_model_repo.session.query(read_model_repo.ClaimReadModel).filter_by(claim_id=claim_id).first()
            if claim:
                read_model_repo.update_customer_stats(
                    customer_id=claim.customer_id,
                    operation='resolved',
                    claim_date=datetime.fromisoformat(event_data.get('timestamp'))
                )
                
                # Mettre à jour les statistiques agent
                if claim.assigned_agent:
                    read_model_repo.update_agent_stats(
                        agent_id=claim.assigned_agent,
                        operation='resolved',
                        assignment_date=datetime.fromisoformat(event_data.get('timestamp'))
                    )
                
                # Mettre à jour les statistiques par type
                read_model_repo.update_claim_type_stats(
                    claim_type=claim.claim_type,
                    status='resolved',
                    operation='status_change'
                )
            
            # Métriques
            PROJECTIONS_UPDATED.labels(projection_type='claim').inc()
            PROJECTIONS_UPDATED.labels(projection_type='customer_stats').inc()
            PROJECTIONS_UPDATED.labels(projection_type='agent_stats').inc()
            PROJECTIONS_UPDATED.labels(projection_type='claim_type_stats').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationResolue').inc()
            
        except Exception as e:
            logger.error(
                "Error handling ReclamationResolue event",
                error=str(e),
                event_data=event_data
            )

def handle_reclamation_cloturee(event_data: Dict[str, Any]):
    """Traite l'événement ReclamationCloturee"""
    with PROCESSING_DURATION.labels(event_type='ReclamationCloturee').time():
        try:
            claim_id = event_data.get('aggregate_id')
            
            # Mettre à jour la réclamation
            claim_data = {
                'claim_id': claim_id,
                'status': 'closed',
                'closed_at': datetime.fromisoformat(event_data.get('timestamp')),
                'updated_at': datetime.fromisoformat(event_data.get('timestamp'))
            }
            
            read_model_repo.upsert_claim(claim_data)
            
            # Mettre à jour les statistiques client
            claim = read_model_repo.session.query(read_model_repo.ClaimReadModel).filter_by(claim_id=claim_id).first()
            if claim:
                read_model_repo.update_customer_stats(
                    customer_id=claim.customer_id,
                    operation='closed',
                    claim_date=datetime.fromisoformat(event_data.get('timestamp'))
                )
                
                # Mettre à jour les statistiques par type
                read_model_repo.update_claim_type_stats(
                    claim_type=claim.claim_type,
                    status='closed',
                    operation='status_change'
                )
            
            # Métriques
            PROJECTIONS_UPDATED.labels(projection_type='claim').inc()
            PROJECTIONS_UPDATED.labels(projection_type='customer_stats').inc()
            PROJECTIONS_UPDATED.labels(projection_type='claim_type_stats').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationCloturee').inc()
            
        except Exception as e:
            logger.error(
                "Error handling ReclamationCloturee event",
                error=str(e),
                event_data=event_data
            )

# Initialiser le consumer d'événements
event_consumer = EventConsumer(
    redis_url=redis_url,
    mongo_url=mongo_url,
    consumer_group='projection-service',
    consumer_name='projection-worker-1'
)

# Enregistrer les handlers
event_consumer.register_handler('ReclamationCreee', handle_reclamation_creee)
event_consumer.register_handler('ReclamationAffectee', handle_reclamation_affectee)
event_consumer.register_handler('ReclamationEnCours', handle_reclamation_en_cours)
event_consumer.register_handler('ReclamationResolue', handle_reclamation_resolue)
event_consumer.register_handler('ReclamationCloturee', handle_reclamation_cloturee)

@api.route('/projections/stats')
class ProjectionStatsResource(Resource):
    @api.doc('get_projection_stats')
    def get(self):
        """Obtenir les statistiques des projections"""
        try:
            total_claims = len(read_model_repo.get_all_claims())
            customer_stats_count = len(read_model_repo.get_customer_stats())
            agent_stats_count = len(read_model_repo.get_agent_stats())
            type_stats_count = len(read_model_repo.get_claim_type_stats())
            
            return {
                "total_claims_projected": total_claims,
                "customer_stats_records": customer_stats_count,
                "agent_stats_records": agent_stats_count,
                "claim_type_stats_records": type_stats_count
            }
        except Exception as e:
            logger.error("Error getting projection stats", error=str(e))
            return {"error": "Could not retrieve projection stats"}, 500

@app.route('/health')
def health():
    """Endpoint de santé"""
    try:
        # Tester la connexion PostgreSQL
        read_model_repo.session.execute('SELECT 1')
        return {"status": "healthy", "service": "projection-service"}
    except Exception as e:
        return {"status": "unhealthy", "service": "projection-service", "error": str(e)}, 503

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def start_event_consumer():
    """Démarre le consumer d'événements en arrière-plan"""
    time.sleep(10)  # Attendre que Redis et MongoDB soient prêts
    streams = ['events:all']  # Écouter tous les événements
    event_consumer.start_consuming(streams)

if __name__ == '__main__':
    # Démarrer le consumer d'événements dans un thread séparé
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    
    logger.info("Starting Projection Service", port=8104)
    app.run(host='0.0.0.0', port=8104, debug=False)