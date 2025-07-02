#!/usr/bin/env python3
"""
Services métier pour Cart Service
Logique métier pour panier d'achat, calculs prix, taxes
"""

import os
import requests
from typing import List, Dict, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import uuid

from redis_client import RedisCartClient


class CartService:
    """Service métier pour la gestion des paniers d'achat"""
    
    def __init__(self, redis_client):
        self.redis_cart = RedisCartClient(redis_client)
        self.product_service_url = os.getenv('PRODUCT_SERVICE_URL', 'http://product-service:8001')
        self.default_currency = 'CAD'
        self.default_cart_expiry = 86400  # 24 heures
    
    def get_cart(self, session_id: str) -> Optional[Dict]:
        """Récupérer un panier existant"""
        cart = self.redis_cart.get_cart(session_id)
        
        if cart:
            # Mettre à jour la date d'accès
            cart['updated_at'] = datetime.now().isoformat()
            self.redis_cart.set_cart(session_id, cart)
        
        return cart
    
    def create_empty_cart(self, session_id: str, customer_id: Optional[int] = None) -> Dict:
        """Créer un panier vide"""
        now = datetime.now()
        expires_at = now + timedelta(seconds=self.default_cart_expiry)
        
        cart = {
            'session_id': session_id,
            'customer_id': customer_id,
            'items': [],
            'total_items': 0,
            'total_amount': 0.0,
            'tax_amount': 0.0,
            'final_amount': 0.0,
            'currency': self.default_currency,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        self.redis_cart.set_cart(session_id, cart)
        return cart
    
    def add_item_to_cart(self, session_id: str, product_id: int, quantity: int, price: Optional[float] = None) -> Dict:
        """Ajouter un article au panier"""
        
        # Récupérer ou créer le panier
        cart = self.get_cart(session_id)
        if not cart:
            cart = self.create_empty_cart(session_id)
        
        # Récupérer les informations du produit si pas de prix fourni
        product_info = None
        if not price:
            product_info = self._get_product_info(product_id)
            if not product_info:
                raise ValueError(f"Produit {product_id} introuvable")
            price = product_info['prix']
        
        # Chercher si l'article existe déjà dans le panier
        existing_item = None
        for item in cart['items']:
            if item['product_id'] == product_id:
                existing_item = item
                break
        
        if existing_item:
            # Mettre à jour la quantité existante
            existing_item['quantity'] += quantity
            existing_item['subtotal'] = round(existing_item['price'] * existing_item['quantity'], 2)
        else:
            # Ajouter un nouvel article
            new_item = {
                'product_id': product_id,
                'product_name': product_info['nom'] if product_info else f'Produit {product_id}',
                'product_sku': product_info['sku'] if product_info else None,
                'price': price,
                'quantity': quantity,
                'subtotal': round(price * quantity, 2)
            }
            cart['items'].append(new_item)
        
        # Recalculer les totaux
        self._recalculate_cart_totals(cart)
        
        # Sauvegarder
        cart['updated_at'] = datetime.now().isoformat()
        self.redis_cart.set_cart(session_id, cart)
        
        return cart
    
    def update_item_quantity(self, session_id: str, product_id: int, quantity: int) -> Optional[Dict]:
        """Mettre à jour la quantité d'un article"""
        
        cart = self.get_cart(session_id)
        if not cart:
            return None
        
        # Chercher l'article
        item_found = False
        for item in cart['items']:
            if item['product_id'] == product_id:
                if quantity == 0:
                    # Supprimer l'article si quantité = 0
                    cart['items'].remove(item)
                else:
                    # Mettre à jour la quantité
                    item['quantity'] = quantity
                    item['subtotal'] = round(item['price'] * quantity, 2)
                item_found = True
                break
        
        if not item_found:
            return None
        
        # Recalculer les totaux
        self._recalculate_cart_totals(cart)
        
        # Sauvegarder
        cart['updated_at'] = datetime.now().isoformat()
        self.redis_cart.set_cart(session_id, cart)
        
        return cart
    
    def remove_item_from_cart(self, session_id: str, product_id: int) -> Optional[Dict]:
        """Retirer un article du panier"""
        return self.update_item_quantity(session_id, product_id, 0)
    
    def clear_cart(self, session_id: str) -> bool:
        """Vider complètement le panier"""
        return self.redis_cart.delete_cart(session_id)
    
    def associate_cart_to_customer(self, session_id: str, customer_id: int) -> Optional[Dict]:
        """Associer un panier à un client connecté"""
        
        cart = self.get_cart(session_id)
        if not cart:
            return None
        
        cart['customer_id'] = customer_id
        cart['updated_at'] = datetime.now().isoformat()
        
        self.redis_cart.set_cart(session_id, cart)
        return cart
    
    def extend_cart_expiry(self, session_id: str, hours: int = 24) -> Optional[Dict]:
        """Prolonger la durée de vie du panier"""
        
        cart = self.get_cart(session_id)
        if not cart:
            return None
        
        # Prolonger dans Redis
        additional_seconds = hours * 3600
        self.redis_cart.extend_cart_expiry(session_id, additional_seconds)
        
        # Mettre à jour la date d'expiration dans les données du panier
        new_expiry = datetime.now() + timedelta(hours=hours)
        cart['expires_at'] = new_expiry.isoformat()
        cart['updated_at'] = datetime.now().isoformat()
        
        self.redis_cart.set_cart(session_id, cart)
        return cart
    
    def recalculate_cart(self, session_id: str, tax_service) -> Optional[Dict]:
        """Recalculer complètement le panier avec taxes"""
        
        cart = self.get_cart(session_id)
        if not cart:
            return None
        
        # Recalculer les sous-totaux des articles
        for item in cart['items']:
            item['subtotal'] = round(item['price'] * item['quantity'], 2)
        
        # Recalculer les totaux avec taxes
        self._recalculate_cart_totals(cart, tax_service)
        
        # Sauvegarder
        cart['updated_at'] = datetime.now().isoformat()
        self.redis_cart.set_cart(session_id, cart)
        
        return cart
    
    def cleanup_expired_carts(self) -> int:
        """Nettoyer les paniers expirés"""
        return self.redis_cart.cleanup_expired_carts()
    
    def get_cart_stats(self) -> Dict:
        """Obtenir des statistiques sur les paniers"""
        return self.redis_cart.get_cart_stats()
    
    def _recalculate_cart_totals(self, cart: Dict, tax_service=None):
        """Recalculer les totaux du panier"""
        
        # Calculer le nombre total d'articles et le montant total
        total_items = sum(item['quantity'] for item in cart['items'])
        total_amount = sum(item['subtotal'] for item in cart['items'])
        
        # Calculer les taxes si un service de taxes est fourni
        tax_amount = 0.0
        if tax_service:
            tax_amount = tax_service.calculate_taxes(total_amount, cart.get('customer_id'))
        
        # Montant final
        final_amount = total_amount + tax_amount
        
        # Mettre à jour le panier
        cart['total_items'] = total_items
        cart['total_amount'] = round(total_amount, 2)
        cart['tax_amount'] = round(tax_amount, 2)
        cart['final_amount'] = round(final_amount, 2)
    
    def _get_product_info(self, product_id: int) -> Optional[Dict]:
        """Récupérer les informations d'un produit depuis le Product Service"""
        try:
            response = requests.get(
                f"{self.product_service_url}/api/v1/products/{product_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Erreur lors de la récupération du produit {product_id}: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"Erreur de connexion au Product Service pour le produit {product_id}: {e}")
            return None


class TaxService:
    """Service de calcul des taxes pour les paniers"""
    
    def __init__(self):
        # Taux de taxes canadiens par province
        self.tax_rates = {
            'QC': {'gst': 0.05, 'pst': 0.09975, 'total': 0.14975},  # Québec
            'ON': {'gst': 0.05, 'pst': 0.08, 'total': 0.13},        # Ontario  
            'BC': {'gst': 0.05, 'pst': 0.07, 'total': 0.12},        # Colombie-Britannique
            'AB': {'gst': 0.05, 'pst': 0.0, 'total': 0.05},         # Alberta
            'SK': {'gst': 0.05, 'pst': 0.06, 'total': 0.11},        # Saskatchewan
            'MB': {'gst': 0.05, 'pst': 0.07, 'total': 0.12},        # Manitoba
            'NS': {'gst': 0.0, 'pst': 0.0, 'total': 0.15},          # Nouvelle-Écosse (HST)
            'NB': {'gst': 0.0, 'pst': 0.0, 'total': 0.15},          # Nouveau-Brunswick (HST)
            'PE': {'gst': 0.0, 'pst': 0.0, 'total': 0.15},          # Île-du-Prince-Édouard (HST)
            'NL': {'gst': 0.0, 'pst': 0.0, 'total': 0.15},          # Terre-Neuve-et-Labrador (HST)
            'YT': {'gst': 0.05, 'pst': 0.0, 'total': 0.05},         # Yukon
            'NT': {'gst': 0.05, 'pst': 0.0, 'total': 0.05},         # Territoires du Nord-Ouest
            'NU': {'gst': 0.05, 'pst': 0.0, 'total': 0.05}          # Nunavut
        }
        self.default_province = 'QC'  # Province par défaut
    
    def calculate_taxes(self, amount: float, customer_id: Optional[int] = None, province: Optional[str] = None) -> float:
        """Calculer les taxes sur un montant"""
        
        if amount <= 0:
            return 0.0
        
        # Déterminer la province (par défaut QC si non spécifiée)
        tax_province = province or self.default_province
        
        # Récupérer les taux de taxes pour la province
        if tax_province not in self.tax_rates:
            tax_province = self.default_province
        
        tax_rate = self.tax_rates[tax_province]['total']
        
        # Calculer les taxes
        tax_amount = amount * tax_rate
        
        # Arrondir à 2 décimales
        return round(tax_amount, 2)
    
    def get_tax_breakdown(self, amount: float, province: Optional[str] = None) -> Dict:
        """Obtenir le détail des taxes"""
        
        if amount <= 0:
            return {'gst': 0.0, 'pst': 0.0, 'hst': 0.0, 'total': 0.0}
        
        tax_province = province or self.default_province
        
        if tax_province not in self.tax_rates:
            tax_province = self.default_province
        
        rates = self.tax_rates[tax_province]
        
        # Calculer chaque composante
        gst = round(amount * rates['gst'], 2)
        pst = round(amount * rates['pst'], 2)
        hst = 0.0
        
        # Pour les provinces avec HST, tout est dans 'total'
        if rates['gst'] == 0 and rates['pst'] == 0:
            hst = round(amount * rates['total'], 2)
            gst = 0.0
            pst = 0.0
        
        total = gst + pst + hst
        
        return {
            'gst': gst,
            'pst': pst, 
            'hst': hst,
            'total': round(total, 2),
            'province': tax_province,
            'rates': rates
        }
    
    def get_supported_provinces(self) -> List[Dict]:
        """Obtenir la liste des provinces supportées avec leurs taux"""
        
        provinces = []
        for code, rates in self.tax_rates.items():
            provinces.append({
                'code': code,
                'gst_rate': rates['gst'],
                'pst_rate': rates['pst'],
                'total_rate': rates['total']
            })
        
        return provinces


class CartValidationService:
    """Service de validation des paniers"""
    
    def __init__(self, product_service_url: str):
        self.product_service_url = product_service_url
    
    def validate_cart(self, cart: Dict) -> Dict:
        """Valider un panier avant checkout"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'updated_items': []
        }
        
        if not cart['items']:
            validation_result['valid'] = False
            validation_result['errors'].append("Le panier est vide")
            return validation_result
        
        # Valider chaque article
        for item in cart['items']:
            item_validation = self._validate_cart_item(item)
            
            if not item_validation['valid']:
                validation_result['valid'] = False
                validation_result['errors'].extend(item_validation['errors'])
            
            if item_validation['warnings']:
                validation_result['warnings'].extend(item_validation['warnings'])
            
            if item_validation['updated']:
                validation_result['updated_items'].append(item_validation['updated_item'])
        
        return validation_result
    
    def _validate_cart_item(self, item: Dict) -> Dict:
        """Valider un article du panier"""
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'updated': False,
            'updated_item': None
        }
        
        try:
            # Vérifier que le produit existe toujours
            response = requests.get(
                f"{self.product_service_url}/api/v1/products/{item['product_id']}",
                timeout=5
            )
            
            if response.status_code == 404:
                result['valid'] = False
                result['errors'].append(f"Produit {item['product_name']} n'est plus disponible")
                return result
            
            if response.status_code != 200:
                result['warnings'].append(f"Impossible de vérifier la disponibilité de {item['product_name']}")
                return result
            
            product = response.json()
            
            # Vérifier le stock
            if product['stock'] < item['quantity']:
                if product['stock'] > 0:
                    result['warnings'].append(
                        f"Stock insuffisant pour {item['product_name']}. "
                        f"Disponible: {product['stock']}, Demandé: {item['quantity']}"
                    )
                    # Mettre à jour la quantité
                    updated_item = item.copy()
                    updated_item['quantity'] = product['stock']
                    updated_item['subtotal'] = round(updated_item['price'] * product['stock'], 2)
                    result['updated'] = True
                    result['updated_item'] = updated_item
                else:
                    result['valid'] = False
                    result['errors'].append(f"Produit {item['product_name']} en rupture de stock")
            
            # Vérifier si le prix a changé
            if abs(product['prix'] - item['price']) > 0.01:
                result['warnings'].append(
                    f"Prix modifié pour {item['product_name']}. "
                    f"Ancien: {item['price']}$, Nouveau: {product['prix']}$"
                )
                # Mettre à jour le prix
                if not result['updated']:
                    result['updated_item'] = item.copy()
                    result['updated'] = True
                
                result['updated_item']['price'] = product['prix']
                result['updated_item']['subtotal'] = round(
                    product['prix'] * result['updated_item']['quantity'], 2
                )
            
        except requests.RequestException:
            result['warnings'].append(f"Impossible de vérifier {item['product_name']}")
        
        return result 