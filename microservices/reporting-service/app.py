#!/usr/bin/env python3
"""
Reporting Service - Microservice pour l'analytique et rapports
Port: 8004
Responsabilité: Rapports, tableaux de bord, analytique multi-magasins
"""

import os
import requests
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any, List, Optional

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'reporting-service-secret')

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
    title='Reporting Service API',
    description='Microservice pour l\'analytique et rapports multi-magasins',
    doc='/docs/',
    prefix='/api/v1'
)

# Métriques Prometheus
REPORTS_GENERATED = Counter('reports_generated_total', 'Total number of reports generated', ['report_type'])
REPORT_GENERATION_DURATION = Histogram('report_generation_duration_seconds', 'Report generation time', ['report_type'])
DASHBOARD_REQUESTS = Counter('dashboard_requests_total', 'Total dashboard requests', ['dashboard_type'])

# Configuration des services externes
SALES_SERVICE_URL = os.getenv('SALES_SERVICE_URL', 'http://sales-service:8003')
INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:8002')
PRODUCT_SERVICE_URL = os.getenv('PRODUCT_SERVICE_URL', 'http://product-service:8001')

# Cache des rapports
reports_cache = {}
dashboard_cache = {}
cache_ttl = 300  # 5 minutes

# Modèles API
date_range_model = api.model('DateRange', {
    'start_date': fields.String(required=True, description='Date de début (YYYY-MM-DD)'),
    'end_date': fields.String(required=True, description='Date de fin (YYYY-MM-DD)')
})

report_filter_model = api.model('ReportFilter', {
    'store_ids': fields.List(fields.Integer, description='IDs des magasins'),
    'product_ids': fields.List(fields.Integer, description='IDs des produits'),
    'cashier_ids': fields.List(fields.String, description='IDs des caissiers'),
    'date_range': fields.Nested(date_range_model, description='Plage de dates')
})

sales_report_model = api.model('SalesReport', {
    'report_id': fields.String(description='ID unique du rapport'),
    'type': fields.String(description='Type de rapport'),
    'generated_at': fields.DateTime(description='Date de génération'),
    'filters_applied': fields.Raw(description='Filtres appliqués'),
    'summary': fields.Raw(description='Résumé des données'),
    'data': fields.Raw(description='Données détaillées')
})

