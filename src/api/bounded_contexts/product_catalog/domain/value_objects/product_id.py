"""
Value Objects pour le Product Catalog
"""
from dataclasses import dataclass
from src.api.bounded_contexts.shared.value_objects.entity_id import EntityId


@dataclass(frozen=True)
class ProductId(EntityId):
    """Value Object pour l'ID de produit"""
    pass


@dataclass(frozen=True)
class ProductCode:
    """Value Object pour le code produit"""
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) < 3:
            raise ValueError("Product code must be at least 3 characters")
        object.__setattr__(self, 'value', self.value.strip().upper())


@dataclass(frozen=True)
class ProductName:
    """Value Object pour le nom de produit"""
    value: str
    
    def __post_init__(self):
        if not self.value or len(self.value.strip()) < 2:
            raise ValueError("Product name must be at least 2 characters")
        if len(self.value.strip()) > 100:
            raise ValueError("Product name cannot exceed 100 characters")
        object.__setattr__(self, 'value', self.value.strip())


@dataclass(frozen=True)
class ProductDescription:
    """Value Object pour la description de produit"""
    value: str
    
    def __post_init__(self):
        if self.value is not None:
            if len(self.value.strip()) > 500:
                raise ValueError("Product description cannot exceed 500 characters")
            object.__setattr__(self, 'value', self.value.strip() if self.value.strip() else None)


@dataclass(frozen=True)
class StockQuantity:
    """Value Object pour les quantités de stock"""
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Stock quantity cannot be negative")
    
    def add(self, other: 'StockQuantity') -> 'StockQuantity':
        """Ajouter des quantités"""
        return StockQuantity(self.value + other.value)
    
    def subtract(self, other: 'StockQuantity') -> 'StockQuantity':
        """Soustraire des quantités"""
        result = self.value - other.value
        if result < 0:
            raise ValueError("Cannot subtract more than available quantity")
        return StockQuantity(result)
    
    def is_sufficient_for(self, required: 'StockQuantity') -> bool:
        """Vérifier si la quantité est suffisante"""
        return self.value >= required.value
    
    def is_zero(self) -> bool:
        """Vérifier si la quantité est zéro"""
        return self.value == 0


@dataclass(frozen=True)
class AlertThreshold:
    """Value Object pour le seuil d'alerte"""
    value: int
    
    def __post_init__(self):
        if self.value < 0:
            raise ValueError("Alert threshold cannot be negative")
        if self.value > 1000:
            raise ValueError("Alert threshold seems unreasonably high (max: 1000)")
    
    def is_below_threshold(self, quantity: StockQuantity) -> bool:
        """Vérifier si une quantité est sous le seuil"""
        return quantity.value <= self.value 