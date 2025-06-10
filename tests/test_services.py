import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from src.domain.entities import Produit, LigneVente, Vente
from src.domain.services import (ServiceInventaire, ServiceVente,
                                 ServiceTransaction, ServiceApprovisionnement,
                                 ServiceRapport, ServiceTableauBord)


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

        produits_manquants = service.verifier_disponibilite(panier, 1)

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

        produits_manquants = service.verifier_disponibilite(panier, 1)

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
            id_caissier=1, id_entite=1, statut="COMPLETEE", lignes=[]
        )
        service.repo_vente.sauvegarder.return_value = vente_mock

        produit = Produit(
            id=1, nom="Test", prix=Decimal("10.00"),
            stock=5, id_categorie=1
        )
        panier = [LigneVente(produit=produit, qte=2)]

        vente = service.creer_vente(panier, 1, 1, 1)

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
            service.creer_vente(panier, 1, 1, 1)

        service.service_transaction.commencer.assert_called_once()
        assert service.service_transaction.annuler.call_count >= 1


class TestServiceApprovisionnement:
    """Tests pour le service d'approvisionnement multi-magasins"""

    def test_creer_demande_approvisionnement(self):
        """Test de création d'une demande d'approvisionnement"""
        session_mock = Mock()
        service = ServiceApprovisionnement(session_mock)
        service.repo_demande = Mock()
        service.repo_stock = Mock()

        # Mock du stock insuffisant
        service.repo_stock.obtenir_stock_entite.return_value = 5

        demande_mock = Mock()
        demande_mock.id = 1
        service.repo_demande.sauvegarder.return_value = demande_mock

        demande = service.creer_demande_approvisionnement(
            id_entite_demandeur=1,
            id_entite_fournisseur=2,
            id_produit=1,
            quantite=10
        )

        assert demande is not None
        service.repo_demande.sauvegarder.assert_called_once()

    def test_traiter_demande_approvisionnement_stock_suffisant(self):
        """Test de traitement d'une demande avec stock suffisant"""
        session_mock = Mock()
        service = ServiceApprovisionnement(session_mock)
        service.repo_demande = Mock()
        service.repo_stock = Mock()
        service.repo_transfert = Mock()

        # Mock de la demande
        demande_mock = Mock()
        demande_mock.id = 1
        demande_mock.statut = "EN_ATTENTE"
        demande_mock.quantite = 10
        demande_mock.produit_id = 1
        demande_mock.entite_source_id = 1
        demande_mock.entite_destination_id = 2

        # Mock du stock suffisant
        service.repo_stock.obtenir_par_produit_et_entite.return_value = Mock(quantite=15)

        resultat = service.approuver_demande(demande_mock.id, 10)

        assert resultat is True
        service.repo_transfert.sauvegarder.assert_called_once()

    def test_traiter_demande_approvisionnement_stock_insuffisant(self):
        """Test de traitement d'une demande avec stock insuffisant"""
        session_mock = Mock()
        service = ServiceApprovisionnement(session_mock)
        service.repo_demande = Mock()
        service.repo_stock = Mock()

        # Mock de la demande
        demande_mock = Mock()
        demande_mock.quantite = 10
        demande_mock.produit_id = 1
        demande_mock.entite_source_id = 1

        # Mock du stock insuffisant
        service.repo_stock.obtenir_par_produit_et_entite.return_value = Mock(quantite=5)

        with pytest.raises(ValueError):
            service.approuver_demande(demande_mock.id, 10)


