import threading
from typing import Dict, Optional
from datetime import datetime

class InventoryManager:
    """Gestionnaire d'inventaire simplifié pour les remboursements"""
    
    def __init__(self):
        # Simulation d'une base de données de stock
        self.stock_levels = {
            'product_123': 45,
            'product_456': 23,
            'product_789': 12,
            'product_001': 78,
            'product_002': 56,
            'product_003': 34,
        }
        
        # Historique des ajustements
        self.adjustment_history = []
        
        # Lock pour les opérations thread-safe
        self.lock = threading.Lock()
        
    def get_stock_level(self, product_id: str) -> int:
        """Obtient le niveau de stock d'un produit"""
        with self.lock:
            return self.stock_levels.get(product_id, 0)
    
    def adjust_stock(self, product_id: str, quantity_change: int, reason: str, claim_id: str) -> Dict:
        """Ajuste le stock d'un produit"""
        with self.lock:
            # Vérifier si le produit existe
            if product_id not in self.stock_levels:
                # Créer le produit avec stock initial de 0
                self.stock_levels[product_id] = 0
            
            current_stock = self.stock_levels[product_id]
            new_stock = max(0, current_stock + quantity_change)  # Ne pas permettre de stock négatif
            
            # Effectuer l'ajustement
            self.stock_levels[product_id] = new_stock
            
            # Enregistrer l'historique
            adjustment = {
                'product_id': product_id,
                'quantity_change': quantity_change,
                'old_stock': current_stock,
                'new_stock': new_stock,
                'reason': reason,
                'claim_id': claim_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.adjustment_history.append(adjustment)
            
            return {
                'product_id': product_id,
                'old_stock_level': current_stock,
                'new_stock_level': new_stock,
                'quantity_change': quantity_change,
                'reason': reason,
                'claim_id': claim_id,
                'timestamp': adjustment['timestamp']
            }
    
    def get_adjustment_history(self, claim_id: Optional[str] = None) -> list:
        """Obtient l'historique des ajustements"""
        with self.lock:
            if claim_id:
                return [adj for adj in self.adjustment_history if adj['claim_id'] == claim_id]
            return self.adjustment_history.copy()
    
    def get_all_stock_levels(self) -> Dict[str, int]:
        """Obtient tous les niveaux de stock"""
        with self.lock:
            return self.stock_levels.copy()
    
    def validate_stock_adjustment(self, product_id: str, quantity_change: int) -> bool:
        """Valide si un ajustement de stock est possible"""
        with self.lock:
            current_stock = self.stock_levels.get(product_id, 0)
            
            # Pour les ajustements négatifs, vérifier qu'on ne va pas sous 0
            if quantity_change < 0 and current_stock + quantity_change < 0:
                return False
            
            return True