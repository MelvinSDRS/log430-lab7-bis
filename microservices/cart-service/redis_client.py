#!/usr/bin/env python3
"""
Redis client configuration pour Cart Service
Base de données: Redis (cart_cache)
"""

import os
import redis
import json
from typing import Optional, Dict, Any

# Configuration Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://:cart-cache-secret-2025@cart-cache:6379/0')
REDIS_HOST = os.getenv('REDIS_HOST', 'cart-cache')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'cart-cache-secret-2025')
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

# Configuration connexions
REDIS_SOCKET_CONNECT_TIMEOUT = 5
REDIS_SOCKET_TIMEOUT = 5
REDIS_CONNECTION_POOL_MAX_CONNECTIONS = 20


def init_redis_client():
    """Initialiser le client Redis avec pool de connexions"""
    
    try:
        # Pool de connexions Redis
        pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            db=REDIS_DB,
            max_connections=REDIS_CONNECTION_POOL_MAX_CONNECTIONS,
            socket_connect_timeout=REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=True,
            health_check_interval=30
        )
        
        # Client Redis
        client = redis.Redis(
            connection_pool=pool,
            decode_responses=True,  # Décoder automatiquement les bytes en strings
            encoding='utf-8'
        )
        
        # Test de connexion
        client.ping()
        print("Redis client initialisé avec succès")
        
        return client
        
    except redis.ConnectionError as e:
        print(f"Erreur de connexion Redis: {e}")
        raise
    except Exception as e:
        print(f"Erreur lors de l'initialisation Redis: {e}")
        raise


