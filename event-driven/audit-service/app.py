import os
import time
import threading
from datetime import datetime
from typing import Dict, Any

import structlog
from flask import Flask, jsonify, request
from flask_restx import Api, Resource
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pymongo import MongoClient

from event_consumer import EventConsumer

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
AUDIT_ENTRIES_CREATED = Counter('audit_entries_created_total', 'Total number of audit entries created', ['event_type'])
EVENTS_PROCESSED = Counter('audit_events_processed_total', 'Total number of events processed', ['event_type'])
PROCESSING_DURATION = Histogram('audit_processing_duration_seconds', 'Audit processing duration', ['event_type'])

app = Flask(__name__)
api = Api(app, version='1.0', title='Audit Service API',
          description='Service d\'audit événementiel',
          doc='/docs/')

# Configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6381/0')
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')

class AuditService:
    def __init__(self):
        self.mongo_client = MongoClient(mongo_url)
        self.audit_collection = self.mongo_client.event_store.audit_trail
        
        # Créer les indexes pour optimiser les requêtes
        self.audit_collection.create_index("aggregate_id")
        self.audit_collection.create_index("event_type")
        self.audit_collection.create_index("timestamp")
        self.audit_collection.create_index("user_id")
        
    def create_audit_entry(self, event_data: Dict[str, Any], audit_type: str = "EVENT_PROCESSED"):
        """Crée une entrée d'audit"""
        audit_entry = {
            "audit_id": f"audit_{int(time.time())}_{event_data.get('event_id', 'unknown')}",
            "audit_type": audit_type,
            "event_id": event_data.get('event_id'),
            "event_type": event_data.get('event_type'),
            "aggregate_id": event_data.get('aggregate_id'),
            "correlation_id": event_data.get('correlation_id'),
            "timestamp": datetime.utcnow().isoformat(),
            "event_timestamp": event_data.get('timestamp'),
            "event_data": event_data,
            "processed_by": "audit-service",
            "processing_duration": None
        }
        
        # Calculer la latence de traitement
        if event_data.get('timestamp'):
            try:
                event_time = datetime.fromisoformat(event_data['timestamp'])
                processing_time = datetime.utcnow()
                latency = (processing_time - event_time).total_seconds()
                audit_entry["processing_latency_seconds"] = latency
            except Exception as e:
                logger.warning("Could not calculate processing latency", error=str(e))
        
        # Sauvegarder l'entrée d'audit
        self.audit_collection.insert_one(audit_entry)
        
        logger.info(
            "Audit entry created",
            audit_id=audit_entry["audit_id"],
            event_type=event_data.get('event_type'),
            aggregate_id=event_data.get('aggregate_id'),
            correlation_id=event_data.get('correlation_id')
        )
        
        return audit_entry
    
    def get_audit_trail(self, aggregate_id: str = None, event_type: str = None, 
                       limit: int = 100, offset: int = 0) -> list:
        """Récupère la piste d'audit"""
        query = {}
        if aggregate_id:
            query["aggregate_id"] = aggregate_id
        if event_type:
            query["event_type"] = event_type
        
        cursor = self.audit_collection.find(query).sort("timestamp", -1).skip(offset).limit(limit)
        audit_entries = list(cursor)
        
        # Supprimer l'_id MongoDB pour sérialisation JSON
        for entry in audit_entries:
            entry.pop("_id", None)
        
        return audit_entries
    
    def get_audit_stats(self) -> Dict[str, Any]:
        """Génère des statistiques d'audit"""
        pipeline = [
            {
                "$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1},
                    "avg_latency": {"$avg": "$processing_latency_seconds"}
                }
            }
        ]
        
        stats = list(self.audit_collection.aggregate(pipeline))
        
        total_entries = self.audit_collection.count_documents({})
        
        return {
            "total_entries": total_entries,
            "by_event_type": [
                {
                    "event_type": stat["_id"],
                    "count": stat["count"],
                    "avg_latency_seconds": stat.get("avg_latency", 0)
                }
                for stat in stats
            ]
        }

# Initialiser le service d'audit
audit_service = AuditService()

