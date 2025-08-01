#!/usr/bin/env python3
"""
Customer Service - Microservice pour la gestion des clients e-commerce
Port: 8005
Responsabilité: Comptes clients, profils, authentification
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
import hashlib
import jwt
from datetime import datetime, timedelta

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'customer-service-secret')
app.config['JWT_SECRET'] = os.getenv('JWT_SECRET', 'jwt-customer-secret')

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
    title='Customer Service API',
    description='Microservice pour la gestion des clients e-commerce',
    doc='/docs',
    prefix='/api/v1'
)

# Modèles Swagger
customer_model = api.model('Customer', {
    'id': fields.Integer(description='ID du client'),
    'email': fields.String(required=True, description='Email du client'),
    'nom': fields.String(required=True, description='Nom du client'),
    'prenom': fields.String(required=True, description='Prénom du client'),
    'telephone': fields.String(description='Numéro de téléphone'),
    'date_naissance': fields.Date(description='Date de naissance'),
    'actif': fields.Boolean(description='Compte actif')
})

address_model = api.model('Address', {
    'id': fields.Integer(description='ID de l\'adresse'),
    'type': fields.String(required=True, description='Type d\'adresse (livraison/facturation)'),
    'nom_complet': fields.String(required=True, description='Nom complet'),
    'adresse_ligne1': fields.String(required=True, description='Ligne 1 de l\'adresse'),
    'adresse_ligne2': fields.String(description='Ligne 2 de l\'adresse'),
    'ville': fields.String(required=True, description='Ville'),
    'province': fields.String(required=True, description='Province'),
    'code_postal': fields.String(required=True, description='Code postal'),
    'pays': fields.String(required=True, description='Pays')
})

auth_model = api.model('AuthRequest', {
    'email': fields.String(required=True, description='Email du client'),
    'password': fields.String(required=True, description='Mot de passe')
})

register_model = api.model('RegisterRequest', {
    'email': fields.String(required=True, description='Email du client'),
    'password': fields.String(required=True, description='Mot de passe'),
    'nom': fields.String(required=True, description='Nom du client'),
    'prenom': fields.String(required=True, description='Prénom du client'),
    'telephone': fields.String(description='Numéro de téléphone'),
    'date_naissance': fields.Date(description='Date de naissance')
})

# Import des services métier
from database import init_customer_db, get_customer_session
from services import CustomerService, AddressService, AuthService

# Initialisation de la base de données
db_session = None

def init_app():
    """Initialiser l'application avec la base de données"""
    global db_session
    db_session = init_customer_db()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.logger.info("[CUSTOMER] Service démarré sur le port 8005")
    app.logger.info("[CUSTOMER] Base de données initialisée")

