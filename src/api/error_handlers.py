"""
Gestionnaires d'erreur standardisés pour l'API REST
"""

from flask import jsonify, request, Response
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """Enregistrer tous les gestionnaires d'erreur"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Gestionnaire pour les erreurs 400 Bad Request"""
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 400,
            'error': 'Bad Request',
            'message': 'Requête malformée ou paramètres invalides',
            'path': request.path
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Gestionnaire pour les erreurs 401 Unauthorized"""
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 401,
            'error': 'Unauthorized',
            'message': 'Authentification requise',
            'path': request.path
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Gestionnaire pour les erreurs 403 Forbidden"""
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 403,
            'error': 'Forbidden',
            'message': 'Accès interdit à cette ressource',
            'path': request.path
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Gestionnaire pour les erreurs 404 Not Found"""
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 404,
            'error': 'Not Found',
            'message': 'Ressource introuvable',
            'path': request.path
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Gestionnaire pour les erreurs 405 Method Not Allowed"""
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 405,
            'error': 'Method Not Allowed',
            'message': 'Méthode HTTP non autorisée pour cette ressource',
            'path': request.path
        }), 405
    
    @app.errorhandler(406)
    def not_acceptable(error):
        """Gestionnaire pour les erreurs 406 Not Acceptable"""
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 406,
            'error': 'Not Acceptable',
            'message': 'Format de réponse non supporté',
            'path': request.path
        }), 406
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """Gestionnaire pour les erreurs 500 Internal Server Error"""
        logger.error(f"Erreur interne: {str(error)}")
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 500,
            'error': 'Internal Server Error',
            'message': 'Erreur interne du serveur',
            'path': request.path
        }), 500
    
    @app.errorhandler(ValueError)
    def handle_value_error(error):
        """Gestionnaire pour les erreurs de validation métier"""
        logger.warning(f"Erreur de validation: {str(error)}")
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 400,
            'error': 'Bad Request',
            'message': str(error),
            'path': request.path
        }), 400
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        """Gestionnaire générique pour toutes les autres exceptions"""
        # Ne pas traiter les objets Response Flask
        if isinstance(error, Response):
            return error
        
        if "Object of type Response is not JSON serializable" in str(error):
            return jsonify({
                'timestamp': datetime.now().isoformat() + 'Z',
                'status': 401,
                'error': 'Unauthorized',
                'message': 'Authentification requise',
                'path': request.path
            }), 401
        
        logger.error(f"Exception non gérée: {str(error)}")
        return jsonify({
            'timestamp': datetime.now().isoformat() + 'Z',
            'status': 500,
            'error': 'Internal Server Error',
            'message': 'Une erreur inattendue s\'est produite',
            'path': request.path
        }), 500 