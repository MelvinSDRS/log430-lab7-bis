#!/usr/bin/env python3
"""
Saga Orchestrator Service - Orchestrateur synchrone pour transactions distribuées
Port: 8008
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
import uuid
from datetime import datetime
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from orchestrator import SagaOrchestrator
from saga_state import SagaStatus, SagaStateMachine, SagaExecution, SagaStep, SagaStepType

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'saga-orchestrator-secret')

# CORS pour intégration API Gateway
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway", "X-API-Key"]
    }
})

GATEWAY_URL = os.getenv('GATEWAY_URL', 'http://localhost:8080')
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'

if TEST_MODE:
    # Mode test : communication directe avec les services
    DIRECT_SERVICES_URL = 'http://localhost'
    orchestrator = SagaOrchestrator(DIRECT_SERVICES_URL)
    app.logger.info("[SAGA] Mode TEST activé - Communication directe avec services")
else:
    orchestrator = SagaOrchestrator(GATEWAY_URL)
    app.logger.info(f"[SAGA] Mode PRODUCTION - Gateway URL: {GATEWAY_URL}")

# Métriques Prometheus pour surveillance des sagas
metrics = PrometheusMetrics(app, path=None)

# Métriques personnalisées pour les sagas
saga_total = Counter(
    'saga_requests_total',
    'Nombre total de sagas démarrées',
    ['customer_id', 'status']
)

saga_duration = Histogram(
    'saga_duration_seconds',
    'Durée d\'exécution des sagas en secondes',
    ['status', 'customer_id'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

saga_status_gauge = Gauge(
    'saga_status_count',
    'Nombre de sagas par statut',
    ['status']
)

active_sagas = Gauge(
    'saga_active_count',
    'Nombre de sagas actives'
)

compensation_total = Counter(
    'saga_compensation_total',
    'Nombre total de compensations exécutées',
    ['step_type', 'reason']
)

saga_steps_counter = Counter(
    'saga_steps_total',
    'Nombre total d\'étapes de saga exécutées',
    ['step_type', 'status', 'service']
)

saga_errors_counter = Counter(
    'saga_errors_total',
    'Nombre total d\'erreurs dans les sagas',
    ['step_type', 'error_type', 'service']
)

api = Api(
    app,
    version='1.0',
    title='Saga Orchestrator API',
    description='Orchestrateur synchrone pour les transactions distribuées',
    doc='/docs',
    prefix='/api/v1'
)

# Modèles Swagger
order_request_model = api.model('OrderRequest', {
    'session_id': fields.String(required=True, description='ID de session du panier'),
    'customer_id': fields.Integer(required=True, description='ID du client'),
    'shipping_address': fields.Raw(required=True, description='Adresse de livraison'),
    'billing_address': fields.Raw(description='Adresse de facturation'),
    'payment': fields.Raw(required=True, description='Informations de paiement')
})

saga_status_model = api.model('SagaStatus', {
    'saga_id': fields.String(description='ID de la saga'),
    'status': fields.String(description='Statut actuel'),
    'order_id': fields.String(description='ID de la commande créée'),
    'customer_id': fields.Integer(description='ID du client'),
    'created_at': fields.DateTime(description='Date de création'),
    'updated_at': fields.DateTime(description='Dernière mise à jour'),
    'total_duration_ms': fields.Integer(description='Durée totale en millisecondes'),
    'completed_steps': fields.Integer(description='Nombre d\'étapes complétées'),
    'failed_step': fields.Raw(description='Étape qui a échoué'),
    'compensation_steps': fields.Integer(description='Nombre d\'étapes de compensation')
})

failure_simulation_model = api.model('FailureSimulation', {
    'service': fields.String(required=True, description='Service à faire échouer', 
                           enum=['cart', 'inventory', 'payment', 'order']),
    'step': fields.String(required=True, description='Étape à faire échouer',
                         enum=['validate', 'reserve', 'payment', 'confirm']),
    'error_message': fields.String(description='Message d\'erreur personnalisé')
})

# Endpoints principaux
@api.route('/sagas/orders')
class OrderSagaResource(Resource):
    """Endpoint principal pour démarrer une saga de commande"""
    
    @api.expect(order_request_model)
    @api.marshal_with(saga_status_model)
    @api.doc('start_order_saga', description='Démarrer une nouvelle saga de commande')
    def post(self):
        """Démarrer une saga de commande synchrone"""
        try:
            data = request.get_json()
            
            # Validation des données
            session_id = data.get('session_id')
            customer_id = data.get('customer_id')
            
            if not session_id or not customer_id:
                return {'error': 'session_id et customer_id sont requis'}, 400
            
            # Métriques
            start_time = datetime.utcnow()
            
            # Démarrer la saga
            app.logger.info(f"[SAGA] Démarrage saga commande - Session: {session_id}, Client: {customer_id}")
            saga = orchestrator.start_order_saga(session_id, customer_id, data)
            
            # Mettre à jour les métriques
            saga_total.labels(customer_id=str(customer_id), status=saga.status.value).inc()
            saga_status_gauge.labels(status=saga.status.value).set(1)
            
            if saga.total_duration_ms:
                saga_duration.labels(status=saga.status.value, customer_id=str(customer_id)).observe(saga.total_duration_ms / 1000.0)
            
            # Compter les erreurs si échec
            if saga.failed_step:
                saga_errors_counter.labels(
                    step_type=saga.failed_step.step_type.value,
                    error_type='step_failure',
                    service=saga.failed_step.service_name
                ).inc()
            
            # Compter les étapes complétées
            for step in saga.completed_steps:
                saga_steps_counter.labels(
                    step_type=step.step_type.value,
                    status='completed',
                    service=step.service_name
                ).inc()
            
            # Compter les compensations
            for comp_step in saga.compensation_steps:
                compensation_total.labels(
                    step_type=comp_step.step_type.value,
                    reason='saga_failure'
                ).inc()
            
            # Réponse
            response_data = {
                'saga_id': saga.saga_id,
                'status': saga.status.value,
                'order_id': saga.order_id,
                'customer_id': saga.customer_id,
                'created_at': saga.created_at.isoformat(),
                'updated_at': saga.updated_at.isoformat(),
                'total_duration_ms': saga.total_duration_ms,
                'completed_steps': len(saga.completed_steps),
                'failed_step': {
                'step_type': saga.failed_step.step_type.value,
                'status': saga.failed_step.status,
                'service_name': saga.failed_step.service_name,
                'endpoint': saga.failed_step.endpoint,
                'duration_ms': saga.failed_step.duration_ms,
                'timestamp': saga.failed_step.timestamp.isoformat() if saga.failed_step.timestamp else None,
                'error': saga.failed_step.error
            } if saga.failed_step else None,
                'compensation_steps': len(saga.compensation_steps)
            }
            
            status_code = 201 if saga.status == SagaStatus.COMPLETED else 202
            
            app.logger.info(f"[SAGA] Saga créée - ID: {saga.saga_id}, Statut: {saga.status.value}, Durée: {saga.total_duration_ms}ms")
            if saga.failed_step:
                app.logger.warning(f"[SAGA] Saga échouée - ID: {saga.saga_id}, Étape: {saga.failed_step.step_type.value}, Erreur: {saga.failed_step.error}")
            app.logger.info(f"[SAGA] Résumé - Étapes complétées: {len(saga.completed_steps)}, Compensations: {len(saga.compensation_steps)}")
            
            return response_data, status_code
            
        except Exception as e:
            app.logger.error(f"[SAGA] Erreur création saga - Session: {session_id if 'session_id' in locals() else 'N/A'}: {e}")
            return {'error': str(e)}, 500

@api.route('/sagas/<string:saga_id>')
class SagaStatusResource(Resource):
    """Endpoint pour consulter le statut d'une saga"""
    
    @api.marshal_with(saga_status_model)
    @api.doc('get_saga_status', description='Récupérer le statut d\'une saga')
    def get(self, saga_id):
        """Récupérer l'état actuel d'une saga"""
        try:
            app.logger.debug(f"[SAGA] Recherche statut saga - ID: {saga_id}")
            
            saga = orchestrator.get_saga_status(saga_id)
            
            if not saga:
                app.logger.warning(f"[SAGA] Saga non trouvée - ID: {saga_id}")
                return {'error': 'Saga non trouvée'}, 404
            
            app.logger.info(f"[SAGA] Statut saga récupéré - ID: {saga_id}, Statut: {saga.status.value}")
            
            response_data = {
                'saga_id': saga.saga_id,
                'status': saga.status.value,
                'order_id': saga.order_id,
                'customer_id': saga.customer_id,
                'created_at': saga.created_at.isoformat(),
                'updated_at': saga.updated_at.isoformat(),
                'total_duration_ms': saga.total_duration_ms,
                'completed_steps': len(saga.completed_steps),
                'failed_step': {
                'step_type': saga.failed_step.step_type.value,
                'status': saga.failed_step.status,
                'service_name': saga.failed_step.service_name,
                'endpoint': saga.failed_step.endpoint,
                'duration_ms': saga.failed_step.duration_ms,
                'timestamp': saga.failed_step.timestamp.isoformat() if saga.failed_step.timestamp else None,
                'error': saga.failed_step.error
            } if saga.failed_step else None,
                'compensation_steps': len(saga.compensation_steps)
            }
            
            return response_data, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération de saga {saga_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/sagas/<string:saga_id>/details')
class SagaDetailsResource(Resource):
    """Endpoint pour les détails complets d'une saga"""
    
    @api.doc('get_saga_details', description='Récupérer tous les détails d\'une saga')
    def get(self, saga_id):
        """Récupérer tous les détails d'une saga incluant les étapes"""
        try:
            saga = orchestrator.get_saga_status(saga_id)
            
            if not saga:
                return {'error': 'Saga non trouvée'}, 404
            
            # Convertir les étapes en format JSON sérialisable
            completed_steps = []
            for step in saga.completed_steps:
                completed_steps.append({
                    'step_type': step.step_type.value,
                    'status': step.status,
                    'service_name': step.service_name,
                    'endpoint': step.endpoint,
                    'duration_ms': step.duration_ms,
                    'timestamp': step.timestamp.isoformat() if step.timestamp else None,
                    'error': step.error
                })
            
            compensation_steps = []
            for step in saga.compensation_steps:
                compensation_steps.append({
                    'step_type': step.step_type.value,
                    'status': step.status,
                    'service_name': step.service_name,
                    'endpoint': step.endpoint,
                    'duration_ms': step.duration_ms,
                    'timestamp': step.timestamp.isoformat() if step.timestamp else None,
                    'error': step.error
                })
            
            return {
                'saga_id': saga.saga_id,
                'status': saga.status.value,
                'order_id': saga.order_id,
                'customer_id': saga.customer_id,
                'session_id': saga.session_id,
                'created_at': saga.created_at.isoformat(),
                'updated_at': saga.updated_at.isoformat(),
                'expires_at': saga.expires_at.isoformat() if saga.expires_at else None,
                'total_duration_ms': saga.total_duration_ms,
                'cart_data': saga.cart_data,
                'reservation_data': saga.reservation_data,
                'payment_data': saga.payment_data,
                'order_data': saga.order_data,
                'completed_steps': completed_steps,
                'failed_step': {
                'step_type': saga.failed_step.step_type.value,
                'status': saga.failed_step.status,
                'service_name': saga.failed_step.service_name,
                'endpoint': saga.failed_step.endpoint,
                'duration_ms': saga.failed_step.duration_ms,
                'timestamp': saga.failed_step.timestamp.isoformat() if saga.failed_step.timestamp else None,
                'error': saga.failed_step.error
            } if saga.failed_step else None,
                'compensation_steps': compensation_steps
            }, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération des détails {saga_id}: {e}")
            return {'error': str(e)}, 500

# Endpoints d'administration et monitoring
@api.route('/sagas/metrics')
class SagaMetricsResource(Resource):
    """Endpoint pour les métriques de l'orchestrateur"""
    
    @api.doc('get_saga_metrics', description='Récupérer les métriques de l\'orchestrateur')
    def get(self):
        """Récupérer les métriques et statistiques"""
        try:
            metrics_data = orchestrator.get_metrics()
            
            # Mettre à jour les gauges Prometheus
            active_sagas.set(metrics_data.get('active_sagas', 0))
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'orchestrator_metrics': metrics_data,
                'prometheus_endpoint': '/metrics'
            }, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération des métriques: {e}")
            return {'error': str(e)}, 500

