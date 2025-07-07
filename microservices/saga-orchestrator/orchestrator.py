#!/usr/bin/env python3
"""
Saga Orchestrator - Orchestrateur synchrone pour les transactions distribuées
"""

import requests
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import time

from saga_state import (
    SagaExecution, SagaStep, SagaStatus, SagaStepType, 
    SagaStateMachine, SagaRepository
)


class ServiceClient:
    """Client pour communiquer avec les microservices"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Headers pour API Gateway
        self.session.headers.update({
            'Content-Type': 'application/json',
            'X-API-Key': 'pos-test-automation-dev-key-2025',
            'X-Saga-Orchestrator': 'true'
        })
    
    def call_service(self, method: str, endpoint: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        """Appel synchrone à un microservice"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url, params=payload, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=payload, timeout=self.timeout)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=payload, timeout=self.timeout)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log de la requête
            logging.info(f"Service call: {method} {url} -> {response.status_code} ({duration_ms}ms)")
            
            if response.status_code >= 400:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get('error', error_detail)
                except:
                    pass
                
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'error': error_detail,
                    'duration_ms': duration_ms
                }
            
            return {
                'success': True,
                'status_code': response.status_code,
                'data': response.json() if response.content else {},
                'duration_ms': duration_ms
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': f'Timeout après {self.timeout}s',
                'duration_ms': self.timeout * 1000
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Erreur de connexion au service',
                'duration_ms': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'duration_ms': 0
            }


