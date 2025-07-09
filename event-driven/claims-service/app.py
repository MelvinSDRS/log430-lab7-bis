import os
import uuid
import structlog
from datetime import datetime
from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from event_publisher import EventPublisher
from claims_model import Claim, ClaimStatus, ClaimType

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
EVENTS_PUBLISHED = Counter('events_published_total', 'Total number of events published', ['event_type'])
CLAIMS_CREATED = Counter('claims_created_total', 'Total number of claims created')
CLAIMS_STATUS_CHANGES = Counter('claims_status_changes_total', 'Total number of status changes', ['from_status', 'to_status'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

app = Flask(__name__)
api = Api(app, version='1.0', title='Claims Service API',
          description='Service de gestion des réclamations avec événements',
          doc='/docs/')

# Configuration
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6381/0')
mongo_url = os.getenv('MONGO_URL', 'mongodb://localhost:27017/event_store')

# Initialiser l'event publisher
event_publisher = EventPublisher(redis_url, mongo_url)

# Modèles API
claim_model = api.model('Claim', {
    'customer_id': fields.String(required=True, description='ID du client'),
    'claim_type': fields.String(required=True, enum=['product_defect', 'delivery_issue', 'billing_error', 'service_complaint']),
    'description': fields.String(required=True, description='Description de la réclamation'),
    'product_id': fields.String(description='ID du produit concerné (optionnel)')
})

assignment_model = api.model('Assignment', {
    'agent_id': fields.String(required=True, description='ID de l\'agent assigné')
})

resolution_model = api.model('Resolution', {
    'resolution': fields.String(required=True, description='Résolution de la réclamation')
})

# Stockage en mémoire des réclamations pour cet exemple
claims_store = {}

def reconstruct_claim_from_events(claim_id: str) -> Claim:
    """Reconstruit l'état d'une réclamation à partir des événements"""
    events = event_publisher.get_events_for_aggregate(claim_id)
    
    if not events:
        return None
    
    # Construire l'état à partir des événements
    claim = None
    
    for event in events:
        event_type = event['event_type']
        data = event['data']
        
        if event_type == 'ReclamationCreee':
            claim = Claim(
                claim_id=data['claim_id'],
                customer_id=data['customer_id'],
                claim_type=ClaimType(data['claim_type']),
                description=data['description'],
                product_id=data.get('product_id')
            )
        elif event_type == 'ReclamationAffectee' and claim:
            claim.assign_to_agent(data['agent_id'])
        elif event_type == 'ReclamationEnCours' and claim:
            claim.start_processing()
        elif event_type == 'ReclamationResolue' and claim:
            claim.resolve(data['resolution'])
        elif event_type == 'ReclamationCloturee' and claim:
            claim.close()
    
    return claim

@api.route('/claims')
class ClaimsResource(Resource):
    @api.doc('create_claim')
    @api.expect(claim_model)
    def post(self):
        """Créer une nouvelle réclamation"""
        data = request.get_json()
        claim_id = str(uuid.uuid4())
        
        # Créer la réclamation
        claim = Claim(
            claim_id=claim_id,
            customer_id=data['customer_id'],
            claim_type=ClaimType(data['claim_type']),
            description=data['description'],
            product_id=data.get('product_id')
        )
        
        # Stocker en mémoire
        claims_store[claim_id] = claim
        
        # Publier l'événement
        event_data = claim.to_dict()
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        event_publisher.publish_event(
            event_type='ReclamationCreee',
            aggregate_id=claim_id,
            data=event_data,
            correlation_id=correlation_id
        )
        
        # Métriques
        EVENTS_PUBLISHED.labels(event_type='ReclamationCreee').inc()
        CLAIMS_CREATED.inc()
        
        logger.info(
            "Claim created",
            claim_id=claim_id,
            customer_id=data['customer_id'],
            claim_type=data['claim_type'],
            correlation_id=correlation_id
        )
        
        return {"claim_id": claim_id, "status": "created"}, 201
    
    @api.doc('list_claims')
    def get(self):
        """Lister toutes les réclamations"""
        claims = []
        for claim in claims_store.values():
            claims.append(claim.to_dict())
        return claims

@api.route('/claims/<string:claim_id>')
class ClaimResource(Resource):
    @api.doc('get_claim')
    def get(self, claim_id):
        """Obtenir une réclamation par ID"""
        claim = claims_store.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        return claim.to_dict()
    
    @api.doc('assign_claim')
    @api.expect(assignment_model)
    def post(self, claim_id):
        """Assigner une réclamation à un agent"""
        claim = claims_store.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        
        data = request.get_json()
        agent_id = data['agent_id']
        
        old_status = claim.status
        claim.assign_to_agent(agent_id)
        
        # Publier l'événement
        event_data = {
            "claim_id": claim_id,
            "agent_id": agent_id,
            "assigned_at": datetime.utcnow().isoformat()
        }
        
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        event_publisher.publish_event(
            event_type='ReclamationAffectee',
            aggregate_id=claim_id,
            data=event_data,
            correlation_id=correlation_id
        )
        
        # Métriques
        EVENTS_PUBLISHED.labels(event_type='ReclamationAffectee').inc()
        CLAIMS_STATUS_CHANGES.labels(from_status=old_status.value, to_status=claim.status.value).inc()
        
        logger.info(
            "Claim assigned",
            claim_id=claim_id,
            agent_id=agent_id,
            correlation_id=correlation_id
        )
        
        return {"message": "Claim assigned successfully"}

@api.route('/claims/<string:claim_id>/start')
class ClaimStartResource(Resource):
    @api.doc('start_claim_processing')
    def post(self, claim_id):
        """Commencer le traitement d'une réclamation"""
        claim = claims_store.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        
        if claim.status != ClaimStatus.ASSIGNED:
            return {"error": "Claim must be assigned before processing"}, 400
        
        old_status = claim.status
        claim.start_processing()
        
        # Publier l'événement
        event_data = {
            "claim_id": claim_id,
            "started_at": datetime.utcnow().isoformat()
        }
        
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        event_publisher.publish_event(
            event_type='ReclamationEnCours',
            aggregate_id=claim_id,
            data=event_data,
            correlation_id=correlation_id
        )
        
        # Métriques
        EVENTS_PUBLISHED.labels(event_type='ReclamationEnCours').inc()
        CLAIMS_STATUS_CHANGES.labels(from_status=old_status.value, to_status=claim.status.value).inc()
        
        logger.info(
            "Claim processing started",
            claim_id=claim_id,
            correlation_id=correlation_id
        )
        
        return {"message": "Claim processing started"}

@api.route('/claims/<string:claim_id>/resolve')
class ClaimResolveResource(Resource):
    @api.doc('resolve_claim')
    @api.expect(resolution_model)
    def post(self, claim_id):
        """Résoudre une réclamation"""
        claim = claims_store.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        
        if claim.status != ClaimStatus.IN_PROGRESS:
            return {"error": "Claim must be in progress to be resolved"}, 400
        
        data = request.get_json()
        resolution = data['resolution']
        
        old_status = claim.status
        claim.resolve(resolution)
        
        # Publier l'événement
        event_data = {
            "claim_id": claim_id,
            "resolution": resolution,
            "resolved_at": datetime.utcnow().isoformat()
        }
        
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        event_publisher.publish_event(
            event_type='ReclamationResolue',
            aggregate_id=claim_id,
            data=event_data,
            correlation_id=correlation_id
        )
        
        # Métriques
        EVENTS_PUBLISHED.labels(event_type='ReclamationResolue').inc()
        CLAIMS_STATUS_CHANGES.labels(from_status=old_status.value, to_status=claim.status.value).inc()
        
        logger.info(
            "Claim resolved",
            claim_id=claim_id,
            resolution=resolution,
            correlation_id=correlation_id
        )
        
        return {"message": "Claim resolved successfully"}

@api.route('/claims/<string:claim_id>/close')
class ClaimCloseResource(Resource):
    @api.doc('close_claim')
    def post(self, claim_id):
        """Fermer une réclamation"""
        claim = claims_store.get(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        
        if claim.status != ClaimStatus.RESOLVED:
            return {"error": "Claim must be resolved before closing"}, 400
        
        old_status = claim.status
        claim.close()
        
        # Publier l'événement
        event_data = {
            "claim_id": claim_id,
            "closed_at": datetime.utcnow().isoformat()
        }
        
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        
        event_publisher.publish_event(
            event_type='ReclamationCloturee',
            aggregate_id=claim_id,
            data=event_data,
            correlation_id=correlation_id
        )
        
        # Métriques
        EVENTS_PUBLISHED.labels(event_type='ReclamationCloturee').inc()
        CLAIMS_STATUS_CHANGES.labels(from_status=old_status.value, to_status=claim.status.value).inc()
        
        logger.info(
            "Claim closed",
            claim_id=claim_id,
            correlation_id=correlation_id
        )
        
        return {"message": "Claim closed successfully"}

@api.route('/claims/<string:claim_id>/events')
class ClaimEventsResource(Resource):
    @api.doc('get_claim_events')
    def get(self, claim_id):
        """Obtenir tous les événements d'une réclamation"""
        events = event_publisher.get_events_for_aggregate(claim_id)
        return events

@api.route('/claims/<string:claim_id>/replay')
class ClaimReplayResource(Resource):
    @api.doc('replay_claim_events')
    def get(self, claim_id):
        """Rejouer les événements pour reconstituer l'état d'une réclamation"""
        claim = reconstruct_claim_from_events(claim_id)
        if not claim:
            return {"error": "Claim not found"}, 404
        
        return {
            "claim": claim.to_dict(),
            "reconstructed_from_events": True
        }

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {"status": "healthy", "service": "claims-service"}

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("Starting Claims Service", port=8101)
    app.run(host='0.0.0.0', port=8101, debug=False)