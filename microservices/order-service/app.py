#!/usr/bin/env python3
"""
Order Service - Microservice pour la gestion des commandes e-commerce
Port: 8007
Responsabilité: Commandes e-commerce, checkout, validation
Pattern réutilisé de Customer Service pour cohérence structurelle
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
from datetime import datetime

from database import get_session, init_db
from services import OrderService, OrderItemService, OrderAnalyticsService

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'order-service-secret')

CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway", "X-API-Key"]
    }
})

api = Api(
    app,
    version='1.0',
    title='Order Service API',
    description='Microservice pour la gestion des commandes e-commerce',
    doc='/docs',
    prefix='/api/v1'
)

# Modèles de validation Swagger - Pattern identique Customer Service
order_create_model = api.model('OrderCreate', {
    'customer_id': fields.Integer(required=True, description='ID du client'),
    'items': fields.List(fields.Raw, required=True, description='Liste des items'),
    'shipping_address': fields.Raw(required=True, description='Adresse de livraison'),
    'billing_address': fields.Raw(required=False, description='Adresse de facturation'),
    'shipping_amount': fields.Float(required=False, description='Frais de livraison')
})

order_status_model = api.model('OrderStatusUpdate', {
    'status': fields.String(required=True, description='Nouveau statut')
})

@app.route('/health')
def health_check():
    """Health check avec informations détaillées - Pattern Customer Service"""
    app.logger.debug(f"[ORDER] Health check effectué")
    return {
        'status': 'healthy',
        'service': 'order-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0',
        'database': 'connected',
        'capabilities': [
            'order_management', 
            'checkout_processing', 
            'order_analytics',
            'status_tracking'
        ]
    }, 200

@api.route('/orders')
class OrdersResource(Resource):
    """Ressource pour la gestion des commandes - Pattern identique Customer Service"""
    
    def get(self):
        """Récupérer les commandes avec pagination et filtres"""
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            customer_id = request.args.get('customer_id', type=int)
            status = request.args.get('status')
            
            app.logger.info(f"[ORDER] Requête liste commandes - Page: {page}, Par page: {per_page}, Client: {customer_id}, Statut: {status}")
            
            session = get_session()
            order_service = OrderService(session)
            
            orders = order_service.get_orders_paginated(
                page=page, 
                per_page=per_page, 
                customer_id=customer_id,
                status=status
            )
            total_count = order_service.count_orders(customer_id=customer_id, status=status)
            
            app.logger.info(f"[ORDER] Commandes récupérées - {len(orders)} commandes sur {total_count} total")
            
            session.close()
            
            return {
                'orders': orders,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'filters': {
                    'customer_id': customer_id,
                    'status': status
                }
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @api.expect(order_create_model)
    def post(self):
        """Créer une nouvelle commande"""
        try:
            order_data = request.get_json()
            
            session = get_session()
            order_service = OrderService(session)
            
            order = order_service.create_order(order_data)
            
            session.close()
            
            return order, 201
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/orders/<int:order_id>')
class OrderResource(Resource):
    """Ressource pour une commande spécifique - Pattern Customer Service"""
    
    def get(self, order_id):
        """Récupérer une commande par ID"""
        try:
            customer_id = request.args.get('customer_id', type=int)
            
            session = get_session()
            order_service = OrderService(session)
            
            order = order_service.get_order_by_id(order_id, customer_id)
            
            session.close()
            
            if not order:
                return {'error': 'Commande non trouvée'}, 404
            
            return order, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @api.expect(order_status_model)
    def put(self, order_id):
        """Mettre à jour le statut d'une commande"""
        try:
            data = request.get_json()
            new_status = data.get('status')
            customer_id = request.args.get('customer_id', type=int)
            
            if not new_status:
                return {'error': 'Le statut est requis'}, 400
            
            session = get_session()
            order_service = OrderService(session)
            
            order = order_service.update_order_status(order_id, new_status, customer_id)
            
            session.close()
            
            if not order:
                return {'error': 'Commande non trouvée'}, 404
            
            return order, 200
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, order_id):
        """Annuler une commande"""
        try:
            customer_id = request.args.get('customer_id', type=int)
            
            session = get_session()
            order_service = OrderService(session)
            
            success = order_service.cancel_order(order_id, customer_id)
            
            session.close()
            
            if not success:
                return {'error': 'Commande non trouvée'}, 404
            
            return {'message': 'Commande annulée avec succès'}, 200
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/orders/<int:order_id>/items')
class OrderItemsResource(Resource):
    """Ressource pour les items d'une commande - Pattern AddressService"""
    
    def get(self, order_id):
        """Récupérer les items d'une commande"""
        try:
            session = get_session()
            item_service = OrderItemService(session)
            
            items = item_service.get_items_by_order(order_id)
            
            session.close()
            
            return {'items': items}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/orders/<int:order_id>/items/<int:item_id>')
class OrderItemResource(Resource):
    """Ressource pour un item spécifique - Pattern AddressService"""
    
    def put(self, order_id, item_id):
        """Mettre à jour la quantité d'un item"""
        try:
            data = request.get_json()
            new_quantity = data.get('quantity')
            
            if not new_quantity or new_quantity <= 0:
                return {'error': 'Quantité invalide'}, 400
            
            session = get_session()
            item_service = OrderItemService(session)
            
            item = item_service.update_item_quantity(item_id, order_id, new_quantity)
            
            session.close()
            
            if not item:
                return {'error': 'Item non trouvé'}, 404
            
            return item, 200
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception as e:
            return {'error': str(e)}, 500
    
    def delete(self, order_id, item_id):
        """Supprimer un item de la commande"""
        try:
            session = get_session()
            item_service = OrderItemService(session)
            
            success = item_service.remove_item(item_id, order_id)
            
            session.close()
            
            if not success:
                return {'error': 'Item non trouvé'}, 404
            
            return {'message': 'Item supprimé avec succès'}, 200
            
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/analytics/orders')
class OrderAnalyticsResource(Resource):
    """Ressource pour l'analytique des commandes - Pattern AuthService"""
    
    def get(self):
        """Obtenir des statistiques de commandes"""
        try:
            customer_id = request.args.get('customer_id', type=int)
            days = int(request.args.get('days', 30))
            
            session = get_session()
            analytics_service = OrderAnalyticsService(session)
            
            stats = analytics_service.get_order_statistics(customer_id, days)
            
            session.close()
            
            return stats, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/analytics/products/top')
class TopProductsResource(Resource):
    """Ressource pour les produits les plus vendus"""
    
    def get(self):
        """Obtenir les produits les plus vendus"""
        try:
            limit = int(request.args.get('limit', 10))
            days = int(request.args.get('days', 30))
            
            session = get_session()
            analytics_service = OrderAnalyticsService(session)
            
            top_products = analytics_service.get_top_products(limit, days)
            
            session.close()
            
            return {'top_products': top_products}, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# Instance info pour load balancing - Pattern Cart Service
@app.route('/metrics/instance')
def instance_metrics():
    """Métriques d'instance pour load balancing"""
    return {
        'instance_info': {
            'service': 'order-service',
            'port': 8007,
            'version': '1.0',
            'served_by': f"order-service-{os.getenv('HOSTNAME', 'unknown')}",
            'timestamp': datetime.now().isoformat()
        },
        'health': 'healthy'
    }, 200

if __name__ == '__main__':
    # Initialiser la base de données
    init_db()
    
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Order Service démarré sur le port 8007")
    app.run(host='0.0.0.0', port=8007, debug=os.getenv('DEBUG', 'False').lower() == 'true') 