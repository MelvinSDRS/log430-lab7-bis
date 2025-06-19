"""
Agrégat Product - Racine d'agrégat pour la gestion des produits
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

from ..value_objects.product_id import (
    ProductId, ProductName, ProductDescription, 
    StockQuantity, AlertThreshold
)
from src.api.bounded_contexts.shared.value_objects.money import Money
from src.api.bounded_contexts.shared.value_objects.entity_id import CategoryId
from src.api.bounded_contexts.shared.events.domain_event import DomainEvent


@dataclass(frozen=True)
class ProductCreatedEvent(DomainEvent):
    """Événement : Produit créé"""
    product_id: ProductId
    product_name: str
    price: float
    
    def to_dict(self):
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'occurred_on': self.occurred_on.isoformat(),
            'product_id': self.product_id.value,
            'product_name': self.product_name,
            'price': self.price
        }


@dataclass(frozen=True)
class ProductUpdatedEvent(DomainEvent):
    """Événement : Produit mis à jour"""
    product_id: ProductId
    updated_fields: List[str]
    
    def to_dict(self):
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'occurred_on': self.occurred_on.isoformat(),
            'product_id': self.product_id.value,
            'updated_fields': self.updated_fields
        }


@dataclass(frozen=True)
class ProductDeletedEvent(DomainEvent):
    """Événement : Produit supprimé"""
    product_id: ProductId
    product_name: str
    
    def to_dict(self):
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'occurred_on': self.occurred_on.isoformat(),
            'product_id': self.product_id.value,
            'product_name': self.product_name
        }


@dataclass
class Product:
    """
    AGGREGATE ROOT - Produit avec logique métier riche
    Gère les règles métier liées aux produits et maintient la cohérence
    """
    _id: ProductId
    _name: ProductName
    _price: Money
    _stock_quantity: StockQuantity
    _category_id: CategoryId
    _alert_threshold: AlertThreshold
    _description: Optional[ProductDescription] = None
    _events: List[DomainEvent] = field(default_factory=list)
    
    def __post_init__(self):
        """Validation des invariants métier lors de la création"""
        if self._price.is_zero():
            raise ValueError("Product price cannot be zero")
    
    # Properties pour accès en lecture seule
    @property
    def id(self) -> ProductId:
        return self._id
    
    @property
    def name(self) -> ProductName:
        return self._name
    
    @property
    def price(self) -> Money:
        return self._price
    
    @property
    def stock_quantity(self) -> StockQuantity:
        return self._stock_quantity
    
    @property
    def category_id(self) -> CategoryId:
        return self._category_id
    
    @property
    def alert_threshold(self) -> AlertThreshold:
        return self._alert_threshold
    
    @property
    def description(self) -> Optional[ProductDescription]:
        return self._description
    
    # Méthodes métier
    def update_name(self, new_name: ProductName) -> None:
        """RÈGLE MÉTIER : Mise à jour du nom avec validation"""
        if self._name.value != new_name.value:
            old_name = self._name
            self._name = new_name
            self._record_event(ProductUpdatedEvent(
                event_id="",
                occurred_on=datetime.now(),
                event_type="ProductUpdated",
                product_id=self._id,
                updated_fields=["name"]
            ))
    
    def update_price(self, new_price: Money) -> None:
        """RÈGLE MÉTIER : Mise à jour du prix avec validation"""
        if new_price.is_zero():
            raise ValueError("Product price cannot be zero")
        
        if new_price.currency != self._price.currency:
            raise ValueError("Cannot change product currency")
        
        if self._price.amount != new_price.amount:
            self._price = new_price
            self._record_event(ProductUpdatedEvent(
                event_id="",
                occurred_on=datetime.now(),
                event_type="ProductUpdated",
                product_id=self._id,
                updated_fields=["price"]
            ))
    
    def update_stock_quantity(self, new_quantity: StockQuantity) -> None:
        """RÈGLE MÉTIER : Mise à jour du stock"""
        self._stock_quantity = new_quantity
        # L'événement de stock sera géré par l'Inventory Context
    
    def update_alert_threshold(self, new_threshold: AlertThreshold) -> None:
        """RÈGLE MÉTIER : Mise à jour du seuil d'alerte"""
        if self._alert_threshold.value != new_threshold.value:
            self._alert_threshold = new_threshold
            self._record_event(ProductUpdatedEvent(
                event_id="",
                occurred_on=datetime.now(),
                event_type="ProductUpdated",
                product_id=self._id,
                updated_fields=["alert_threshold"]
            ))
    
    def update_description(self, new_description: Optional[ProductDescription]) -> None:
        """RÈGLE MÉTIER : Mise à jour de la description"""
        current_desc = self._description.value if self._description else None
        new_desc = new_description.value if new_description else None
        
        if current_desc != new_desc:
            self._description = new_description
            self._record_event(ProductUpdatedEvent(
                event_id="",
                occurred_on=datetime.now(),
                event_type="ProductUpdated",
                product_id=self._id,
                updated_fields=["description"]
            ))
    
    def update_category(self, new_category_id: CategoryId) -> None:
        """RÈGLE MÉTIER : Changement de catégorie"""
        if self._category_id.value != new_category_id.value:
            self._category_id = new_category_id
            self._record_event(ProductUpdatedEvent(
                event_id="",
                occurred_on=datetime.now(),
                event_type="ProductUpdated",
                product_id=self._id,
                updated_fields=["category"]
            ))
    
    def is_stock_below_threshold(self) -> bool:
        """RÈGLE MÉTIER : Vérifier si le stock est sous le seuil"""
        return self._alert_threshold.is_below_threshold(self._stock_quantity)
    
    def is_out_of_stock(self) -> bool:
        """RÈGLE MÉTIER : Vérifier si le produit est en rupture"""
        return self._stock_quantity.is_zero()
    
    def can_fulfill_quantity(self, required_quantity: StockQuantity) -> bool:
        """RÈGLE MÉTIER : Vérifier si on peut satisfaire une quantité"""
        return self._stock_quantity.is_sufficient_for(required_quantity)
    
    def mark_for_deletion(self) -> None:
        """RÈGLE MÉTIER : Marquer le produit pour suppression"""
        self._record_event(ProductDeletedEvent(
            event_id="",
            occurred_on=datetime.now(),
            event_type="ProductDeleted",
            product_id=self._id,
            product_name=self._name.value
        ))
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Récupérer les événements non commitées"""
        events = self._events.copy()
        self._events.clear()
        return events
    
    def _record_event(self, event: DomainEvent) -> None:
        """Enregistrer un événement du domaine"""
        self._events.append(event)
    
    @classmethod
    def create(cls,
               product_id: ProductId,
               name: ProductName,
               price: Money,
               stock_quantity: StockQuantity,
               category_id: CategoryId,
               alert_threshold: AlertThreshold,
               description: Optional[ProductDescription] = None) -> 'Product':
        """
        Factory Method : Créer un nouveau produit avec validation
        """
        if price.is_zero():
            raise ValueError("Product price cannot be zero")
        
        product = cls(
            _id=product_id,
            _name=name,
            _price=price,
            _stock_quantity=stock_quantity,
            _category_id=category_id,
            _alert_threshold=alert_threshold,
            _description=description
        )
        
        # Événement de création
        product._record_event(ProductCreatedEvent(
            event_id="",
            occurred_on=datetime.now(),
            event_type="ProductCreated",
            product_id=product_id,
            product_name=name.value,
            price=price.to_float()
        ))
        
        return product
    
    def to_dict(self) -> dict:
        """Convertir en dictionnaire pour l'API (compatibilité)"""
        return {
            'id': self._id.value,
            'nom': self._name.value,
            'prix': self._price.to_float(),
            'stock': self._stock_quantity.value,
            'id_categorie': self._category_id.value,
            'seuil_alerte': self._alert_threshold.value,
            'description': self._description.value if self._description else None
        } 