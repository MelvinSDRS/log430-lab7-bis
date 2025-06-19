"""
Système d'authentification pour l'API REST
Implémentation simple avec token statique
"""

import os
from functools import wraps
from flask import request, current_app
from datetime import datetime
import logging


logger = logging.getLogger(__name__)

# Token d'authentification statique
API_TOKEN = os.getenv('API_TOKEN', 'pos-api-token-2025')


def auth_token(f):
    """
    Décorateur pour vérifier l'authentification par token
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                logger.warning(f"Format d'authentification invalide: {auth_header}")
                return {
                    'timestamp': datetime.now().isoformat() + 'Z',
                    'status': 401,
                    'error': 'Unauthorized',
                    'message': 'Format d\'authentification invalide. Utilisez: Bearer TOKEN',
                    'path': request.path
                }, 401
        
        if not token:
            logger.warning(f"Tentative d'accès non autorisée à {request.path}")
            return {
                'timestamp': datetime.now().isoformat() + 'Z',
                'status': 401,
                'error': 'Unauthorized',
                'message': 'Token d\'authentification requis',
                'path': request.path
            }, 401
        
        if token != API_TOKEN:
            logger.warning(f"Token invalide utilisé pour accéder à {request.path}")
            return {
                'timestamp': datetime.now().isoformat() + 'Z',
                'status': 401,
                'error': 'Unauthorized',
                'message': 'Token d\'authentification invalide',
                'path': request.path
            }, 401
        
        logger.info(f"Accès autorisé à {request.path}")
        return f(*args, **kwargs)
    
    return decorated_function


def get_api_token():
    """Retourner le token API pour les tests"""
    return API_TOKEN 