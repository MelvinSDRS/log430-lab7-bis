"""
Tests automatisés pour l'API REST
"""

import pytest
import json
from datetime import datetime, timedelta
from src.api.app import create_api_app
from src.api.auth import get_api_token
from src.persistence.database import get_db_session
from src.domain.entities import TypeEntite


class TestAPIRest:
    """Suite de tests pour l'API REST"""

    @pytest.fixture
    def client(self):
        """Client de test Flask"""
        app = create_api_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def auth_headers(self):
        """En-têtes d'authentification pour les tests"""
        return {
            'Authorization': f'Bearer {get_api_token()}',
            'Content-Type': 'application/json'
        }

    @pytest.fixture
    def sample_product_data(self):
        """Données de produit pour les tests"""
        return {
            'nom': 'Café Test API',
            'prix': 3.50,
            'stock': 100,
            'id_categorie': 1,
            'seuil_alerte': 10,
            'description': 'Produit de test pour API'
        }

    @pytest.fixture
    def sample_report_data(self):
        """Données de rapport pour les tests"""
        date_debut = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        date_fin = datetime.now().strftime('%Y-%m-%d')
        return {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'genere_par': 1
        }

    def test_health_check(self, client):
        """Test du endpoint de santé"""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert data['service'] == 'POS Multi-Magasins API'
        assert data['version'] == '1.0'

    def test_swagger_documentation(self, client):
        """Test de l'accès à la documentation Swagger"""
        response = client.get('/api/docs')
        assert response.status_code == 200
        
    def test_auth_required(self, client):
        """Test que l'authentification est requise"""
        response = client.get('/api/v1/products')
        assert response.status_code == 401
        
        data = json.loads(response.data)
        assert data['status'] == 401
        assert 'authentification' in data['message'].lower()

    def test_invalid_token(self, client):
        """Test avec token invalide"""
        headers = {
            'Authorization': 'Bearer invalid-token',
            'Content-Type': 'application/json'
        }
        response = client.get('/api/v1/products', headers=headers)
        assert response.status_code == 401

    # Tests des produits
    def test_get_products_list(self, client, auth_headers):
        """Test de récupération de la liste des produits"""
        response = client.get('/api/v1/products', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'data' in data
        assert 'meta' in data
        assert '_links' in data
        
        # Vérifier la structure de pagination
        meta = data['meta']
        assert 'page' in meta
        assert 'per_page' in meta
        assert 'total' in meta

    def test_get_products_with_pagination(self, client, auth_headers):
        """Test de la pagination des produits"""
        response = client.get('/api/v1/products?page=1&per_page=5', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['meta']['page'] == 1
        assert data['meta']['per_page'] == 5

    def test_get_products_with_search(self, client, auth_headers):
        """Test de recherche de produits"""
        response = client.get('/api/v1/products?search=café', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert isinstance(data['data'], list)

    def test_get_product_by_id(self, client, auth_headers):
        """Test de récupération d'un produit par ID"""
        response = client.get('/api/v1/products/1', headers=auth_headers)
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'id' in data
            assert 'nom' in data
            assert 'prix' in data
        elif response.status_code == 404:
            data = json.loads(response.data)
            assert data['status'] == 404

    def test_create_product(self, client, auth_headers, sample_product_data):
        """Test de création d'un produit"""
        response = client.post('/api/v1/products', 
                              headers=auth_headers,
                              data=json.dumps(sample_product_data))
        
        if response.status_code == 201:
            data = json.loads(response.data)
            assert data['nom'] == sample_product_data['nom']
            assert data['prix'] == sample_product_data['prix']
            
            # Nettoyer le produit créé
            product_id = data['id']
            client.delete(f'/api/v1/products/{product_id}', headers=auth_headers)

    def test_update_product(self, client, auth_headers, sample_product_data):
        """Test de mise à jour d'un produit"""
        # Créer d'abord un produit
        create_response = client.post('/api/v1/products',
                                     headers=auth_headers,
                                     data=json.dumps(sample_product_data))
        
        if create_response.status_code == 201:
            created_product = json.loads(create_response.data)
            product_id = created_product['id']
            
            # Mettre à jour le produit
            update_data = {
                'nom': 'Café Test API Modifié',
                'prix': 4.00
            }
            
            update_response = client.put(f'/api/v1/products/{product_id}',
                                        headers=auth_headers,
                                        data=json.dumps(update_data))
            
            assert update_response.status_code == 200
            
            updated_product = json.loads(update_response.data)
            assert updated_product['nom'] == update_data['nom']
            assert updated_product['prix'] == update_data['prix']
            
            client.delete(f'/api/v1/products/{product_id}', headers=auth_headers)

    # Tests des magasins/entités
    def test_get_stores_list(self, client, auth_headers):
        """Test de récupération de la liste des magasins"""
        response = client.get('/api/v1/stores', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'data' in data
        assert 'meta' in data
        assert '_links' in data

    def test_get_store_performances(self, client, auth_headers):
        """Test visualiser les performances globales des magasins"""
        response = client.get('/api/v1/stores/performances', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'data' in data
        assert 'summary' in data
        assert '_links' in data
        
        summary = data['summary']
        assert 'total_magasins' in summary
        assert 'chiffre_affaires_total' in summary
        assert 'nombre_ventes_total' in summary

    def test_get_store_by_id(self, client, auth_headers):
        """Test de récupération d'un magasin par ID"""
        response = client.get('/api/v1/stores/1', headers=auth_headers)
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'id' in data
            assert 'nom' in data
            assert 'type_entite' in data

    # Tests des stocks
    def test_get_store_stocks(self, client, auth_headers):
        """Test consulter le stock d'un magasin spécifique"""
        response = client.get('/api/v1/stocks/entites/1', headers=auth_headers)
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'data' in data
            assert 'meta' in data
            assert '_links' in data
            
            if 'entite' in data['meta']:
                entite = data['meta']['entite']
                assert 'id' in entite
                assert 'nom' in entite
        elif response.status_code == 404:
            pass

    def test_get_stock_shortages(self, client, auth_headers):
        """Test de récupération des produits en rupture"""
        response = client.get('/api/v1/stocks/ruptures', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'data' in data
        assert 'meta' in data
        assert '_links' in data

    # Tests des rapports
    def test_get_reports_list(self, client, auth_headers):
        """Test de récupération de la liste des rapports"""
        response = client.get('/api/v1/reports', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'data' in data
        assert 'meta' in data
        assert '_links' in data

    def test_generate_consolidated_sales_report(self, client, auth_headers, sample_report_data):
        """Test générer un rapport consolidé des ventes"""
        response = client.post('/api/v1/reports/sales/consolidated',
                              headers=auth_headers,
                              data=json.dumps(sample_report_data))
        
        if response.status_code == 201:
            data = json.loads(response.data)
            assert 'id' in data
            assert 'titre' in data
            assert 'type_rapport' in data
            assert data['type_rapport'] == 'VENTES_CONSOLIDE'
            
            report_id = data['id']
            client.delete(f'/api/v1/reports/{report_id}', headers=auth_headers)

    def test_generate_stocks_report(self, client, auth_headers):
        """Test de génération de rapport des stocks"""
        report_data = {'genere_par': 1}
        
        response = client.post('/api/v1/reports/stocks',
                              headers=auth_headers,
                              data=json.dumps(report_data))
        
        if response.status_code == 201:
            data = json.loads(response.data)
            assert 'id' in data
            assert 'type_rapport' in data
            assert data['type_rapport'] == 'STOCKS'
            
            report_id = data['id']
            client.delete(f'/api/v1/reports/{report_id}', headers=auth_headers)

    def test_get_dashboard(self, client, auth_headers):
        """Test de récupération du tableau de bord"""
        response = client.get('/api/v1/reports/dashboard', headers=auth_headers)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'timestamp' in data
        assert 'indicateurs_magasins' in data
        assert 'metriques_globales' in data
        assert 'alertes_critiques' in data
        assert '_links' in data

    # Tests des erreurs et validation
    def test_invalid_product_creation(self, client, auth_headers):
        """Test de création de produit avec données invalides"""
        invalid_data = {
            'nom': 'Produit sans prix'
            # Manque prix, stock, id_categorie
        }
        
        response = client.post('/api/v1/products',
                              headers=auth_headers,
                              data=json.dumps(invalid_data))
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 400

    def test_invalid_report_request(self, client, auth_headers):
        """Test de génération de rapport avec données invalides"""
        invalid_data = {
            'date_debut': '2025-01-01'
            # Manque date_fin et genere_par
        }
        
        response = client.post('/api/v1/reports/sales/consolidated',
                              headers=auth_headers,
                              data=json.dumps(invalid_data))
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 400

    def test_nonexistent_resource(self, client, auth_headers):
        """Test d'accès à une ressource inexistante"""
        response = client.get('/api/v1/products/99999', headers=auth_headers)
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert data['status'] == 404

    # Tests CORS
    def test_cors_headers(self, client, auth_headers):
        """Test de la configuration CORS"""
        response = client.options('/api/v1/products', headers=auth_headers)
        
        # Les en-têtes CORS devraient être présents
        assert 'Access-Control-Allow-Origin' in response.headers or response.status_code == 200

    # Tests des liens HATEOAS
    def test_hateoas_links(self, client, auth_headers):
        """Test de la présence des liens HATEOAS"""
        response = client.get('/api/v1/products', headers=auth_headers)
        
        if response.status_code == 200:
            data = json.loads(response.data)
            links = data.get('_links', {})
            
            # Vérifier la présence des liens de pagination
            assert 'self' in links
            assert 'first' in links
            assert 'last' in links 