# Endpoints Authentification
@api.route('/auth/register')
class CustomerRegister(Resource):
    @api.expect(register_model)
    @api.doc('register_customer', description='Créer un compte client')
    def post(self):
        """Créer un nouveau compte client"""
        try:
            data = request.get_json()
            
            app.logger.info(f"[CUSTOMER] Début enregistrement client - Email: {data.get('email', 'N/A')}")
            app.logger.debug(f"[CUSTOMER] Données enregistrement: {data}")
            
            auth_service = AuthService(db_session)
            customer = auth_service.register_customer(data)
            
            app.logger.info(f"[CUSTOMER] Client enregistré avec succès - Email: {customer['email']}, ID: {customer['id']}")
            return {
                'message': 'Compte créé avec succès',
                'customer': customer
            }, 201
            
        except ValueError as e:
            app.logger.warning(f"[CUSTOMER] Données invalides pour enregistrement: {str(e)}")
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"[CUSTOMER] Erreur enregistrement: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/auth/login')
class CustomerLogin(Resource):
    @api.expect(auth_model)
    @api.doc('login_customer', description='Authentifier un client')
    def post(self):
        """Authentifier un client et retourner un token JWT"""
        try:
            data = request.get_json()
            email = data.get('email', 'N/A')
            
            app.logger.info(f"[CUSTOMER] Tentative authentification - Email: {email}")
            
            auth_service = AuthService(db_session)
            result = auth_service.authenticate_customer(email, data.get('password', ''))
            
            if not result:
                app.logger.warning(f"[CUSTOMER] Échec authentification - Email: {email}")
                api.abort(401, "Email ou mot de passe incorrect")
            
            app.logger.info(f"[CUSTOMER] Authentification réussie - Email: {email}")
            return result, 200
            
        except Exception as e:
            app.logger.error(f"[CUSTOMER] Erreur authentification: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Endpoints Gestion des clients
@api.route('/customers')
class CustomerList(Resource):
    @api.marshal_list_with(customer_model)
    @api.doc('get_customers', description='Lister tous les clients (admin)')
    def get(self):
        """Récupérer la liste des clients (admin uniquement)"""
        try:
            # TODO: Ajouter vérification autorisation admin
            page = int(request.args.get('page', 1))
            per_page = min(int(request.args.get('per_page', 20)), 100)
            
            app.logger.info(f"[CUSTOMER] Requête liste clients - Page: {page}, Par page: {per_page}")
            
            service = CustomerService(db_session)
            customers = service.get_customers_paginated(page, per_page)
            total = service.count_customers()
            
            app.logger.info(f"[CUSTOMER] Liste clients récupérée - {len(customers)} clients sur {total} total")
            
            return {
                'data': customers,
                'meta': {
                    'page': page,
                    'per_page': per_page,
                    'total': total
                }
            }
        except Exception as e:
            app.logger.error(f"[CUSTOMER] Erreur récupération clients: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/customers/<int:customer_id>')
class Customer(Resource):
    @api.marshal_with(customer_model)
    @api.doc('get_customer', description='Récupérer un client par son ID')
    def get(self, customer_id):
        """Récupérer un client spécifique"""
        try:
            # TODO: Vérifier que l'utilisateur peut accéder à ce profil
            app.logger.info(f"[CUSTOMER] Recherche client - ID: {customer_id}")
            
            service = CustomerService(db_session)
            customer = service.get_customer_by_id(customer_id)
            
            if not customer:
                app.logger.warning(f"[CUSTOMER] Client non trouvé - ID: {customer_id}")
                api.abort(404, f"Client {customer_id} non trouvé")
            
            app.logger.info(f"[CUSTOMER] Client récupéré - ID: {customer_id}, Email: {customer.get('email', 'N/A')}")
            return customer
            
        except Exception as e:
            app.logger.error(f"[CUSTOMER] Erreur récupération client {customer_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.expect(customer_model)
    @api.marshal_with(customer_model)
    @api.doc('update_customer', description='Mettre à jour un client')
    def put(self, customer_id):
        """Mettre à jour un client"""
        try:
            # TODO: Vérifier autorisation
            data = request.get_json()
            
            app.logger.info(f"[CUSTOMER] Début mise à jour client - ID: {customer_id}")
            app.logger.debug(f"[CUSTOMER] Données de mise à jour: {data}")
            
            service = CustomerService(db_session)
            customer = service.update_customer(customer_id, data)
            
            if not customer:
                api.abort(404, f"Client {customer_id} non trouvé")
                
            app.logger.info(f"Client mis à jour: {customer['email']} (ID: {customer_id})")
            return customer
            
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"Erreur lors de la mise à jour du client {customer_id}: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Endpoints Adresses
@api.route('/customers/<int:customer_id>/addresses')
class CustomerAddresses(Resource):
    @api.marshal_list_with(address_model)
    @api.doc('get_customer_addresses', description='Récupérer les adresses d\'un client')
    def get(self, customer_id):
        """Récupérer les adresses d'un client"""
        try:
            service = AddressService(db_session)
            addresses = service.get_addresses_by_customer(customer_id)
            return addresses
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération des adresses: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.expect(address_model)
    @api.marshal_with(address_model, code=201)
    @api.doc('create_customer_address', description='Ajouter une adresse à un client')
    def post(self, customer_id):
        """Ajouter une nouvelle adresse à un client"""
        try:
            data = request.get_json()
            data['customer_id'] = customer_id
            
            service = AddressService(db_session)
            address = service.create_address(data)
            
            app.logger.info(f"Adresse créée pour client {customer_id}")
            return address, 201
            
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"Erreur lors de la création de l'adresse: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

@api.route('/customers/<int:customer_id>/addresses/<int:address_id>')
class CustomerAddress(Resource):
    @api.expect(address_model)
    @api.marshal_with(address_model)
    @api.doc('update_customer_address', description='Mettre à jour une adresse')
    def put(self, customer_id, address_id):
        """Mettre à jour une adresse"""
        try:
            data = request.get_json()
            service = AddressService(db_session)
            address = service.update_address(address_id, customer_id, data)
            
            if not address:
                api.abort(404, f"Adresse {address_id} non trouvée")
                
            return address
            
        except ValueError as e:
            api.abort(400, str(e))
        except Exception as e:
            app.logger.error(f"Erreur lors de la mise à jour de l'adresse: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")
    
    @api.doc('delete_customer_address', description='Supprimer une adresse')
    def delete(self, customer_id, address_id):
        """Supprimer une adresse"""
        try:
            service = AddressService(db_session)
            success = service.delete_address(address_id, customer_id)
            
            if not success:
                api.abort(404, f"Adresse {address_id} non trouvée")
            
            return {'message': f'Adresse {address_id} supprimée avec succès'}, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la suppression de l'adresse: {str(e)}")
            api.abort(500, f"Erreur interne: {str(e)}")

# Health Check
@app.route('/health')
def health_check():
    """Endpoint de santé pour le service"""
    return {
        'status': 'healthy',
        'service': 'customer-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0'
    }, 200

# Point d'entrée
if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=8005, debug=os.getenv('DEBUG', 'False').lower() == 'true') 