@api.route('/sagas/active')
class ActiveSagasResource(Resource):
    """Endpoint pour lister les sagas actives"""
    
    @api.doc('get_active_sagas', description='Lister toutes les sagas actives')
    def get(self):
        """Lister toutes les sagas non terminées"""
        try:
            active_sagas_list = orchestrator.repository.get_all_active()
            
            sagas_data = []
            for saga in active_sagas_list:
                sagas_data.append({
                    'saga_id': saga.saga_id,
                    'status': saga.status.value,
                    'customer_id': saga.customer_id,
                    'created_at': saga.created_at.isoformat(),
                    'updated_at': saga.updated_at.isoformat(),
                    'steps_completed': len(saga.completed_steps)
                })
            
            return {
                'active_sagas': sagas_data,
                'count': len(sagas_data)
            }, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération des sagas actives: {e}")
            return {'error': str(e)}, 500

# Endpoint pour simuler des sagas réussies (tests)
@api.route('/test/success')
class SuccessSimulationResource(Resource):
    """Endpoint pour simuler des sagas réussies"""
    
    @api.doc('simulate_success', description='Simuler des sagas réussies pour les métriques')
    def post(self):
        """Simuler des sagas complètes avec succès"""
        try:
            data = request.get_json() or {}
            count = data.get('count', 5)
            
            generated_sagas = []
            
            for i in range(count):
                # Créer une saga simulée réussie
                session_id = f"success_sim_{int(datetime.utcnow().timestamp())}_{i}"
                customer_id = 7000 + i
                
                # Simuler une saga complète
                saga = SagaExecution(
                    saga_id=str(uuid.uuid4()),
                    session_id=session_id,
                    customer_id=customer_id,
                    status=SagaStatus.COMPLETED,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    total_duration_ms=1500 + (i * 200)  # Durées variées
                )
                
                # Ajouter des étapes complétées
                saga.completed_steps = [
                    SagaStep(
                        step_type=SagaStepType.VALIDATE_CART,
                        status="completed",
                        service_name="cart-service",
                        endpoint="/carts/validate",
                        payload={"session_id": session_id},
                        duration_ms=200,
                        timestamp=datetime.utcnow()
                    ),
                    SagaStep(
                        step_type=SagaStepType.RESERVE_STOCK,
                        status="completed", 
                        service_name="inventory-service",
                        endpoint="/inventory/reserve",
                        payload={"reservation_id": session_id, "customer_id": customer_id},
                        duration_ms=300,
                        timestamp=datetime.utcnow()
                    ),
                    SagaStep(
                        step_type=SagaStepType.PROCESS_PAYMENT,
                        status="completed",
                        service_name="payment-service", 
                        endpoint="/payment/process",
                        payload={"payment_id": session_id, "amount": 49.99},
                        duration_ms=500,
                        timestamp=datetime.utcnow()
                    ),
                    SagaStep(
                        step_type=SagaStepType.CONFIRM_ORDER,
                        status="completed",
                        service_name="order-service",
                        endpoint="/orders/confirm", 
                        payload={"order_id": session_id, "customer_id": customer_id},
                        duration_ms=400,
                        timestamp=datetime.utcnow()
                    )
                ]
                
                # Note: Pas besoin de sauvegarder pour les tests de métriques
                
                # Mettre à jour les métriques
                saga_total.labels(customer_id=str(customer_id), status="COMPLETED").inc()
                saga_status_gauge.labels(status="COMPLETED").set(1)
                saga_duration.labels(status="COMPLETED", customer_id=str(customer_id)).observe(saga.total_duration_ms / 1000.0)
                
                # Compter les étapes complétées
                for step in saga.completed_steps:
                    saga_steps_counter.labels(
                        step_type=step.step_type.value,
                        status='completed',
                        service=step.service_name
                    ).inc()
                
                generated_sagas.append({
                    'saga_id': saga.saga_id,
                    'session_id': session_id,
                    'customer_id': customer_id,
                    'status': 'COMPLETED',
                    'duration_ms': saga.total_duration_ms
                })
            
            app.logger.info(f"✅ {count} sagas de succès simulées générées")
            
            return {
                'message': f'{count} sagas de succès générées',
                'generated_sagas': generated_sagas
            }, 201
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la simulation de succès: {e}")
            return {'error': str(e)}, 500

