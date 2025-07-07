#!/usr/bin/env python3
"""
Inventory Service - Microservice pour la gestion des stocks
Port: 8002
Responsabilité: Stocks par entité, approvisionnement, alertes, réservations
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
import uuid
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'inventory-service-secret')

# CORS pour intégration API Gateway
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway", "X-API-Key"]
    }
})

# Configuration des échecs simulés
failure_config = {
    'enabled': os.getenv('SIMULATE_FAILURES', 'false').lower() == 'true',
    'failure_rate': float(os.getenv('FAILURE_RATE', '0.05')),  # 5% par défaut
    'out_of_stock_products': os.getenv('OUT_OF_STOCK_PRODUCTS', '').split(',') if os.getenv('OUT_OF_STOCK_PRODUCTS') else []
}

# Stockage en mémoire des stocks et réservations
inventory_db = {
    1: {'product_id': 1, 'location_id': 1, 'available_quantity': 100, 'reserved_quantity': 0},
    2: {'product_id': 2, 'location_id': 1, 'available_quantity': 50, 'reserved_quantity': 0},
    3: {'product_id': 3, 'location_id': 1, 'available_quantity': 25, 'reserved_quantity': 0},
    4: {'product_id': 4, 'location_id': 1, 'available_quantity': 75, 'reserved_quantity': 0},
    5: {'product_id': 5, 'location_id': 1, 'available_quantity': 200, 'reserved_quantity': 0},
}

reservations_db = {}

# API Documentation
api = Api(
    app,
    version='1.0',
    title='Inventory Service API',
    description='Microservice pour la gestion des stocks avec réservations',
    doc='/docs',
    prefix='/api/v1'
)

# Modèles Swagger
reservation_request_model = api.model('ReservationRequest', {
    'reservation_id': fields.String(required=True, description='ID unique de réservation'),
    'customer_id': fields.Integer(required=True, description='ID du client'),
    'items': fields.List(fields.Raw, required=True, description='Liste des produits à réserver')
})

inventory_item_model = api.model('InventoryItem', {
    'product_id': fields.Integer(description='ID du produit'),
    'location_id': fields.Integer(description='ID de l\'emplacement'),
    'available_quantity': fields.Integer(description='Quantité disponible'),
    'reserved_quantity': fields.Integer(description='Quantité réservée'),
    'total_quantity': fields.Integer(description='Quantité totale')
})

reservation_model = api.model('Reservation', {
    'reservation_id': fields.String(description='ID de la réservation'),
    'customer_id': fields.Integer(description='ID du client'),
    'status': fields.String(description='Statut de la réservation'),
    'items': fields.List(fields.Raw, description='Articles réservés'),
    'created_at': fields.DateTime(description='Date de création'),
    'expires_at': fields.DateTime(description='Date d\'expiration')
})

def should_simulate_failure(product_id: int) -> tuple[bool, str]:
    """Détermine si on doit simuler un échec de stock"""
    if not failure_config['enabled']:
        return False, ""
    
    # Échec sur produits spécifiques
    if str(product_id) in failure_config['out_of_stock_products']:
        return True, f"Produit {product_id} en rupture de stock"
    
    # Échec aléatoire
    if random.random() < failure_config['failure_rate']:
        return True, f"Stock insuffisant pour le produit {product_id}"
    
    return False, ""

def get_inventory_item(product_id: int, location_id: int = 1) -> Dict[str, Any]:
    """Récupérer un item d'inventaire"""
    for item in inventory_db.values():
        if item['product_id'] == product_id and item['location_id'] == location_id:
            return item
    return None

@api.route('/inventory')
class InventoryResource(Resource):
    """Endpoint pour consulter l'inventaire"""
    
    @api.marshal_list_with(inventory_item_model)
    @api.doc('get_inventory', description='Récupérer l\'inventaire')
    def get(self):
        """Récupérer l'inventaire complet"""
        try:
            location_id = request.args.get('location_id', 1, type=int)
            
            items = []
            for item in inventory_db.values():
                if item['location_id'] == location_id:
                    items.append({
                        **item,
                        'total_quantity': item['available_quantity'] + item['reserved_quantity']
                    })
            
            return items, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération de l'inventaire: {e}")
            return {'error': str(e)}, 500

