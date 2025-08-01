#!/usr/bin/env python3
"""
Product Service - Microservice pour la gestion des produits
Port: 8001
Responsabilité: Catalogue produits, CRUD, catégories
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
from datetime import datetime

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'product-service-secret')

# CORS pour intégration API Gateway
CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway"]
    }
})

# API Documentation
api = Api(
    app,
    version='1.0',
    title='Product Service API',
    description='Microservice pour la gestion du catalogue produits',
    doc='/docs',
    prefix='/api/v1'
)

# Modèles Swagger
product_model = api.model('Product', {
    'id': fields.Integer(description='ID du produit'),
    'nom': fields.String(required=True, description='Nom du produit'),
    'prix': fields.Float(required=True, description='Prix du produit'),
    'stock': fields.Integer(required=True, description='Stock disponible'),
    'id_categorie': fields.Integer(required=True, description='ID de la catégorie'),
    'seuil_alerte': fields.Integer(description='Seuil d\'alerte stock'),
    'description': fields.String(description='Description du produit')
})

category_model = api.model('Category', {
    'id': fields.Integer(description='ID de la catégorie'),
    'nom': fields.String(required=True, description='Nom de la catégorie'),
    'description': fields.String(description='Description de la catégorie')
})

# Import des services métier (à adapter depuis l'existant)
from database import init_product_db, get_product_session
from services import ProductService, CategoryService

# Initialisation de la base de données
db_session = None

def init_app():
    """Initialiser l'application avec la base de données"""
    global db_session
    db_session = init_product_db()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.logger.info("[PRODUCT] Service démarré sur le port 8001")
    app.logger.info("[PRODUCT] Base de données initialisée")

# Endpoints Produits
@api.route('/products')
class ProductList(Resource):
    @api.marshal_list_with(product_model)
    @api.doc('get_products', description='Lister tous les produits')
    def get(self):
        """Récupérer la liste des produits avec pagination"""
        try:
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            search = request.args.get('search', '')
            
            app.logger.info(f"[PRODUCT] Requête liste produits - Page: {page}, Par page: {per_page}, Recherche: '{search}'")
            
            service = ProductService(db_session)
            products = service.get_products_paginated(page, per_page, search)
            total = service.count_products(search)
            
            app.logger.debug(f"[PRODUCT] Récupéré {len(products)} produits sur {total} total")
            
            result = {
                'data': products,
                'meta': {
                    'page': page,
                    'per_page': per_page,
                    'total': total
                }
            }
            
            app.logger.info(f"[PRODUCT] Liste produits rétournée - {len(products)} produits")
            return result
            
        except Exception as e:
            app.logger.error(f"[PRODUCT] Erreur récupération produits: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.expect(product_model)
    @api.marshal_with(product_model, code=201)
    @api.doc('create_product', description='Créer un nouveau produit')
    def post(self):
        """Créer un nouveau produit"""
        try:
            data = request.get_json()
            
            app.logger.info(f"[PRODUCT] Début création produit - Nom: {data.get('nom', 'N/A')}")
            app.logger.debug(f"[PRODUCT] Données produit reçues: {data}")
            
            service = ProductService(db_session)
            product = service.create_product(data)
            
            app.logger.info(f"[PRODUCT] Produit créé avec succès - Nom: {product['nom']}, ID: {product['id']}, Prix: {product.get('prix')}$")
            return product, 201
            
        except ValueError as e:
            app.logger.warning(f"[PRODUCT] Données invalides pour création produit: {str(e)}")
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"[PRODUCT] Erreur création produit: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/products/<int:product_id>')
class Product(Resource):
    @api.marshal_with(product_model)
    @api.doc('get_product', description='Récupérer un produit par son ID')
    def get(self, product_id):
        """Récupérer un produit spécifique"""
        try:
            app.logger.debug(f"[PRODUCT] Recherche produit ID: {product_id}")
            
            service = ProductService(db_session)
            product = service.get_product_by_id(product_id)
            
            if not product:
                app.logger.warning(f"[PRODUCT] Produit non trouvé - ID: {product_id}")
                api.abort(404, f"Produit {product_id} non trouvé")
            
            app.logger.info(f"[PRODUCT] Produit récupéré - ID: {product_id}, Nom: {product.get('nom', 'N/A')}")
            return product
            
        except Exception as e:
            app.logger.error(f"[PRODUCT] Erreur récupération produit {product_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.expect(product_model)
    @api.marshal_with(product_model)
    @api.doc('update_product', description='Mettre à jour un produit')
    def put(self, product_id):
        """Mettre à jour un produit"""
        try:
            data = request.get_json()
            
            app.logger.info(f"[PRODUCT] Début mise à jour produit ID: {product_id}")
            app.logger.debug(f"[PRODUCT] Données de mise à jour: {data}")
            
            service = ProductService(db_session)
            product = service.update_product(product_id, data)
            
            if not product:
                app.logger.warning(f"[PRODUCT] Produit non trouvé pour mise à jour - ID: {product_id}")
                api.abort(404, f"Produit {product_id} non trouvé")
                
            app.logger.info(f"[PRODUCT] Produit mis à jour avec succès - ID: {product_id}, Nom: {product['nom']}")
            return product
            
        except ValueError as e:
            app.logger.warning(f"[PRODUCT] Données invalides pour mise à jour produit {product_id}: {str(e)}")
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"[PRODUCT] Erreur mise à jour produit {product_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.doc('delete_product', description='Supprimer un produit')
    def delete(self, product_id):
        """Supprimer un produit"""
        try:
            app.logger.info(f"[PRODUCT] Début suppression produit ID: {product_id}")
            
            service = ProductService(db_session)
            success = service.delete_product(product_id)
            
            if not success:
                app.logger.warning(f"[PRODUCT] Produit non trouvé pour suppression - ID: {product_id}")
                api.abort(404, f"Produit {product_id} non trouvé")
            
            app.logger.info(f"[PRODUCT] Produit supprimé avec succès - ID: {product_id}")
            return {'message': f'Produit {product_id} supprimé avec succès'}, 200
            
        except Exception as e:
            app.logger.error(f"[PRODUCT] Erreur suppression produit {product_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Endpoints Catégories
@api.route('/categories')
class CategoryList(Resource):
    @api.marshal_list_with(category_model)
    @api.doc('get_categories', description='Lister toutes les catégories')
    def get(self):
        """Récupérer la liste des catégories"""
        try:
            app.logger.info(f"[PRODUCT] Requête liste catégories")
            
            service = CategoryService(db_session)
            categories = service.get_all_categories()
            
            app.logger.info(f"[PRODUCT] Catégories récupérées - Total: {len(categories)}")
            return categories
            
        except Exception as e:
            app.logger.error(f"[PRODUCT] Erreur récupération catégories: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Health Check
@app.route('/health')
def health_check():
    """Endpoint de santé pour le service"""
    app.logger.debug(f"[PRODUCT] Health check effectué")
    return {
        'status': 'healthy',
        'service': 'product-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }, 200

# Point d'entrée
if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=8001, debug=os.getenv('DEBUG', 'False').lower() == 'true') 