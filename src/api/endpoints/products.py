"""
Endpoints REST pour la gestion des produits
UC4 - Mettre à jour les informations d'un produit
"""

from flask import request
from flask_restx import Namespace, Resource, fields
from ...persistence.database import get_db_session
from ..auth import auth_token
from ..models import product_model, product_create_model, product_update_model, error_model
from ..bounded_contexts.product_catalog.application.product_application_service import ProductApplicationService
from ..bounded_contexts.product_catalog.infrastructure.product_repository_adapter import ProductRepositoryAdapter
import logging
from werkzeug.exceptions import NotFound

logger = logging.getLogger(__name__)

ns_products = Namespace('products', description='Gestion des produits', path='/products')

product_response = ns_products.model('Product', product_model)
product_create = ns_products.model('ProductCreate', product_create_model)
product_update = ns_products.model('ProductUpdate', product_update_model)
error_response = ns_products.model('Error', error_model)

products_paginated_model = {
    'data': fields.List(fields.Raw, description='Liste des produits'),
    'meta': fields.Raw(description='Métadonnées de pagination'),
    '_links': fields.Raw(description='Liens HATEOAS pour la navigation')
}
products_paginated = ns_products.model('ProductsPaginated', products_paginated_model)


@ns_products.route('')
class ProductListResource(Resource):
    """Collection de produits"""

    @ns_products.doc('list_products', security='apikey')
    @ns_products.response(200, 'Succès')
    @ns_products.response(401, 'Non autorisé', error_response)
    @ns_products.param('page', 'Numéro de page (défaut: 1)', type=int)
    @ns_products.param('per_page', 'Éléments par page (défaut: 20, max: 100)', type=int)
    @ns_products.param('search', 'Recherche par nom de produit', type=str)
    @ns_products.param('category', 'Filtrer par identifiant de catégorie', type=int)
    @ns_products.param('sort', 'Tri: nom,asc|nom,desc|prix,asc|prix,desc (défaut: nom,asc)', type=str)
    @auth_token
    def get(self):
        """
        Récupérer la liste des produits avec pagination, filtrage et tri
        """
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        search = request.args.get('search', '').strip()
        category = request.args.get('category', type=int)
        
        sort = request.args.get('sort', 'nom,asc')
        sort_field, sort_order = sort.split(',') if ',' in sort else (sort, 'asc')
        
        session = get_db_session()
        try:
            product_repo = ProductRepositoryAdapter(session)
            product_service = ProductApplicationService(product_repo)
            
            search_term = search if search else None
            tous_produits = product_service.list_products(
                search=search_term,
                category_id=category,
                sort_field=sort_field,
                sort_order=sort_order
            )
            
            # Pagination (reste au niveau API)
            total = len(tous_produits)
            start = (page - 1) * per_page
            end = start + per_page
            produits_page = tous_produits[start:end]
            
            pages = (total + per_page - 1) // per_page if total > 0 else 1
            has_prev = page > 1
            has_next = page < pages
            
            # Liens HATEOAS
            links = {
                'self': f'/api/v1/products?page={page}&per_page={per_page}',
                'first': f'/api/v1/products?page=1&per_page={per_page}',
                'last': f'/api/v1/products?page={pages}&per_page={per_page}'
            }
            if has_prev:
                links['prev'] = f'/api/v1/products?page={page-1}&per_page={per_page}'
            if has_next:
                links['next'] = f'/api/v1/products?page={page+1}&per_page={per_page}'
            
            response = {
                'data': produits_page,
                'meta': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_prev': has_prev,
                    'has_next': has_next
                },
                '_links': links
            }
            
            logger.info(f"Liste produits récupérée - Page {page}, Total: {total}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des produits: {str(e)}")
            raise
        finally:
            session.close()

    @ns_products.doc('create_product', security='apikey')
    @ns_products.expect(product_create)
    @ns_products.marshal_with(product_response, code=201)
    @ns_products.response(201, 'Produit créé')
    @ns_products.response(400, 'Données invalides', error_response)
    @ns_products.response(401, 'Non autorisé', error_response)
    @auth_token
    def post(self):
        """
        Créer un nouveau produit
        """
        data = request.get_json()
        
        # Validation des données requises
        required_fields = ['nom', 'prix', 'stock', 'id_categorie']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Le champ '{field}' est requis")
        
        session = get_db_session()
        try:
            product_repo = ProductRepositoryAdapter(session)
            product_service = ProductApplicationService(product_repo)
            
            # Préparation des données
            product_data = {
                'nom': data['nom'],
                'prix': data['prix'],
                'stock': data['stock'],
                'id_categorie': data['id_categorie'],
                'seuil_alerte': data.get('seuil_alerte', 5),
                'description': data.get('description')
            }
            
            response = product_service.create_product(product_data)
            
            logger.info(f"Produit créé - ID: {response['id']}, Nom: {response['nom']}")
            return response, 201
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du produit: {str(e)}")
            raise
        finally:
            session.close()


