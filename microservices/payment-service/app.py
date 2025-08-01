#!/usr/bin/env python3
"""
Payment Service - Microservice pour le traitement des paiements
Port: 8009
Responsabilité: Traitement paiements, remboursements, transactions
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource, fields
import os
import logging
import uuid
import random
import time
from datetime import datetime
from typing import Dict, Any

# Configuration de base
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'payment-service-secret')

CORS(app, resources={
    r"/api/*": {
        "origins": ["*"],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Gateway", "X-API-Key"]
    }
})

api = Api(
    app,
    version='1.0',
    title='Payment Service API',
    description='Microservice pour le traitement des paiements',
    doc='/docs',
    prefix='/api/v1'
)

# Configuration des échecs simulés
failure_config = {
    'enabled': os.getenv('SIMULATE_FAILURES', 'false').lower() == 'true',
    'failure_rate': float(os.getenv('FAILURE_RATE', '0.1')),
    'failure_on_amount': os.getenv('FAIL_ON_AMOUNT'),
}

transactions_db = {}
refunds_db = {}

# Modèles Swagger
payment_request_model = api.model('PaymentRequest', {
    'transaction_id': fields.String(required=True, description='ID de transaction unique'),
    'customer_id': fields.Integer(required=True, description='ID du client'),
    'amount': fields.Float(required=True, description='Montant à débiter'),
    'currency': fields.String(required=True, description='Devise (CAD, USD, EUR)'),
    'payment_method': fields.String(required=True, description='Méthode de paiement'),
    'card_details': fields.Raw(description='Détails de la carte'),
    'billing_address': fields.Raw(description='Adresse de facturation')
})

refund_request_model = api.model('RefundRequest', {
    'original_transaction_id': fields.String(required=True, description='ID de la transaction originale'),
    'refund_amount': fields.Float(required=True, description='Montant du remboursement'),
    'reason': fields.String(description='Raison du remboursement')
})

payment_response_model = api.model('PaymentResponse', {
    'transaction_id': fields.String(description='ID de la transaction'),
    'status': fields.String(description='Statut du paiement'),
    'amount': fields.Float(description='Montant traité'),
    'currency': fields.String(description='Devise'),
    'payment_method': fields.String(description='Méthode utilisée'),
    'processed_at': fields.DateTime(description='Date de traitement'),
    'authorization_code': fields.String(description='Code d\'autorisation'),
    'gateway_response': fields.Raw(description='Réponse de la passerelle')
})

def should_simulate_failure(amount: float, transaction_id: str) -> tuple[bool, str]:
    """Détermine si on doit simuler un échec"""
    if not failure_config['enabled']:
        return False, ""
    
    # Échec sur montant spécifique
    if failure_config['failure_on_amount']:
        target_amount = float(failure_config['failure_on_amount'])
        if abs(amount - target_amount) < 0.01:
            return True, f"Échec simulé pour le montant {amount}"
    
    # Échec aléatoire selon le taux configuré
    if random.random() < failure_config['failure_rate']:
        error_reasons = [
            "Insufficient funds",
            "Card declined",
            "Card expired",
            "Invalid CVV",
            "Blocked card",
            "Daily limit exceeded"
        ]
        return True, random.choice(error_reasons)
    
    return False, ""

@api.route('/payment/process')
class PaymentProcessResource(Resource):
    """Endpoint principal pour traiter un paiement"""
    
    @api.expect(payment_request_model)
    @api.marshal_with(payment_response_model)
    @api.doc('process_payment', description='Traiter un paiement')
    def post(self):
        """Traiter un nouveau paiement"""
        try:
            data = request.get_json()
            
            # Validation des données
            transaction_id = data.get('transaction_id')
            customer_id = data.get('customer_id')
            amount = data.get('amount')
            currency = data.get('currency', 'CAD')
            
            app.logger.info(f"[PAYMENT] Début traitement paiement - Transaction: {transaction_id}, Client: {customer_id}, Montant: {amount} {currency}")
            
            if not all([transaction_id, customer_id, amount]):
                app.logger.warning(f"[PAYMENT] Données manquantes - Transaction: {transaction_id}, Data: {data}")
                return {'error': 'transaction_id, customer_id et amount sont requis'}, 400
            
            if amount <= 0:
                app.logger.warning(f"[PAYMENT] Montant invalide - Transaction: {transaction_id}, Montant: {amount}")
                return {'error': 'Le montant doit être positif'}, 400
            
            # Vérifier si la transaction existe déjà
            if transaction_id in transactions_db:
                existing = transactions_db[transaction_id]
                app.logger.info(f"[PAYMENT] Transaction existante retournée - ID: {transaction_id}, Statut: {existing.get('status')}")
                return existing, 200
            
            # Simulation du temps de traitement
            processing_time = random.uniform(0.5, 2.0)
            app.logger.debug(f"[PAYMENT] Temps de traitement simulé - {processing_time:.2f}s")
            time.sleep(processing_time)
            
            # Vérifier si on doit simuler un échec
            should_fail, failure_reason = should_simulate_failure(amount, transaction_id)
            
            if should_fail:
                app.logger.warning(f"[PAYMENT] Simulation échec paiement - Transaction: {transaction_id}, Raison: {failure_reason}")
                
                # Enregistrer l'échec
                app.logger.info(f"[PAYMENT] Enregistrement échec paiement - Transaction: {transaction_id}")
                failed_transaction = {
                    'transaction_id': transaction_id,
                    'status': 'failed',
                    'amount': amount,
                    'currency': currency,
                    'customer_id': customer_id,
                    'payment_method': data.get('payment_method', 'credit_card'),
                    'processed_at': datetime.utcnow().isoformat(),
                    'error_code': 'PAYMENT_DECLINED',
                    'error_message': failure_reason,
                    'gateway_response': {
                        'response_code': '05',
                        'response_message': failure_reason,
                        'risk_score': random.randint(60, 90)
                    }
                }
                
                transactions_db[transaction_id] = failed_transaction
                return {'error': failure_reason, 'details': failed_transaction}, 402  # Payment Required
            
            # Traitement réussi
            authorization_code = f"AUTH_{uuid.uuid4().hex[:8].upper()}"
            
            transaction = {
                'transaction_id': transaction_id,
                'status': 'completed',
                'amount': amount,
                'currency': currency,
                'customer_id': customer_id,
                'payment_method': data.get('payment_method', 'credit_card'),
                'processed_at': datetime.utcnow().isoformat(),
                'authorization_code': authorization_code,
                'gateway_response': {
                    'response_code': '00',
                    'response_message': 'Approved',
                    'risk_score': random.randint(10, 30),
                    'processor_reference': f"REF_{uuid.uuid4().hex[:12].upper()}"
                },
                'card_details': {
                    'last_four': data.get('card_details', {}).get('number', '****')[-4:] if data.get('card_details') else '****',
                    'brand': data.get('card_details', {}).get('brand', 'VISA'),
                    'exp_month': data.get('card_details', {}).get('exp_month', '12'),
                    'exp_year': data.get('card_details', {}).get('exp_year', '2025')
                }
            }
            
            # Sauvegarder la transaction
            transactions_db[transaction_id] = transaction
            
            app.logger.info(f"Paiement traité avec succès: {transaction_id} - {amount} {currency}")
            
            return transaction, 201
            
        except Exception as e:
            app.logger.error(f"Erreur lors du traitement du paiement: {e}")
            return {'error': str(e)}, 500

@api.route('/payment/refund')
class PaymentRefundResource(Resource):
    """Endpoint pour traiter les remboursements"""
    
    @api.expect(refund_request_model)
    @api.doc('refund_payment', description='Rembourser un paiement')
    def post(self):
        """Effectuer un remboursement"""
        try:
            data = request.get_json()
            
            original_transaction_id = data.get('original_transaction_id')
            refund_amount = data.get('refund_amount')
            reason = data.get('reason', 'Customer request')
            
            if not original_transaction_id or not refund_amount:
                return {'error': 'original_transaction_id et refund_amount sont requis'}, 400
            
            # Vérifier que la transaction originale existe
            original_transaction = transactions_db.get(original_transaction_id)
            if not original_transaction:
                return {'error': 'Transaction originale non trouvée'}, 404
            
            if original_transaction['status'] != 'completed':
                return {'error': 'Impossible de rembourser une transaction non complétée'}, 400
            
            # Vérifier le montant
            if refund_amount > original_transaction['amount']:
                return {'error': 'Le montant du remboursement ne peut excéder le montant original'}, 400
            
            # Simulation du temps de traitement
            time.sleep(random.uniform(0.3, 1.0))
            
            # Générer le remboursement
            refund_id = str(uuid.uuid4())
            
            refund = {
                'refund_id': refund_id,
                'original_transaction_id': original_transaction_id,
                'status': 'completed',
                'amount': refund_amount,
                'currency': original_transaction['currency'],
                'reason': reason,
                'processed_at': datetime.utcnow().isoformat(),
                'refund_reference': f"REF_{uuid.uuid4().hex[:8].upper()}",
                'gateway_response': {
                    'response_code': '00',
                    'response_message': 'Refund processed',
                    'processor_reference': f"REFUND_{uuid.uuid4().hex[:10].upper()}"
                }
            }
            
            # Sauvegarder le remboursement
            refunds_db[refund_id] = refund
            
            app.logger.info(f"Remboursement traité: {refund_id} - {refund_amount} {original_transaction['currency']}")
            
            return refund, 201
            
        except Exception as e:
            app.logger.error(f"Erreur lors du remboursement: {e}")
            return {'error': str(e)}, 500

@api.route('/payment/transactions/<string:transaction_id>')
class TransactionStatusResource(Resource):
    """Endpoint pour consulter le statut d'une transaction"""
    
    @api.doc('get_transaction_status', description='Récupérer le statut d\'une transaction')
    def get(self, transaction_id):
        """Récupérer les détails d'une transaction"""
        try:
            transaction = transactions_db.get(transaction_id)
            
            if not transaction:
                return {'error': 'Transaction non trouvée'}, 404
            
            return transaction, 200
            
        except Exception as e:
            app.logger.error(f"Erreur lors de la récupération de la transaction {transaction_id}: {e}")
            return {'error': str(e)}, 500

