#!/usr/bin/env python3
"""
Tests pour l'interface web de supervisione
"""

import pytest
import time
from unittest.mock import Mock, patch
from decimal import Decimal

from src.web.app import create_app
from src.domain.entities import IndicateurPerformance


class TestInterfaceWebSupervision:
    """Tests pour l'interface web de supervision uniquement"""

    @pytest.fixture
    def app(self):
        """Créer l'application Flask pour les tests"""
        app = create_app()
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Client de test Flask"""
        return app.test_client()

    def test_route_accueil(self, client):
        """Test de la route d'accueil"""
        with patch('src.web.app.get_db_session'):
            response = client.get('/')
        
        assert response.status_code == 200

    def test_route_dashboard(self, client):
        """Test de la route dashboard (tableau de bord)"""
        with patch('src.web.app.get_db_session') as mock_session:
            # Mock du service tableau de bord
            mock_service = Mock()
            mock_service.obtenir_indicateurs_performance.return_value = []
            
            with patch('src.web.app.ServiceTableauBord', return_value=mock_service):
                response = client.get('/dashboard')
        
        assert response.status_code == 200

    def test_dashboard_performance(self, client):
        """Test performance dashboard"""
        with patch('src.web.app.get_db_session') as mock_session:
            mock_service = Mock()
            mock_service.obtenir_indicateurs_performance.return_value = []
            
            with patch('src.web.app.ServiceTableauBord', return_value=mock_service):
                start_time = time.time()
                response = client.get('/dashboard')
                end_time = time.time()
        
        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 1.0, f"Dashboard trop lent: {response_time:.2f}s"

    def test_auto_refresh_dashboard(self, client):
        """Vérifier que le dashboard a l'auto-refresh"""
        with patch('src.web.app.get_db_session') as mock_session:
            mock_service = Mock()
            mock_service.obtenir_indicateurs_performance.return_value = []
            
            with patch('src.web.app.ServiceTableauBord', return_value=mock_service):
                response = client.get('/dashboard')
        
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__]) 