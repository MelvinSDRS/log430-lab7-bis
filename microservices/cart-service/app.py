#!/usr/bin/env python3
"""
Cart Service - Microservice pour gestion du panier e-commerce
Support multi-instances pour load balancing
"""

from flask import Flask, request
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
from datetime import datetime
import socket
import time
from services import CartService, TaxService
from redis_client import get_redis_client

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'cart-service-secret')

# CORS pour intégration API Gateway
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway"]
    }
})

# Configuration multi-instances
INSTANCE_ID = os.getenv('INSTANCE_ID', 'cart-default')
SERVICE_NAME = os.getenv('SERVICE_NAME', 'cart-service')
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# API Documentation
api = Api(
    app,
    version='1.0',
    title=f'Cart Service API - Instance {INSTANCE_ID}',
    description=f'Service de gestion du panier e-commerce - Instance {INSTANCE_ID}',
    doc='/docs',
    prefix='/api/v1'
)

# Modèles Swagger
cart_item_model = api.model('CartItem', {
    'product_id': fields.Integer(required=True, description='ID du produit'),
    'product_name': fields.String(description='Nom du produit'),
    'product_sku': fields.String(description='SKU du produit'),
    'price': fields.Float(required=True, description='Prix unitaire'),
    'quantity': fields.Integer(required=True, description='Quantité'),
    'subtotal': fields.Float(description='Sous-total (prix × quantité)'),
    'instance_info': fields.Raw(description='Informations de l\'instance (Load Balancing)')
})

cart_model = api.model('Cart', {
    'session_id': fields.String(description='ID de session'),
    'customer_id': fields.Integer(description='ID du client (si connecté)'),
    'items': fields.List(fields.Nested(cart_item_model), description='Articles du panier'),
    'total_items': fields.Integer(description='Nombre total d\'articles'),
    'total_amount': fields.Float(description='Montant total'),
    'tax_amount': fields.Float(description='Montant des taxes'),
    'final_amount': fields.Float(description='Montant final (TTC)'),
    'currency': fields.String(description='Devise'),
    'created_at': fields.DateTime(description='Date de création'),
    'updated_at': fields.DateTime(description='Dernière mise à jour'),
    'expires_at': fields.DateTime(description='Date d\'expiration'),
    'instance_info': fields.Raw(description='Informations de l\'instance (Load Balancing)')
})

add_item_model = api.model('AddItem', {
    'product_id': fields.Integer(required=True, description='ID du produit'),
    'quantity': fields.Integer(required=True, description='Quantité à ajouter'),
    'price': fields.Float(description='Prix unitaire (optionnel)')
})

update_item_model = api.model('UpdateItem', {
    'quantity': fields.Integer(required=True, description='Nouvelle quantité')
})

# Import des services métier
from services import CartService, TaxService
from redis_client import get_redis_client

# Initialisation de Redis
redis_client = get_redis_client()

def init_app():
    """Initialiser l'application avec Redis"""
    global redis_client
    redis_client = get_redis_client()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.logger.info("Cart Service démarré sur le port 8006")

