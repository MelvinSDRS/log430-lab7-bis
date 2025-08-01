#!/usr/bin/env python3
"""
Sales Service - Microservice pour les transactions de vente
Port: 8003
Responsabilité: Ventes en magasin physique, transactions POS
"""

import os
import uuid
import requests
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sales-service-secret')

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# CORS pour intégration API Gateway
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway", "X-API-Key"]
    }
})

# Configuration Swagger
api = Api(
    app,
    version='1.0',
    title='Sales Service API',
    description='Microservice pour les transactions de vente en magasin',
    doc='/docs/',
    prefix='/api/v1'
)

# Métriques Prometheus
SALES_TOTAL = Counter('sales_total', 'Total number of sales transactions', ['store_id', 'status'])
SALES_AMOUNT = Counter('sales_amount_total', 'Total sales amount', ['store_id', 'currency'])
TRANSACTION_DURATION = Histogram('sales_transaction_duration_seconds', 'Sales transaction processing time')
ITEMS_SOLD = Counter('items_sold_total', 'Total number of items sold', ['product_id', 'store_id'])

# Configuration des services externes
INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:8002')
PRODUCT_SERVICE_URL = os.getenv('PRODUCT_SERVICE_URL', 'http://product-service:8001')

# Base de données simulée des ventes
sales_db = {}
daily_sales_summary = {}

# Modèles API
sale_item_model = api.model('SaleItem', {
    'product_id': fields.Integer(required=True, description='ID du produit'),
    'quantity': fields.Integer(required=True, description='Quantité vendue'),
    'unit_price': fields.Float(required=True, description='Prix unitaire'),
    'discount_percent': fields.Float(description='Pourcentage de remise', default=0.0)
})

sale_model = api.model('Sale', {
    'store_id': fields.Integer(required=True, description='ID du magasin'),
    'cashier_id': fields.String(required=True, description='ID du caissier'),
    'register_id': fields.String(required=True, description='ID de la caisse'),
    'customer_id': fields.String(description='ID du client (optionnel)'),
    'items': fields.List(fields.Nested(sale_item_model), required=True, description='Articles vendus'),
    'payment_method': fields.String(required=True, description='Méthode de paiement', 
                                   enum=['cash', 'credit_card', 'debit_card', 'mobile_payment'])
})

sale_response_model = api.model('SaleResponse', {
    'transaction_id': fields.String(description='ID unique de la transaction'),
    'total_amount': fields.Float(description='Montant total'),
    'tax_amount': fields.Float(description='Montant des taxes'),
    'discount_amount': fields.Float(description='Montant des remises'),
    'final_amount': fields.Float(description='Montant final'),
    'timestamp': fields.DateTime(description='Horodatage de la vente'),
    'status': fields.String(description='Statut de la transaction')
})

return_model = api.model('Return', {
    'transaction_id': fields.String(required=True, description='ID de la transaction originale'),
    'items': fields.List(fields.Nested(sale_item_model), required=True, description='Articles retournés'),
    'reason': fields.String(required=True, description='Raison du retour'),
    'cashier_id': fields.String(required=True, description='ID du caissier traitant le retour')
})

class SalesCalculator:
    """Calculateur pour les ventes et taxes"""
    
    TAX_RATES = {
        'default': 0.15,  # 15% TVQ + GST au Québec
        'food': 0.05,     # 5% GST seulement pour l'alimentation
        'books': 0.05,    # 5% GST seulement pour les livres
    }
    
    @staticmethod
    def calculate_sale(items: List[Dict], store_id: int) -> Dict[str, float]:
        """Calcule les totaux d'une vente"""
        subtotal = 0.0
        discount_total = 0.0
        tax_total = 0.0
        
        for item in items:
            quantity = item['quantity']
            unit_price = item['unit_price']
            discount_percent = item.get('discount_percent', 0.0)
            
            # Calculer le montant avant remise
            item_total = quantity * unit_price
            
            # Calculer la remise
            discount_amount = item_total * (discount_percent / 100)
            discount_total += discount_amount
            
            # Montant après remise
            discounted_amount = item_total - discount_amount
            subtotal += discounted_amount
            
            # Calculer les taxes (simulé - basé sur la catégorie du produit)
            tax_rate = SalesCalculator.TAX_RATES['default']
            tax_amount = discounted_amount * tax_rate
            tax_total += tax_amount
        
        final_amount = subtotal + tax_total
        
        return {
            'subtotal': round(subtotal, 2),
            'discount_amount': round(discount_total, 2),
            'tax_amount': round(tax_total, 2),
            'final_amount': round(final_amount, 2)
        }

