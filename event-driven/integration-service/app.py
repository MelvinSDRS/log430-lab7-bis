import os
import requests
import structlog
from datetime import datetime
from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
import psycopg2

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

app = Flask(__name__)
api = Api(app, version='1.0', title='Integration Service API',
          description='Service d\'intégration entre Lab 6 et Lab 7',
          doc='/docs/')

# Configuration
LAB6_ORDER_SERVICE = os.getenv('LAB6_ORDER_SERVICE', 'http://localhost:8007')
LAB6_CUSTOMER_SERVICE = os.getenv('LAB6_CUSTOMER_SERVICE', 'http://localhost:8005')
LAB7_CLAIMS_SERVICE = os.getenv('LAB7_CLAIMS_SERVICE', 'http://localhost:8101')

# Modèles API
integrated_claim_model = api.model('IntegratedClaim', {
    'order_id': fields.String(required=True, description='ID de la commande (Lab 6)'),
    'claim_type': fields.String(required=True, enum=['product_defect', 'delivery_issue', 'billing_error', 'service_complaint']),
    'description': fields.String(required=True, description='Description de la réclamation'),
    'urgency': fields.String(enum=['low', 'medium', 'high'], default='medium')
})

class IntegrationService:
    def __init__(self):
        self.lab6_available = self._check_lab6_availability()
        
    def _check_lab6_availability(self):
        """Vérifie si les services Lab 6 sont disponibles"""
        try:
            response = requests.get(f"{LAB6_ORDER_SERVICE}/health", timeout=5)
            return response.status_code == 200
        except:
            logger.warning("Lab 6 services not available - working in standalone mode")
            return False
    
    def get_order_details(self, order_id: str):
        """Récupère les détails d'une commande depuis Lab 6"""
        if not self.lab6_available:
            # Mode dégradé - retourner des données simulées
            return {
                "order_id": order_id,
                "customer_id": f"customer_{order_id[-3:]}",
                "status": "delivered",
                "items": [{"product_id": "product_123", "name": "Produit exemple"}],
                "total": 99.99,
                "created_at": "2025-01-01T10:00:00Z",
                "source": "simulated"
            }
        
        try:
            response = requests.get(f"{LAB6_ORDER_SERVICE}/orders/{order_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Order {order_id} not found in Lab 6")
                return None
        except Exception as e:
            logger.error(f"Error fetching order details: {str(e)}")
            return None
    
    def get_customer_details(self, customer_id: str):
        """Récupère les détails d'un client depuis Lab 6"""
        if not self.lab6_available:
            return {
                "customer_id": customer_id,
                "email": f"{customer_id}@example.com",
                "name": f"Client {customer_id}",
                "source": "simulated"
            }
        
        try:
            response = requests.get(f"{LAB6_CUSTOMER_SERVICE}/customers/{customer_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception as e:
            logger.error(f"Error fetching customer details: {str(e)}")
            return None
    
    def create_integrated_claim(self, order_id: str, claim_type: str, description: str, urgency: str = 'medium'):
        """Crée une réclamation avec contexte de commande"""
        # 1. Récupérer le contexte de la commande
        order_details = self.get_order_details(order_id)
        if not order_details:
            raise ValueError(f"Order {order_id} not found")
        
        customer_id = order_details.get('customer_id')
        customer_details = self.get_customer_details(customer_id)
        
        # 2. Enrichir la description avec le contexte
        enriched_description = f"""
RÉCLAMATION LIÉE À UNE COMMANDE

Commande: {order_id}
Client: {customer_id}
Statut commande: {order_details.get('status', 'unknown')}
Produits concernés: {', '.join([item.get('name', 'Unknown') for item in order_details.get('items', [])])}
Montant: {order_details.get('total', 0)} €

Description de la réclamation:
{description}

Urgence: {urgency}
        """.strip()
        
        # 3. Déterminer le product_id si défaut produit
        product_id = None
        if claim_type == 'product_defect' and order_details.get('items'):
            product_id = order_details['items'][0].get('product_id')
        
        # 4. Créer la réclamation dans Lab 7
        claim_data = {
            "customer_id": customer_id,
            "claim_type": claim_type,
            "description": enriched_description,
            "product_id": product_id
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-Correlation-ID": f"integration-{order_id}-{datetime.now().timestamp()}"
        }
        
        response = requests.post(f"{LAB7_CLAIMS_SERVICE}/claims", json=claim_data, headers=headers)
        
        if response.status_code == 201:
            claim_result = response.json()
            
            # 5. Retourner le résultat enrichi
            return {
                "claim_id": claim_result.get("claim_id"),
                "order_context": order_details,
                "customer_context": customer_details,
                "integration_status": "success",
                "lab6_available": self.lab6_available
            }
        else:
            raise Exception(f"Failed to create claim: {response.text}")

integration_service = IntegrationService()

@api.route('/claims/from-order')
class IntegratedClaimResource(Resource):
    @api.doc('create_claim_from_order')
    @api.expect(integrated_claim_model)
    def post(self):
        """Créer une réclamation à partir d'une commande existante"""
        data = request.get_json()
        
        try:
            result = integration_service.create_integrated_claim(
                order_id=data['order_id'],
                claim_type=data['claim_type'],
                description=data['description'],
                urgency=data.get('urgency', 'medium')
            )
            
            logger.info(
                "Integrated claim created",
                claim_id=result.get("claim_id"),
                order_id=data['order_id'],
                customer_id=result.get("order_context", {}).get("customer_id")
            )
            
            return result, 201
            
        except ValueError as e:
            return {"error": str(e)}, 404
        except Exception as e:
            logger.error("Failed to create integrated claim", error=str(e))
            return {"error": "Internal server error"}, 500

@api.route('/orders/<string:order_id>')
class OrderDetailsResource(Resource):
    @api.doc('get_order_details')
    def get(self, order_id):
        """Récupérer les détails d'une commande"""
        order_details = integration_service.get_order_details(order_id)
        
        if order_details:
            return order_details
        else:
            return {"error": "Order not found"}, 404

@api.route('/customers/<string:customer_id>')
class CustomerDetailsResource(Resource):
    @api.doc('get_customer_details')
    def get(self, customer_id):
        """Récupérer les détails d'un client"""
        customer_details = integration_service.get_customer_details(customer_id)
        
        if customer_details:
            return customer_details
        else:
            return {"error": "Customer not found"}, 404

@api.route('/status')
class IntegrationStatusResource(Resource):
    @api.doc('get_integration_status')
    def get(self):
        """Statut de l'intégration entre Lab 6 et Lab 7"""
        return {
            "lab6_available": integration_service.lab6_available,
            "lab7_claims_service": LAB7_CLAIMS_SERVICE,
            "integration_mode": "full" if integration_service.lab6_available else "degraded",
            "endpoints": {
                "create_claim_from_order": "/claims/from-order",
                "order_details": "/orders/{order_id}",
                "customer_details": "/customers/{customer_id}"
            }
        }

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {
        "status": "healthy", 
        "service": "integration-service",
        "lab6_connected": integration_service.lab6_available
    }

if __name__ == '__main__':
    logger.info("Starting Integration Service", port=8107)
    app.run(host='0.0.0.0', port=8107, debug=False)