"""
Module de métriques Prometheus pour l'API POS Multi-Magasins
Implémentation des 4 Golden Signals : Latence, Trafic, Erreurs, Saturation
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_flask_exporter import PrometheusMetrics
from flask import Flask, Response
import time
import psutil
import threading
from functools import wraps

# Métriques Golden Signals
# 1. Latence (Latency)
request_duration = Histogram(
    'api_request_duration_seconds',
    'Temps de réponse des requêtes API',
    ['method', 'endpoint', 'status']
)

# 2. Trafic (Traffic)
request_total = Counter(
    'api_requests_total',
    'Nombre total de requêtes',
    ['method', 'endpoint', 'status']
)

# 3. Erreurs (Errors)
error_total = Counter(
    'api_errors_total',
    'Nombre total d\'erreurs',
    ['method', 'endpoint', 'error_type']
)

# 4. Saturation (Saturation)
active_connections = Gauge(
    'api_active_connections',
    'Nombre de connexions actives'
)

database_connections = Gauge(
    'api_database_connections',
    'Connexions base de données',
    ['state']
)

# Métriques système
cpu_usage = Gauge('system_cpu_usage_percent', 'Utilisation CPU')
memory_usage = Gauge('system_memory_usage_percent', 'Utilisation mémoire')

# Métriques business
business_operations = Counter(
    'business_operations_total',
    'Opérations métier',
    ['operation', 'entity_type', 'status']
)

_active_connections_count = 0
_connections_lock = threading.Lock()


def init_prometheus_metrics(app: Flask):
    """Initialiser les métriques Prometheus pour Flask"""
    
    metrics = PrometheusMetrics(app)
    metrics.excluded_paths = ['/metrics', '/api/health']
    
    @app.before_request
    def before_request():
        global _active_connections_count
        with _connections_lock:
            _active_connections_count += 1
            active_connections.set(_active_connections_count)
    
    @app.after_request
    def after_request(response):
        global _active_connections_count
        with _connections_lock:
            _active_connections_count -= 1
            active_connections.set(_active_connections_count)
        return response
    
    @app.route('/metrics')
    def metrics_endpoint():
        """Endpoint pour Prometheus scraping"""
        update_system_metrics()
        
        return Response(
            generate_latest(),
            mimetype='text/plain; version=0.0.4; charset=utf-8'
        )
    
    return metrics


def update_system_metrics():
    """Mettre à jour les métriques système"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        
        cpu_usage.set(cpu_percent)
        memory_usage.set(memory_percent)
        
    except Exception:
        pass


def track_business_operation(operation: str, entity_type: str = 'unknown'):
    """Décorateur pour tracker les opérations métier"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                raise
            finally:
                business_operations.labels(
                    operation=operation,
                    entity_type=entity_type,
                    status=status
                ).inc()
        
        return wrapper
    return decorator


def increment_error_metric(method: str, endpoint: str, error_type: str):
    """Incrémenter le compteur d'erreurs"""
    error_total.labels(
        method=method,
        endpoint=endpoint,
        error_type=error_type
    ).inc()


def record_request_duration(method: str, endpoint: str, status: str, duration: float):
    """Enregistrer la durée d'une requête"""
    request_duration.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).observe(duration)
    
    request_total.labels(
        method=method,
        endpoint=endpoint,
        status=status
    ).inc() 