#!/usr/bin/env python3
"""
Services métier pour Order Service
Pattern réutilisé de Customer Service pour cohérence structurelle
Logique métier pour commandes e-commerce, checkout, validation
"""

import json
from typing import List, Dict, Optional
from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session
from datetime import datetime
from decimal import Decimal

from database import OrderModel, OrderItemModel


class OrderService:
    """Service métier pour la gestion des commandes - Pattern Customer Service"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_orders_paginated(self, page: int = 1, per_page: int = 20, customer_id: Optional[int] = None, status: Optional[str] = None) -> List[Dict]:
        """Récupérer les commandes avec pagination et filtres - Pattern identique CustomerService"""
        query = self.session.query(OrderModel)
        
        # Filtrage par client
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        
        # Filtrage par statut
        if status:
            query = query.filter(OrderModel.status == status)
        
        # Tri par date décroissante
        query = query.order_by(desc(OrderModel.order_date))
        
        # Pagination
        offset = (page - 1) * per_page
        orders = query.offset(offset).limit(per_page).all()
        
        return [order.to_dict() for order in orders]
    
    def count_orders(self, customer_id: Optional[int] = None, status: Optional[str] = None) -> int:
        """Compter le nombre total de commandes - Pattern identique CustomerService"""
        query = self.session.query(OrderModel)
        
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        
        if status:
            query = query.filter(OrderModel.status == status)
        
        return query.count()
    
    def get_order_by_id(self, order_id: int, customer_id: Optional[int] = None) -> Optional[Dict]:
        """Récupérer une commande par son ID - Pattern identique CustomerService"""
        query = self.session.query(OrderModel).filter(OrderModel.id == order_id)
        
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        
        order = query.first()
        return order.to_dict() if order else None
    
    def create_order(self, order_data: Dict) -> Dict:
        """Créer une nouvelle commande - Pattern identique CustomerService.create_address"""
        
        # Validation des données
        required_fields = ['customer_id', 'items', 'shipping_address']
        for field in required_fields:
            if field not in order_data or not order_data[field]:
                raise ValueError(f"Le champ '{field}' est requis")
        
        # Validation des items
        if not isinstance(order_data['items'], list) or len(order_data['items']) == 0:
            raise ValueError("Au moins un item est requis")
        
        # Calcul des totaux
        subtotal = Decimal('0')
        for item in order_data['items']:
            if not all(field in item for field in ['product_id', 'quantity', 'unit_price', 'product_name']):
                raise ValueError("Chaque item doit contenir: product_id, quantity, unit_price, product_name")
            
            item_total = Decimal(str(item['quantity'])) * Decimal(str(item['unit_price']))
            subtotal += item_total
        
        # Calcul taxes (exemple: 15% - même pattern que Customer Service validation)
        tax_rate = Decimal('0.15')
        tax_amount = subtotal * tax_rate
        
        # Frais de livraison
        shipping_amount = Decimal(str(order_data.get('shipping_amount', '9.99')))
        
        total_amount = subtotal + tax_amount + shipping_amount
        
        # Sérialiser les adresses en JSON
        shipping_address_json = json.dumps(order_data['shipping_address'])
        billing_address_json = json.dumps(order_data.get('billing_address', order_data['shipping_address']))
        
        # Créer la commande
        order = OrderModel(
            customer_id=order_data['customer_id'],
            status='pending',
            total_amount=total_amount,
            tax_amount=tax_amount,
            shipping_amount=shipping_amount,
            shipping_address_json=shipping_address_json,
            billing_address_json=billing_address_json
        )
        
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        
        # Ajouter les items
        for item_data in order_data['items']:
            item_total = Decimal(str(item_data['quantity'])) * Decimal(str(item_data['unit_price']))
            
            order_item = OrderItemModel(
                order_id=order.id,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=Decimal(str(item_data['unit_price'])),
                total_price=item_total,
                product_name=item_data['product_name'],
                product_description=item_data.get('product_description', '')
            )
            
            self.session.add(order_item)
        
        self.session.commit()
        self.session.refresh(order)
        
        return order.to_dict()
    
    def update_order_status(self, order_id: int, new_status: str, customer_id: Optional[int] = None) -> Optional[Dict]:
        """Mettre à jour le statut d'une commande - Pattern identique CustomerService.update_customer"""
        query = self.session.query(OrderModel).filter(OrderModel.id == order_id)
        
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        
        order = query.first()
        
        if not order:
            return None
        
        # Validation du statut
        valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError(f"Statut invalide. Valeurs autorisées: {valid_statuses}")
        
        # Validation des transitions de statut (business logic)
        if order.status == 'delivered' and new_status != 'delivered':
            raise ValueError("Une commande livrée ne peut pas changer de statut")
        
        if order.status == 'cancelled' and new_status != 'cancelled':
            raise ValueError("Une commande annulée ne peut pas changer de statut")
        
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        self.session.commit()
        self.session.refresh(order)
        
        return order.to_dict()
    
    def cancel_order(self, order_id: int, customer_id: Optional[int] = None) -> bool:
        """Annuler une commande - Pattern identique CustomerService.deactivate_customer"""
        query = self.session.query(OrderModel).filter(OrderModel.id == order_id)
        
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        
        order = query.first()
        
        if not order:
            return False
        
        # Validation business: seules les commandes pending/confirmed peuvent être annulées
        if order.status not in ['pending', 'confirmed']:
            raise ValueError(f"Une commande avec le statut '{order.status}' ne peut pas être annulée")
        
        order.status = 'cancelled'
        order.updated_at = datetime.utcnow()
        
        self.session.commit()
        return True


