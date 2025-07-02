#!/usr/bin/env python3
"""
Reporting Service - Microservice pour l'analytique et rapports
Port: 8004
Responsabilité: Rapports, tableaux de bord, analytique
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api
import os
import logging
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'reporting-service-secret')

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
    title='Reporting Service API',
    description='Microservice pour l\'analytique et rapports',
    doc='/docs',
    prefix='/api/v1'
)

@app.route('/health')
def health_check():
    return {
        'status': 'healthy',
        'service': 'reporting-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }, 200

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.logger.info("Reporting Service démarré sur le port 8004")
    app.run(host='0.0.0.0', port=8004, debug=os.getenv('DEBUG', 'False').lower() == 'true') 