# Endpoints Panier
@api.route('/carts/<string:session_id>')
class Cart(Resource):
    @api.marshal_with(cart_model)
    @api.doc('get_cart', description='Récupérer le panier d\'une session')
    def get(self, session_id):
        """Récupérer le contenu du panier"""
        try:
            cart_service = CartService(redis_client)
            cart = cart_service.get_cart(session_id)
            
            if not cart:
                # Créer un panier vide
                cart = cart_service.create_empty_cart(session_id)
            
            # Ajout des informations d'instance pour debugging load balancing
            cart['instance_info'] = {
                'served_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return cart
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.doc('clear_cart', description='Vider le panier')
    def delete(self, session_id):
        """Vider complètement le panier"""
        try:
            cart_service = CartService(redis_client)
            success = cart_service.clear_cart(session_id)
            
            if success:
                app.logger.info(f"Panier vidé: {session_id}")
                return {'message': 'Panier vidé avec succès'}, 200
            else:
                api.abort(404, f"Panier {session_id} non trouvé")
                
        except Exception as e:
            app.logger.error(f"Erreur lors du vidage du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/carts/<string:session_id>/items')
class CartItems(Resource):
    @api.expect(add_item_model)
    @api.marshal_with(cart_model)
    @api.doc('add_item_to_cart', description='Ajouter un article au panier')
    def post(self, session_id):
        """Ajouter un article au panier"""
        try:
            data = request.get_json()
            cart_service = CartService(redis_client)
            
            # Validation des données
            if not data.get('product_id') or not data.get('quantity'):
                api.abort(400, "product_id et quantity sont requis")
            
            if data['quantity'] <= 0:
                api.abort(400, "La quantité doit être positive")
            
            # Ajouter l'article au panier
            cart = cart_service.add_item_to_cart(
                session_id,
                data['product_id'],
                data['quantity'],
                data.get('price')
            )
            
            app.logger.info(f"Article ajouté au panier {session_id}: produit {data['product_id']} × {data['quantity']}")
            
            # Ajout des informations d'instance
            cart['instance_info'] = {
                'processed_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'operation': 'add_item_to_cart'
            }
            
            return cart, 201
            
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"Erreur lors de l'ajout d'article au panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/carts/<string:session_id>/items/<int:product_id>')
class CartItem(Resource):
    @api.expect(update_item_model)
    @api.marshal_with(cart_model)
    @api.doc('update_cart_item', description='Mettre à jour la quantité d\'un article')
    def put(self, session_id, product_id):
        """Mettre à jour la quantité d'un article dans le panier"""
        try:
            data = request.get_json()
            cart_service = CartService(redis_client)
            
            if not data.get('quantity') or data['quantity'] < 0:
                api.abort(400, "La quantité doit être >= 0")
            
            cart = cart_service.update_item_quantity(
                session_id,
                product_id,
                data['quantity']
            )
            
            if not cart:
                api.abort(404, f"Article {product_id} non trouvé dans le panier")
            
            app.logger.info(f"Quantité mise à jour dans panier {session_id}: produit {product_id} → {data['quantity']}")
            
            # Ajout des informations d'instance
            cart['instance_info'] = {
                'processed_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'operation': 'update_item_quantity'
            }
            
            return cart
            
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"Erreur lors de la mise à jour du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.marshal_with(cart_model)
    @api.doc('remove_cart_item', description='Retirer un article du panier')
    def delete(self, session_id, product_id):
        """Retirer un article du panier"""
        try:
            cart_service = CartService(redis_client)
            cart = cart_service.remove_item_from_cart(session_id, product_id)
            
            if not cart:
                api.abort(404, f"Article {product_id} non trouvé dans le panier")
            
            app.logger.info(f"Article retiré du panier {session_id}: produit {product_id}")
            
            # Ajout des informations d'instance
            cart['instance_info'] = {
                'processed_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'operation': 'remove_item_from_cart'
            }
            
            return cart
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la suppression d'article du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Endpoints Calculs et taxes
@api.route('/carts/<string:session_id>/calculate')
class CartCalculation(Resource):
    @api.marshal_with(cart_model)
    @api.doc('calculate_cart', description='Recalculer les totaux du panier')
    def post(self, session_id):
        """Recalculer tous les totaux du panier (avec taxes)"""
        try:
            cart_service = CartService(redis_client)
            tax_service = TaxService()
            
            cart = cart_service.get_cart(session_id)
            if not cart:
                api.abort(404, f"Panier {session_id} non trouvé")
            
            # Recalculer avec les taxes
            cart = cart_service.recalculate_cart(session_id, tax_service)
            
            app.logger.info(f"Panier recalculé: {session_id} - Total: {cart['final_amount']}$")
            
            # Ajout des informations d'instance
            cart['instance_info'] = {
                'calculated_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'operation': 'recalculate_cart'
            }
            
            return cart
            
        except Exception as e:
            app.logger.error(f"Erreur lors du calcul du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Endpoints Gestion des sessions
@api.route('/carts/<string:session_id>/customer/<int:customer_id>')
class CartCustomerAssociation(Resource):
    @api.marshal_with(cart_model)
    @api.doc('associate_cart_to_customer', description='Associer le panier à un client connecté')
    def put(self, session_id, customer_id):
        """Associer un panier à un client connecté"""
        try:
            cart_service = CartService(redis_client)
            cart = cart_service.associate_cart_to_customer(session_id, customer_id)
            
            if not cart:
                api.abort(404, f"Panier {session_id} non trouvé")
            
            app.logger.info(f"Panier {session_id} associé au client {customer_id}")
            
            # Ajout des informations d'instance
            cart['instance_info'] = {
                'processed_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'operation': 'associate_cart_to_customer'
            }
            
            return cart
            
        except Exception as e:
            app.logger.error(f"Erreur lors de l'association du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/carts/<string:session_id>/extend')
class CartExtension(Resource):
    @api.marshal_with(cart_model)
    @api.doc('extend_cart_expiry', description='Prolonger la durée de vie du panier')
    def post(self, session_id):
        """Prolonger la durée de vie du panier"""
        try:
            hours = int(request.args.get('hours', 24))
            cart_service = CartService(redis_client)
            cart = cart_service.extend_cart_expiry(session_id, hours)
            
            if not cart:
                api.abort(404, f"Panier {session_id} non trouvé")
            
            app.logger.info(f"Durée de vie du panier {session_id} prolongée de {hours}h")
            
            # Ajout des informations d'instance
            cart['instance_info'] = {
                'processed_by': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'operation': 'extend_cart_expiry'
            }
            
            return cart
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la prolongation du panier {session_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Endpoints d'administration
@api.route('/carts/expired')
class ExpiredCarts(Resource):
    @api.doc('cleanup_expired_carts', description='Nettoyer les paniers expirés')
    def delete(self):
        """Nettoyer les paniers expirés (endpoint admin)"""
        try:
            cart_service = CartService(redis_client)
            cleaned_count = cart_service.cleanup_expired_carts()
            
            app.logger.info(f"Nettoyage effectué: {cleaned_count} paniers expirés supprimés")
            return {
                'message': f'{cleaned_count} paniers expirés supprimés',
                'cleaned_count': cleaned_count
            }, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors du nettoyage des paniers expirés: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Health Check
@api.route('/health')
class HealthCheck(Resource):
    def get(self):
        """Health check avec informations d'instance"""
        try:
            # Test connexion Redis
            redis_client.ping()
            
            # Informations d'instance pour load balancing
            instance_info = {
                'instance_id': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'redis_status': 'connected',
                'uptime_seconds': time.time() - app.start_time if hasattr(app, 'start_time') else 0
            }
            
            return {
                'status': 'healthy',
                'service': f'Cart Service - {INSTANCE_ID}',
                'version': '1.0',
                'instance': instance_info
            }, 200
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'service': f'Cart Service - {INSTANCE_ID}',
                'error': str(e),
                'instance_id': INSTANCE_ID
            }, 503

# Metrics
@api.route('/metrics/instance')
class InstanceMetrics(Resource):
    def get(self):
        """Métriques spécifiques à cette instance pour load balancing"""
        try:
            # Statistiques Redis pour cette instance
            redis_info = redis_client.info()
            
            # Métriques de charge locale
            cart_keys = redis_client.keys(f"cart:*")
            active_sessions = len(cart_keys)
            
            return {
                'instance_id': INSTANCE_ID,
                'service_name': SERVICE_NAME,
                'hostname': socket.gethostname(),
                'timestamp': datetime.utcnow().isoformat(),
                'metrics': {
                    'active_carts': active_sessions,
                    'redis_connected_clients': redis_info.get('connected_clients', 0),
                    'redis_used_memory': redis_info.get('used_memory', 0),
                    'redis_keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'redis_keyspace_misses': redis_info.get('keyspace_misses', 0)
                },
                'load_balancing': {
                    'ready_for_traffic': True,
                    'weight': 100,
                    'algorithm': 'least-connections'
                }
            }, 200
            
        except Exception as e:
            return {
                'error': str(e),
                'instance_id': INSTANCE_ID
            }, 500

# Point d'entrée
if __name__ == '__main__':
    # Enregistrement du temps de démarrage pour uptime
    app.start_time = time.time()
    
    print(f"🚀 Démarrage Cart Service - Instance {INSTANCE_ID}")
    print(f"🏷️  Service Name: {SERVICE_NAME}")
    print(f"🔗 Redis URL: {REDIS_URL}")
    print(f"💻 Hostname: {socket.gethostname()}")
    print(f"🌐 Load Balancing: Prêt pour distribution de charge")
    
    init_app()
    app.run(host='0.0.0.0', port=8006, debug=True) 