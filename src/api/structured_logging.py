"""
Module de logging structuré pour l'API POS Multi-Magasins
Implémente un logging avec traçabilité des requêtes et formatage JSON
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from flask import request, g
from functools import wraps


class StructuredFormatter(logging.Formatter):
    """Formatter pour logs structurés en JSON"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if hasattr(g, 'trace_id'):
            log_data['trace_id'] = g.trace_id
        
        if request:
            log_data['request'] = {
                'method': request.method,
                'url': request.url,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', ''),
            }
        
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_structured_logging(app):
    """Configurer le logging structuré pour l'application"""
    
    os.makedirs('logs', exist_ok=True)
    api_logger = logging.getLogger('pos_api')
    api_handler = logging.FileHandler('logs/pos_api_structured.log')
    api_handler.setFormatter(StructuredFormatter())
    api_logger.addHandler(api_handler)
    api_logger.setLevel(logging.INFO)
    
    @app.before_request
    def add_trace_id():
        g.trace_id = str(uuid.uuid4())
        g.start_time = time.time()
        
        api_logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'extra_data': {
                    'event': 'request_start',
                    'trace_id': g.trace_id,
                    'method': request.method,
                    'path': request.path,
                    'query_params': dict(request.args),
                    'headers': dict(request.headers),
                }
            }
        )
    
    @app.after_request
    def log_request_completion(response):
        duration = time.time() - g.start_time
        
        api_logger.info(
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            extra={
                'extra_data': {
                    'event': 'request_end',
                    'trace_id': g.trace_id,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2),
                    'response_size': len(response.get_data()),
                }
            }
        )
        
        return response


def log_business_event(operation: str, entity_type: str, entity_id: str = None, **kwargs):
    """Logger un événement métier avec contexte"""
    logger = logging.getLogger('pos_api')
    
    event_data = {
        'event': 'business_operation',
        'operation': operation,
        'entity_type': entity_type,
        'entity_id': entity_id,
        **kwargs
    }
    
    logger.info(
        f"Business operation: {operation} on {entity_type}",
        extra={'extra_data': event_data}
    )


def log_performance_warning(operation: str, duration: float, threshold: float = 1.0):
    """Logger un avertissement de performance"""
    if duration > threshold:
        logger = logging.getLogger('pos_api')
        logger.warning(
            f"Slow operation detected: {operation}",
            extra={
                'extra_data': {
                    'event': 'performance_warning',
                    'operation': operation,
                    'duration_ms': round(duration * 1000, 2),
                    'threshold_ms': threshold * 1000,
                }
            }
        )


def trace_database_query(func):
    """Décorateur pour tracer les requêtes base de données"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = logging.getLogger('pos_api')
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            logger.info(
                f"Database query executed: {func.__name__}",
                extra={
                    'extra_data': {
                        'event': 'database_query',
                        'function': func.__name__,
                        'duration_ms': round(duration * 1000, 2),
                        'status': 'success',
                    }
                }
            )
            
            # Avertissement si requête lente
            log_performance_warning(f"DB:{func.__name__}", duration, 0.5)
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Database query failed: {func.__name__}",
                extra={
                    'extra_data': {
                        'event': 'database_error',
                        'function': func.__name__,
                        'duration_ms': round(duration * 1000, 2),
                        'error': str(e),
                    }
                }
            )
            raise
    
    return wrapper 