@api.route('/inventory/<int:product_id>')
class InventoryItemResource(Resource):
    """Endpoint pour un produit spécifique"""
    
    @api.marshal_with(inventory_item_model)
    @api.doc('get_inventory_item', description='Récupérer l\'inventaire d\'un produit')
    def get(self, product_id):
        """Récupérer l'inventaire d'un produit spécifique"""
        try:
            location_id = request.args.get('location_id', 1, type=int)
            
            item = get_inventory_item(product_id, location_id)
            if not item:
                return {'error': 'Produit non trouvé dans l\'inventaire'}, 404
            
            return {
                **item,
                'total_quantity': item['available_quantity'] + item['reserved_quantity']
            }, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération du produit {product_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/inventory/reserve')
class ReservationResource(Resource):
    """Endpoint principal pour les réservations de stock"""
    
    @api.expect(reservation_request_model)
    @api.marshal_with(reservation_model)
    @api.doc('reserve_stock', description='Réserver du stock pour une commande')
    def post(self):
        """Réserver du stock pour une transaction"""
        try:
            data = request.get_json()
            
            reservation_id = data.get('reservation_id')
            customer_id = data.get('customer_id')
            items_to_reserve = data.get('items', [])
            
            if not all([reservation_id, customer_id, items_to_reserve]):
                return {'error': 'reservation_id, customer_id et items sont requis'}, 400
            
            # Vérifier si la réservation existe déjà
            if reservation_id in reservations_db:
                existing = reservations_db[reservation_id]
                app.logger.info(f"Réservation {reservation_id} déjà existante")
                return existing, 200
            
            # Valider et préparer la réservation
            reserved_items = []
            
            for item_request in items_to_reserve:
                product_id = item_request.get('product_id')
                quantity = item_request.get('quantity', 0)
                location_id = item_request.get('location_id', 1)
                
                if not product_id or quantity <= 0:
                    return {'error': f'product_id et quantity valides requis pour chaque item'}, 400
                
                # Vérifier la simulation d'échec
                should_fail, failure_reason = should_simulate_failure(product_id)
                if should_fail:
                    app.logger.warning(f"Simulation d'échec de réservation: {failure_reason}")
                    return {'error': failure_reason}, 409  # Conflict
                
                # Vérifier la disponibilité
                inventory_item = get_inventory_item(product_id, location_id)
                if not inventory_item:
                    return {'error': f'Produit {product_id} non trouvé dans l\'inventaire'}, 404
                
                if inventory_item['available_quantity'] < quantity:
                    return {
                        'error': f'Stock insuffisant pour le produit {product_id}. '
                               f'Disponible: {inventory_item["available_quantity"]}, '
                               f'Demandé: {quantity}'
                    }, 409
                
                # Préparer l'item réservé
                reserved_items.append({
                    'product_id': product_id,
                    'location_id': location_id,
                    'quantity': quantity,
                    'reserved_at': datetime.utcnow().isoformat()
                })
            
            # Effectuer les réservations
            for reserved_item in reserved_items:
                product_id = reserved_item['product_id']
                location_id = reserved_item['location_id']
                quantity = reserved_item['quantity']
                
                inventory_item = get_inventory_item(product_id, location_id)
                inventory_item['available_quantity'] -= quantity
                inventory_item['reserved_quantity'] += quantity
            
            # Créer la réservation
            reservation = {
                'reservation_id': reservation_id,
                'customer_id': customer_id,
                'status': 'active',
                'items': reserved_items,
                'created_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(minutes=10)).isoformat()
            }
            
            # Sauvegarder la réservation
            reservations_db[reservation_id] = reservation
            
            app.logger.info(f"Réservation créée: {reservation_id} - {len(reserved_items)} produits")
            
            return reservation, 201
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la réservation: {e}")
            return {'error': str(e)}, 500

@api.route('/inventory/release/<string:reservation_id>')
class ReservationReleaseResource(Resource):
    """Endpoint pour libérer une réservation"""
    
    @api.doc('release_reservation', description='Libérer une réservation de stock')
    def delete(self, reservation_id):
        """Libérer une réservation (action de compensation)"""
        try:
            reservation = reservations_db.get(reservation_id)
            
            if not reservation:
                return {'error': 'Réservation non trouvée'}, 404
            
            if reservation['status'] == 'released':
                app.logger.info(f"Réservation {reservation_id} déjà libérée")
                return {'message': 'Réservation déjà libérée'}, 200
            
            # Libérer les stocks réservés
            for item in reservation['items']:
                product_id = item['product_id']
                location_id = item['location_id']
                quantity = item['quantity']
                
                inventory_item = get_inventory_item(product_id, location_id)
                if inventory_item:
                    inventory_item['available_quantity'] += quantity
                    inventory_item['reserved_quantity'] -= quantity
            
            # Marquer la réservation comme libérée
            reservation['status'] = 'released'
            reservation['released_at'] = datetime.utcnow().isoformat()
            
            app.logger.info(f"Réservation libérée: {reservation_id}")
            
            return {
                'message': 'Réservation libérée avec succès',
                'reservation_id': reservation_id,
                'released_items': len(reservation['items'])
            }, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la libération de la réservation {reservation_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/inventory/reservations/<string:reservation_id>')
class ReservationStatusResource(Resource):
    """Endpoint pour consulter une réservation"""
    
    @api.marshal_with(reservation_model)
    @api.doc('get_reservation', description='Récupérer les détails d\'une réservation')
    def get(self, reservation_id):
        """Récupérer les détails d'une réservation"""
        try:
            reservation = reservations_db.get(reservation_id)
            
            if not reservation:
                return {'error': 'Réservation non trouvée'}, 404
            
            return reservation, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération de la réservation {reservation_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/inventory/config/failures')
class InventoryFailureConfigResource(Resource):
    """Endpoint pour configurer les échecs simulés"""
    
    @api.doc('configure_inventory_failures', description='Configurer la simulation d\'échecs d\'inventaire')
    def post(self):
        """Configurer les paramètres de simulation d'échecs"""
        try:
            data = request.get_json()
            
            if 'enabled' in data:
                failure_config['enabled'] = bool(data['enabled'])
            
            if 'failure_rate' in data:
                rate = float(data['failure_rate'])
                if 0 <= rate <= 1:
                    failure_config['failure_rate'] = rate
                else:
                    return {'error': 'failure_rate doit être entre 0 et 1'}, 400
            
            if 'out_of_stock_products' in data:
                failure_config['out_of_stock_products'] = data['out_of_stock_products']
            
            app.logger.info(f"Configuration des échecs d'inventaire mise à jour: {failure_config}")
            
            return {
                'message': 'Configuration mise à jour',
                'config': failure_config
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @api.doc('get_inventory_failure_config', description='Récupérer la configuration des échecs')
    def get(self):
        """Récupérer la configuration actuelle des échecs"""
        return failure_config, 200

@api.route('/inventory/metrics')
class InventoryMetricsResource(Resource):
    """Endpoint pour les métriques du service d'inventaire"""
    
    @api.doc('get_inventory_metrics', description='Récupérer les métriques du service')
    def get(self):
        """Récupérer les statistiques d'inventaire"""
        try:
            total_products = len(inventory_db)
            total_reservations = len(reservations_db)
            active_reservations = len([r for r in reservations_db.values() if r['status'] == 'active'])
            
            total_available = sum(item['available_quantity'] for item in inventory_db.values())
            total_reserved = sum(item['reserved_quantity'] for item in inventory_db.values())
            
            return {
                'total_products': total_products,
                'total_available_quantity': total_available,
                'total_reserved_quantity': total_reserved,
                'total_reservations': total_reservations,
                'active_reservations': active_reservations,
                'failure_config': failure_config,
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# Health Check
@app.route('/health')
def health_check():
    """Endpoint de santé pour le service"""
    return {
        'status': 'healthy',
        'service': 'inventory-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0',
        'capabilities': [
            'inventory_management',
            'stock_reservations',
            'reservation_release',
            'failure_simulation'
        ],
        'failure_simulation': failure_config['enabled']
    }, 200

# Point d'entrée
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.logger.info("Inventory Service démarré sur le port 8002")
    app.logger.info(f"Simulation d'échecs: {failure_config['enabled']}")
    app.run(host='0.0.0.0', port=8002, debug=os.getenv('DEBUG', 'False').lower() == 'true') 