@api.route('/payment/config/failures')
class FailureConfigResource(Resource):
    """Endpoint pour configurer les échecs simulés"""
    
    @api.doc('configure_failures', description='Configurer la simulation d\'échecs')
    def post(self):
        """Configurer les paramètres de simulation d'échecs"""
        try:
            data = request.get_json()
            
            if 'enabled' in data:
                failure_config['enabled'] = bool(data['enabled'])
            
            if 'failure_rate' in data:
                rate = float(data['failure_rate'])
                if 0 <= rate <= 1:
                    failure_config['failure_rate'] = rate
                else:
                    return {'error': 'failure_rate doit être entre 0 et 1'}, 400
            
            if 'failure_on_amount' in data:
                failure_config['failure_on_amount'] = data['failure_on_amount']
            
            app.logger.info(f"Configuration des échecs mise à jour: {failure_config}")
            
            return {
                'message': 'Configuration mise à jour',
                'config': failure_config
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500
    
    @api.doc('get_failure_config', description='Récupérer la configuration des échecs')
    def get(self):
        """Récupérer la configuration actuelle des échecs"""
        return failure_config, 200

@api.route('/payment/metrics')
class PaymentMetricsResource(Resource):
    """Endpoint pour les métriques du service de paiement"""
    
    @api.doc('get_payment_metrics', description='Récupérer les métriques du service')
    def get(self):
        """Récupérer les statistiques de paiement"""
        try:
            total_transactions = len(transactions_db)
            completed_transactions = len([t for t in transactions_db.values() if t['status'] == 'completed'])
            failed_transactions = len([t for t in transactions_db.values() if t['status'] == 'failed'])
            total_refunds = len(refunds_db)
            
            total_amount = sum(t['amount'] for t in transactions_db.values() if t['status'] == 'completed')
            total_refund_amount = sum(r['amount'] for r in refunds_db.values())
            
            return {
                'total_transactions': total_transactions,
                'completed_transactions': completed_transactions,
                'failed_transactions': failed_transactions,
                'success_rate': completed_transactions / total_transactions if total_transactions > 0 else 0,
                'total_refunds': total_refunds,
                'total_amount_processed': total_amount,
                'total_refund_amount': total_refund_amount,
                'failure_config': failure_config,
                'timestamp': datetime.utcnow().isoformat()
            }, 200
            
        except Exception as e:
            return {'error': str(e)}, 500

# Health Check
@app.route('/health')
def health_check():
    """Health check pour le service de paiement"""
    return {
        'status': 'healthy',
        'service': 'payment-service',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0',
        'capabilities': [
            'payment_processing',
            'refund_processing',
            'failure_simulation',
            'transaction_tracking'
        ],
        'failure_simulation': failure_config['enabled']
    }, 200

# Point d'entrée
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    app.logger.info(f"Payment Service démarré sur le port 8009")
    app.logger.info(f"Simulation d'échecs: {failure_config['enabled']}")
    app.run(host='0.0.0.0', port=8009, debug=os.getenv('DEBUG', 'False').lower() == 'true')