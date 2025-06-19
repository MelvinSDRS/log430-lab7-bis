"""
Value Objects partagés pour les identifiants d'entités
"""
from dataclasses import dataclass
from typing import Union
import uuid


@dataclass(frozen=True)
class EntityId:
    """Value Object de base pour les identifiants d'entités"""
    value: int
    
    def __post_init__(self):
        if not isinstance(self.value, int) or self.value <= 0:
            raise ValueError("Entity ID must be a positive integer")


@dataclass(frozen=True)
class StoreId(EntityId):
    """Value Object pour l'ID de magasin/entité"""
    pass


@dataclass(frozen=True)
class CashierId(EntityId):
    """Value Object pour l'ID de caissier"""
    pass


@dataclass(frozen=True)
class CategoryId(EntityId):
    """Value Object pour l'ID de catégorie"""
    pass


@dataclass(frozen=True)
class UserId(EntityId):
    """Value Object pour l'ID d'utilisateur"""
    pass


@dataclass(frozen=True)
class GeneratedId:
    """Value Object pour les IDs générés automatiquement"""
    value: str
    
    @classmethod
    def generate(cls) -> 'GeneratedId':
        return cls(str(uuid.uuid4()))
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Generated ID must be a non-empty string") 