def handle_any_event(event_data: Dict[str, Any]):
    """Traite n'importe quel événement pour l'audit"""
    event_type = event_data.get('event_type', 'unknown')
    
    with PROCESSING_DURATION.labels(event_type=event_type).time():
        try:
            # Créer l'entrée d'audit
            audit_service.create_audit_entry(event_data)
            
            # Métriques
            AUDIT_ENTRIES_CREATED.labels(event_type=event_type).inc()
            EVENTS_PROCESSED.labels(event_type=event_type).inc()
            
            # Log détaillé pour l'audit
            logger.info(
                "Event audited",
                event_type=event_type,
                event_id=event_data.get('event_id'),
                aggregate_id=event_data.get('aggregate_id'),
                correlation_id=event_data.get('correlation_id'),
                timestamp=event_data.get('timestamp')
            )
            
        except Exception as e:
            logger.error(
                "Error auditing event",
                event_type=event_type,
                error=str(e),
                event_data=event_data
            )

# Initialiser le consumer d'événements
event_consumer = EventConsumer(
    redis_url=redis_url,
    mongo_url=mongo_url,
    consumer_group='audit-service',
    consumer_name='audit-worker-1'
)

# Enregistrer un handler générique pour tous les événements
event_consumer.register_handler('ReclamationCreee', handle_any_event)
event_consumer.register_handler('ReclamationAffectee', handle_any_event)
event_consumer.register_handler('ReclamationEnCours', handle_any_event)
event_consumer.register_handler('ReclamationResolue', handle_any_event)
event_consumer.register_handler('ReclamationCloturee', handle_any_event)

@api.route('/audit')
class AuditResource(Resource):
    @api.doc('get_audit_trail')
    def get(self):
        """Récupérer la piste d'audit"""
        aggregate_id = request.args.get('aggregate_id')
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        audit_trail = audit_service.get_audit_trail(
            aggregate_id=aggregate_id,
            event_type=event_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "audit_trail": audit_trail,
            "count": len(audit_trail),
            "offset": offset,
            "limit": limit
        }

@api.route('/audit/stats')
class AuditStatsResource(Resource):
    @api.doc('get_audit_stats')
    def get(self):
        """Obtenir les statistiques d'audit"""
        return audit_service.get_audit_stats()

@api.route('/audit/claims/<string:claim_id>')
class ClaimAuditResource(Resource):
    @api.doc('get_claim_audit')
    def get(self, claim_id):
        """Obtenir l'audit d'une réclamation spécifique"""
        audit_trail = audit_service.get_audit_trail(aggregate_id=claim_id)
        
        return {
            "claim_id": claim_id,
            "audit_trail": audit_trail,
            "count": len(audit_trail)
        }

@api.route('/audit/performance')
class AuditPerformanceResource(Resource):
    @api.doc('get_audit_performance')
    def get(self):
        """Obtenir les métriques de performance de l'audit"""
        pipeline = [
            {
                "$group": {
                    "_id": None,
                    "total_events": {"$sum": 1},
                    "avg_latency": {"$avg": "$processing_latency_seconds"},
                    "max_latency": {"$max": "$processing_latency_seconds"},
                    "min_latency": {"$min": "$processing_latency_seconds"}
                }
            }
        ]
        
        result = list(audit_service.audit_collection.aggregate(pipeline))
        
        if result:
            stats = result[0]
            return {
                "total_events_audited": stats.get("total_events", 0),
                "average_latency_seconds": stats.get("avg_latency", 0),
                "max_latency_seconds": stats.get("max_latency", 0),
                "min_latency_seconds": stats.get("min_latency", 0)
            }
        
        return {
            "total_events_audited": 0,
            "average_latency_seconds": 0,
            "max_latency_seconds": 0,
            "min_latency_seconds": 0
        }

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {"status": "healthy", "service": "audit-service"}

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

def start_event_consumer():
    """Démarre le consumer d'événements en arrière-plan"""
    time.sleep(5)  # Attendre que Redis soit prêt
    streams = ['events:all']  # Écouter tous les événements
    event_consumer.start_consuming(streams)

if __name__ == '__main__':
    # Démarrer le consumer d'événements dans un thread séparé
    consumer_thread = threading.Thread(target=start_event_consumer, daemon=True)
    consumer_thread.start()
    
    logger.info("Starting Audit Service", port=8103)
    app.run(host='0.0.0.0', port=8103, debug=False)