class OrderItemService:
    """Service métier pour la gestion des items de commande - Pattern AddressService"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_items_by_order(self, order_id: int) -> List[Dict]:
        """Récupérer tous les items d'une commande - Pattern identique AddressService.get_addresses_by_customer"""
        items = self.session.query(OrderItemModel).filter(
            OrderItemModel.order_id == order_id
        ).all()
        
        return [item.to_dict() for item in items]
    
    def update_item_quantity(self, item_id: int, order_id: int, new_quantity: int) -> Optional[Dict]:
        """Mettre à jour la quantité d'un item - Pattern identique AddressService.update_address"""
        item = self.session.query(OrderItemModel).filter(
            and_(OrderItemModel.id == item_id, OrderItemModel.order_id == order_id)
        ).first()
        
        if not item:
            return None
        
        # Vérifier que la commande peut encore être modifiée
        order = self.session.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order or order.status not in ['pending']:
            raise ValueError("Seules les commandes en attente peuvent être modifiées")
        
        if new_quantity <= 0:
            raise ValueError("La quantité doit être positive")
        
        # Recalculer le total de l'item
        item.quantity = new_quantity
        item.total_price = item.unit_price * new_quantity
        
        # Recalculer le total de la commande
        self._recalculate_order_total(order_id)
        
        self.session.commit()
        self.session.refresh(item)
        
        return item.to_dict()
    
    def remove_item(self, item_id: int, order_id: int) -> bool:
        """Supprimer un item de commande - Pattern identique AddressService.delete_address"""
        item = self.session.query(OrderItemModel).filter(
            and_(OrderItemModel.id == item_id, OrderItemModel.order_id == order_id)
        ).first()
        
        if not item:
            return False
        
        # Vérifier que la commande peut encore être modifiée
        order = self.session.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order or order.status not in ['pending']:
            raise ValueError("Seules les commandes en attente peuvent être modifiées")
        
        # Vérifier qu'il ne s'agit pas du dernier item
        item_count = self.session.query(OrderItemModel).filter(OrderItemModel.order_id == order_id).count()
        if item_count <= 1:
            raise ValueError("Une commande doit contenir au moins un item")
        
        self.session.delete(item)
        
        # Recalculer le total de la commande
        self._recalculate_order_total(order_id)
        
        self.session.commit()
        return True
    
    def _recalculate_order_total(self, order_id: int):
        """Recalculer le total d'une commande après modification des items"""
        order = self.session.query(OrderModel).filter(OrderModel.id == order_id).first()
        if not order:
            return
        
        # Calculer le sous-total
        items_total = self.session.query(func.sum(OrderItemModel.total_price)).filter(
            OrderItemModel.order_id == order_id
        ).scalar() or Decimal('0')
        
        # Recalculer les taxes (15%)
        tax_rate = Decimal('0.15')
        tax_amount = items_total * tax_rate
        
        # Le shipping reste identique
        total_amount = items_total + tax_amount + order.shipping_amount
        
        order.tax_amount = tax_amount
        order.total_amount = total_amount
        order.updated_at = datetime.utcnow()


class OrderAnalyticsService:
    """Service métier pour l'analytique des commandes - Pattern AuthService"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_order_statistics(self, customer_id: Optional[int] = None, days: int = 30) -> Dict:
        """Obtenir des statistiques de commandes - Pattern similaire aux méthodes AuthService"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.session.query(OrderModel).filter(OrderModel.order_date >= start_date)
        
        if customer_id:
            query = query.filter(OrderModel.customer_id == customer_id)
        
        orders = query.all()
        
        total_orders = len(orders)
        total_revenue = sum(float(order.total_amount) for order in orders)
        
        status_counts = {}
        for order in orders:
            status_counts[order.status] = status_counts.get(order.status, 0) + 1
        
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        return {
            'period_days': days,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order_value': avg_order_value,
            'status_breakdown': status_counts,
            'start_date': start_date.isoformat(),
            'end_date': datetime.utcnow().isoformat()
        }
    
    def get_top_products(self, limit: int = 10, days: int = 30) -> List[Dict]:
        """Obtenir les produits les plus vendus"""
        from datetime import timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Jointure entre OrderItemModel et OrderModel pour filtrer par date
        query = self.session.query(
            OrderItemModel.product_id,
            OrderItemModel.product_name,
            func.sum(OrderItemModel.quantity).label('total_quantity'),
            func.sum(OrderItemModel.total_price).label('total_revenue'),
            func.count(OrderItemModel.id).label('order_count')
        ).join(
            OrderModel, OrderItemModel.order_id == OrderModel.id
        ).filter(
            OrderModel.order_date >= start_date
        ).group_by(
            OrderItemModel.product_id, OrderItemModel.product_name
        ).order_by(
            func.sum(OrderItemModel.quantity).desc()
        ).limit(limit)
        
        results = query.all()
        
        return [
            {
                'product_id': result.product_id,
                'product_name': result.product_name,
                'total_quantity': int(result.total_quantity),
                'total_revenue': float(result.total_revenue),
                'order_count': int(result.order_count)
            }
            for result in results
        ] 