"""
Endpoints REST pour la gestion des entités/magasins
UC3 - Visualiser les performances globales des magasins
"""

from flask import request
from flask_restx import Namespace, Resource
from ...persistence.database import get_db_session
from ...domain.services import ServiceTableauBord
from ...persistence.repositories import RepositoryEntite
from ..auth import auth_token
from ..models import entite_model, indicateur_performance_model, error_model
from flask_restx import fields
from ..cache import cache_endpoint, get_cache_timeout, invalidate_cache_pattern
import logging

logger = logging.getLogger(__name__)

ns_stores = Namespace('stores', description='Gestion des entités et performances', path='/stores')

entite_response = ns_stores.model('Entite', entite_model)
indicateur_response = ns_stores.model('IndicateurPerformance', indicateur_performance_model)
error_response = ns_stores.model('Error', error_model)

stores_paginated_model = {
    'data': fields.List(fields.Raw, description='Liste des entités'),
    'meta': fields.Raw(description='Métadonnées de pagination'),
    '_links': fields.Raw(description='Liens HATEOAS pour la navigation')
}
stores_paginated = ns_stores.model('StoresPaginated', stores_paginated_model)


@ns_stores.route('')
class StoreListResource(Resource):
    """Collection des entités/magasins"""

    @ns_stores.doc('list_stores', security='apikey')
    @ns_stores.marshal_with(stores_paginated)
    @ns_stores.response(200, 'Succès')
    @ns_stores.response(401, 'Non autorisé', error_response)
    @ns_stores.param('page', 'Numéro de page (défaut: 1)', type=int)
    @ns_stores.param('per_page', 'Éléments par page (défaut: 20, max: 100)', type=int)
    @ns_stores.param('type', 'Filtrer par type d\'entité (MAGASIN, CENTRE_LOGISTIQUE, MAISON_MERE)', type=str)
    @ns_stores.param('statut', 'Filtrer par statut (ACTIVE, INACTIVE)', type=str)
    @auth_token
    def get(self):
        """
        Récupérer la liste des entités/magasins
        """
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        type_entite = request.args.get('type', '').strip()
        statut = request.args.get('statut', '').strip()
        
        session = get_db_session()
        try:
            repo_entite = RepositoryEntite(session)
            
            toutes_entites = repo_entite.lister_toutes()
            
            if type_entite:
                toutes_entites = [e for e in toutes_entites if e.type_entite.value == type_entite.upper()]
            
            if statut:
                toutes_entites = [e for e in toutes_entites if e.statut.upper() == statut.upper()]
            
            total = len(toutes_entites)
            start = (page - 1) * per_page
            end = start + per_page
            entites_page = toutes_entites[start:end]
            
            entites_data = []
            for entite in entites_page:
                entites_data.append({
                    'id': entite.id,
                    'nom': entite.nom,
                    'type_entite': entite.type_entite.value if entite.type_entite else None,
                    'adresse': entite.adresse,
                    'statut': entite.statut
                })
            
            pages = (total + per_page - 1) // per_page if total > 0 else 1
            has_prev = page > 1
            has_next = page < pages
            
            # Liens HATEOAS
            links = {
                'self': f'/api/v1/stores?page={page}&per_page={per_page}',
                'first': f'/api/v1/stores?page=1&per_page={per_page}',
                'last': f'/api/v1/stores?page={pages}&per_page={per_page}',
                'performances': '/api/v1/stores/performances'
            }
            if has_prev:
                links['prev'] = f'/api/v1/stores?page={page-1}&per_page={per_page}'
            if has_next:
                links['next'] = f'/api/v1/stores?page={page+1}&per_page={per_page}'
            
            response = {
                'data': entites_data,
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
            
            logger.info(f"Entités récupérées - Page {page}, Total: {total}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des entités: {str(e)}")
            raise
        finally:
            session.close()


@ns_stores.route('/<int:store_id>')
class StoreResource(Resource):
    """Ressource entité/magasin individuelle"""

    @ns_stores.doc('get_store', security='apikey')
    @ns_stores.marshal_with(entite_response)
    @ns_stores.response(200, 'Succès')
    @ns_stores.response(404, 'Entité introuvable', error_response)
    @ns_stores.response(401, 'Non autorisé', error_response)
    @auth_token
    def get(self, store_id):
        """
        Récupérer une entité/magasin par son ID
        """
        session = get_db_session()
        try:
            repo_entite = RepositoryEntite(session)
            entite = repo_entite.obtenir_par_id(store_id)
            
            if not entite:
                ns_stores.abort(404, f"Entité avec l'ID {store_id} introuvable")
            
            response = {
                'id': entite.id,
                'nom': entite.nom,
                'type_entite': entite.type_entite.value if entite.type_entite else None,
                'adresse': entite.adresse,
                'statut': entite.statut
            }
            
            logger.info(f"Entité récupérée - ID: {store_id}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'entité {store_id}: {str(e)}")
            raise
        finally:
            session.close()


@ns_stores.route('/performances')
class StorePerformancesResource(Resource):
    """UC3 - Performances globales des magasins"""

    @ns_stores.doc('get_store_performances', security='apikey')
    @ns_stores.response(200, 'Succès')
    @ns_stores.response(401, 'Non autorisé', error_response)
    @cache_endpoint(timeout=get_cache_timeout('stores_performances'), key_prefix='stores_')
    @auth_token
    def get(self):
        """
        UC3 - Visualiser les performances globales des magasins
        Fournit un tableau de bord regroupant des indicateurs clés de performance
        """
        session = get_db_session()
        try:
            service_tableau_bord = ServiceTableauBord(session)
            indicateurs = service_tableau_bord.obtenir_indicateurs_performance()
            
            indicateurs_data = []
            for indicateur in indicateurs:
                indicateurs_data.append({
                    'entite_id': indicateur.entite_id,
                    'entite_nom': indicateur.entite_nom,
                    'chiffre_affaires': float(indicateur.chiffre_affaires),
                    'nombre_ventes': indicateur.nombre_ventes,
                    'produits_en_rupture': indicateur.produits_en_rupture,
                    'produits_en_surstock': indicateur.produits_en_surstock,
                    'tendance_hebdomadaire': float(indicateur.tendance_hebdomadaire)
                })
            
            total_ca = sum(float(i.chiffre_affaires) for i in indicateurs)
            total_ventes = sum(i.nombre_ventes for i in indicateurs)
            total_ruptures = sum(i.produits_en_rupture for i in indicateurs)
            moyenne_tendance = sum(float(i.tendance_hebdomadaire) for i in indicateurs) / len(indicateurs) if indicateurs else 0
            
            # Liens HATEOAS
            links = {
                'self': '/api/v1/stores/performances',
                'stores': '/api/v1/stores',
                'dashboard': '/api/v1/reports/dashboard'
            }
            
            for indicateur in indicateurs:
                links[f'store_{indicateur.entite_id}'] = f'/api/v1/stores/{indicateur.entite_id}'
                links[f'stocks_store_{indicateur.entite_id}'] = f'/api/v1/stocks/entites/{indicateur.entite_id}'
            
            response = {
                'data': indicateurs_data,
                'summary': {
                    'total_magasins': len(indicateurs),
                    'chiffre_affaires_total': total_ca,
                    'nombre_ventes_total': total_ventes,
                    'produits_en_rupture_total': total_ruptures,
                    'tendance_moyenne': moyenne_tendance
                },
                '_links': links
            }
            
            logger.info(f"Performances globales récupérées - {len(indicateurs)} magasins, CA total: {total_ca}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des performances: {str(e)}")
            raise
        finally:
            session.close()


@ns_stores.route('/<int:store_id>/performance')
class StorePerformanceResource(Resource):
    """Performance d'un magasin spécifique"""

    @ns_stores.doc('get_store_performance', security='apikey')
    @ns_stores.marshal_with(indicateur_response)
    @ns_stores.response(200, 'Succès')
    @ns_stores.response(404, 'Entité introuvable', error_response)
    @ns_stores.response(401, 'Non autorisé', error_response)
    @auth_token
    def get(self, store_id):
        """
        Récupérer les indicateurs de performance d'un magasin spécifique
        """
        session = get_db_session()
        try:
            repo_entite = RepositoryEntite(session)
            entite = repo_entite.obtenir_par_id(store_id)
            if not entite:
                ns_stores.abort(404, f"Entité avec l'ID {store_id} introuvable")
            
            service_tableau_bord = ServiceTableauBord(session)
            tous_indicateurs = service_tableau_bord.obtenir_indicateurs_performance()
            
            indicateur = next((i for i in tous_indicateurs if i.entite_id == store_id), None)
            
            if not indicateur:
                response = {
                    'entite_id': store_id,
                    'entite_nom': entite.nom,
                    'chiffre_affaires': 0.0,
                    'nombre_ventes': 0,
                    'produits_en_rupture': 0,
                    'produits_en_surstock': 0,
                    'tendance_hebdomadaire': 0.0
                }
            else:
                response = {
                    'entite_id': indicateur.entite_id,
                    'entite_nom': indicateur.entite_nom,
                    'chiffre_affaires': float(indicateur.chiffre_affaires),
                    'nombre_ventes': indicateur.nombre_ventes,
                    'produits_en_rupture': indicateur.produits_en_rupture,
                    'produits_en_surstock': indicateur.produits_en_surstock,
                    'tendance_hebdomadaire': float(indicateur.tendance_hebdomadaire)
                }
            
            logger.info(f"Performance magasin récupérée - ID: {store_id}, CA: {response['chiffre_affaires']}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la performance du magasin {store_id}: {str(e)}")
            raise
        finally:
            session.close() 