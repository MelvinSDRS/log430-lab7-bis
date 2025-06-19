"""
Value Object pour représenter l'argent avec validation métier
"""
from dataclasses import dataclass
from decimal import Decimal
from typing import Union


@dataclass(frozen=True)
class Money:
    """Value Object pour représenter une valeur monétaire"""
    amount: Decimal
    currency: str = "CAD"
    
    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))
        
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-character code")
    
    def add(self, other: 'Money') -> 'Money':
        """Additionner deux montants de même devise"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def subtract(self, other: 'Money') -> 'Money':
        """Soustraire deux montants de même devise"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        result_amount = self.amount - other.amount
        if result_amount < 0:
            raise ValueError("Subtraction would result in negative amount")
        return Money(result_amount, self.currency)
    
    def multiply(self, factor: Union[int, float, Decimal]) -> 'Money':
        """Multiplier le montant par un facteur"""
        if not isinstance(factor, Decimal):
            factor = Decimal(str(factor))
        if factor < 0:
            raise ValueError("Cannot multiply by negative factor")
        return Money(self.amount * factor, self.currency)
    
    def is_zero(self) -> bool:
        """Vérifier si le montant est zéro"""
        return self.amount == Decimal('0')
    
    def is_greater_than(self, other: 'Money') -> bool:
        """Comparer si ce montant est supérieur à un autre"""
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount
    
    @classmethod
    def zero(cls, currency: str = "CAD") -> 'Money':
        """Créer un montant zéro"""
        return cls(Decimal('0'), currency)
    
    @classmethod
    def from_float(cls, amount: float, currency: str = "CAD") -> 'Money':
        """Créer un Money à partir d'un float"""
        return cls(Decimal(str(round(amount, 2))), currency)
    
    def to_float(self) -> float:
        """Convertir en float pour compatibilité avec l'API"""
        return float(self.amount) 