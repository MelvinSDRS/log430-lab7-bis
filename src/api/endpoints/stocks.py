"""
Endpoints REST pour la consultation des stocks
UC2 - Consulter le stock d'un magasin spécifique
"""

from flask import request
from flask_restx import Namespace, Resource
from ...persistence.database import get_db_session
from ...domain.services import ServiceInventaire
from ...persistence.repositories import RepositoryStockEntite, RepositoryEntite
from ..auth import auth_token
from ..models import stock_entite_model, entite_model, error_model
from flask_restx import fields
import logging

logger = logging.getLogger(__name__)

ns_stocks = Namespace('stocks', description='Consultation des stocks par entité', path='/stocks')

stock_response = ns_stocks.model('StockEntite', stock_entite_model)
entite_response = ns_stocks.model('Entite', entite_model)
error_response = ns_stocks.model('Error', error_model)

stocks_paginated_model = {
    'data': fields.List(fields.Raw, description='Liste des stocks'),
    'meta': fields.Raw(description='Métadonnées de pagination'),
    '_links': fields.Raw(description='Liens HATEOAS pour la navigation')
}
stocks_paginated = ns_stocks.model('StocksPaginated', stocks_paginated_model)


@ns_stocks.route('')
class StockListResource(Resource):
    """Collection des stocks par entité"""

    @ns_stocks.doc('list_all_stocks', security='apikey')
    @ns_stocks.marshal_with(stocks_paginated)
    @ns_stocks.response(200, 'Succès')
    @ns_stocks.response(401, 'Non autorisé', error_response)
    @ns_stocks.param('page', 'Numéro de page (défaut: 1)', type=int)
    @ns_stocks.param('per_page', 'Éléments par page (défaut: 20, max: 100)', type=int)
    @ns_stocks.param('entite_id', 'Filtrer par ID d\'entité', type=int)
    @ns_stocks.param('produit_id', 'Filtrer par ID de produit', type=int)
    @ns_stocks.param('rupture', 'Afficher uniquement les produits en rupture (true/false)', type=bool)
    @auth_token
    def get(self):
        """
        Récupérer la liste de tous les stocks avec filtrage
        """
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        entite_id = request.args.get('entite_id', type=int)
        produit_id = request.args.get('produit_id', type=int)
        rupture = request.args.get('rupture', type=bool)
        
        session = get_db_session()
        try:
            repo_stock = RepositoryStockEntite(session)
            
            tous_stocks = repo_stock.lister_tous()
            
            if entite_id:
                tous_stocks = [s for s in tous_stocks if s.id_entite == entite_id]
            
            if produit_id:
                tous_stocks = [s for s in tous_stocks if s.id_produit == produit_id]
            
            if rupture:
                tous_stocks = [s for s in tous_stocks if s.quantite <= s.seuil_alerte]
            
            total = len(tous_stocks)
            start = (page - 1) * per_page
            end = start + per_page
            stocks_page = tous_stocks[start:end]
            
            stocks_data = []
            for stock in stocks_page:
                stock_dict = {
                    'id': stock.id,
                    'id_produit': stock.id_produit,
                    'id_entite': stock.id_entite,
                    'quantite': stock.quantite,
                    'seuil_alerte': stock.seuil_alerte,
                    'produit': None,
                    'entite': None
                }
                
                if stock.produit:
                    stock_dict['produit'] = {
                        'id': stock.produit.id,
                        'nom': stock.produit.nom,
                        'prix': float(stock.produit.prix),
                        'description': stock.produit.description
                    }
                
                if stock.entite:
                    stock_dict['entite'] = {
                        'id': stock.entite.id,
                        'nom': stock.entite.nom,
                        'type_entite': stock.entite.type_entite.value if stock.entite.type_entite else None,
                        'adresse': stock.entite.adresse
                    }
                
                stocks_data.append(stock_dict)
            
            pages = (total + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < pages
            
            # Liens HATEOAS
            links = {
                'self': f'/api/v1/stocks?page={page}&per_page={per_page}',
                'first': f'/api/v1/stocks?page=1&per_page={per_page}',
                'last': f'/api/v1/stocks?page={pages}&per_page={per_page}'
            }
            if has_prev:
                links['prev'] = f'/api/v1/stocks?page={page-1}&per_page={per_page}'
            if has_next:
                links['next'] = f'/api/v1/stocks?page={page+1}&per_page={per_page}'
            
            response = {
                'data': stocks_data,
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
            
            logger.info(f"Stocks récupérés - Page {page}, Total: {total}, Filtres: entite_id={entite_id}, produit_id={produit_id}, rupture={rupture}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stocks: {str(e)}")
            raise
        finally:
            session.close()


@ns_stocks.route('/entites/<int:entite_id>')
class StockEntiteResource(Resource):
    """UC2 - Stocks d'une entité spécifique"""

    @ns_stocks.doc('get_store_stocks', security='apikey')
    @ns_stocks.marshal_with(stocks_paginated)
    @ns_stocks.response(200, 'Succès')
    @ns_stocks.response(404, 'Entité introuvable', error_response)
    @ns_stocks.response(401, 'Non autorisé', error_response)
    @ns_stocks.param('page', 'Numéro de page (défaut: 1)', type=int)
    @ns_stocks.param('per_page', 'Éléments par page (défaut: 20, max: 100)', type=int)
    @ns_stocks.param('rupture', 'Afficher uniquement les produits en rupture (true/false)', type=bool)
    @ns_stocks.param('sort', 'Tri: quantite,asc|quantite,desc|nom,asc|nom,desc (défaut: nom,asc)', type=str)
    @auth_token
    def get(self, entite_id):
        """
        UC2 - Consulter le stock d'un magasin spécifique
        """
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        rupture = request.args.get('rupture', type=bool)
        sort = request.args.get('sort', 'nom,asc')
        
        session = get_db_session()
        try:
            repo_entite = RepositoryEntite(session)
            entite = repo_entite.obtenir_par_id(entite_id)
            if not entite:
                ns_stocks.abort(404, f"Entité avec l'ID {entite_id} introuvable")
            
            service_inventaire = ServiceInventaire(session)
            
            if rupture:
                stocks = service_inventaire.obtenir_produits_en_rupture(entite_id)
            else:
                stocks = service_inventaire.obtenir_stocks_par_entite(entite_id)
            
            if sort and stocks:
                sort_field, sort_order = sort.split(',') if ',' in sort else (sort, 'asc')
                reverse = sort_order.lower() == 'desc'
                
                if sort_field == 'quantite':
                    stocks.sort(key=lambda x: x.quantite, reverse=reverse)
                elif sort_field == 'nom' and stocks[0].produit:
                    stocks.sort(key=lambda x: x.produit.nom if x.produit else '', reverse=reverse)
            
            total = len(stocks)
            start = (page - 1) * per_page
            end = start + per_page
            stocks_page = stocks[start:end]
            
            stocks_data = []
            for stock in stocks_page:
                stock_dict = {
                    'id': stock.id,
                    'id_produit': stock.id_produit,
                    'id_entite': stock.id_entite,
                    'quantite': stock.quantite,
                    'seuil_alerte': stock.seuil_alerte,
                    'produit': None,
                    'entite': {
                        'id': entite.id,
                        'nom': entite.nom,
                        'type_entite': entite.type_entite.value if entite.type_entite else None,
                        'adresse': entite.adresse,
                        'statut': entite.statut
                    }
                }
                
                if stock.produit:
                    stock_dict['produit'] = {
                        'id': stock.produit.id,
                        'nom': stock.produit.nom,
                        'prix': float(stock.produit.prix),
                        'description': stock.produit.description,
                        'id_categorie': stock.produit.id_categorie
                    }
                
                stocks_data.append(stock_dict)
            
            pages = (total + per_page - 1) // per_page if total > 0 else 1
            has_prev = page > 1
            has_next = page < pages
            
            # Liens HATEOAS
            base_url = f'/api/v1/stocks/entites/{entite_id}'
            query_params = []
            if rupture:
                query_params.append('rupture=true')
            if sort != 'nom,asc':
                query_params.append(f'sort={sort}')
            
            query_string = '&'.join(query_params)
            separator = '&' if query_params else ''
            
            links = {
                'self': f'{base_url}?page={page}&per_page={per_page}{separator}{query_string}',
                'first': f'{base_url}?page=1&per_page={per_page}{separator}{query_string}',
                'last': f'{base_url}?page={pages}&per_page={per_page}{separator}{query_string}',
                'entite': f'/api/v1/stores/{entite_id}'
            }
            if has_prev:
                links['prev'] = f'{base_url}?page={page-1}&per_page={per_page}{separator}{query_string}'
            if has_next:
                links['next'] = f'{base_url}?page={page+1}&per_page={per_page}{separator}{query_string}'
            
            response = {
                'data': stocks_data,
                'meta': {
                    'page': page,
                    'per_page': per_page,
                    'total': total,
                    'pages': pages,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'entite': {
                        'id': entite.id,
                        'nom': entite.nom,
                        'type_entite': entite.type_entite.value if entite.type_entite else None
                    }
                },
                '_links': links
            }
            
            logger.info(f"Stocks entité récupérés - Entité: {entite_id}, Page: {page}, Total: {total}, Rupture: {rupture}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stocks de l'entité {entite_id}: {str(e)}")
            raise
        finally:
            session.close()


@ns_stocks.route('/entites/<int:entite_id>/produits/<int:produit_id>')
class StockProduitEntiteResource(Resource):
    """Stock d'un produit spécifique dans une entité"""

    @ns_stocks.doc('get_product_stock_in_store', security='apikey')
    @ns_stocks.marshal_with(stock_response)
    @ns_stocks.response(200, 'Succès')
    @ns_stocks.response(404, 'Stock introuvable', error_response)
    @ns_stocks.response(401, 'Non autorisé', error_response)
    @auth_token
    def get(self, entite_id, produit_id):
        """
        Consulter le stock d'un produit spécifique dans une entité
        """
        session = get_db_session()
        try:
            repo_stock = RepositoryStockEntite(session)
            stock = repo_stock.obtenir_par_produit_et_entite(produit_id, entite_id)
            
            if not stock:
                ns_stocks.abort(404, f"Stock du produit {produit_id} introuvable dans l'entité {entite_id}")
            
            response = {
                'id': stock.id,
                'id_produit': stock.id_produit,
                'id_entite': stock.id_entite,
                'quantite': stock.quantite,
                'seuil_alerte': stock.seuil_alerte,
                'produit': None,
                'entite': None
            }
            
            if stock.produit:
                response['produit'] = {
                    'id': stock.produit.id,
                    'nom': stock.produit.nom,
                    'prix': float(stock.produit.prix),
                    'description': stock.produit.description,
                    'id_categorie': stock.produit.id_categorie
                }
            
            if stock.entite:
                response['entite'] = {
                    'id': stock.entite.id,
                    'nom': stock.entite.nom,
                    'type_entite': stock.entite.type_entite.value if stock.entite.type_entite else None,
                    'adresse': stock.entite.adresse,
                    'statut': stock.entite.statut
                }
            
            logger.info(f"Stock produit-entité récupéré - Produit: {produit_id}, Entité: {entite_id}, Quantité: {stock.quantite}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du stock produit {produit_id} entité {entite_id}: {str(e)}")
            raise
        finally:
            session.close()


@ns_stocks.route('/ruptures')
class StockRupturesResource(Resource):
    """Produits en rupture de stock toutes entités"""

    @ns_stocks.doc('get_stock_shortages', security='apikey')
    @ns_stocks.marshal_with(stocks_paginated)
    @ns_stocks.response(200, 'Succès')
    @ns_stocks.response(401, 'Non autorisé', error_response)
    @ns_stocks.param('page', 'Numéro de page (défaut: 1)', type=int)
    @ns_stocks.param('per_page', 'Éléments par page (défaut: 20, max: 100)', type=int)
    @ns_stocks.param('entite_id', 'Filtrer par ID d\'entité', type=int)
    @auth_token
    def get(self):
        """
        Récupérer tous les produits en rupture de stock
        """
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        entite_id = request.args.get('entite_id', type=int)
        
        session = get_db_session()
        try:
            service_inventaire = ServiceInventaire(session)
            
            if entite_id:
                stocks_rupture = service_inventaire.obtenir_produits_en_rupture(entite_id)
            else:
                repo_stock = RepositoryStockEntite(session)
                tous_stocks = repo_stock.lister_tous()
                stocks_rupture = [s for s in tous_stocks if s.quantite <= s.seuil_alerte]
            
            total = len(stocks_rupture)
            start = (page - 1) * per_page
            end = start + per_page
            stocks_page = stocks_rupture[start:end]
            
            stocks_data = []
            for stock in stocks_page:
                stock_dict = {
                    'id': stock.id,
                    'id_produit': stock.id_produit,
                    'id_entite': stock.id_entite,
                    'quantite': stock.quantite,
                    'seuil_alerte': stock.seuil_alerte,
                    'produit': None,
                    'entite': None
                }
                
                if stock.produit:
                    stock_dict['produit'] = {
                        'id': stock.produit.id,
                        'nom': stock.produit.nom,
                        'prix': float(stock.produit.prix),
                        'description': stock.produit.description
                    }
                
                if stock.entite:
                    stock_dict['entite'] = {
                        'id': stock.entite.id,
                        'nom': stock.entite.nom,
                        'type_entite': stock.entite.type_entite.value if stock.entite.type_entite else None
                    }
                
                stocks_data.append(stock_dict)
            
            pages = (total + per_page - 1) // per_page if total > 0 else 1
            has_prev = page > 1
            has_next = page < pages
            
            links = {
                'self': f'/api/v1/stocks/ruptures?page={page}&per_page={per_page}',
                'first': f'/api/v1/stocks/ruptures?page=1&per_page={per_page}',
                'last': f'/api/v1/stocks/ruptures?page={pages}&per_page={per_page}'
            }
            if has_prev:
                links['prev'] = f'/api/v1/stocks/ruptures?page={page-1}&per_page={per_page}'
            if has_next:
                links['next'] = f'/api/v1/stocks/ruptures?page={page+1}&per_page={per_page}'
            
            response = {
                'data': stocks_data,
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
            
            logger.info(f"Stocks en rupture récupérés - Total: {total}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stocks en rupture: {str(e)}")
            raise
        finally:
            session.close() 