class DataAggregator:
    """Agrégateur de données pour les rapports"""
    
    @staticmethod
    def get_sales_data(store_ids: List[int] = None, date_from: str = None, date_to: str = None) -> List[Dict]:
        """Récupérer les données de ventes"""
        try:
            logger.info(f"[REPORTING] Récupération données ventes - Magasins: {store_ids}, Période: {date_from} à {date_to}")
            
            params = {}
            if date_from:
                params['date_from'] = date_from
            if date_to:
                params['date_to'] = date_to
            
            all_sales = []
            
            if store_ids:
                # Récupérer les ventes pour chaque magasin
                logger.debug(f"[REPORTING] Récupération pour {len(store_ids)} magasins spécifiques")
                for store_id in store_ids:
                    params['store_id'] = store_id
                    logger.debug(f"[REPORTING] Appel sales service - Magasin: {store_id}")
                    response = requests.get(f"{SALES_SERVICE_URL}/api/v1/sales", params=params, timeout=10)
                    if response.status_code == 200:
                        store_sales = response.json().get('sales', [])
                        logger.debug(f"[REPORTING] Récupéré {len(store_sales)} ventes pour magasin {store_id}")
                        all_sales.extend(store_sales)
                    else:
                        logger.warning(f"[REPORTING] Échec récupération ventes magasin {store_id} - Code: {response.status_code}")
            else:
                # Récupérer toutes les ventes
                logger.debug(f"[REPORTING] Récupération toutes les ventes")
                response = requests.get(f"{SALES_SERVICE_URL}/api/v1/sales", params=params, timeout=10)
                if response.status_code == 200:
                    all_sales = response.json().get('sales', [])
                    logger.debug(f"[REPORTING] Récupéré {len(all_sales)} ventes au total")
                else:
                    logger.warning(f"[REPORTING] Échec récupération toutes ventes - Code: {response.status_code}")
            
            logger.info(f"[REPORTING] Données ventes récupérées - Total: {len(all_sales)} ventes")
            return all_sales
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[REPORTING] Erreur récupération ventes: {e}")
            return []
    
    @staticmethod
    def get_inventory_data(store_ids: List[int] = None) -> List[Dict]:
        """Récupérer les données d'inventaire"""
        try:
            logger.info(f"[REPORTING] Récupération données inventaire - Magasins: {store_ids}")
            all_inventory = []
            
            if store_ids:
                logger.debug(f"[REPORTING] Récupération pour {len(store_ids)} magasins spécifiques")
                for store_id in store_ids:
                    logger.debug(f"[REPORTING] Appel inventory service - Magasin: {store_id}")
                    response = requests.get(
                        f"{INVENTORY_SERVICE_URL}/api/v1/inventory",
                        params={'location_id': store_id},
                        timeout=10
                    )
                    if response.status_code == 200:
                        store_inventory = response.json()
                        logger.debug(f"[REPORTING] Récupéré {len(store_inventory)} items inventaire pour magasin {store_id}")
                        all_inventory.extend(store_inventory)
                    else:
                        logger.warning(f"[REPORTING] Échec récupération inventaire magasin {store_id} - Code: {response.status_code}")
            else:
                # Par défaut, récupérer pour tous les magasins (1 à 5)
                logger.debug(f"[REPORTING] Récupération inventaire pour tous les magasins (1-5)")
                for store_id in range(1, 6):
                    logger.debug(f"[REPORTING] Appel inventory service - Magasin: {store_id}")
                    response = requests.get(
                        f"{INVENTORY_SERVICE_URL}/api/v1/inventory",
                        params={'location_id': store_id},
                        timeout=10
                    )
                    if response.status_code == 200:
                        store_inventory = response.json()
                        logger.debug(f"[REPORTING] Récupéré {len(store_inventory)} items inventaire pour magasin {store_id}")
                        all_inventory.extend(store_inventory)
                    else:
                        logger.warning(f"[REPORTING] Échec récupération inventaire magasin {store_id} - Code: {response.status_code}")
            
            logger.info(f"[REPORTING] Données inventaire récupérées - Total: {len(all_inventory)} items")
            return all_inventory
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[REPORTING] Erreur récupération inventaire: {e}")
            return []
    
    @staticmethod
    def get_products_data() -> List[Dict]:
        """Récupérer les données des produits"""
        try:
            logger.info(f"[REPORTING] Récupération données produits")
            response = requests.get(f"{PRODUCT_SERVICE_URL}/api/v1/products", timeout=10)
            if response.status_code == 200:
                products = response.json().get('products', [])
                logger.info(f"[REPORTING] Données produits récupérées - Total: {len(products)} produits")
                return products
            else:
                logger.warning(f"[REPORTING] Échec récupération produits - Code: {response.status_code}")
                return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[REPORTING] Erreur récupération produits: {e}")
            return []

