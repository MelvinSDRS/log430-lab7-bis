import json
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import redis
import structlog
from pymongo import MongoClient

logger = structlog.get_logger()

class EventPublisher:
    def __init__(self, redis_url: str, mongo_url: str):
        self.redis_client = redis.from_url(redis_url)
        
        # Essayer de se connecter à MongoDB
        try:
            self.mongo_client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            # Test de connexion
            self.mongo_client.admin.command('ping')
            self.event_store = self.mongo_client.event_store.events
            
            # Créer les indexes pour optimiser les requêtes
            self.event_store.create_index("aggregate_id")
            self.event_store.create_index("event_type")
            self.event_store.create_index("timestamp")
            self.event_store.create_index("correlation_id")
            self.mongo_available = True
            logger.info("MongoDB connected successfully")
        except Exception as e:
            logger.warning(f"MongoDB not available, running in degraded mode: {e}")
            self.mongo_client = None
            self.event_store = None
            self.mongo_available = False
        
    def publish_event(self, 
                     event_type: str, 
                     aggregate_id: str, 
                     data: Dict[str, Any], 
                     correlation_id: Optional[str] = None) -> str:
        """Publie un événement dans Redis Streams et l'Event Store"""
        
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        event = {
            "event_id": event_id,
            "event_type": event_type,
            "aggregate_id": aggregate_id,
            "data": data,
            "timestamp": timestamp,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "service": "refund-inventory-service"
        }
        
        try:
            # Sauvegarder dans l'Event Store (MongoDB) si disponible
            if self.mongo_available and self.event_store is not None:
                self.event_store.insert_one(event.copy())
            
            # Publier dans Redis Streams (sérialiser les données)
            redis_event = {}
            for key, value in event.items():
                if isinstance(value, dict):
                    redis_event[key] = json.dumps(value)
                else:
                    redis_event[key] = str(value)
            
            stream_name = f"events:{event_type.lower()}"
            self.redis_client.xadd(stream_name, redis_event)
            
            # Publier aussi dans un stream global pour les auditeurs
            self.redis_client.xadd("events:all", redis_event)
            
            logger.info(
                "Event published",
                event_id=event_id,
                event_type=event_type,
                aggregate_id=aggregate_id,
                correlation_id=event["correlation_id"]
            )
            
            return event_id
            
        except Exception as e:
            logger.error(
                "Failed to publish event",
                event_type=event_type,
                aggregate_id=aggregate_id,
                error=str(e)
            )
            raise