class TestServiceRapport:
    """Tests pour le service de génération de rapports"""

    def test_generer_rapport_ventes_consolidees(self):
        """Test de génération d'un rapport de ventes consolidées"""
        session_mock = Mock()
        service = ServiceRapport(session_mock)
        service.repo_vente = Mock()
        service.repo_rapport = Mock()

        # Mock des données de ventes
        ventes_mock = [
            Mock(entite_id=1, total=Decimal("100.00"), horodatage=datetime.now()),
            Mock(entite_id=2, total=Decimal("150.00"), horodatage=datetime.now())
        ]
        service.repo_vente.obtenir_ventes_periode.return_value = ventes_mock

        rapport_mock = Mock()
        rapport_mock.id = 1
        service.repo_rapport.sauvegarder.return_value = rapport_mock

        date_debut = datetime.now().date()
        date_fin = datetime.now().date()

        rapport = service.generer_rapport_ventes_consolide(date_debut, date_fin, 1)

        assert rapport is not None
        service.repo_vente.obtenir_ventes_periode.assert_called_once_with(date_debut, date_fin)
        service.repo_rapport.sauvegarder.assert_called_once()

    def test_generer_rapport_stocks_entites(self):
        """Test de génération d'un rapport de stocks par entité"""
        session_mock = Mock()
        service = ServiceRapport(session_mock)
        service.repo_stock = Mock()
        service.repo_rapport = Mock()

        # Mock des données de stocks
        stocks_mock = [
            Mock(entite_id=1, produit_id=1, quantite=50),
            Mock(entite_id=2, produit_id=1, quantite=30)
        ]
        service.repo_stock.obtenir_tous_stocks.return_value = stocks_mock

        rapport_mock = Mock()
        rapport_mock.id = 1
        service.repo_rapport.sauvegarder.return_value = rapport_mock

        rapport = service.generer_rapport_stocks(1)

        assert rapport is not None
        service.repo_stock.obtenir_tous_stocks.assert_called_once()
        service.repo_rapport.sauvegarder.assert_called_once()


class TestServiceTableauBord:
    """Tests pour le service de tableau de bord"""

    def test_calculer_indicateurs_performance(self):
        """Test de calcul des indicateurs de performance"""
        session_mock = Mock()
        service = ServiceTableauBord(session_mock)
        service.repo_vente = Mock()
        service.repo_stock = Mock()
        service.repo_entite = Mock()

        # Mock des entités
        entites_mock = [
            Mock(id=1, nom="Magasin 1", type="MAGASIN"),
            Mock(id=2, nom="Magasin 2", type="MAGASIN")
        ]
        service.repo_entite.obtenir_magasins.return_value = entites_mock

        # Mock des ventes par entité
        service.repo_vente.obtenir_ca_par_entite.return_value = [
            (1, Decimal("1000.00"), 10),
            (2, Decimal("1500.00"), 15)
        ]

        # Mock des stocks critiques
        service.repo_stock.compter_ruptures_par_entite.return_value = [(1, 2), (2, 1)]
        service.repo_stock.compter_surstock_par_entite.return_value = [(1, 0), (2, 3)]

        indicateurs = service.obtenir_indicateurs_performance()

        assert len(indicateurs) == 2
        assert indicateurs[0]['entite_id'] == 1
        assert indicateurs[0]['chiffre_affaires'] == Decimal("1000.00")
        assert indicateurs[0]['nombre_ventes'] == 10
        assert indicateurs[1]['entite_id'] == 2
        assert indicateurs[1]['chiffre_affaires'] == Decimal("1500.00")

    def test_detecter_alertes_critiques(self):
        """Test de détection des alertes critiques"""
        session_mock = Mock()
        service = ServiceTableauBord(session_mock)
        service.repo_stock = Mock()

        # Mock des produits en rupture critique
        ruptures_mock = [
            Mock(produit_nom="Produit A", entite_nom="Magasin 1", quantite=0),
            Mock(produit_nom="Produit B", entite_nom="Magasin 2", quantite=1)
        ]
        service.repo_stock.obtenir_ruptures_critiques.return_value = ruptures_mock

        alertes = service.detecter_alertes_critiques()

        assert len(alertes) == 2
        assert "Produit A" in alertes[0]['message']
        assert "Produit B" in alertes[1]['message']
        service.repo_stock.obtenir_ruptures_critiques.assert_called_once()
