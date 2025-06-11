#!/usr/bin/env python3
"""
API REST pour le système POS Multi-Magasins
Architecture RESTful avec sécurité, CORS et documentation Swagger
"""

from flask import Flask
from flask_cors import CORS
from flask_restx import Api
import logging
import os
from logging.handlers import RotatingFileHandler

from .auth import auth_token
from .endpoints.products import ns_products
from .endpoints.stores import ns_stores  
from .endpoints.reports import ns_reports
from .endpoints.stocks import ns_stocks
from .error_handlers import register_error_handlers


def create_api_app():
    """Factory pour créer l'application API Flask"""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('API_SECRET_KEY', 'dev-api-secret-key-change-in-production')
    
    # Configuration CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5000"],
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Configuration Swagger/OpenAPI
    api = Api(
        app,
        version='1.0',
        title='POS Multi-Magasins API',
        description='API REST pour le système de point de vente multi-magasins avec gestion centralisée',
        doc='/api/docs',  # Interface Swagger UI
        prefix='/api/v1',
        contact_email='support@pos-multimagasins.com',
        security='apikey'
    )
    
    # Configuration de la sécurité globale
    api.authorizations = {
        'apikey': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Token d\'authentification (Bearer TOKEN)'
        }
    }
    
    api.add_namespace(ns_products)
    api.add_namespace(ns_stores)
    api.add_namespace(ns_reports)
    api.add_namespace(ns_stocks)
    
    configure_api_logging(app)
    register_error_handlers(app)
    
    @app.route('/api/health')
    def health_check():
        """Endpoint de santé pour vérifier le statut de l'API"""
        return {
            'status': 'healthy',
            'service': 'POS Multi-Magasins API',
            'version': '1.0'
        }, 200
    
    return app


def configure_api_logging(app):
    """Configuration du système de logging pour l'API"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # Handler pour l'API
        api_handler = RotatingFileHandler(
            'logs/pos_api.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        api_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        api_handler.setLevel(logging.INFO)
        app.logger.addHandler(api_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Démarrage de l\'API POS Multi-Magasins')


api_app = create_api_app()


if __name__ == '__main__':
    api_app.run(debug=True, host='0.0.0.0', port=8000) 