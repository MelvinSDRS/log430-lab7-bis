"""
Cache distribué Redis pour l'API POS Multi-Magasins
Optimisation des endpoints critiques avec cache intelligent
"""

import redis
import json
import hashlib
import logging
import time
from functools import wraps
from flask import request, current_app
from flask_caching import Cache
from datetime import timedelta
import os

logger = logging.getLogger(__name__)

cache = Cache()

# Variable pour désactiver le cache (pour tests)
CACHE_DISABLED = os.getenv('DISABLE_CACHE', 'false').lower() == 'true'

cache_hits = 0
cache_misses = 0
cache_operations = {}

redis_pool = None
redis_client = None

def init_cache(app):
    """Initialiser le cache Redis avec l'application Flask"""
    global redis_pool, redis_client
    
    redis_password = os.getenv('REDIS_PASSWORD', 'redis-secret-lab4-2025')
    redis_url = f"redis://:{redis_password}@redis-cache:6379/0"
    
    redis_pool = redis.ConnectionPool.from_url(
        redis_url,
        max_connections=20,
        retry_on_timeout=True,
        socket_keepalive=True,
        socket_keepalive_options={},
        health_check_interval=30
    )
    redis_client = redis.Redis(connection_pool=redis_pool)
    
    cache_config = {
        'CACHE_TYPE': 'RedisCache',
        'CACHE_REDIS_URL': redis_url,
        'CACHE_DEFAULT_TIMEOUT': 300,
        'CACHE_KEY_PREFIX': 'pos_api_',
    }
    
    app.config.update(cache_config)
    cache.init_app(app)
    
    logger.info(f"Cache Redis initialisé avec pool de connexions")
    
    try:
        redis_client.ping()
        warm_cache()
    except Exception as e:
        logger.error(f"Erreur connexion Redis: {e}")
    
    return cache


def generate_cache_key(endpoint, *args, **kwargs):
    """Générer une clé de cache optimisée pour améliorer le hit rate"""
    query_params = dict(request.args) if request else {}
    
    excluded_params = ['timestamp', '_', 'cache_bust', 't']
    filtered_params = {k: v for k, v in query_params.items() 
                      if k not in excluded_params}
    
    if 'page' in filtered_params:
        filtered_params['page'] = str(filtered_params['page'])
    if 'per_page' in filtered_params:
        filtered_params['per_page'] = str(min(int(filtered_params['per_page']), 100))
    
    key_data = {
        'endpoint': endpoint,
        'query': filtered_params
    }
    
    key_string = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{endpoint}:{key_hash}"


def cache_endpoint(timeout=300, key_prefix='', invalidate_on=None):
    """
    Décorateur pour cache automatique des endpoints REST
    
    Args:
        timeout: Durée de vie du cache en secondes
        key_prefix: Préfixe optionnel pour la clé
        invalidate_on: Liste d'événements qui invalident le cache
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global cache_hits, cache_misses
            
            if CACHE_DISABLED:
                logger.info(f"Cache DISABLED - {func.__name__}")
                return func(*args, **kwargs)
            
            # Générer la clé de cache
            endpoint_name = f"{key_prefix}{func.__name__}" if key_prefix else func.__name__
            cache_key = generate_cache_key(endpoint_name, *args, **kwargs)
            
            start_time = time.time()
            
            # Tentative de récupération du cache
            try:
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    cache_hits += 1
                    duration = time.time() - start_time
                    
                    logger.info(
                        f"Cache HIT - {endpoint_name}",
                        extra={
                            'extra_data': {
                                'event': 'cache_hit',
                                'endpoint': endpoint_name,
                                'cache_key': cache_key,
                                'duration_ms': round(duration * 1000, 2)
                            }
                        }
                    )
                    
                    return cached_result
                    
            except Exception as e:
                logger.warning(f"Erreur cache GET - {endpoint_name}: {str(e)}")
            
            cache_misses += 1
            result = func(*args, **kwargs)
            
            # Sauvegarder en cache
            try:
                cache.set(cache_key, result, timeout=timeout)
                duration = time.time() - start_time
                
                logger.info(
                    f"Cache MISS + SET - {endpoint_name}",
                    extra={
                        'extra_data': {
                            'event': 'cache_miss_set',
                            'endpoint': endpoint_name,
                            'cache_key': cache_key,
                            'timeout': timeout,
                            'duration_ms': round(duration * 1000, 2)
                        }
                    }
                )
                
            except Exception as e:
                logger.warning(f"Erreur cache SET - {endpoint_name}: {str(e)}")
            
            return result
            
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """Invalider tous les caches correspondant à un pattern"""
    global redis_client
    try:
        if not redis_client:
            redis_client = redis.Redis(connection_pool=redis_pool)
        
        keys = redis_client.keys(f"pos_api_{pattern}*")
        
        if keys:
            redis_client.delete(*keys)
            logger.info(f"Cache invalidé - Pattern: {pattern}, Clés supprimées: {len(keys)}")
            return len(keys)
        
        return 0
        
    except Exception as e:
        logger.error(f"Erreur invalidation cache pattern {pattern}: {str(e)}")
        return 0


def invalidate_endpoint_cache(endpoint_name):
    """Invalider le cache d'un endpoint spécifique"""
    return invalidate_cache_pattern(endpoint_name)