class ReportGenerator:
    """Générateur de rapports"""
    
    @staticmethod
    def generate_sales_summary(sales_data: List[Dict], filters: Dict = None) -> Dict:
        """Générer un résumé des ventes"""
        if not sales_data:
            return {
                'total_transactions': 0,
                'total_revenue': 0.0,
                'total_items_sold': 0,
                'average_transaction_value': 0.0,
                'by_store': {},
                'by_payment_method': {},
                'by_day': {}
            }
        
        # Calculs de base
        total_transactions = len(sales_data)
        total_revenue = sum(sale.get('final_amount', 0) for sale in sales_data)
        total_items_sold = sum(len(sale.get('items', [])) for sale in sales_data)
        average_transaction_value = total_revenue / total_transactions if total_transactions > 0 else 0
        
        # Agrégation par magasin
        by_store = defaultdict(lambda: {'transactions': 0, 'revenue': 0.0, 'items': 0})
        for sale in sales_data:
            store_id = sale.get('store_id')
            by_store[store_id]['transactions'] += 1
            by_store[store_id]['revenue'] += sale.get('final_amount', 0)
            by_store[store_id]['items'] += len(sale.get('items', []))
        
        # Agrégation par méthode de paiement
        by_payment_method = defaultdict(lambda: {'transactions': 0, 'revenue': 0.0})
        for sale in sales_data:
            payment_method = sale.get('payment_method', 'unknown')
            by_payment_method[payment_method]['transactions'] += 1
            by_payment_method[payment_method]['revenue'] += sale.get('final_amount', 0)
        
        # Agrégation par jour
        by_day = defaultdict(lambda: {'transactions': 0, 'revenue': 0.0})
        for sale in sales_data:
            sale_date = datetime.fromisoformat(sale['timestamp']).strftime('%Y-%m-%d')
            by_day[sale_date]['transactions'] += 1
            by_day[sale_date]['revenue'] += sale.get('final_amount', 0)
        
        return {
            'total_transactions': total_transactions,
            'total_revenue': round(total_revenue, 2),
            'total_items_sold': total_items_sold,
            'average_transaction_value': round(average_transaction_value, 2),
            'by_store': dict(by_store),
            'by_payment_method': dict(by_payment_method),
            'by_day': dict(sorted(by_day.items()))
        }
    
    @staticmethod
    def generate_inventory_report(inventory_data: List[Dict]) -> Dict:
        """Générer un rapport d'inventaire"""
        if not inventory_data:
            return {
                'total_products': 0,
                'total_stock_value': 0.0,
                'low_stock_alerts': [],
                'by_location': {},
                'stock_distribution': {}
            }
        
        total_products = len(set(item['product_id'] for item in inventory_data))
        low_stock_alerts = []
        by_location = defaultdict(lambda: {'products': 0, 'total_quantity': 0, 'stock_value': 0.0})
        
        for item in inventory_data:
            location_id = item.get('location_id')
            available_quantity = item.get('available_quantity', 0)
            reserved_quantity = item.get('reserved_quantity', 0)
            total_quantity = available_quantity + reserved_quantity
            
            # Vérifier les alertes de stock bas
            if available_quantity <= item.get('reorder_point', 5):
                low_stock_alerts.append({
                    'product_id': item['product_id'],
                    'location_id': location_id,
                    'available_quantity': available_quantity,
                    'reorder_point': item.get('reorder_point', 5)
                })
            
            # Agrégation par emplacement
            by_location[location_id]['products'] += 1
            by_location[location_id]['total_quantity'] += total_quantity
            by_location[location_id]['stock_value'] += total_quantity * item.get('unit_cost', 0)
        
        total_stock_value = sum(loc['stock_value'] for loc in by_location.values())
        
        return {
            'total_products': total_products,
            'total_stock_value': round(total_stock_value, 2),
            'low_stock_alerts': low_stock_alerts,
            'low_stock_count': len(low_stock_alerts),
            'by_location': dict(by_location)
        }
    
    @staticmethod
    def generate_product_performance(sales_data: List[Dict], products_data: List[Dict]) -> Dict:
        """Générer un rapport de performance des produits"""
        product_sales = defaultdict(lambda: {'quantity': 0, 'revenue': 0.0, 'transactions': 0})
        
        # Analyser les ventes par produit
        for sale in sales_data:
            for item in sale.get('items', []):
                product_id = item['product_id']
                quantity = item['quantity']
                revenue = quantity * item['unit_price']
                
                product_sales[product_id]['quantity'] += quantity
                product_sales[product_id]['revenue'] += revenue
                product_sales[product_id]['transactions'] += 1
        
        # Enrichir avec les informations produits
        products_dict = {p['id']: p for p in products_data}
        enriched_performance = []
        
        for product_id, stats in product_sales.items():
            product_info = products_dict.get(product_id, {})
            enriched_performance.append({
                'product_id': product_id,
                'product_name': product_info.get('nom', f'Produit {product_id}'),
                'category': product_info.get('categorie', 'Inconnue'),
                'quantity_sold': stats['quantity'],
                'revenue': round(stats['revenue'], 2),
                'transactions': stats['transactions'],
                'average_quantity_per_transaction': round(stats['quantity'] / stats['transactions'], 2)
            })
        
        # Trier par revenus décroissants
        enriched_performance.sort(key=lambda x: x['revenue'], reverse=True)
        
        return {
            'top_products': enriched_performance[:10],
            'all_products': enriched_performance,
            'total_products_sold': len(enriched_performance)
        }

def get_cache_key(report_type: str, filters: Dict = None) -> str:
    """Générer une clé de cache pour un rapport"""
    import hashlib
    import json
    
    cache_data = {'type': report_type, 'filters': filters or {}}
    cache_string = json.dumps(cache_data, sort_keys=True)
    return hashlib.md5(cache_string.encode()).hexdigest()

def is_cache_valid(cache_entry: Dict) -> bool:
    """Vérifier si l'entrée de cache est valide"""
    if not cache_entry:
        return False
    
    cache_time = datetime.fromisoformat(cache_entry['cached_at'])
    return (datetime.utcnow() - cache_time).total_seconds() < cache_ttl