def get_product_info(product_id: int) -> Optional[Dict]:
    """Récupérer les informations d'un produit"""
    try:
        logger.debug(f"[SALES] Appel service produit - ID: {product_id}")
        response = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products/{product_id}", timeout=5)
        if response.status_code == 200:
            logger.debug(f"[SALES] Produit récupéré avec succès - ID: {product_id}")
            return response.json()
        else:
            logger.warning(f"[SALES] Produit non trouvé - ID: {product_id}, Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"[SALES] Échec appel service produit - ID {product_id}: {e}")
    return None

def check_inventory(product_id: int, quantity: int, store_id: int) -> bool:
    """Vérifier la disponibilité en stock"""
    try:
        logger.debug(f"[SALES] Appel service inventory - Produit: {product_id}, Magasin: {store_id}")
        response = requests.get(
            f"{INVENTORY_SERVICE_URL}/api/v1/inventory",
            params={'location_id': store_id, 'product_id': product_id},
            timeout=5
        )
        if response.status_code == 200:
            inventory_items = response.json()
            for item in inventory_items:
                if item['product_id'] == product_id and item['available_quantity'] >= quantity:
                    logger.debug(f"[SALES] Stock OK - Produit: {product_id}, Disponible: {item['available_quantity']}, Demandé: {quantity}")
                    return True
            logger.debug(f"[SALES] Stock insuffisant - Produit: {product_id}")
        else:
            logger.warning(f"[SALES] Service inventory indisponible - Code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"[SALES] Échec appel service inventory - Produit {product_id}: {e}")
    return False

def update_inventory(product_id: int, quantity: int, store_id: int, operation: str = 'sale') -> bool:
    """Mettre à jour le stock après une vente ou un retour"""
    try:
        # Pour une vente, on décrémente le stock
        # Pour un retour, on incrémente le stock
        adjustment = -quantity if operation == 'sale' else quantity
        
        logger.debug(f"[SALES] Appel ajustement stock - Produit: {product_id}, Opération: {operation}, Ajustement: {adjustment}")
        
        response = requests.post(
            f"{INVENTORY_SERVICE_URL}/api/v1/inventory/adjust",
            json={
                'product_id': product_id,
                'location_id': store_id,
                'quantity_change': adjustment,
                'reason': f'POS {operation}'
            },
            timeout=5
        )
        
        if response.status_code == 200:
            logger.debug(f"[SALES] Ajustement stock réussi - Produit: {product_id}")
            return True
        else:
            logger.error(f"[SALES] Échec ajustement stock - Produit: {product_id}, Code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"[SALES] Erreur communication inventory - Produit {product_id}: {e}")
        return False

@api.route('/sales')
class SalesResource(Resource):
    """Endpoint pour les ventes"""
    
    @api.expect(sale_model)
    @api.marshal_with(sale_response_model)
    @api.doc('create_sale', description='Créer une nouvelle vente')
    def post(self):
        """Créer une nouvelle transaction de vente"""
        with TRANSACTION_DURATION.time():
            try:
                data = request.get_json()
                transaction_id = str(uuid.uuid4())
                timestamp = datetime.utcnow()
                
                logger.info(f"[SALES] Début création vente - Transaction ID: {transaction_id}")
                logger.debug(f"[SALES] Données reçues: {data}")
                
                # Valider les données
                store_id = data['store_id']
                items = data['items']
                
                logger.info(f"[SALES] Validation - Magasin: {store_id}, Articles: {len(items)}")
                
                # Vérifier le stock pour tous les articles
                logger.info(f"[SALES] Vérification stock pour {len(items)} articles")
                for item in items:
                    product_id = item['product_id']
                    quantity = item['quantity']
                    
                    logger.debug(f"[SALES] Vérification stock - Produit: {product_id}, Quantité: {quantity}")
                    if not check_inventory(product_id, quantity, store_id):
                        logger.warning(f"[SALES] Stock insuffisant - Produit: {product_id}, Demandé: {quantity}")
                        SALES_TOTAL.labels(store_id=store_id, status='failed_inventory').inc()
                        return {'error': f'Stock insuffisant pour le produit {product_id}'}, 400
                
                # Calculer les totaux
                logger.info(f"[SALES] Calcul des totaux pour la transaction {transaction_id}")
                calculation = SalesCalculator.calculate_sale(items, store_id)
                logger.debug(f"[SALES] Calculs terminés - Total: {calculation['final_amount']}$")
                
                # Créer la transaction
                sale_record = {
                    'transaction_id': transaction_id,
                    'store_id': store_id,
                    'cashier_id': data['cashier_id'],
                    'register_id': data['register_id'],
                    'customer_id': data.get('customer_id'),
                    'items': items,
                    'payment_method': data['payment_method'],
                    'timestamp': timestamp.isoformat(),
                    'status': 'completed',
                    **calculation
                }
                
                # Sauvegarder la vente
                sales_db[transaction_id] = sale_record
                
                # Mettre à jour les stocks
                logger.info(f"[SALES] Mise à jour des stocks pour {len(items)} articles")
                for item in items:
                    product_id = item['product_id']
                    quantity = item['quantity']
                    logger.debug(f"[SALES] Mise à jour stock - Produit: {product_id}, Quantité vendue: {quantity}")
                    
                    if update_inventory(product_id, quantity, store_id, 'sale'):
                        logger.debug(f"[SALES] Stock mis à jour avec succès - Produit: {product_id}")
                    else:
                        logger.error(f"[SALES] Échec mise à jour stock - Produit: {product_id}")
                    
                    # Métriques
                    ITEMS_SOLD.labels(product_id=str(product_id), store_id=str(store_id)).inc(quantity)
                
                # Mettre à jour le résumé quotidien
                date_key = timestamp.strftime('%Y-%m-%d')
                if date_key not in daily_sales_summary:
                    daily_sales_summary[date_key] = {
                        'date': date_key,
                        'total_sales': 0,
                        'total_amount': 0.0,
                        'transactions': 0
                    }
                
                daily_sales_summary[date_key]['transactions'] += 1
                daily_sales_summary[date_key]['total_amount'] += calculation['final_amount']
                daily_sales_summary[date_key]['total_sales'] += len(items)
                
                # Métriques
                SALES_TOTAL.labels(store_id=str(store_id), status='completed').inc()
                SALES_AMOUNT.labels(store_id=str(store_id), currency='CAD').inc(calculation['final_amount'])
                
                logger.info(f"[SALES] Vente créée avec succès - ID: {transaction_id}, Montant: {calculation['final_amount']}$, Magasin: {store_id}")
                logger.info(f"[SALES] Résumé vente - Articles: {len(items)}, Caissier: {data['cashier_id']}, Paiement: {data['payment_method']}")
                
                return sale_record, 201
                
            except Exception as e:
                logger.error(f"[SALES] Erreur création vente - Transaction: {transaction_id if 'transaction_id' in locals() else 'N/A'}: {e}")
                logger.error(f"[SALES] Données problématiques: {data if 'data' in locals() else 'N/A'}")
                SALES_TOTAL.labels(store_id=str(data.get('store_id', 0) if 'data' in locals() else 0), status='error').inc()
                return {'error': str(e)}, 500
    
    @api.doc('list_sales', description='Lister les ventes')
    def get(self):
        """Lister les ventes avec filtres optionnels"""
        try:
            store_id = request.args.get('store_id', type=int)
            cashier_id = request.args.get('cashier_id')
            date_from = request.args.get('date_from')  # YYYY-MM-DD
            date_to = request.args.get('date_to')  # YYYY-MM-DD
            limit = request.args.get('limit', 100, type=int)
            
            logger.info(f"[SALES] Requête liste ventes - Filtres: magasin={store_id}, caissier={cashier_id}, dates={date_from} à {date_to}, limite={limit}")
            
            filtered_sales = []
            
            for sale in sales_db.values():
                # Filtrer par magasin
                if store_id and sale['store_id'] != store_id:
                    continue
                
                # Filtrer par caissier
                if cashier_id and sale['cashier_id'] != cashier_id:
                    continue
                
                # Filtrer par date
                sale_date = datetime.fromisoformat(sale['timestamp']).strftime('%Y-%m-%d')
                if date_from and sale_date < date_from:
                    continue
                if date_to and sale_date > date_to:
                    continue
                
                filtered_sales.append(sale)
                
                if len(filtered_sales) >= limit:
                    break
            
            # Trier par date décroissante
            filtered_sales.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"[SALES] Liste ventes récupérée - {len(filtered_sales)} résultats trouvés")
            logger.debug(f"[SALES] Filtres appliqués: {{'store_id': {store_id}, 'cashier_id': '{cashier_id}', 'date_from': '{date_from}', 'date_to': '{date_to}'}}")
            
            return {
                'sales': filtered_sales,
                'total_count': len(filtered_sales),
                'filters_applied': {
                    'store_id': store_id,
                    'cashier_id': cashier_id,
                    'date_from': date_from,
                    'date_to': date_to
                }
            }, 200
            
        except Exception as e:
            logger.error(f"[SALES] Erreur récupération liste ventes: {e}")
            return {'error': str(e)}, 500

@api.route('/sales/<string:transaction_id>')
class SaleResource(Resource):
    """Endpoint pour une vente spécifique"""
    
    @api.marshal_with(sale_response_model)
    @api.doc('get_sale', description='Récupérer une vente par ID')
    def get(self, transaction_id):
        """Récupérer une vente spécifique"""
        try:
            if transaction_id not in sales_db:
                return {'error': 'Transaction non trouvée'}, 404
            
            return sales_db[transaction_id], 200
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la vente {transaction_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/sales/<string:transaction_id>/return')
class SaleReturnResource(Resource):
    """Endpoint pour les retours"""
    
    @api.expect(return_model)
    @api.doc('process_return', description='Traiter un retour de marchandise')
    def post(self, transaction_id):
        """Traiter un retour de marchandise"""
        try:
            logger.info(f"[SALES] Début traitement retour - Transaction originale: {transaction_id}")
            
            if transaction_id not in sales_db:
                logger.warning(f"[SALES] Transaction originale non trouvée: {transaction_id}")
                return {'error': 'Transaction originale non trouvée'}, 404
            
            data = request.get_json()
            original_sale = sales_db[transaction_id]
            
            return_id = str(uuid.uuid4())
            timestamp = datetime.utcnow()
            
            logger.info(f"[SALES] Retour ID généré: {return_id}")
            logger.debug(f"[SALES] Données retour reçues: {data}")
            
            # Valider les articles retournés
            return_items = data['items']
            original_items = {item['product_id']: item for item in original_sale['items']}
            
            for return_item in return_items:
                product_id = return_item['product_id']
                return_quantity = return_item['quantity']
                
                if product_id not in original_items:
                    return {'error': f'Produit {product_id} non présent dans la vente originale'}, 400
                
                if return_quantity > original_items[product_id]['quantity']:
                    return {'error': f'Quantité de retour supérieure à la quantité vendue pour le produit {product_id}'}, 400
            
            # Calculer le montant du retour
            logger.info(f"[SALES] Calcul montant retour pour {len(return_items)} articles")
            return_calculation = SalesCalculator.calculate_sale(return_items, original_sale['store_id'])
            logger.debug(f"[SALES] Montant retour calculé: {return_calculation['final_amount']}$")
            
            # Créer le retour
            return_record = {
                'return_id': return_id,
                'original_transaction_id': transaction_id,
                'store_id': original_sale['store_id'],
                'cashier_id': data['cashier_id'],
                'reason': data['reason'],
                'items': return_items,
                'timestamp': timestamp.isoformat(),
                'status': 'completed',
                'return_amount': return_calculation['final_amount']
            }
            
            # Mettre à jour les stocks (remettre en stock)
            logger.info(f"[SALES] Remise en stock pour {len(return_items)} articles")
            for item in return_items:
                product_id = item['product_id']
                quantity = item['quantity']
                logger.debug(f"[SALES] Remise en stock - Produit: {product_id}, Quantité: {quantity}")
                
                if update_inventory(product_id, quantity, original_sale['store_id'], 'return'):
                    logger.debug(f"[SALES] Stock restauré avec succès - Produit: {product_id}")
                else:
                    logger.error(f"[SALES] Échec restauration stock - Produit: {product_id}")
            
            # Sauvegarder le retour dans la vente originale
            if 'returns' not in original_sale:
                original_sale['returns'] = []
            original_sale['returns'].append(return_record)
            
            # Métriques
            SALES_TOTAL.labels(store_id=str(original_sale['store_id']), status='returned').inc()
            
            logger.info(f"[SALES] Retour traité avec succès - ID: {return_id}, Montant: {return_calculation['final_amount']}$")
            logger.info(f"[SALES] Résumé retour - Transaction originale: {transaction_id}, Raison: {data['reason']}, Caissier: {data['cashier_id']}")
            
            return return_record, 201
            
        except Exception as e:
            logger.error(f"[SALES] Erreur traitement retour - Transaction: {transaction_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/sales/summary/daily')
class DailySalesResource(Resource):
    """Endpoint pour le résumé quotidien des ventes"""
    
    @api.doc('get_daily_summary', description='Résumé des ventes par jour')
    def get(self):
        """Récupérer le résumé quotidien des ventes"""
        try:
            date = request.args.get('date')  # YYYY-MM-DD
            store_id = request.args.get('store_id', type=int)
            
            if date:
                # Résumé pour une date spécifique
                if date in daily_sales_summary:
                    summary = daily_sales_summary[date].copy()
                    
                    # Filtrer par magasin si demandé
                    if store_id:
                        store_sales = [s for s in sales_db.values() 
                                     if s['store_id'] == store_id and 
                                     datetime.fromisoformat(s['timestamp']).strftime('%Y-%m-%d') == date]
                        
                        summary = {
                            'date': date,
                            'store_id': store_id,
                            'transactions': len(store_sales),
                            'total_amount': sum(s['final_amount'] for s in store_sales),
                            'total_sales': sum(len(s['items']) for s in store_sales)
                        }
                    
                    return summary, 200
                else:
                    return {'date': date, 'transactions': 0, 'total_amount': 0.0, 'total_sales': 0}, 200
            else:
                # Résumé de tous les jours
                summaries = list(daily_sales_summary.values())
                summaries.sort(key=lambda x: x['date'], reverse=True)
                return {'daily_summaries': summaries}, 200
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé quotidien: {e}")
            return {'error': str(e)}, 500

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {
        'status': 'healthy',
        'service': 'sales-service',
        'timestamp': datetime.utcnow().isoformat(),
        'dependencies': {
            'inventory-service': 'available',
            'product-service': 'available'
        }
    }, 200

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

if __name__ == '__main__':
    logger.info("Démarrage du Sales Service sur le port 8003")
    app.run(host='0.0.0.0', port=8003, debug=os.getenv('DEBUG', 'False').lower() == 'true')