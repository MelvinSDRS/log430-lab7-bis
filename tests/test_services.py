import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import Mock

from src.domain.entities import Produit, LigneVente, Vente, StatutDemande
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
        service.repo_stock_entite = Mock()
        
        mock_stock_entite = Mock()
        mock_stock_entite.quantite = 10
        service.repo_stock_entite.obtenir_par_produit_et_entite.return_value = mock_stock_entite

        produits_manquants = service.verifier_disponibilite(panier, 1)

        assert len(produits_manquants) == 0
        service.repo_stock_entite.obtenir_par_produit_et_entite.assert_called_once_with(1, 1)

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
        service.repo_stock_entite = Mock()
        
        mock_stock_entite = Mock()
        mock_stock_entite.quantite = 2
        service.repo_stock_entite.obtenir_par_produit_et_entite.return_value = mock_stock_entite

        produits_manquants = service.verifier_disponibilite(panier, 1)

        assert len(produits_manquants) == 1
        assert "Test (stock: 2, demandé: 5)" in produits_manquants[0]


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
            panier, 1)

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
        service.service_transaction = Mock()

        # Mock de la demande
        demande_mock = Mock()
        demande_mock.id = 1
        demande_mock.statut = StatutDemande.EN_ATTENTE
        demande_mock.quantite_demandee = 10
        demande_mock.id_produit = 1
        demande_mock.id_entite_demandeur = 1
        demande_mock.id_entite_fournisseur = 2
        
        service.repo_demande.obtenir_par_id.return_value = demande_mock

        # Mock du stock suffisant
        service.repo_stock.obtenir_par_produit_et_entite.return_value = Mock(quantite=15)

        resultat = service.approuver_demande(demande_mock.id, 10)

        assert resultat is True
        service.repo_demande.mettre_a_jour_statut.assert_called_once()

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
        service.repo_entite = Mock()

        # Mock des données de ventes par entité
        ventes_par_entite = {
            1: [Mock(total=Decimal("100.00"), horodatage=datetime.now())],
            2: [Mock(total=Decimal("150.00"), horodatage=datetime.now())]
        }
        service.repo_vente.obtenir_ventes_par_entite.return_value = ventes_par_entite

        entite_mock_1 = Mock()
        entite_mock_1.nom = "Magasin 1"
        entite_mock_2 = Mock()
        entite_mock_2.nom = "Magasin 2"
        
        def mock_obtenir_par_id(entite_id):
            if entite_id == 1:
                return entite_mock_1
            elif entite_id == 2:
                return entite_mock_2
            return None
            
        service.repo_entite.obtenir_par_id.side_effect = mock_obtenir_par_id

        rapport_mock = Mock()
        rapport_mock.id = 1
        service.repo_rapport.sauvegarder.return_value = rapport_mock

        date_debut = datetime.now().date()
        date_fin = datetime.now().date()

        rapport = service.generer_rapport_ventes_consolide(date_debut, date_fin, 1)

        assert rapport is not None
        service.repo_vente.obtenir_ventes_par_entite.assert_called_once_with(date_debut, date_fin)
        service.repo_rapport.sauvegarder.assert_called_once()

    def test_generer_rapport_stocks_entites(self):
        """Test de génération d'un rapport de stocks par entité"""
        session_mock = Mock()
        service = ServiceRapport(session_mock)
        service.repo_stock = Mock()
        service.repo_rapport = Mock()
        service.repo_entite = Mock()

        # Mock des entités (liste itérable) avec attributs nécessaires
        entite_mock_1 = Mock()
        entite_mock_1.id = 1
        entite_mock_1.nom = "Magasin 1"
        entite_mock_1.type_entite.value = "MAGASIN"
        
        entite_mock_2 = Mock()
        entite_mock_2.id = 2
        entite_mock_2.nom = "Magasin 2"
        entite_mock_2.type_entite.value = "MAGASIN"
        
        entites_mock = [entite_mock_1, entite_mock_2]
        service.repo_entite.lister_par_type.return_value = entites_mock
        service.repo_entite.obtenir_centre_logistique.return_value = None

        service.repo_stock.lister_par_entite.return_value = []
        service.repo_stock.lister_en_rupture.return_value = []

        rapport_mock = Mock()
        rapport_mock.id = 1
        service.repo_rapport.sauvegarder.return_value = rapport_mock

        rapport = service.generer_rapport_stocks(1)

        assert rapport is not None
        service.repo_stock.lister_par_entite.assert_called()
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

        # Mock des entités (liste itérable)
        entite_mock_1 = Mock()
        entite_mock_1.id = 1
        entite_mock_1.nom = "Magasin 1"
        
        entite_mock_2 = Mock()
        entite_mock_2.id = 2
        entite_mock_2.nom = "Magasin 2"
        
        entites_mock = [entite_mock_1, entite_mock_2]
        service.repo_entite.lister_par_type.return_value = entites_mock

        # Mock des méthodes de vente 
        service.repo_vente.calculer_ca_entite.return_value = Decimal("1000.00")
        service.repo_vente.compter_ventes_entite.return_value = 10

        service.repo_stock.lister_en_rupture.return_value = []
        service.repo_stock.lister_en_surstock.return_value = []

        indicateurs = service.obtenir_indicateurs_performance()

        assert indicateurs is not None
        assert len(indicateurs) >= 0
        service.repo_entite.lister_par_type.assert_called_once()

    def test_detecter_alertes_critiques(self):
        """Test de détection des alertes critiques"""
        session_mock = Mock()
        service = ServiceTableauBord(session_mock)
        service.repo_stock = Mock()

        # Mock des produits en rupture critique avec des attributs appropriés
        rupture_mock_1 = Mock()
        rupture_mock_1.id_produit = 1
        rupture_mock_1.id_entite = 1
        rupture_mock_1.quantite = 0
        rupture_mock_1.produit = Mock()
        rupture_mock_1.produit.nom = "Produit A"
        rupture_mock_1.entite = Mock()
        rupture_mock_1.entite.nom = "Magasin 1"
        
        rupture_mock_2 = Mock()
        rupture_mock_2.id_produit = 2
        rupture_mock_2.id_entite = 2
        rupture_mock_2.quantite = 1
        rupture_mock_2.produit = Mock()
        rupture_mock_2.produit.nom = "Produit B"
        rupture_mock_2.entite = Mock()
        rupture_mock_2.entite.nom = "Magasin 2"
        
        ruptures_mock = [rupture_mock_1, rupture_mock_2]
        service.repo_stock.obtenir_ruptures_critiques.return_value = ruptures_mock

        alertes = service.detecter_alertes_critiques()

        assert len(alertes) == 2
        assert "Produit A" in alertes[0]['message']
        assert "Produit B" in alertes[1]['message']
        service.repo_stock.obtenir_ruptures_critiques.assert_called_once()
