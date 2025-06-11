"""
Endpoints REST pour la génération de rapports
UC1 - Générer un rapport consolidé des ventes
"""

from flask import request
from flask_restx import Namespace, Resource
from datetime import datetime
from ...persistence.database import get_db_session
from ...domain.services import ServiceRapport, ServiceTableauBord
from ...persistence.repositories import RepositoryRapport
from ..auth import auth_token
from ..models import rapport_model, rapport_request_model, indicateur_performance_model, error_model
from flask_restx import fields
import logging
import json

logger = logging.getLogger(__name__)

ns_reports = Namespace('reports', description='Génération et consultation de rapports', path='/reports')

rapport_response = ns_reports.model('Rapport', rapport_model)
rapport_request = ns_reports.model('RapportRequest', rapport_request_model)
indicateur_response = ns_reports.model('IndicateurPerformance', indicateur_performance_model)
error_response = ns_reports.model('Error', error_model)

reports_paginated_model = {
    'data': fields.List(fields.Raw, description='Liste des rapports'),
    'meta': fields.Raw(description='Métadonnées de pagination'),
    '_links': fields.Raw(description='Liens HATEOAS pour la navigation')
}
reports_paginated = ns_reports.model('ReportsPaginated', reports_paginated_model)


@ns_reports.route('')
class ReportListResource(Resource):
    """Collection des rapports générés"""

    @ns_reports.doc('list_reports', security='apikey')
    @ns_reports.marshal_with(reports_paginated)
    @ns_reports.response(200, 'Succès')
    @ns_reports.response(401, 'Non autorisé', error_response)
    @ns_reports.param('page', 'Numéro de page (défaut: 1)', type=int)
    @ns_reports.param('per_page', 'Éléments par page (défaut: 20, max: 100)', type=int)
    @ns_reports.param('type', 'Filtrer par type de rapport', type=str)
    @ns_reports.param('date_from', 'Date de génération à partir de (YYYY-MM-DD)', type=str)
    @ns_reports.param('date_to', 'Date de génération jusqu\'à (YYYY-MM-DD)', type=str)
    @auth_token
    def get(self):
        """
        Récupérer la liste des rapports générés
        """
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        type_rapport = request.args.get('type', '').strip()
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        
        session = get_db_session()
        try:
            repo_rapport = RepositoryRapport(session)
            
            tous_rapports = repo_rapport.lister_tous()
            
            if type_rapport:
                tous_rapports = [r for r in tous_rapports if r.type_rapport == type_rapport.upper()]
            
            if date_from:
                try:
                    date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                    tous_rapports = [r for r in tous_rapports if r.date_generation >= date_from_obj]
                except ValueError:
                    raise ValueError("Format de date invalide pour date_from. Utilisez YYYY-MM-DD")
            
            if date_to:
                try:
                    date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                    tous_rapports = [r for r in tous_rapports if r.date_generation <= date_to_obj]
                except ValueError:
                    raise ValueError("Format de date invalide pour date_to. Utilisez YYYY-MM-DD")
            
            tous_rapports.sort(key=lambda x: x.date_generation, reverse=True)
            
            total = len(tous_rapports)
            start = (page - 1) * per_page
            end = start + per_page
            rapports_page = tous_rapports[start:end]
            
            rapports_data = []
            for rapport in rapports_page:
                rapports_data.append({
                    'id': rapport.id,
                    'titre': rapport.titre,
                    'type_rapport': rapport.type_rapport,
                    'date_generation': rapport.date_generation.isoformat(),
                    'date_debut': rapport.date_debut.isoformat(),
                    'date_fin': rapport.date_fin.isoformat(),
                    'contenu_json': rapport.contenu_json,
                    'genere_par': rapport.genere_par
                })
            
            pages = (total + per_page - 1) // per_page if total > 0 else 1
            has_prev = page > 1
            has_next = page < pages
            
            # Liens HATEOAS
            links = {
                'self': f'/api/v1/reports?page={page}&per_page={per_page}',
                'first': f'/api/v1/reports?page=1&per_page={per_page}',
                'last': f'/api/v1/reports?page={pages}&per_page={per_page}',
                'generate_sales': '/api/v1/reports/sales/consolidated',
                'dashboard': '/api/v1/reports/dashboard'
            }
            if has_prev:
                links['prev'] = f'/api/v1/reports?page={page-1}&per_page={per_page}'
            if has_next:
                links['next'] = f'/api/v1/reports?page={page+1}&per_page={per_page}'
            
            response = {
                'data': rapports_data,
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
            
            logger.info(f"Rapports récupérés - Page {page}, Total: {total}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des rapports: {str(e)}")
            raise
        finally:
            session.close()


@ns_reports.route('/sales/consolidated')
class ConsolidatedSalesReportResource(Resource):
    """UC1 - Génération de rapport consolidé des ventes"""

    @ns_reports.doc('generate_consolidated_sales_report', security='apikey')
    @ns_reports.expect(rapport_request)
    @ns_reports.marshal_with(rapport_response, code=201)
    @ns_reports.response(201, 'Rapport généré')
    @ns_reports.response(400, 'Données invalides', error_response)
    @ns_reports.response(401, 'Non autorisé', error_response)
    @auth_token
    def post(self):
        """
        UC1 - Générer un rapport consolidé des ventes
        Permet d'obtenir un résumé agrégé des ventes réalisées dans tous les magasins pour une période donnée
        """
        data = request.get_json()
        
        required_fields = ['date_debut', 'date_fin', 'genere_par']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Le champ '{field}' est requis")
        
        try:
            date_debut = datetime.strptime(data['date_debut'], '%Y-%m-%d')
            date_fin = datetime.strptime(data['date_fin'], '%Y-%m-%d')
            
            date_fin = date_fin.replace(hour=23, minute=59, second=59)
            
        except ValueError:
            raise ValueError("Format de date invalide. Utilisez YYYY-MM-DD")
        
        if date_debut > date_fin:
            raise ValueError("La date de début doit être antérieure à la date de fin")
        
        session = get_db_session()
        try:
            service_rapport = ServiceRapport(session)
            
            rapport = service_rapport.generer_rapport_ventes_consolide(
                date_debut, 
                date_fin, 
                data['genere_par']
            )
            
            response = {
                'id': rapport.id,
                'titre': rapport.titre,
                'type_rapport': rapport.type_rapport,
                'date_generation': rapport.date_generation.isoformat(),
                'date_debut': rapport.date_debut.isoformat(),
                'date_fin': rapport.date_fin.isoformat(),
                'contenu_json': rapport.contenu_json,
                'genere_par': rapport.genere_par
            }
            
            logger.info(f"Rapport consolidé généré - ID: {rapport.id}, Période: {data['date_debut']} à {data['date_fin']}")
            return response, 201
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport consolidé: {str(e)}")
            raise
        finally:
            session.close()


@ns_reports.route('/stocks')
class StocksReportResource(Resource):
    """Rapport des stocks"""

    @ns_reports.doc('generate_stocks_report', security='apikey')
    @ns_reports.marshal_with(rapport_response, code=201)
    @ns_reports.response(201, 'Rapport généré')
    @ns_reports.response(400, 'Données invalides', error_response)
    @ns_reports.response(401, 'Non autorisé', error_response)
    @auth_token
    def post(self):
        """
        Générer un rapport des stocks actuels de toutes les entités
        """
        data = request.get_json() or {}
        
        if 'genere_par' not in data:
            raise ValueError("Le champ 'genere_par' est requis")
        
        session = get_db_session()
        try:
            service_rapport = ServiceRapport(session)
            
            rapport = service_rapport.generer_rapport_stocks(data['genere_par'])
            
            response = {
                'id': rapport.id,
                'titre': rapport.titre,
                'type_rapport': rapport.type_rapport,
                'date_generation': rapport.date_generation.isoformat(),
                'date_debut': rapport.date_debut.isoformat(),
                'date_fin': rapport.date_fin.isoformat(),
                'contenu_json': rapport.contenu_json,
                'genere_par': rapport.genere_par
            }
            
            logger.info(f"Rapport stocks généré - ID: {rapport.id}")
            return response, 201
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport stocks: {str(e)}")
            raise
        finally:
            session.close()


@ns_reports.route('/dashboard')
class DashboardResource(Resource):
    """Tableau de bord avec indicateurs temps réel"""

    @ns_reports.doc('get_dashboard', security='apikey')
    @ns_reports.response(200, 'Succès')
    @ns_reports.response(401, 'Non autorisé', error_response)
    @auth_token
    def get(self):
        """
        Récupérer le tableau de bord avec indicateurs temps réel
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
            
            metriques_globales = {
                'total_magasins': len(indicateurs),
                'chiffre_affaires_total': sum(float(i.chiffre_affaires) for i in indicateurs),
                'nombre_ventes_total': sum(i.nombre_ventes for i in indicateurs),
                'produits_en_rupture_total': sum(i.produits_en_rupture for i in indicateurs),
                'produits_en_surstock_total': sum(i.produits_en_surstock for i in indicateurs),
                'tendance_moyenne': sum(float(i.tendance_hebdomadaire) for i in indicateurs) / len(indicateurs) if indicateurs else 0
            }
            
            alertes = service_tableau_bord.detecter_alertes_critiques()
            
            # Liens HATEOAS
            links = {
                'self': '/api/v1/reports/dashboard',
                'stores': '/api/v1/stores',
                'performances': '/api/v1/stores/performances',
                'stocks_ruptures': '/api/v1/stocks/ruptures',
                'generate_sales_report': '/api/v1/reports/sales/consolidated'
            }
            
            response = {
                'timestamp': datetime.now().isoformat(),
                'indicateurs_magasins': indicateurs_data,
                'metriques_globales': metriques_globales,
                'alertes_critiques': alertes,
                '_links': links
            }
            
            logger.info(f"Tableau de bord récupéré - {len(indicateurs)} magasins, {len(alertes)} alertes")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du tableau de bord: {str(e)}")
            raise
        finally:
            session.close()


@ns_reports.route('/<int:report_id>')
class ReportResource(Resource):
    """Ressource rapport individuel"""

    @ns_reports.doc('get_report', security='apikey')
    @ns_reports.marshal_with(rapport_response)
    @ns_reports.response(200, 'Succès')
    @ns_reports.response(404, 'Rapport introuvable', error_response)
    @ns_reports.response(401, 'Non autorisé', error_response)
    @auth_token
    def get(self, report_id):
        """
        Récupérer un rapport par son ID
        """
        session = get_db_session()
        try:
            repo_rapport = RepositoryRapport(session)
            rapport = repo_rapport.obtenir_par_id(report_id)
            
            if not rapport:
                ns_reports.abort(404, f"Rapport avec l'ID {report_id} introuvable")
            
            response = {
                'id': rapport.id,
                'titre': rapport.titre,
                'type_rapport': rapport.type_rapport,
                'date_generation': rapport.date_generation.isoformat(),
                'date_debut': rapport.date_debut.isoformat(),
                'date_fin': rapport.date_fin.isoformat(),
                'contenu_json': rapport.contenu_json,
                'genere_par': rapport.genere_par
            }
            
            logger.info(f"Rapport récupéré - ID: {report_id}")
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du rapport {report_id}: {str(e)}")
            raise
        finally:
            session.close()

    @ns_reports.doc('delete_report', security='apikey')
    @ns_reports.response(204, 'Rapport supprimé')
    @ns_reports.response(404, 'Rapport introuvable', error_response)
    @ns_reports.response(401, 'Non autorisé', error_response)
    @auth_token
    def delete(self, report_id):
        """
        Supprimer un rapport
        """
        session = get_db_session()
        try:
            repo_rapport = RepositoryRapport(session)
            rapport = repo_rapport.obtenir_par_id(report_id)
            
            if not rapport:
                ns_reports.abort(404, f"Rapport avec l'ID {report_id} introuvable")
            
            repo_rapport.supprimer(report_id)
            
            logger.info(f"Rapport supprimé - ID: {report_id}")
            return '', 204
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du rapport {report_id}: {str(e)}")
            raise
        finally:
            session.close() 