class RedisCartClient:
    """Client Redis spécialisé pour les opérations sur les paniers"""
    
    def __init__(self, redis_client):
        self.client = redis_client
        self.cart_prefix = "cart:"
        self.cart_expiry = 86400  # 24 heures en secondes
    
    def _get_cart_key(self, session_id: str) -> str:
        """Générer la clé Redis pour un panier"""
        return f"{self.cart_prefix}{session_id}"
    
    def get_cart(self, session_id: str) -> Optional[Dict]:
        """Récupérer un panier depuis Redis"""
        try:
            cart_key = self._get_cart_key(session_id)
            cart_data = self.client.get(cart_key)
            
            if cart_data:
                return json.loads(cart_data)
            return None
            
        except (redis.RedisError, json.JSONDecodeError) as e:
            print(f"Erreur lors de la récupération du panier {session_id}: {e}")
            return None
    
    def set_cart(self, session_id: str, cart_data: Dict, expiry: Optional[int] = None) -> bool:
        """Sauvegarder un panier dans Redis"""
        try:
            cart_key = self._get_cart_key(session_id)
            cart_json = json.dumps(cart_data, default=str)
            
            expiry_seconds = expiry or self.cart_expiry
            
            return self.client.setex(cart_key, expiry_seconds, cart_json)
            
        except (redis.RedisError, json.JSONEncodeError) as e:
            print(f"Erreur lors de la sauvegarde du panier {session_id}: {e}")
            return False
    
    def delete_cart(self, session_id: str) -> bool:
        """Supprimer un panier de Redis"""
        try:
            cart_key = self._get_cart_key(session_id)
            return bool(self.client.delete(cart_key))
            
        except redis.RedisError as e:
            print(f"Erreur lors de la suppression du panier {session_id}: {e}")
            return False
    
    def cart_exists(self, session_id: str) -> bool:
        """Vérifier si un panier existe"""
        try:
            cart_key = self._get_cart_key(session_id)
            return bool(self.client.exists(cart_key))
            
        except redis.RedisError as e:
            print(f"Erreur lors de la vérification du panier {session_id}: {e}")
            return False
    
    def extend_cart_expiry(self, session_id: str, additional_seconds: int) -> bool:
        """Prolonger la durée de vie d'un panier"""
        try:
            cart_key = self._get_cart_key(session_id)
            current_ttl = self.client.ttl(cart_key)
            
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                return bool(self.client.expire(cart_key, new_ttl))
            else:
                # Le panier n'existe pas ou n'a pas d'expiration
                return bool(self.client.expire(cart_key, additional_seconds))
                
        except redis.RedisError as e:
            print(f"Erreur lors de l'extension du panier {session_id}: {e}")
            return False
    
    def get_cart_ttl(self, session_id: str) -> int:
        """Obtenir le TTL restant d'un panier"""
        try:
            cart_key = self._get_cart_key(session_id)
            return self.client.ttl(cart_key)
            
        except redis.RedisError as e:
            print(f"Erreur lors de la récupération du TTL du panier {session_id}: {e}")
            return -1
    
    def get_all_cart_keys(self) -> list:
        """Récupérer toutes les clés de paniers (pour nettoyage administratif)"""
        try:
            pattern = f"{self.cart_prefix}*"
            return self.client.keys(pattern)
            
        except redis.RedisError as e:
            print(f"Erreur lors de la récupération des clés de paniers: {e}")
            return []
    
    def cleanup_expired_carts(self) -> int:
        """Nettoyer les paniers expirés (retourne le nombre supprimé)"""
        try:
            all_keys = self.get_all_cart_keys()
            expired_count = 0
            
            for key in all_keys:
                ttl = self.client.ttl(key)
                # TTL -2 signifie que la clé n'existe pas (expirée)
                # TTL -1 signifie que la clé n'a pas d'expiration
                if ttl == -2:
                    expired_count += 1
            
            return expired_count
            
        except redis.RedisError as e:
            print(f"Erreur lors du nettoyage des paniers expirés: {e}")
            return 0
    
    def get_cart_stats(self) -> Dict:
        """Obtenir des statistiques sur les paniers"""
        try:
            all_keys = self.get_all_cart_keys()
            total_carts = len(all_keys)
            
            expired_carts = 0
            active_carts = 0
            
            for key in all_keys:
                ttl = self.client.ttl(key)
                if ttl == -2:
                    expired_carts += 1
                elif ttl > 0:
                    active_carts += 1
            
            return {
                'total_carts': total_carts,
                'active_carts': active_carts,
                'expired_carts': expired_carts,
                'redis_memory_usage': self.get_redis_memory_info()
            }
            
        except redis.RedisError as e:
            print(f"Erreur lors de la récupération des statistiques: {e}")
            return {}
    
    def get_redis_memory_info(self) -> Dict:
        """Obtenir les informations mémoire de Redis"""
        try:
            info = self.client.info('memory')
            return {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B')
            }
        except redis.RedisError:
            return {}


# Instance globale (sera initialisée par l'application)
redis_cart_client = None


def get_redis_client():
    """Obtenir l'instance du client Redis (alias pour compatibilité)"""
    return init_redis_client()

def get_redis_cart_client():
    """Obtenir l'instance du client Redis pour les paniers"""
    global redis_cart_client
    if redis_cart_client is None:
        redis_client = init_redis_client()
        redis_cart_client = RedisCartClient(redis_client)
    return redis_cart_client


if __name__ == "__main__":
    # Test de connexion
    try:
        client = init_redis_client()
        print("Test Redis réussi")
        
        # Test des opérations de base
        test_key = "test:cart:123"
        test_data = {"items": [], "total": 0}
        
        # Test SET
        cart_client = RedisCartClient(client)
        success = cart_client.set_cart("test123", test_data, 60)
        print(f"Test SET: {'OK' if success else 'FAILED'}")
        
        # Test GET
        retrieved = cart_client.get_cart("test123")
        print(f"Test GET: {'OK' if retrieved else 'FAILED'}")
        
        # Test DELETE
        deleted = cart_client.delete_cart("test123")
        print(f"Test DELETE: {'OK' if deleted else 'FAILED'}")
        
    except Exception as e:
        print(f"Test Redis échoué: {e}") 