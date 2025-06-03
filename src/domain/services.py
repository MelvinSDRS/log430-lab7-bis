from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .entities import Produit, Vente, LigneVente
from ..persistence.repositories import (RepositoryProduit, RepositoryVente)


class ServiceTransaction:
    def __init__(self, session: Session):
        self.session = session
        self.transaction_active = False

    def commencer(self):
        """Commencer une transaction"""
        if not self.session.in_transaction() and not self.transaction_active:
            self.session.begin()
            self.transaction_active = True
        elif not self.transaction_active:
            self.transaction_active = True

    def valider(self):
        """Valider une transaction"""
        if self.transaction_active:
            self.session.commit()
            self.transaction_active = False

    def annuler(self):
        """Annuler une transaction"""
        if self.transaction_active:
            self.session.rollback()
            self.transaction_active = False


class ServiceInventaire:
    def __init__(self, session: Session):
        self.session = session
        self.repo_produit = RepositoryProduit(session)

    def verifier_disponibilite(self, panier: List[LigneVente]) -> List[str]:
        """Vérifier la disponibilité des produits dans le panier"""
        produits_manquants = []

        for ligne in panier:
            produit = self.repo_produit.obtenir_par_id(ligne.produit.id)
            if not produit or produit.stock < ligne.qte:
                stock_actuel = produit.stock if produit else 0
                message = (f"{ligne.produit.nom} (stock: {stock_actuel}, "
                           f"demandé: {ligne.qte})")
                produits_manquants.append(message)

        return produits_manquants

    def reserver_stock(self, panier: List[LigneVente]):
        """Réserver le stock pour les produits du panier"""
        for ligne in panier:
            produit = self.repo_produit.obtenir_par_id(ligne.produit.id)
            if produit:
                nouvelle_quantite = produit.stock - ligne.qte
                self.repo_produit.mettre_a_jour_stock(
                    ligne.produit.id, nouvelle_quantite)

    def restituer_stock(self, panier: List[LigneVente]):
        """Restituer le stock pour les produits du panier (retours)"""
        for ligne in panier:
            produit = self.repo_produit.obtenir_par_id(ligne.produit.id)
            if produit:
                nouvelle_quantite = produit.stock + ligne.qte
                self.repo_produit.mettre_a_jour_stock(
                    ligne.produit.id, nouvelle_quantite)


class ServicePaiement:
    def __init__(self):
        pass

    def facturer(self, vente: Vente) -> bool:
        """Simuler le processus de paiement"""
        return True


class ServiceVente:
    def __init__(self, session: Session):
        self.session = session
        self.service_transaction = ServiceTransaction(session)
        self.service_inventaire = ServiceInventaire(session)
        self.service_paiement = ServicePaiement()
        self.repo_vente = RepositoryVente(session)

    def creer_vente(self, panier: List[LigneVente], id_caisse: int,
                    id_caissier: int) -> Optional[Vente]:
        """Créer une nouvelle vente avec gestion des transactions"""
        try:
            self.service_transaction.commencer()

            produits_manquants = self.service_inventaire.verifier_disponibilite(
                panier)
            if produits_manquants:
                self.service_transaction.annuler()
                raise ValueError(
                    f"Stock insuffisant pour: {', '.join(produits_manquants)}"
                )

            self.service_inventaire.reserver_stock(panier)

            vente = Vente(
                id=None,
                horodatage=datetime.now(),
                id_caisse=id_caisse,
                id_caissier=id_caissier,
                statut="COMPLETEE",
                lignes=panier
            )

            if not self.service_paiement.facturer(vente):
                self.service_transaction.annuler()
                raise ValueError("Erreur lors du paiement")

            vente = self.repo_vente.sauvegarder(vente)

            self.service_transaction.valider()
            return vente

        except Exception as e:
            self.service_transaction.annuler()
            raise e

    def retourner_vente(self, vente_id: int) -> bool:
        """Retourner une vente"""
        try:
            self.service_transaction.commencer()

            vente = self.repo_vente.obtenir_par_id(vente_id)
            if not vente:
                raise ValueError("Vente introuvable")

            if vente.statut == "RETOURNEE":
                raise ValueError("Vente déjà retournée")

            self.repo_vente.marquer_comme_retournee(vente_id)

            self.service_transaction.valider()
            return True

        except Exception as e:
            self.service_transaction.annuler()
            raise e


class ServiceProduit:
    def __init__(self, session: Session):
        self.session = session
        self.repo_produit = RepositoryProduit(session)

    def rechercher(self, critere: str, valeur: str) -> List[Produit]:
        """Rechercher des produits selon différents critères"""
        return self.repo_produit.rechercher(critere, valeur)