class SagaOrchestrator:
    """Orchestrateur principal pour les sagas de commande"""
    
    def __init__(self, gateway_url: str = "http://localhost:8080"):
        self.repository = SagaRepository()
        self.client = ServiceClient(gateway_url)
        self.logger = logging.getLogger(__name__)
        
        # Configuration des endpoints de services
        self.service_endpoints = {
            'cart': '/api/v1/cart',
            'inventory': '/api/v1/inventory',
            'payment': '/api/v1/payment',
            'order': '/api/v1/orders'
        }
        
        # Métriques
        self.metrics = {
            'sagas_started': 0,
            'sagas_completed': 0,
            'sagas_failed': 0,
            'compensations_executed': 0
        }
    
    def start_order_saga(self, session_id: str, customer_id: int, 
                        order_data: Dict[str, Any]) -> SagaExecution:
        """Démarrer une nouvelle saga de commande"""
        
        saga_id = str(uuid.uuid4())
        
        saga = SagaExecution(
            saga_id=saga_id,
            customer_id=customer_id,
            session_id=session_id,
            status=SagaStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        # Sauvegarder l'état initial
        self.repository.save(saga)
        self.metrics['sagas_started'] += 1
        
        self.logger.info(f"Saga démarrée: {saga_id} pour client {customer_id}")
        
        # Exécuter la saga de manière synchrone
        try:
            self._execute_saga(saga, order_data)
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la saga {saga_id}: {e}")
            saga.status = SagaStatus.FAILED
            self.repository.save(saga)
            self.metrics['sagas_failed'] += 1
        
        return saga
    
    def _execute_saga(self, saga: SagaExecution, order_data: Dict[str, Any]) -> None:
        """Exécuter une saga étape par étape"""
        
        start_time = time.time()
        
        try:
            # Étape 1: Validation du panier
            if not self._validate_cart(saga):
                self._handle_failure(saga, SagaStatus.CART_VALIDATION_FAILED)
                return
            
            # Étape 2: Réservation du stock
            if not self._reserve_stock(saga):
                self._handle_failure(saga, SagaStatus.STOCK_RESERVATION_FAILED)
                return
            
            # Étape 3: Traitement du paiement
            if not self._process_payment(saga, order_data.get('payment', {})):
                self._handle_failure(saga, SagaStatus.PAYMENT_FAILED)
                return
            
            # Étape 4: Confirmation de la commande
            if not self._confirm_order(saga, order_data):
                self._handle_failure(saga, SagaStatus.PAYMENT_FAILED)  # Nécessite compensation
                return
            
            # Saga terminée avec succès
            SagaStateMachine.transition(saga, SagaStatus.COMPLETED)
            saga.total_duration_ms = int((time.time() - start_time) * 1000)
            self.repository.save(saga)
            self.metrics['sagas_completed'] += 1
            
            self.logger.info(f"Saga complétée avec succès: {saga.saga_id}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'exécution de la saga: {e}")
            self._handle_failure(saga, SagaStatus.FAILED)
    
    def _validate_cart(self, saga: SagaExecution) -> bool:
        """Étape 1: Valider le panier"""
        
        step = SagaStep(
            step_type=SagaStepType.VALIDATE_CART,
            status="pending",
            service_name="cart-service",
            endpoint=f"/carts/{saga.session_id}",
            payload={}
        )
        
        self.logger.info(f"Validation du panier pour la session {saga.session_id}")
        
        # Appel au Cart Service
        result = self.client.call_service('GET', step.endpoint)
        
        step.response = result
        step.duration_ms = result.get('duration_ms', 0)
        step.timestamp = datetime.utcnow()
        
        if result['success']:
            cart_data = result['data']
            
            # Validation métier
            if not cart_data.get('items') or len(cart_data['items']) == 0:
                step.status = "failed"
                step.error = "Panier vide"
                SagaStateMachine.transition(saga, SagaStatus.CART_VALIDATION_FAILED, step)
                return False
            
            if cart_data.get('total_amount', 0) <= 0:
                step.status = "failed"
                step.error = "Montant total invalide"
                SagaStateMachine.transition(saga, SagaStatus.CART_VALIDATION_FAILED, step)
                return False
            
            # Sauvegarde des données du panier
            saga.cart_data = cart_data
            step.status = "success"
            SagaStateMachine.transition(saga, SagaStatus.CART_VALIDATED, step)
            self.repository.save(saga)
            
            self.logger.info(f"Panier validé: {len(cart_data['items'])} articles, total: {cart_data['total_amount']}$")
            return True
        
        else:
            step.status = "failed"
            step.error = result.get('error', 'Erreur de validation du panier')
            SagaStateMachine.transition(saga, SagaStatus.CART_VALIDATION_FAILED, step)
            self.repository.save(saga)
            return False
    
    def _reserve_stock(self, saga: SagaExecution) -> bool:
        """Étape 2: Réserver le stock"""
        
        # Préparer les données de réservation
        items_to_reserve = []
        for item in saga.cart_data['items']:
            items_to_reserve.append({
                'product_id': item['product_id'],
                'quantity': item['quantity'],
                'location_id': 1  # Magasin par défaut
            })
        
        step = SagaStep(
            step_type=SagaStepType.RESERVE_STOCK,
            status="pending",
            service_name="inventory-service",
            endpoint="/inventory/reserve",
            payload={
                'reservation_id': saga.saga_id,
                'customer_id': saga.customer_id,
                'items': items_to_reserve
            }
        )
        
        self.logger.info(f"Réservation de stock pour {len(items_to_reserve)} produits")
        
        # Appel au Inventory Service
        result = self.client.call_service('POST', step.endpoint, step.payload)
        
        step.response = result
        step.duration_ms = result.get('duration_ms', 0)
        step.timestamp = datetime.utcnow()
        
        if result['success']:
            reservation_data = result['data']
            saga.reservation_data = reservation_data
            step.status = "success"
            SagaStateMachine.transition(saga, SagaStatus.STOCK_RESERVED, step)
            self.repository.save(saga)
            
            self.logger.info(f"Stock réservé avec succès: réservation {saga.saga_id}")
            return True
        
        else:
            step.status = "failed"
            step.error = result.get('error', 'Erreur de réservation de stock')
            SagaStateMachine.transition(saga, SagaStatus.STOCK_RESERVATION_FAILED, step)
            self.repository.save(saga)
            return False
    
    def _process_payment(self, saga: SagaExecution, payment_data: Dict[str, Any]) -> bool:
        """Étape 3: Traiter le paiement"""
        
        total_amount = saga.cart_data.get('final_amount', saga.cart_data.get('total_amount', 0))
        
        step = SagaStep(
            step_type=SagaStepType.PROCESS_PAYMENT,
            status="pending",
            service_name="payment-service",
            endpoint="/payment/process",
            payload={
                'transaction_id': saga.saga_id,
                'customer_id': saga.customer_id,
                'amount': total_amount,
                'currency': 'CAD',
                'payment_method': payment_data.get('method', 'credit_card'),
                'card_details': payment_data.get('card_details', {}),
                'billing_address': payment_data.get('billing_address', {})
            }
        )
        
        self.logger.info(f"Traitement du paiement: {total_amount}$ CAD")
        
        # Appel au Payment Service
        result = self.client.call_service('POST', step.endpoint, step.payload)
        
        step.response = result
        step.duration_ms = result.get('duration_ms', 0)
        step.timestamp = datetime.utcnow()
        
        if result['success']:
            payment_result = result['data']
            saga.payment_data = payment_result
            step.status = "success"
            SagaStateMachine.transition(saga, SagaStatus.PAYMENT_PROCESSED, step)
            self.repository.save(saga)
            
            self.logger.info(f"Paiement traité avec succès: {payment_result.get('transaction_id')}")
            return True
        
        else:
            step.status = "failed"
            step.error = result.get('error', 'Erreur de traitement du paiement')
            SagaStateMachine.transition(saga, SagaStatus.PAYMENT_FAILED, step)
            self.repository.save(saga)
            return False
    
    def _confirm_order(self, saga: SagaExecution, order_data: Dict[str, Any]) -> bool:
        """Étape 4: Confirmer la commande"""
        
        # Préparer les données de commande
        order_payload = {
            'customer_id': saga.customer_id,
            'items': saga.cart_data['items'],
            'total_amount': saga.cart_data.get('final_amount', saga.cart_data.get('total_amount')),
            'payment_transaction_id': saga.payment_data.get('transaction_id'),
            'reservation_id': saga.saga_id,
            'shipping_address': order_data.get('shipping_address', {}),
            'billing_address': order_data.get('billing_address', {}),
            'saga_id': saga.saga_id
        }
        
        step = SagaStep(
            step_type=SagaStepType.CONFIRM_ORDER,
            status="pending",
            service_name="order-service",
            endpoint="/orders",
            payload=order_payload
        )
        
        self.logger.info(f"Confirmation de commande pour le client {saga.customer_id}")
        
        # Appel au Order Service
        result = self.client.call_service('POST', step.endpoint, step.payload)
        
        step.response = result
        step.duration_ms = result.get('duration_ms', 0)
        step.timestamp = datetime.utcnow()
        
        if result['success']:
            order_result = result['data']
            saga.order_data = order_result
            saga.order_id = str(order_result.get('id', ''))
            step.status = "success"
            SagaStateMachine.transition(saga, SagaStatus.ORDER_CONFIRMED, step)
            self.repository.save(saga)
            
            self.logger.info(f"Commande confirmée: {saga.order_id}")
            return True
        
        else:
            step.status = "failed"
            step.error = result.get('error', 'Erreur de confirmation de commande')
            self.repository.save(saga)
            return False
    
    def _handle_failure(self, saga: SagaExecution, failure_status: SagaStatus) -> None:
        """Gérer l'échec d'une saga avec compensation si nécessaire"""
        
        SagaStateMachine.transition(saga, failure_status)
        
        # Déterminer si une compensation est nécessaire
        if SagaStateMachine.requires_compensation(failure_status):
            self.logger.info(f"Démarrage de la compensation pour la saga {saga.saga_id}")
            self._execute_compensation(saga)
        else:
            saga.status = SagaStatus.FAILED
            self.metrics['sagas_failed'] += 1
        
        self.repository.save(saga)
    
    def _execute_compensation(self, saga: SagaExecution) -> None:
        """Exécuter les actions de compensation"""
        
        self.metrics['compensations_executed'] += 1
        
        try:
            # Compensation dans l'ordre inverse
            if saga.status == SagaStatus.PAYMENT_FAILED:
                # Seulement libérer le stock
                self._release_stock(saga)
            
            elif saga.payment_data:
                # Rembourser le paiement ET libérer le stock
                self._refund_payment(saga)
                self._release_stock(saga)
            
            else:
                # Seulement libérer le stock
                self._release_stock(saga)
            
            SagaStateMachine.transition(saga, SagaStatus.COMPENSATED)
            saga.status = SagaStatus.FAILED  # État final après compensation
            
            self.logger.info(f"Compensation terminée pour la saga {saga.saga_id}")
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la compensation: {e}")
            saga.status = SagaStatus.FAILED
    
    def _release_stock(self, saga: SagaExecution) -> None:
        """Action de compensation: Libérer le stock réservé"""
        
        if not saga.reservation_data:
            return
        
        step = SagaStep(
            step_type=SagaStepType.RELEASE_STOCK,
            status="pending",
            service_name="inventory-service",
            endpoint=f"/inventory/release/{saga.saga_id}",
            payload={}
        )
        
        result = self.client.call_service('DELETE', step.endpoint)
        
        step.response = result
        step.duration_ms = result.get('duration_ms', 0)
        step.timestamp = datetime.utcnow()
        step.status = "success" if result['success'] else "failed"
        
        saga.compensation_steps.append(step)
        
        if result['success']:
            self.logger.info(f"Stock libéré avec succès pour la réservation {saga.saga_id}")
        else:
            self.logger.error(f"Échec de libération du stock: {result.get('error')}")
    
    def _refund_payment(self, saga: SagaExecution) -> None:
        """Action de compensation: Rembourser le paiement"""
        
        if not saga.payment_data:
            return
        
        step = SagaStep(
            step_type=SagaStepType.REFUND_PAYMENT,
            status="pending",
            service_name="payment-service",
            endpoint=f"/payment/refund",
            payload={
                'original_transaction_id': saga.payment_data.get('transaction_id'),
                'refund_amount': saga.payment_data.get('amount'),
                'reason': 'Saga compensation'
            }
        )
        
        result = self.client.call_service('POST', step.endpoint, step.payload)
        
        step.response = result
        step.duration_ms = result.get('duration_ms', 0)
        step.timestamp = datetime.utcnow()
        step.status = "success" if result['success'] else "failed"
        
        saga.compensation_steps.append(step)
        
        if result['success']:
            self.logger.info(f"Paiement remboursé avec succès: {saga.payment_data.get('transaction_id')}")
        else:
            self.logger.error(f"Échec du remboursement: {result.get('error')}")
    
    def get_saga_status(self, saga_id: str) -> Optional[SagaExecution]:
        """Récupérer l'état d'une saga"""
        return self.repository.get(saga_id)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Récupérer les métriques de l'orchestrateur"""
        repo_stats = self.repository.get_statistics()
        
        return {
            **self.metrics,
            **repo_stats,
            'active_sagas': len(self.repository.get_all_active()),
            'expired_sagas': len(self.repository.get_expired())
        }