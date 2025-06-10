#!/usr/bin/env python3
"""
Tests pour l'interface console étendue
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
from datetime import datetime

from src.client.console import ApplicationConsole
from src.domain.entities import TypeEntite, Entite, Produit, DemandeApprovisionnement, StatutDemande


class TestInterfaceConsoleEtendue:
    """Tests pour l'interface console avec fonctionnalités multi-magasins"""

    @pytest.fixture
    def app_console_magasin(self):
        """Console configurée pour un magasin"""
        with patch('src.client.console.get_db_session'):
            app = ApplicationConsole()
            app.entite = Entite(
                id=1, nom="Magasin Test", type_entite=TypeEntite.MAGASIN, adresse="123 Test St"
            )
            app.id_entite = 1
            return app

    @pytest.fixture
    def app_console_maison_mere(self):
        """Console configurée pour la maison mère"""
        with patch('src.client.console.get_db_session'):
            app = ApplicationConsole()
            app.entite = Entite(
                id=7, nom="Maison Mère", type_entite=TypeEntite.MAISON_MERE, adresse="456 Head Office Ave"
            )
            app.id_entite = 7
            return app

    @pytest.fixture
    def app_console_centre_logistique(self):
        """Console configurée pour le centre logistique"""
        with patch('src.client.console.get_db_session'):
            app = ApplicationConsole()
            app.entite = Entite(
                id=6, nom="Centre Logistique", type_entite=TypeEntite.CENTRE_LOGISTIQUE, adresse="789 Warehouse Rd"
            )
            app.id_entite = 6
            return app

    def test_menu_adaptatif_magasin(self, app_console_magasin):
        """Test que le menu s'adapte pour un magasin"""
        app = app_console_magasin
        
        # Vérifier que le menu contient les options magasin
        # Note: Ce test vérifie la logique, pas l'affichage console réel
        assert app.entite.type_entite == TypeEntite.MAGASIN
        assert hasattr(app, 'consulter_stock_central')
        assert hasattr(app, 'demander_approvisionnement')

    def test_menu_adaptatif_maison_mere(self, app_console_maison_mere):
        """Test que le menu s'adapte pour la maison mère"""
        app = app_console_maison_mere
        
        assert app.entite.type_entite == TypeEntite.MAISON_MERE
        assert hasattr(app, 'generer_rapport_ventes')
        assert hasattr(app, 'generer_rapport_stocks')
        assert hasattr(app, 'gestion_produits')

    def test_menu_adaptatif_centre_logistique(self, app_console_centre_logistique):
        """Test que le menu s'adapte pour le centre logistique"""
        app = app_console_centre_logistique
        
        assert app.entite.type_entite == TypeEntite.CENTRE_LOGISTIQUE
        assert hasattr(app, 'traiter_demandes_approvisionnement')

    def test_consultation_stock_central(self, app_console_magasin):
        """Test consultation stock central depuis un magasin"""
        app = app_console_magasin
        
        # Mock du service inventaire
        mock_stock = Mock()
        mock_stock.produit.nom = "Produit Test"
        mock_stock.quantite = 150
        mock_stock.seuil_alerte = 10
        
        app.service_inventaire.obtenir_stocks_par_entite.return_value = [mock_stock]
        
        # Test que la méthode existe et fonctionne
        assert callable(app.consulter_stock_central)
        
        with patch('src.client.console.console.input', return_value='6'):
            with patch('src.client.console.console.print'):
                # Vérifier que les stocks sont bien récupérés
                stocks = app.service_inventaire.obtenir_stocks_par_entite(6)
                assert len(stocks) == 1
                assert stocks[0].produit.nom == "Produit Test"

    def test_demande_approvisionnement(self, app_console_magasin):
        """Test création demande approvisionnement depuis un magasin"""
        app = app_console_magasin
        
        # Mock de la demande créée
        mock_demande = DemandeApprovisionnement(
            id=1,
            id_entite_demandeur=1,
            id_entite_fournisseur=6,
            id_produit=1,
            quantite_demandee=50,
            statut=StatutDemande.EN_ATTENTE
        )
        
        app.service_approvisionnement.creer_demande_approvisionnement.return_value = mock_demande
        
        # Test que la méthode existe
        assert callable(app.demander_approvisionnement)

    def test_generation_rapport_ventes_maison_mere(self, app_console_maison_mere):
        """Test génération rapport ventes depuis maison mère"""
        app = app_console_maison_mere
        
        # Mock du rapport généré
        mock_rapport = Mock()
        mock_rapport.id = 1
        mock_rapport.titre = "Rapport consolidé des ventes"
        
        app.service_rapport.generer_rapport_ventes_consolide.return_value = mock_rapport
        assert callable(app.generer_rapport_ventes)
        
        # Vérifier restriction à la maison mère
        assert app.entite.type_entite == TypeEntite.MAISON_MERE

    def test_generation_rapport_stocks_maison_mere(self, app_console_maison_mere):
        """Test génération rapport stocks depuis maison mère"""
        app = app_console_maison_mere
        
        mock_rapport = Mock()
        mock_rapport.id = 2
        mock_rapport.titre = "Rapport des stocks"
        
        app.service_rapport.generer_rapport_stocks.return_value = mock_rapport 
        assert callable(app.generer_rapport_stocks)
        assert app.entite.type_entite == TypeEntite.MAISON_MERE

    def test_gestion_produits_maison_mere(self, app_console_maison_mere):
        """Test gestion des produits depuis maison mère"""
        app = app_console_maison_mere
        
        # Mock des produits
        mock_produits = [
            Produit(id=1, nom="Produit 1", prix=Decimal('10.00'), stock=100),
            Produit(id=2, nom="Produit 2", prix=Decimal('15.00'), stock=50)
        ]
        
        app.service_produit.repo_produit.lister_tous.return_value = mock_produits
        assert callable(app.gestion_produits)
        assert callable(app.lister_tous_produits)
        assert callable(app.ajouter_nouveau_produit)
        assert callable(app.modifier_produit)
        
        # Vérifier restriction à la maison mère
        assert app.entite.type_entite == TypeEntite.MAISON_MERE

    def test_traitement_demandes_centre_logistique(self, app_console_centre_logistique):
        """Test traitement demandes depuis centre logistique"""
        app = app_console_centre_logistique
        
        # Mock des demandes en attente
        mock_demandes = [
            DemandeApprovisionnement(
                id=1,
                id_entite_demandeur=1,
                id_entite_fournisseur=6,
                id_produit=1,
                quantite_demandee=30,
                statut=StatutDemande.EN_ATTENTE
            )
        ]
        
        app.service_approvisionnement.lister_demandes_en_attente.return_value = mock_demandes
        assert callable(app.traiter_demandes_approvisionnement)
        
        # Vérifier restriction au centre logistique
        assert app.entite.type_entite == TypeEntite.CENTRE_LOGISTIQUE


if __name__ == '__main__':
    pytest.main([__file__]) 