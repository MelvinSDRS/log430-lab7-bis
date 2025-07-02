#!/usr/bin/env python3
"""
Inventory Service - Microservice pour la gestion des stocks
Port: 8002
Responsabilité: Stocks par entité, approvisionnement, alertes
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
from datetime import datetime

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'inventory-service-secret')

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
    title='Inventory Service API',
    description='Microservice pour la gestion des stocks',
    doc='/docs',
    prefix='/api/v1'
)

# Health Check
@app.route('/health')
def health_check():
    """Endpoint de santé pour le service"""
    return {
        'status': 'healthy',
        'service': 'inventory-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }, 200

# Point d'entrée
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Inventory Service démarré sur le port 8002")
    app.run(host='0.0.0.0', port=8002, debug=os.getenv('DEBUG', 'False').lower() == 'true') 