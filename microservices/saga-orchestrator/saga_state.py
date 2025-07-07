#!/usr/bin/env python3
"""
Saga State Machine - Gestion des états de la saga de commande
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json


class SagaStatus(Enum):
    """États possibles d'une saga"""
    PENDING = "PENDING"
    CART_VALIDATED = "CART_VALIDATED"
    STOCK_RESERVED = "STOCK_RESERVED"
    PAYMENT_PROCESSED = "PAYMENT_PROCESSED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    
    # États d'échec et compensation
    CART_VALIDATION_FAILED = "CART_VALIDATION_FAILED"
    STOCK_RESERVATION_FAILED = "STOCK_RESERVATION_FAILED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    
    # États de compensation
    COMPENSATING_STOCK = "COMPENSATING_STOCK"
    COMPENSATING_PAYMENT = "COMPENSATING_PAYMENT"
    COMPENSATED = "COMPENSATED"
    
    # États finaux
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SagaStepType(Enum):
    """Types d'étapes dans la saga"""
    VALIDATE_CART = "VALIDATE_CART"
    RESERVE_STOCK = "RESERVE_STOCK"
    PROCESS_PAYMENT = "PROCESS_PAYMENT"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    
    # Étapes de compensation
    RELEASE_STOCK = "RELEASE_STOCK"
    REFUND_PAYMENT = "REFUND_PAYMENT"


@dataclass
class SagaStep:
    """Représentation d'une étape de saga"""
    step_type: SagaStepType
    status: str
    service_name: str
    endpoint: str
    payload: Dict[str, Any]
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    duration_ms: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class SagaExecution:
    """État d'exécution d'une saga"""
    saga_id: str
    order_id: Optional[str] = None
    customer_id: Optional[int] = None
    session_id: Optional[str] = None
    status: SagaStatus = SagaStatus.PENDING
    
    # Données métier
    cart_data: Optional[Dict[str, Any]] = None
    reservation_data: Optional[Dict[str, Any]] = None
    payment_data: Optional[Dict[str, Any]] = None
    order_data: Optional[Dict[str, Any]] = None
    
    # Exécution
    current_step: Optional[SagaStepType] = None
    completed_steps: List[SagaStep] = field(default_factory=list)
    failed_step: Optional[SagaStep] = None
    compensation_steps: List[SagaStep] = field(default_factory=list)
    
    # Métadonnées
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    
    # Configuration
    timeout_seconds: int = 300  # 5 minutes par défaut
    auto_compensation: bool = True