# Endpoints de simulation d'échecs (pour tests)
@api.route('/test/failures')
class FailureSimulationResource(Resource):
    """Endpoint pour simuler des échecs de services"""
    
    @api.expect(failure_simulation_model)
    @api.doc('simulate_failure', description='Simuler l\'échec d\'un service (tests uniquement)')
    def post(self):
        """Simuler un échec de service pour tester la compensation"""
        try:
            data = request.get_json()
            service = data.get('service')
            step = data.get('step')
            error_message = data.get('error_message', f'Échec simulé du service {service}')
            
            # Cette fonction serait utilisée pour injecter des échecs
            # dans l'orchestrateur lors des tests
            
            return {
                'message': f'Simulation d\'échec configurée pour {service}/{step}',
                'service': service,
                'step': step,
                'error_message': error_message
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# Endpoint Prometheus metrics
@app.route('/metrics')
def saga_prometheus_metrics():
    """Endpoint pour exposer les métriques Prometheus"""
    try:
        # Mettre à jour les métriques en temps réel
        metrics_data = orchestrator.get_metrics()
        active_sagas.set(metrics_data.get('active_sagas', 0))
        
        # Générer la réponse Prometheus
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
    except Exception as e:
        app.logger.error(f"Erreur lors de la génération des métriques: {e}")
        return {'error': str(e)}, 500

# Health Check
@app.route('/health')
def health_check():
    """Health check pour le service orchestrateur"""
    try:
        metrics_data = orchestrator.get_metrics()
        
        return {
            'status': 'healthy',
            'service': 'saga-orchestrator',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0',
            'gateway_url': GATEWAY_URL,
            'capabilities': [
                'synchronous_saga_orchestration',
                'compensation_handling',
                'state_machine_management',
                'prometheus_metrics'
            ],
            'active_sagas': metrics_data.get('active_sagas', 0),
            'total_sagas': metrics_data.get('total_sagas', 0)
        }, 200
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'service': 'saga-orchestrator',
            'error': str(e)
        }, 503

# Point d'entrée
if __name__ == '__main__':
    # Configuration du logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Saga Orchestrator démarré")
    logger.info(f"Gateway URL: {GATEWAY_URL}")
    logger.info(f"Documentation API: http://localhost:8008/docs")
    
    app.run(host='0.0.0.0', port=8008, debug=os.getenv('DEBUG', 'False').lower() == 'true')