"""
Base pour les Domain Events dans l'architecture DDD
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List
import uuid


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Interface de base pour tous les événements du domaine"""
    event_id: str
    occurred_on: datetime
    event_type: str
    
    def __post_init__(self):
        if not self.event_id:
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))
        if not self.occurred_on:
            object.__setattr__(self, 'occurred_on', datetime.now())
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Sérialiser l'événement en dictionnaire"""
        pass


class DomainEventPublisher:
    """Publisher pour les événements du domaine"""
    _subscribers: List = []
    _events_to_publish: List[DomainEvent] = []
    
    @classmethod
    def subscribe(cls, subscriber):
        """S'abonner aux événements du domaine"""
        cls._subscribers.append(subscriber)
    
    @classmethod
    def clear_subscribers(cls):
        """Nettoyer les abonnés (utile pour les tests)"""
        cls._subscribers.clear()
    
    @classmethod
    def publish(cls, events: List[DomainEvent]):
        """Publier une liste d'événements"""
        for event in events:
            cls._publish_single_event(event)
    
    @classmethod
    def _publish_single_event(cls, event: DomainEvent):
        """Publier un seul événement à tous les abonnés"""
        for subscriber in cls._subscribers:
            try:
                subscriber.handle(event)
            except Exception as e:
                # Log l'erreur mais ne bloque pas les autres subscribers
                print(f"Error handling event {event.event_type}: {str(e)}")
    
    @classmethod
    def collect_events(cls, event: DomainEvent):
        """Collecter un événement pour publication ultérieure"""
        cls._events_to_publish.append(event)
    
    @classmethod
    def publish_collected_events(cls):
        """Publier tous les événements collectés"""
        events_to_publish = cls._events_to_publish.copy()
        cls._events_to_publish.clear()
        cls.publish(events_to_publish)


class DomainEventHandler(ABC):
    """Interface de base pour les gestionnaires d'événements"""
    
    @abstractmethod
    def handle(self, event: DomainEvent):
        """Traiter un événement du domaine"""
        pass
    
    @abstractmethod
    def can_handle(self, event_type: str) -> bool:
        """Vérifier si ce handler peut traiter ce type d'événement"""
        pass 