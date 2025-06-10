#!/usr/bin/env python3
"""
Interface web simplifiée - UC3 et UC8 uniquement
Système POS Multi-Magasins
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, timedelta
import json
import logging
import os
from logging.handlers import RotatingFileHandler

from ..persistence.database import get_db_session
from ..domain.services import ServiceTableauBord
from ..persistence.repositories import RepositoryEntite
from ..domain.entities import TypeEntite


def create_app():
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)
    app.secret_key = 'dev-secret-key-change-in-production'
    
    configure_logging(app)
    
    app.jinja_env.globals.update(
        enumerate=enumerate,
        len=len,
        datetime=datetime
    )
    
    @app.route('/')
    def index():
        """Page d'accueil - Interface web légère pour supervision"""
        app.logger.info("Accès à l'interface de supervision")
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard():
        """UC3 - Tableau de bord avec indicateurs clés pour supervision"""
        app.logger.info("Accès au tableau de bord de supervision")
        
        session = get_db_session()
        try:
            service_tableau_bord = ServiceTableauBord(session)
            indicateurs = service_tableau_bord.obtenir_indicateurs_performance()
            
            app.logger.info(f"Tableau de bord généré - {len(indicateurs)} magasins")
            return render_template('dashboard.html', 
                                   indicateurs=indicateurs,
                                   titre="Supervision - Indicateurs clés")
        except Exception as e:
            app.logger.error(f"Erreur génération tableau de bord: {str(e)}")
            flash("Erreur lors du chargement des indicateurs", "error")
            return redirect(url_for('index'))
        finally:
            session.close()

    @app.errorhandler(404)
    def page_not_found(e):
        """Gestionnaire d'erreur 404"""
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """Gestionnaire d'erreur 500"""
        app.logger.error(f"Erreur interne: {str(e)}")
        return render_template('500.html'), 500
    
    return app


def configure_logging(app):
    """Configuration du système de logging"""
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        file_handler = RotatingFileHandler(
            'logs/pos_multimagasins.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Démarrage du système POS Multi-Magasins')
    
    service_logger = logging.getLogger('src.domain.services')
    service_logger.setLevel(logging.INFO)
    
    if not service_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        service_logger.addHandler(console_handler)
        
        if not app.debug:
            service_handler = RotatingFileHandler(
                'logs/services.log',
                maxBytes=5242880,  # 5MB
                backupCount=5
            )
            service_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            service_handler.setLevel(logging.INFO)
            service_logger.addHandler(service_handler)


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 