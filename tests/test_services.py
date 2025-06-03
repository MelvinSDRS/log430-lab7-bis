import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from src.domain.entities import Produit, LigneVente, Vente
from src.domain.services import (ServiceInventaire, ServiceVente,
                                 ServiceTransaction)


class TestServiceInventaire:

    def test_verifier_disponibilite_stock_suffisant(self):
        """Test de vérification de disponibilité avec stock suffisant"""
        session_mock = Mock()
        repo_mock = Mock()

        produit = Produit(
            id=1, nom="Test", prix=Decimal("10.00"),
            stock=5, id_categorie=1
        )

        ligne_vente = LigneVente(produit=produit, qte=3)
        panier = [ligne_vente]

        service = ServiceInventaire(session_mock)
        service.repo_produit = repo_mock
        repo_mock.obtenir_par_id.return_value = produit

        produits_manquants = service.verifier_disponibilite(panier)

        assert len(produits_manquants) == 0
        repo_mock.obtenir_par_id.assert_called_once_with(1)

    def test_verifier_disponibilite_stock_insuffisant(self):
        """Test de vérification de disponibilité avec stock insuffisant"""
        session_mock = Mock()
        repo_mock = Mock()

        produit = Produit(
            id=1, nom="Test", prix=Decimal("10.00"),
            stock=2, id_categorie=1
        )

        ligne_vente = LigneVente(produit=produit, qte=5)
        panier = [ligne_vente]

        service = ServiceInventaire(session_mock)
        service.repo_produit = repo_mock
        repo_mock.obtenir_par_id.return_value = produit

        produits_manquants = service.verifier_disponibilite(panier)

        assert len(produits_manquants) == 1
        assert "Test" in produits_manquants[0]
        assert "stock: 2" in produits_manquants[0]
        assert "demandé: 5" in produits_manquants[0]


class TestServiceTransaction:

    def test_commencer_transaction(self):
        """Test de début de transaction"""
        session_mock = Mock()
        # Simule qu'il n'y a pas de transaction active
        session_mock.in_transaction.return_value = False
        service = ServiceTransaction(session_mock)

        service.commencer()

        session_mock.in_transaction.assert_called_once()
        session_mock.begin.assert_called_once()
        assert service.transaction_active is True

    def test_valider_transaction(self):
        """Test de validation de transaction"""
        session_mock = Mock()
        service = ServiceTransaction(session_mock)
        service.transaction_active = True

        service.valider()

        session_mock.commit.assert_called_once()
        assert service.transaction_active is False

    def test_annuler_transaction(self):
        """Test d'annulation de transaction"""
        session_mock = Mock()
        service = ServiceTransaction(session_mock)
        service.transaction_active = True

        service.annuler()

        session_mock.rollback.assert_called_once()
        assert service.transaction_active is False


class TestServiceVente:

    def test_creer_vente_succes(self):
        """Test de création de vente avec succès"""
        session_mock = Mock()
        service = ServiceVente(session_mock)

        # Mock des services
        service.service_transaction = Mock()
        service.service_inventaire = Mock()
        service.service_paiement = Mock()
        service.repo_vente = Mock()

        # Configuration des mocks
        service.service_inventaire.verifier_disponibilite.return_value = []
        service.service_paiement.facturer.return_value = True

        vente_mock = Vente(
            id=1, horodatage=datetime.now(), id_caisse=1,
            id_caissier=1, statut="COMPLETEE", lignes=[]
        )
        service.repo_vente.sauvegarder.return_value = vente_mock

        produit = Produit(
            id=1, nom="Test", prix=Decimal("10.00"),
            stock=5, id_categorie=1
        )
        panier = [LigneVente(produit=produit, qte=2)]

        vente = service.creer_vente(panier, 1, 1)

        assert vente is not None
        assert vente.id == 1
        service.service_transaction.commencer.assert_called_once()
        service.service_transaction.valider.assert_called_once()
        service.service_inventaire.reserver_stock.assert_called_once_with(
            panier)

    def test_creer_vente_stock_insuffisant(self):
        """Test de création de vente avec stock insuffisant"""
        session_mock = Mock()
        service = ServiceVente(session_mock)

        # Mock des services
        service.service_transaction = Mock()
        service.service_inventaire = Mock()

        # Configuration des mocks - stock insuffisant
        service.service_inventaire.verifier_disponibilite.return_value = [
            "Produit manquant"]

        produit = Produit(
            id=1, nom="Test", prix=Decimal("10.00"),
            stock=1, id_categorie=1
        )
        panier = [LigneVente(produit=produit, qte=5)]

        with pytest.raises(ValueError, match="Stock insuffisant"):
            service.creer_vente(panier, 1, 1)

        service.service_transaction.commencer.assert_called_once()
        assert service.service_transaction.annuler.call_count >= 1