@ns_products.route('/<int:product_id>')
class ProductResource(Resource):
    """Ressource produit individuelle"""

    @ns_products.doc('get_product', security='apikey')
    @ns_products.marshal_with(product_response)
    @ns_products.response(200, 'Succès')
    @ns_products.response(404, 'Produit introuvable', error_response)
    @ns_products.response(401, 'Non autorisé', error_response)
    @auth_token
    def get(self, product_id):
        """
        Récupérer un produit par son ID
        """
        session = get_db_session()
        try:
            product_repo = ProductRepositoryAdapter(session)
            product_service = ProductApplicationService(product_repo)
            
            response = product_service.get_product_by_id(product_id)
            
            if not response:
                raise NotFound(description=f'Produit avec l\'ID {product_id} introuvable')
            
            logger.info(f"Produit récupéré - ID: {product_id}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du produit {product_id}: {str(e)}")
            raise
        finally:
            session.close()

    @ns_products.doc('update_product', security='apikey')
    @ns_products.expect(product_update)
    @ns_products.marshal_with(product_response)
    @ns_products.response(200, 'Produit mis à jour')
    @ns_products.response(404, 'Produit introuvable', error_response)
    @ns_products.response(400, 'Données invalides', error_response)
    @ns_products.response(401, 'Non autorisé', error_response)
    @auth_token
    def put(self, product_id):
        """
        UC4 - Mettre à jour complètement un produit
        """
        data = request.get_json()
        
        session = get_db_session()
        try:
            product_repo = ProductRepositoryAdapter(session)
            product_service = ProductApplicationService(product_repo)
            
            # Préparer les données de mise à jour
            updates = {}
            allowed_fields = ['nom', 'prix', 'stock', 'id_categorie', 'seuil_alerte', 'description']
            for field in allowed_fields:
                if field in data:
                    updates[field] = data[field]
            
            if updates:
                response = product_service.update_product(product_id, updates)
                logger.info(f"Produit mis à jour - ID: {product_id}, Champs: {list(updates.keys())}")
                return response
            else:
                # Si aucune mise à jour, retourner le produit actuel
                response = product_service.get_product_by_id(product_id)
                if not response:
                    raise NotFound(description=f'Produit avec l\'ID {product_id} introuvable')
                return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du produit {product_id}: {str(e)}")
            raise
        finally:
            session.close()

    @ns_products.doc('delete_product', security='apikey')
    @ns_products.response(204, 'Produit supprimé')
    @ns_products.response(404, 'Produit introuvable', error_response)
    @ns_products.response(401, 'Non autorisé', error_response)
    @auth_token
    def delete(self, product_id):
        """
        Supprimer un produit
        """
        session = get_db_session()
        try:
            product_repo = ProductRepositoryAdapter(session)
            product_service = ProductApplicationService(product_repo)
            
            success = product_service.delete_product(product_id)
            
            if not success:
                raise NotFound(description=f'Produit avec l\'ID {product_id} introuvable')
            
            logger.info(f"Produit supprimé - ID: {product_id}")
            return '', 204
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du produit {product_id}: {str(e)}")
            raise
        finally:
            session.close() 