@api.route('/reports/sales')
class SalesReportResource(Resource):
    """Endpoint pour les rapports de ventes"""
    
    @api.expect(report_filter_model)
    @api.marshal_with(sales_report_model)
    @api.doc('generate_sales_report', description='Générer un rapport de ventes')
    def post(self):
        """Générer un rapport de ventes"""
        with REPORT_GENERATION_DURATION.labels(report_type='sales').time():
            try:
                filters = request.get_json() or {}
                cache_key = get_cache_key('sales', filters)
                
                logger.info(f"[REPORTING] Début génération rapport ventes - Filtres: {filters}")
                
                # Vérifier le cache
                if cache_key in reports_cache and is_cache_valid(reports_cache[cache_key]):
                    logger.info(f"[REPORTING] Rapport ventes servi depuis le cache - Clé: {cache_key[:8]}...")
                    REPORTS_GENERATED.labels(report_type='sales_cached').inc()
                    return reports_cache[cache_key]['data'], 200
                
                # Extraire les filtres
                store_ids = filters.get('store_ids')
                date_range = filters.get('date_range', {})
                date_from = date_range.get('start_date')
                date_to = date_range.get('end_date')
                
                logger.debug(f"[REPORTING] Filtres extraits - Magasins: {store_ids}, Période: {date_from} à {date_to}")
                
                # Récupérer les données
                logger.info(f"[REPORTING] Récupération données pour rapport ventes")
                sales_data = DataAggregator.get_sales_data(store_ids, date_from, date_to)
                
                # Filtrer par caissier si spécifié
                cashier_ids = filters.get('cashier_ids')
                if cashier_ids:
                    original_count = len(sales_data)
                    sales_data = [sale for sale in sales_data if sale.get('cashier_id') in cashier_ids]
                    logger.debug(f"[REPORTING] Filtre caissier appliqué - {original_count} → {len(sales_data)} ventes")
                
                # Générer le rapport
                logger.info(f"[REPORTING] Génération rapport ventes avec {len(sales_data)} ventes")
                summary = ReportGenerator.generate_sales_summary(sales_data, filters)
                
                report = {
                    'report_id': f"sales_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'sales_summary',
                    'generated_at': datetime.utcnow().isoformat(),
                    'filters_applied': filters,
                    'summary': summary,
                    'data': sales_data[:100]  # Limiter les données détaillées
                }
                
                # Mettre en cache
                reports_cache[cache_key] = {
                    'data': report,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                logger.info(f"[REPORTING] Rapport ventes généré - ID: {report['report_id']}, Ventes: {summary['total_transactions']}, Revenus: {summary['total_revenue']}$")
                logger.debug(f"[REPORTING] Rapport mis en cache - Clé: {cache_key[:8]}...")
                
                REPORTS_GENERATED.labels(report_type='sales').inc()
                
                return report, 200
                
            except Exception as e:
                logger.error(f"[REPORTING] Erreur génération rapport ventes: {e}")
                return {'error': str(e)}, 500

@api.route('/reports/inventory')
class InventoryReportResource(Resource):
    """Endpoint pour les rapports d'inventaire"""
    
    @api.doc('generate_inventory_report', description='Générer un rapport d\'inventaire')
    def post(self):
        """Générer un rapport d'inventaire"""
        with REPORT_GENERATION_DURATION.labels(report_type='inventory').time():
            try:
                filters = request.get_json() or {}
                cache_key = get_cache_key('inventory', filters)
                
                logger.info(f"[REPORTING] Début génération rapport inventaire - Filtres: {filters}")
                
                # Vérifier le cache
                if cache_key in reports_cache and is_cache_valid(reports_cache[cache_key]):
                    logger.info(f"[REPORTING] Rapport inventaire servi depuis le cache - Clé: {cache_key[:8]}...")
                    REPORTS_GENERATED.labels(report_type='inventory_cached').inc()
                    return reports_cache[cache_key]['data'], 200
                
                store_ids = filters.get('store_ids')
                
                logger.debug(f"[REPORTING] Filtres extraits - Magasins: {store_ids}")
                
                # Récupérer les données
                logger.info(f"[REPORTING] Récupération données pour rapport inventaire")
                inventory_data = DataAggregator.get_inventory_data(store_ids)
                
                # Générer le rapport
                logger.info(f"[REPORTING] Génération rapport inventaire avec {len(inventory_data)} items")
                inventory_report = ReportGenerator.generate_inventory_report(inventory_data)
                
                report = {
                    'report_id': f"inventory_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'inventory_summary',
                    'generated_at': datetime.utcnow().isoformat(),
                    'filters_applied': filters,
                    'summary': inventory_report,
                    'data': inventory_data
                }
                
                # Mettre en cache
                reports_cache[cache_key] = {
                    'data': report,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                logger.info(f"[REPORTING] Rapport inventaire généré - ID: {report['report_id']}, Produits: {inventory_report['total_products']}, Alertes: {inventory_report['low_stock_count']}")
                logger.debug(f"[REPORTING] Rapport mis en cache - Clé: {cache_key[:8]}...")
                
                REPORTS_GENERATED.labels(report_type='inventory').inc()
                
                return report, 200
                
            except Exception as e:
                logger.error(f"[REPORTING] Erreur génération rapport inventaire: {e}")
                return {'error': str(e)}, 500

@api.route('/reports/products/performance')
class ProductPerformanceResource(Resource):
    """Endpoint pour les rapports de performance des produits"""
    
    @api.expect(report_filter_model)
    @api.doc('generate_product_performance', description='Générer un rapport de performance des produits')
    def post(self):
        """Générer un rapport de performance des produits"""
        with REPORT_GENERATION_DURATION.labels(report_type='product_performance').time():
            try:
                filters = request.get_json() or {}
                cache_key = get_cache_key('product_performance', filters)
                
                # Vérifier le cache
                if cache_key in reports_cache and is_cache_valid(reports_cache[cache_key]):
                    REPORTS_GENERATED.labels(report_type='product_performance_cached').inc()
                    return reports_cache[cache_key]['data'], 200
                
                # Extraire les filtres
                store_ids = filters.get('store_ids')
                product_ids = filters.get('product_ids')
                date_range = filters.get('date_range', {})
                date_from = date_range.get('start_date')
                date_to = date_range.get('end_date')
                
                # Récupérer les données
                sales_data = DataAggregator.get_sales_data(store_ids, date_from, date_to)
                products_data = DataAggregator.get_products_data()
                
                # Filtrer par produits si spécifié
                if product_ids:
                    filtered_sales = []
                    for sale in sales_data:
                        filtered_items = [item for item in sale.get('items', []) 
                                        if item['product_id'] in product_ids]
                        if filtered_items:
                            sale_copy = sale.copy()
                            sale_copy['items'] = filtered_items
                            filtered_sales.append(sale_copy)
                    sales_data = filtered_sales
                
                # Générer le rapport
                performance_report = ReportGenerator.generate_product_performance(sales_data, products_data)
                
                report = {
                    'report_id': f"product_performance_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    'type': 'product_performance',
                    'generated_at': datetime.utcnow().isoformat(),
                    'filters_applied': filters,
                    'summary': performance_report,
                    'data': performance_report['all_products'][:50]  # Limiter à 50 produits
                }
                
                # Mettre en cache
                reports_cache[cache_key] = {
                    'data': report,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                REPORTS_GENERATED.labels(report_type='product_performance').inc()
                
                return report, 200
                
            except Exception as e:
                logger.error(f"Erreur lors de la génération du rapport de performance: {e}")
                return {'error': str(e)}, 500

@api.route('/dashboard/overview')
class DashboardOverviewResource(Resource):
    """Endpoint pour le tableau de bord général"""
    
    @api.doc('get_dashboard_overview', description='Tableau de bord vue d\'ensemble')
    def get(self):
        """Récupérer le tableau de bord général"""
        with REPORT_GENERATION_DURATION.labels(report_type='dashboard').time():
            try:
                cache_key = 'dashboard_overview'
                
                logger.info(f"[REPORTING] Début génération dashboard overview")
                
                # Vérifier le cache
                if cache_key in dashboard_cache and is_cache_valid(dashboard_cache[cache_key]):
                    logger.info(f"[REPORTING] Dashboard servi depuis le cache")
                    DASHBOARD_REQUESTS.labels(dashboard_type='overview_cached').inc()
                    return dashboard_cache[cache_key]['data'], 200
                
                # Récupérer les données des dernières 24h
                yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
                today = datetime.utcnow().strftime('%Y-%m-%d')
                
                logger.info(f"[REPORTING] Récupération données dashboard - Période: {yesterday} à {today}")
                
                sales_data = DataAggregator.get_sales_data(date_from=yesterday, date_to=today)
                inventory_data = DataAggregator.get_inventory_data()
                
                # Calculs du dashboard
                total_revenue_today = sum(sale.get('final_amount', 0) for sale in sales_data)
                total_transactions_today = len(sales_data)
                
                # Ventes par magasin
                sales_by_store = defaultdict(lambda: {'revenue': 0.0, 'transactions': 0})
                for sale in sales_data:
                    store_id = sale.get('store_id')
                    sales_by_store[store_id]['revenue'] += sale.get('final_amount', 0)
                    sales_by_store[store_id]['transactions'] += 1
                
                # Alertes de stock
                low_stock_count = len([item for item in inventory_data 
                                     if item.get('available_quantity', 0) <= item.get('reorder_point', 5)])
                
                # Top 5 produits vendus aujourd'hui
                product_sales = defaultdict(int)
                for sale in sales_data:
                    for item in sale.get('items', []):
                        product_sales[item['product_id']] += item['quantity']
                
                top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
                
                dashboard = {
                    'generated_at': datetime.utcnow().isoformat(),
                    'period': f"{yesterday} to {today}",
                    'summary': {
                        'total_revenue_today': round(total_revenue_today, 2),
                        'total_transactions_today': total_transactions_today,
                        'average_transaction_value': round(total_revenue_today / total_transactions_today, 2) if total_transactions_today > 0 else 0,
                        'low_stock_alerts': low_stock_count
                    },
                    'sales_by_store': dict(sales_by_store),
                    'top_products_today': [{'product_id': pid, 'quantity_sold': qty} for pid, qty in top_products],
                    'total_stores': len(sales_by_store),
                    'total_products_in_system': len(set(item['product_id'] for item in inventory_data))
                }
                
                # Mettre en cache
                dashboard_cache[cache_key] = {
                    'data': dashboard,
                    'cached_at': datetime.utcnow().isoformat()
                }
                
                logger.info(f"[REPORTING] Dashboard généré - Transactions: {total_transactions_today}, Revenus: {total_revenue_today}$, Magasins actifs: {len(sales_by_store)}")
                logger.debug(f"[REPORTING] Dashboard mis en cache")
                
                DASHBOARD_REQUESTS.labels(dashboard_type='overview').inc()
                
                return dashboard, 200
                
            except Exception as e:
                logger.error(f"[REPORTING] Erreur génération dashboard: {e}")
                return {'error': str(e)}, 500

@api.route('/dashboard/realtime')
class DashboardRealtimeResource(Resource):
    """Endpoint pour les données temps réel"""
    
    @api.doc('get_realtime_data', description='Données temps réel')
    def get(self):
        """Récupérer les données en temps réel"""
        try:
            # Données des dernières heures (pas de cache pour le temps réel)
            now = datetime.utcnow()
            hour_ago = (now - timedelta(hours=1)).strftime('%Y-%m-%d')
            
            recent_sales = DataAggregator.get_sales_data(date_from=hour_ago)
            
            # Filtrer les ventes de la dernière heure
            recent_sales = [
                sale for sale in recent_sales
                if datetime.fromisoformat(sale['timestamp']) > (now - timedelta(hours=1))
            ]
            
            realtime_data = {
                'timestamp': now.isoformat(),
                'last_hour': {
                    'transactions': len(recent_sales),
                    'revenue': sum(sale.get('final_amount', 0) for sale in recent_sales),
                    'items_sold': sum(len(sale.get('items', [])) for sale in recent_sales)
                },
                'recent_transactions': recent_sales[-10:] if recent_sales else []  # 10 dernières transactions
            }
            
            DASHBOARD_REQUESTS.labels(dashboard_type='realtime').inc()
            
            return realtime_data, 200
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données temps réel: {e}")
            return {'error': str(e)}, 500

@app.route('/health')
def health():
    """Endpoint de santé"""
    return {
        'status': 'healthy',
        'service': 'reporting-service',
        'timestamp': datetime.utcnow().isoformat(),
        'cache_stats': {
            'reports_cached': len(reports_cache),
            'dashboard_cached': len(dashboard_cache)
        },
        'dependencies': {
            'sales-service': 'available',
            'inventory-service': 'available',
            'product-service': 'available'
        }
    }, 200

@app.route('/metrics')
def metrics():
    """Endpoint pour les métriques Prometheus"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/cache/clear')
def clear_cache():
    """Vider le cache des rapports"""
    global reports_cache, dashboard_cache
    reports_cache.clear()
    dashboard_cache.clear()
    return {'message': 'Cache cleared successfully'}, 200

if __name__ == '__main__':
    logger.info("Démarrage du Reporting Service sur le port 8004")
    app.run(host='0.0.0.0', port=8004, debug=os.getenv('DEBUG', 'False').lower() == 'true')