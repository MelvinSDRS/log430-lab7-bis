import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import structlog
from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pymongo import MongoClient
from pymongo.errors import PyMongoError

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
EVENTS_QUERIED = Counter('events_queried_total', 'Total number of events queried', ['query_type'])
REPLAYS_PERFORMED = Counter('replays_performed_total', 'Total number of event replays performed')
SNAPSHOTS_CREATED = Counter('snapshots_created_total', 'Total number of snapshots created')
QUERY_DURATION = Histogram('event_query_duration_seconds', 'Event query duration', ['query_type'])

app = Flask(__name__)
api = Api(app, version='1.0', title='Event Store Service API',
          description='Service de gestion de l\'Event Store avec replay',
          doc='/docs/')

# Configuration
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')

class EventStoreService:
    def __init__(self, mongo_url: str):
        self.mongo_client = MongoClient(mongo_url)
        self.db = self.mongo_client.event_store
        self.events_collection = self.db.events
        self.snapshots_collection = self.db.snapshots
        
        # Créer les indexes pour optimiser les requêtes
        self.events_collection.create_index("aggregate_id")
        self.events_collection.create_index("event_type")
        self.events_collection.create_index("timestamp")
        self.events_collection.create_index([("aggregate_id", 1), ("timestamp", 1)])
        
        self.snapshots_collection.create_index("aggregate_id")
        self.snapshots_collection.create_index("timestamp")
        
    def get_events_by_aggregate(self, aggregate_id: str, 
                               from_timestamp: Optional[str] = None,
                               to_timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
        """Récupère tous les événements pour un agrégat donné"""
        query = {"aggregate_id": aggregate_id}
        
        if from_timestamp or to_timestamp:
            timestamp_query = {}
            if from_timestamp:
                timestamp_query["$gte"] = from_timestamp
            if to_timestamp:
                timestamp_query["$lte"] = to_timestamp
            query["timestamp"] = timestamp_query
        
        events = list(self.events_collection.find(query).sort("timestamp", 1))
        
        # Supprimer l'_id MongoDB pour sérialisation JSON
        for event in events:
            event.pop("_id", None)
            
        return events
    
    def get_events_by_type(self, event_type: str, 
                          limit: int = 100, 
                          offset: int = 0) -> List[Dict[str, Any]]:
        """Récupère les événements par type"""
        events = list(self.events_collection.find({"event_type": event_type})
                     .sort("timestamp", -1)
                     .skip(offset)
                     .limit(limit))
        
        # Supprimer l'_id MongoDB
        for event in events:
            event.pop("_id", None)
            
        return events
    
    def get_events_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Récupère les événements par correlation_id"""
        events = list(self.events_collection.find({"correlation_id": correlation_id})
                     .sort("timestamp", 1))
        
        # Supprimer l'_id MongoDB
        for event in events:
            event.pop("_id", None)
            
        return events
    
    def replay_events(self, aggregate_id: str, 
                     up_to_timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Rejoue les événements pour reconstituer l'état d'un agrégat"""
        events = self.get_events_by_aggregate(aggregate_id, to_timestamp=up_to_timestamp)
        
        # Reconstituer l'état à partir des événements
        state = self._reconstruct_state_from_events(events)
        
        return {
            "aggregate_id": aggregate_id,
            "reconstructed_state": state,
            "events_count": len(events),
            "events": events,
            "up_to_timestamp": up_to_timestamp
        }
    
    def _reconstruct_state_from_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Reconstruit l'état d'un agrégat à partir des événements"""
        if not events:
            return {}
        
        # État initial
        state = {
            "aggregate_id": events[0].get("aggregate_id"),
            "status": "unknown",
            "created_at": None,
            "updated_at": None,
            "history": []
        }
        
        # Appliquer les événements dans l'ordre chronologique
        for event in events:
            event_type = event.get("event_type")
            event_data = event.get("data", {})
            timestamp = event.get("timestamp")
            
            # Traiter selon le type d'événement
            if event_type == "ReclamationCreee":
                state.update({
                    "status": "created",
                    "customer_id": event_data.get("customer_id"),
                    "claim_type": event_data.get("claim_type"),
                    "description": event_data.get("description"),
                    "product_id": event_data.get("product_id"),
                    "created_at": timestamp
                })
            elif event_type == "ReclamationAffectee":
                state.update({
                    "status": "assigned",
                    "assigned_agent": event_data.get("agent_id"),
                    "assigned_at": timestamp
                })
            elif event_type == "ReclamationEnCours":
                state.update({
                    "status": "in_progress",
                    "started_at": timestamp
                })
            elif event_type == "ReclamationResolue":
                state.update({
                    "status": "resolved",
                    "resolution": event_data.get("resolution"),
                    "resolved_at": timestamp
                })
            elif event_type == "ReclamationCloturee":
                state.update({
                    "status": "closed",
                    "closed_at": timestamp
                })
            
            # Mettre à jour l'historique
            state["history"].append({
                "event_type": event_type,
                "timestamp": timestamp,
                "event_id": event.get("event_id")
            })
            
            state["updated_at"] = timestamp
        
        return state
    
    def create_snapshot(self, aggregate_id: str, state: Dict[str, Any]) -> str:
        """Crée un snapshot de l'état d'un agrégat"""
        snapshot = {
            "aggregate_id": aggregate_id,
            "state": state,
            "timestamp": datetime.utcnow().isoformat(),
            "version": len(state.get("history", []))
        }
        
        # Supprimer l'ancien snapshot s'il existe
        self.snapshots_collection.delete_many({"aggregate_id": aggregate_id})
        
        # Insérer le nouveau snapshot
        result = self.snapshots_collection.insert_one(snapshot)
        
        logger.info(
            "Snapshot created",
            aggregate_id=aggregate_id,
            version=snapshot["version"],
            timestamp=snapshot["timestamp"]
        )
        
        return str(result.inserted_id)
    
    def get_snapshot(self, aggregate_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le snapshot le plus récent d'un agrégat"""
        snapshot = self.snapshots_collection.find_one(
            {"aggregate_id": aggregate_id},
            sort=[("timestamp", -1)]
        )
        
        if snapshot:
            snapshot.pop("_id", None)
            
        return snapshot
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Génère des statistiques sur les événements"""
        # Statistiques par type d'événement
        pipeline = [
            {"$group": {
                "_id": "$event_type",
                "count": {"$sum": 1}
            }}
        ]
        
        event_types_stats = list(self.events_collection.aggregate(pipeline))
        
        # Statistiques par agrégat
        aggregate_pipeline = [
            {"$group": {
                "_id": "$aggregate_id",
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        
        top_aggregates = list(self.events_collection.aggregate(aggregate_pipeline))
        
        # Statistiques générales
        total_events = self.events_collection.count_documents({})
        total_aggregates = len(self.events_collection.distinct("aggregate_id"))
        
        return {
            "total_events": total_events,
            "total_aggregates": total_aggregates,
            "by_event_type": [
                {
                    "event_type": stat["_id"],
                    "count": stat["count"]
                }
                for stat in event_types_stats
            ],
            "top_aggregates": [
                {
                    "aggregate_id": stat["_id"],
                    "events_count": stat["count"]
                }
                for stat in top_aggregates
            ]
        }

# Initialiser le service Event Store
event_store_service = EventStoreService(mongo_url)

@api.route('/events/<string:aggregate_id>')
class AggregateEventsResource(Resource):
    @api.doc('get_aggregate_events')
    def get(self, aggregate_id):
        """Récupérer tous les événements d'un agrégat"""
        with QUERY_DURATION.labels(query_type='aggregate').time():
            from_timestamp = request.args.get('from_timestamp')
            to_timestamp = request.args.get('to_timestamp')
            
            events = event_store_service.get_events_by_aggregate(
                aggregate_id, from_timestamp, to_timestamp
            )
            
            EVENTS_QUERIED.labels(query_type='aggregate').inc()
            
            return {
                "aggregate_id": aggregate_id,
                "events": events,
                "count": len(events)
            }

@api.route('/events/type/<string:event_type>')
class EventTypeResource(Resource):
    @api.doc('get_events_by_type')
    def get(self, event_type):
        """Récupérer les événements par type"""
        with QUERY_DURATION.labels(query_type='event_type').time():
            limit = int(request.args.get('limit', 100))
            offset = int(request.args.get('offset', 0))
            
            events = event_store_service.get_events_by_type(event_type, limit, offset)
            
            EVENTS_QUERIED.labels(query_type='event_type').inc()
            
            return {
                "event_type": event_type,
                "events": events,
                "count": len(events),
                "limit": limit,
                "offset": offset
            }

@api.route('/events/correlation/<string:correlation_id>')
class CorrelationEventsResource(Resource):
    @api.doc('get_events_by_correlation')
    def get(self, correlation_id):
        """Récupérer les événements par correlation_id"""
        with QUERY_DURATION.labels(query_type='correlation').time():
            events = event_store_service.get_events_by_correlation_id(correlation_id)
            
            EVENTS_QUERIED.labels(query_type='correlation').inc()
            
            return {
                "correlation_id": correlation_id,
                "events": events,
                "count": len(events)
            }

@api.route('/replay/<string:aggregate_id>')
class ReplayResource(Resource):
    @api.doc('replay_events')
    def get(self, aggregate_id):
        """Rejouer les événements pour reconstituer l'état"""
        with QUERY_DURATION.labels(query_type='replay').time():
            up_to_timestamp = request.args.get('up_to_timestamp')
            
            result = event_store_service.replay_events(aggregate_id, up_to_timestamp)
            
            REPLAYS_PERFORMED.inc()
            
            return result

@api.route('/snapshots/<string:aggregate_id>')
class SnapshotResource(Resource):
    @api.doc('get_snapshot')
    def get(self, aggregate_id):
        """Récupérer le snapshot d'un agrégat"""
        snapshot = event_store_service.get_snapshot(aggregate_id)
        
        if not snapshot:
            return {"error": "Snapshot not found"}, 404
        
        return snapshot
    
    @api.doc('create_snapshot')
    def post(self, aggregate_id):
        """Créer un snapshot à partir de l'état reconstruit"""
        # Rejouer les événements pour obtenir l'état actuel
        replay_result = event_store_service.replay_events(aggregate_id)
        state = replay_result["reconstructed_state"]
        
        # Créer le snapshot
        snapshot_id = event_store_service.create_snapshot(aggregate_id, state)
        
        SNAPSHOTS_CREATED.inc()
        
        return {
            "message": "Snapshot created",
            "aggregate_id": aggregate_id,
            "snapshot_id": snapshot_id,
            "version": len(state.get("history", []))
        }

@api.route('/statistics')
class StatisticsResource(Resource):
    @api.doc('get_event_statistics')
    def get(self):
        """Obtenir les statistiques de l'Event Store"""
        return event_store_service.get_event_statistics()

@app.route('/health')
def health():
    """Endpoint de santé"""
    try:
        # Tester la connexion MongoDB
        event_store_service.mongo_client.admin.command('ping')
        return {"status": "healthy", "service": "event-store-service"}
    except PyMongoError:
        return {"status": "unhealthy", "service": "event-store-service"}, 503

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("Starting Event Store Service", port=8106)
    app.run(host='0.0.0.0', port=8106, debug=False)