def warm_cache():
    """Préchauffer le cache avec les données les plus fréquemment accédées"""
    global redis_client
    try:
        if not redis_client:
            return
        
        logger.info("Démarrage du cache warming")
        
        warm_keys = [
            'pos_api_stores_get:default',
            'pos_api_products_get:page_1',
            'pos_api_reports_get:dashboard'
        ]
        
        for key in warm_keys:
            if not redis_client.exists(key):
                logger.debug(f"Cache warming - clé à préchauffer: {key}")
        
        logger.info("Cache warming terminé")
        
    except Exception as e:
        logger.warning(f"Erreur cache warming: {str(e)}")


def check_cache_health():
    """Vérifier la santé du cache et alerter si nécessaire"""
    global cache_hits, cache_misses
    
    total_requests = cache_hits + cache_misses
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    
    if total_requests > 100 and hit_rate < 30:
        logger.warning(f"Cache hit rate trop faible: {hit_rate:.2f}%")
    
    try:
        if redis_client:
            redis_info = redis_client.info()
            used_memory = redis_info.get('used_memory', 0)
            max_memory = redis_info.get('maxmemory', 512 * 1024 * 1024)
            
            if used_memory > (max_memory * 0.8):
                logger.warning("Utilisation mémoire Redis élevée")
                
    except Exception as e:
        logger.error(f"Erreur vérification santé cache: {str(e)}")


def get_cache_stats():
    """Récupérer les statistiques du cache"""
    global cache_hits, cache_misses, redis_client
    
    total_requests = cache_hits + cache_misses
    hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
    
    try:
        if not redis_client:
            redis_client = redis.Redis(connection_pool=redis_pool)
            
        redis_info = redis_client.info()
        
        stats = {
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'redis_info': {
                'used_memory': redis_info.get('used_memory_human'),
                'connected_clients': redis_info.get('connected_clients'),
                'total_commands_processed': redis_info.get('total_commands_processed'),
                'keyspace_hits': redis_info.get('keyspace_hits', 0),
                'keyspace_misses': redis_info.get('keyspace_misses', 0),
                'uptime_in_seconds': redis_info.get('uptime_in_seconds', 0)
            }
        }
        
        check_cache_health()
        return stats
        
    except Exception as e:
        logger.error(f"Erreur récupération stats cache: {str(e)}")
        return {
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2),
            'error': str(e)
        }


CACHE_TIMEOUTS = {
    'stores_performances': 600,
    'dashboard': 300,
    'products_list': 900,
    'stock_ruptures': 180,
    'reports_list': 1200,
    'store_performance': 600,
}


def get_cache_timeout(endpoint_name):
    """Récupérer le timeout approprié pour un endpoint"""
    return CACHE_TIMEOUTS.get(endpoint_name, 300) 