import os
import time
import threading
from datetime import datetime
from typing import Dict, Any

import structlog
from flask import Flask, jsonify
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
NOTIFICATIONS_SENT = Counter('notifications_sent_total', 'Total number of notifications sent', ['notification_type', 'event_type'])
EVENTS_PROCESSED = Counter('events_processed_total', 'Total number of events processed', ['event_type'])
PROCESSING_DURATION = Histogram('event_processing_duration_seconds', 'Event processing duration', ['event_type'])

app = Flask(__name__)
api = Api(app, version='1.0', title='Notification Service API',
          description='Service de notifications événementielles',
          doc='/docs/')

# Configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6381/0')
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')

# Stockage des notifications envoyées
notifications_store = []

class NotificationService:
    def __init__(self):
        self.mongo_client = MongoClient(mongo_url)
        self.notifications_collection = self.mongo_client.event_store.notifications
        
    def send_email_notification(self, recipient: str, subject: str, body: str, event_data: Dict[str, Any]):
        """Simule l'envoi d'un email"""
        notification = {
            "notification_id": f"notif_{int(time.time())}",
            "type": "email",
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "event_data": event_data,
            "sent_at": datetime.utcnow().isoformat(),
            "status": "sent"
        }
        
        # Sauvegarder la notification
        self.notifications_collection.insert_one(notification.copy())
        notifications_store.append(notification)
        
        logger.info(
            "Email notification sent",
            recipient=recipient,
            subject=subject,
            event_id=event_data.get('event_id'),
            correlation_id=event_data.get('correlation_id')
        )
        
        return notification
        
    def send_sms_notification(self, phone: str, message: str, event_data: Dict[str, Any]):
        """Simule l'envoi d'un SMS"""
        notification = {
            "notification_id": f"sms_{int(time.time())}",
            "type": "sms",
            "phone": phone,
            "message": message,
            "event_data": event_data,
            "sent_at": datetime.utcnow().isoformat(),
            "status": "sent"
        }
        
        # Sauvegarder la notification
        self.notifications_collection.insert_one(notification.copy())
        notifications_store.append(notification)
        
        logger.info(
            "SMS notification sent",
            phone=phone,
            message=message,
            event_id=event_data.get('event_id'),
            correlation_id=event_data.get('correlation_id')
        )
        
        return notification

# Initialiser le service de notifications
notification_service = NotificationService()

def handle_reclamation_creee(event_data: Dict[str, Any]):
    """Traite l'événement ReclamationCreee"""
    with PROCESSING_DURATION.labels(event_type='ReclamationCreee').time():
        try:
            claim_data = event_data.get('data', {})
            if isinstance(claim_data, str):
                import json
                claim_data = json.loads(claim_data)
            
            customer_id = claim_data.get('customer_id')
            claim_id = claim_data.get('claim_id')
            description = claim_data.get('description')
            
            # Envoyer notification email au client
            notification_service.send_email_notification(
                recipient=f"customer_{customer_id}@example.com",
                subject=f"Réclamation #{claim_id} créée",
                body=f"Votre réclamation a été créée avec succès.\n\nDescription: {description}\n\nNous vous tiendrons informé du traitement.",
                event_data=event_data
            )
            
            # Envoyer notification SMS au client
            notification_service.send_sms_notification(
                phone=f"+33123456{customer_id}",
                message=f"Réclamation #{claim_id} créée. Vous recevrez un email de confirmation.",
                event_data=event_data
            )
            
            # Métriques
            NOTIFICATIONS_SENT.labels(notification_type='email', event_type='ReclamationCreee').inc()
            NOTIFICATIONS_SENT.labels(notification_type='sms', event_type='ReclamationCreee').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationCreee').inc()
            
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
                import json
                data = json.loads(data)
            
            agent_id = data.get('agent_id')
            
            # Notification à l'agent
            notification_service.send_email_notification(
                recipient=f"agent_{agent_id}@company.com",
                subject=f"Réclamation #{claim_id} assignée",
                body=f"Une nouvelle réclamation vous a été assignée.\n\nRéclamation: {claim_id}\n\nVeuillez la traiter dans les plus brefs délais.",
                event_data=event_data
            )
            
            # Métriques
            NOTIFICATIONS_SENT.labels(notification_type='email', event_type='ReclamationAffectee').inc()
            EVENTS_PROCESSED.labels(event_type='ReclamationAffectee').inc()
            
        except Exception as e:
            logger.error(
                "Error handling ReclamationAffectee event",
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
                import json
                data = json.loads(data)
            
            resolution = data.get('resolution')
            
            # Notification au client (on simule en récupérant le customer_id)
            notification_service.send_email_notification(
                recipient=f"customer@example.com",
                subject=f"Réclamation #{claim_id} résolue",
                body=f"Votre réclamation a été résolue.\n\nRésolution: {resolution}\n\nMerci pour votre patience.",
                event_data=event_data
            )
            
            # Métriques
            NOTIFICATIONS_SENT.labels(notification_type='email', event_type='ReclamationResolue').inc()
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
            
            # Notification finale au client
            notification_service.send_email_notification(
                recipient=f"customer@example.com",
                subject=f"Réclamation #{claim_id} clôturée",
                body=f"Votre réclamation a été clôturée.\n\nMerci d'avoir utilisé nos services.",
                event_data=event_data
            )
            
            # Métriques
            NOTIFICATIONS_SENT.labels(notification_type='email', event_type='ReclamationCloturee').inc()
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
    consumer_group='notification-service',
    consumer_name='notification-worker-1'
)

# Enregistrer les handlers
event_consumer.register_handler('ReclamationCreee', handle_reclamation_creee)
event_consumer.register_handler('ReclamationAffectee', handle_reclamation_affectee)
event_consumer.register_handler('ReclamationResolue', handle_reclamation_resolue)
event_consumer.register_handler('ReclamationCloturee', handle_reclamation_cloturee)

@api.route('/notifications')
class NotificationsResource(Resource):
    @api.doc('list_notifications')
    def get(self):
        """Lister toutes les notifications envoyées"""
        return notifications_store

@api.route('/notifications/stats')
class NotificationStatsResource(Resource):
    @api.doc('get_notification_stats')
    def get(self):
        """Obtenir les statistiques des notifications"""
        stats = {
            "total_notifications": len(notifications_store),
            "by_type": {},
            "by_event_type": {}
        }
        
        for notification in notifications_store:
            notif_type = notification.get('type')
            stats['by_type'][notif_type] = stats['by_type'].get(notif_type, 0) + 1
            
            event_type = notification.get('event_data', {}).get('event_type')
            if event_type:
                stats['by_event_type'][event_type] = stats['by_event_type'].get(event_type, 0) + 1
        
        return stats

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {"status": "healthy", "service": "notification-service"}

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
    
    logger.info("Starting Notification Service", port=8102)
    app.run(host='0.0.0.0', port=8102, debug=False)