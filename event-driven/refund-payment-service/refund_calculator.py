import random
from decimal import Decimal
from typing import Optional

class RefundCalculator:
    """Calculateur de remboursement pour les réclamations"""
    
    # Taux de remboursement par type de réclamation
    REFUND_RATES = {
        'product_defect': 1.0,      # Remboursement complet
        'delivery_issue': 0.5,      # Remboursement partiel
        'billing_error': 1.0,       # Remboursement complet
        'service_complaint': 0.3    # Remboursement partiel
    }
    
    # Base de données simulée des prix des produits
    PRODUCT_PRICES = {
        'product_123': Decimal('49.99'),
        'product_456': Decimal('89.99'),
        'product_789': Decimal('129.99'),
        'product_001': Decimal('19.99'),
        'product_002': Decimal('39.99'),
        'product_003': Decimal('59.99'),
    }
    
    def calculate_refund(self, product_id: str, claim_type: str) -> float:
        """Calcule le montant du remboursement"""
        
        # Simuler un échec occasionnel (5% de chance)
        if random.random() < 0.05:
            raise Exception(f"Service de paiement temporairement indisponible")
        
        # Obtenir le prix du produit
        product_price = self.PRODUCT_PRICES.get(product_id, Decimal('25.00'))
        
        # Obtenir le taux de remboursement
        refund_rate = self.REFUND_RATES.get(claim_type, 0.5)
        
        # Calculer le montant du remboursement
        refund_amount = float(product_price * Decimal(str(refund_rate)))
        
        # Ajouter des frais de traitement si remboursement partiel
        if refund_rate < 1.0:
            processing_fee = 2.99
            refund_amount = max(0, refund_amount - processing_fee)
        
        return round(refund_amount, 2)
    
    def validate_refund_eligibility(self, claim_id: str, product_id: str) -> bool:
        """Valide l'éligibilité au remboursement"""
        
        # Simuler des vérifications d'éligibilité
        if not product_id or not claim_id:
            return False
        
        # Simuler un produit non éligible
        if product_id == 'product_non_eligible':
            return False
        
        return True