class SagaStateMachine:
    """Machine d'état pour gérer les transitions de saga"""
    
    # Transitions valides entre états
    VALID_TRANSITIONS = {
        SagaStatus.PENDING: [
            SagaStatus.CART_VALIDATED,
            SagaStatus.CART_VALIDATION_FAILED,
            SagaStatus.FAILED
        ],
        SagaStatus.CART_VALIDATED: [
            SagaStatus.STOCK_RESERVED,
            SagaStatus.STOCK_RESERVATION_FAILED,
            SagaStatus.FAILED
        ],
        SagaStatus.STOCK_RESERVED: [
            SagaStatus.PAYMENT_PROCESSED,
            SagaStatus.PAYMENT_FAILED,
            SagaStatus.COMPENSATING_STOCK
        ],
        SagaStatus.PAYMENT_PROCESSED: [
            SagaStatus.ORDER_CONFIRMED,
            SagaStatus.COMPENSATING_PAYMENT,
            SagaStatus.COMPENSATING_STOCK
        ],
        SagaStatus.ORDER_CONFIRMED: [
            SagaStatus.COMPLETED
        ],
        
        # Transitions d'échec
        SagaStatus.CART_VALIDATION_FAILED: [SagaStatus.FAILED],
        SagaStatus.STOCK_RESERVATION_FAILED: [SagaStatus.FAILED],
        SagaStatus.PAYMENT_FAILED: [SagaStatus.COMPENSATING_STOCK],
        
        # Transitions de compensation
        SagaStatus.COMPENSATING_STOCK: [
            SagaStatus.COMPENSATED,
            SagaStatus.FAILED
        ],
        SagaStatus.COMPENSATING_PAYMENT: [
            SagaStatus.COMPENSATING_STOCK,
            SagaStatus.COMPENSATED,
            SagaStatus.FAILED
        ],
        SagaStatus.COMPENSATED: [SagaStatus.FAILED],
        
        # États finaux
        SagaStatus.COMPLETED: [],
        SagaStatus.FAILED: []
    }
    
    @staticmethod
    def can_transition(current_status: SagaStatus, target_status: SagaStatus) -> bool:
        """Vérifie si une transition est valide"""
        valid_targets = SagaStateMachine.VALID_TRANSITIONS.get(current_status, [])
        return target_status in valid_targets
    
    @staticmethod
    def transition(saga: SagaExecution, target_status: SagaStatus, 
                  step_result: Optional[SagaStep] = None) -> bool:
        """Effectue une transition d'état"""
        if not SagaStateMachine.can_transition(saga.status, target_status):
            raise ValueError(
                f"Transition invalide: {saga.status.value} -> {target_status.value}"
            )
        
        saga.status = target_status
        saga.updated_at = datetime.utcnow()
        
        # Enregistrer l'étape si fournie
        if step_result:
            if step_result.status == "success":
                saga.completed_steps.append(step_result)
            else:
                saga.failed_step = step_result
        
        return True
    
    @staticmethod
    def is_final_state(status: SagaStatus) -> bool:
        """Vérifie si l'état est final"""
        return status in [SagaStatus.COMPLETED, SagaStatus.FAILED]
    
    @staticmethod
    def requires_compensation(status: SagaStatus) -> bool:
        """Vérifie si l'état nécessite une compensation"""
        return status in [
            SagaStatus.PAYMENT_FAILED,
            SagaStatus.COMPENSATING_STOCK,
            SagaStatus.COMPENSATING_PAYMENT
        ]
    
    @staticmethod
    def get_compensation_steps(failed_after_step: SagaStepType) -> List[SagaStepType]:
        """Retourne les étapes de compensation nécessaires"""
        compensation_map = {
            SagaStepType.PROCESS_PAYMENT: [SagaStepType.RELEASE_STOCK],
            SagaStepType.CONFIRM_ORDER: [
                SagaStepType.REFUND_PAYMENT,
                SagaStepType.RELEASE_STOCK
            ]
        }
        
        return compensation_map.get(failed_after_step, [])


class SagaRepository:
    """Repository pour persister les états de saga"""
    
    def __init__(self):
        self._sagas: Dict[str, SagaExecution] = {}
    
    def save(self, saga: SagaExecution) -> None:
        """Sauvegarder une saga"""
        saga.updated_at = datetime.utcnow()
        self._sagas[saga.saga_id] = saga
    
    def get(self, saga_id: str) -> Optional[SagaExecution]:
        """Récupérer une saga par ID"""
        return self._sagas.get(saga_id)
    
    def get_by_order_id(self, order_id: str) -> Optional[SagaExecution]:
        """Récupérer une saga par ID de commande"""
        for saga in self._sagas.values():
            if saga.order_id == order_id:
                return saga
        return None
    
    def get_all_active(self) -> List[SagaExecution]:
        """Récupérer toutes les sagas actives"""
        return [
            saga for saga in self._sagas.values()
            if not SagaStateMachine.is_final_state(saga.status)
        ]
    
    def get_expired(self) -> List[SagaExecution]:
        """Récupérer les sagas expirées"""
        now = datetime.utcnow()
        return [
            saga for saga in self._sagas.values()
            if saga.expires_at and saga.expires_at < now
            and not SagaStateMachine.is_final_state(saga.status)
        ]
    
    def delete(self, saga_id: str) -> bool:
        """Supprimer une saga"""
        if saga_id in self._sagas:
            del self._sagas[saga_id]
            return True
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtenir des statistiques sur les sagas"""
        status_counts = {}
        total_duration = 0
        completed_count = 0
        
        for saga in self._sagas.values():
            status = saga.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if saga.total_duration_ms:
                total_duration += saga.total_duration_ms
                completed_count += 1
        
        avg_duration = total_duration / completed_count if completed_count > 0 else 0
        
        return {
            'total_sagas': len(self._sagas),
            'status_distribution': status_counts,
            'average_duration_ms': avg_duration,
            'success_rate': status_counts.get('COMPLETED', 0) / len(self._sagas) if self._sagas else 0
        }