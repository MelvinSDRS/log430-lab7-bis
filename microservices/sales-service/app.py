#!/usr/bin/env python3
"""
Sales Service - Microservice pour les transactions de vente
Port: 8003
Responsabilité: Ventes en magasin physique
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api
import os
import logging
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'sales-service-secret')

CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway"]
    }
})

api = Api(
    app,
    version='1.0',
    title='Sales Service API',
    description='Microservice pour les transactions de vente',
    doc='/docs',
    prefix='/api/v1'
)

@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'service': 'sales-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }, 200

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Sales Service démarré sur le port 8003")
    app.run(host='0.0.0.0', port=8003, debug=os.getenv('DEBUG', 'False').lower() == 'true') 