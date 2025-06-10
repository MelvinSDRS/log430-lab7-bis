from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import logging

from .entities import (
    Produit, Vente, LigneVente, Entite, StockEntite, 
    DemandeApprovisionnement, TransfertStock, Rapport, 
    IndicateurPerformance, TypeEntite, StatutDemande
)
from ..persistence.repositories import (
    RepositoryProduit, RepositoryVente, RepositoryEntite,
    RepositoryStockEntite, RepositoryDemandeApprovisionnement,
    RepositoryTransfertStock, RepositoryRapport
)

logger = logging.getLogger(__name__)

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
        self.repo_stock_entite = RepositoryStockEntite(session)

    def verifier_disponibilite(self, panier: List[LigneVente], id_entite: int) -> List[str]:
        """Vérifier la disponibilité des produits dans le panier pour une entité"""
        produits_manquants = []

        for ligne in panier:
            stock_entite = self.repo_stock_entite.obtenir_par_produit_et_entite(
                ligne.produit.id, id_entite)
            
            if not stock_entite or stock_entite.quantite < ligne.qte:
                stock_actuel = stock_entite.quantite if stock_entite else 0
                message = (f"{ligne.produit.nom} (stock: {stock_actuel}, "
                           f"demandé: {ligne.qte})")
                produits_manquants.append(message)

        return produits_manquants

    def reserver_stock(self, panier: List[LigneVente], id_entite: int):
        """Réserver le stock pour les produits du panier dans une entité"""
        for ligne in panier:
            stock_entite = self.repo_stock_entite.obtenir_par_produit_et_entite(
                ligne.produit.id, id_entite)
            if stock_entite:
                nouvelle_quantite = stock_entite.quantite - ligne.qte
                self.repo_stock_entite.mettre_a_jour_quantite(
                    stock_entite.id, nouvelle_quantite)

    def restituer_stock(self, panier: List[LigneVente], id_entite: int):
        """Restituer le stock pour les produits du panier (retours)"""
        for ligne in panier:
            stock_entite = self.repo_stock_entite.obtenir_par_produit_et_entite(
                ligne.produit.id, id_entite)
            if stock_entite:
                nouvelle_quantite = stock_entite.quantite + ligne.qte
                self.repo_stock_entite.mettre_a_jour_quantite(
                    stock_entite.id, nouvelle_quantite)

    def obtenir_stocks_par_entite(self, id_entite: int) -> List[StockEntite]:
        """Obtenir tous les stocks d'une entité"""
        return self.repo_stock_entite.lister_par_entite(id_entite)

    def obtenir_produits_en_rupture(self, id_entite: int) -> List[StockEntite]:
        """Obtenir les produits en rupture de stock pour une entité"""
        return self.repo_stock_entite.lister_en_rupture(id_entite)


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
                    id_caissier: int, id_entite: int) -> Optional[Vente]:
        """Créer une nouvelle vente avec gestion des transactions"""
        logger.info(f"Début création vente - Caisse: {id_caisse}, Caissier: {id_caissier}, Entité: {id_entite}")
        
        try:
            self.service_transaction.commencer()

            produits_manquants = self.service_inventaire.verifier_disponibilite(
                panier, id_entite)
            if produits_manquants:
                logger.warning(f"Stock insuffisant pour vente - Produits manquants: {len(produits_manquants)}")
                self.service_transaction.annuler()
                raise ValueError(
                    f"Stock insuffisant pour: {', '.join(produits_manquants)}"
                )

            self.service_inventaire.reserver_stock(panier, id_entite)

            vente = Vente(
                id=None,
                horodatage=datetime.now(),
                id_caisse=id_caisse,
                id_caissier=id_caissier,
                id_entite=id_entite,
                statut="COMPLETEE",
                lignes=panier
            )

            if not self.service_paiement.facturer(vente):
                self.service_transaction.annuler()
                raise ValueError("Erreur lors du paiement")

            vente = self.repo_vente.sauvegarder(vente)

            self.service_transaction.valider()
            logger.info(f"Vente créée avec succès - ID: {vente.id}, Total: {sum(ligne.produit.prix * ligne.qte for ligne in panier)}$")
            return vente

        except Exception as e:
            logger.error(f"Erreur lors de la création de vente: {str(e)}")
            self.service_transaction.annuler()
            raise

    def retourner_vente(self, vente_id: int) -> bool:
        """Retourner une vente"""
        try:
            self.service_transaction.commencer()

            vente = self.repo_vente.obtenir_par_id(vente_id)
            if not vente:
                raise ValueError("Vente introuvable")

            if vente.statut == "RETOURNEE":
                raise ValueError("Vente déjà retournée")

            self.service_inventaire.restituer_stock(vente.lignes, vente.id_entite)

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


class ServiceApprovisionnement:
    """Service pour gérer les demandes d'approvisionnement et transferts"""
    
    def __init__(self, session: Session):
        self.session = session
        self.service_transaction = ServiceTransaction(session)
        self.repo_demande = RepositoryDemandeApprovisionnement(session)
        self.repo_transfert = RepositoryTransfertStock(session)
        self.repo_stock = RepositoryStockEntite(session)

    def creer_demande_approvisionnement(self, id_entite_demandeur: int,
                                        id_entite_fournisseur: int, id_produit: int,
                                        quantite: int) -> DemandeApprovisionnement:
        """Créer une demande d'approvisionnement"""
        logger.info(f"Création demande approvisionnement - Source: {id_entite_demandeur}, Dest: {id_entite_fournisseur}, Produit: {id_produit}, Qté: {quantite}")
        
        try:
            demande = DemandeApprovisionnement(
                id=None,
                id_entite_demandeur=id_entite_demandeur,
                id_entite_fournisseur=id_entite_fournisseur,
                id_produit=id_produit,
                quantite_demandee=quantite,
                quantite_approuvee=None,
                statut=StatutDemande.EN_ATTENTE,
                date_demande=datetime.now(),
                date_traitement=None,
                commentaire=None
            )
            demande_sauvee = self.repo_demande.sauvegarder(demande)
            logger.info(f"Demande d'approvisionnement créée - ID: {demande_sauvee.id}")
            return demande_sauvee
            
        except Exception as e:
            logger.error(f"Erreur création demande approvisionnement: {str(e)}")
            raise

    def approuver_demande(self, demande_id: int, quantite_approuvee: int,
                          commentaire: str = None) -> bool:
        """Approuver une demande d'approvisionnement"""
        try:
            self.service_transaction.commencer()

            demande = self.repo_demande.obtenir_par_id(demande_id)
            if not demande:
                raise ValueError("Demande introuvable")

            if demande.statut != StatutDemande.EN_ATTENTE:
                raise ValueError("Demande déjà traitée")

            stock_fournisseur = self.repo_stock.obtenir_par_produit_et_entite(
                demande.id_produit, demande.id_entite_fournisseur)
            
            if not stock_fournisseur or stock_fournisseur.quantite < quantite_approuvee:
                raise ValueError("Stock insuffisant chez le fournisseur")

            self.repo_demande.mettre_a_jour_statut(
                demande_id, StatutDemande.APPROUVEE, quantite_approuvee, commentaire)

            self.service_transaction.valider()
            return True

        except Exception as e:
            self.service_transaction.annuler()
            raise e

    def effectuer_transfert(self, demande_id: int) -> TransfertStock:
        """Effectuer le transfert de stock pour une demande approuvée"""
        try:
            self.service_transaction.commencer()

            demande = self.repo_demande.obtenir_par_id(demande_id)
            if not demande or demande.statut != StatutDemande.APPROUVEE:
                raise ValueError("Demande non approuvée")

            # Transférer le stock
            # Diminuer le stock du fournisseur
            stock_source = self.repo_stock.obtenir_par_produit_et_entite(
                demande.id_produit, demande.id_entite_fournisseur)
            nouvelle_qte_source = stock_source.quantite - demande.quantite_approuvee
            self.repo_stock.mettre_a_jour_quantite(stock_source.id, nouvelle_qte_source)

            # Augmenter le stock du demandeur
            stock_dest = self.repo_stock.obtenir_par_produit_et_entite(
                demande.id_produit, demande.id_entite_demandeur)
            if stock_dest:
                nouvelle_qte_dest = stock_dest.quantite + demande.quantite_approuvee
                self.repo_stock.mettre_a_jour_quantite(stock_dest.id, nouvelle_qte_dest)
            else:
                self.repo_stock.creer_stock_entite(
                    demande.id_produit, demande.id_entite_demandeur, 
                    demande.quantite_approuvee)

            # Créer l'enregistrement de transfert
            transfert = TransfertStock(
                id=None,
                id_entite_source=demande.id_entite_fournisseur,
                id_entite_destination=demande.id_entite_demandeur,
                id_produit=demande.id_produit,
                quantite=demande.quantite_approuvee,
                date_transfert=datetime.now(),
                id_demande_approvisionnement=demande_id
            )
            transfert = self.repo_transfert.sauvegarder(transfert)

            # Marquer la demande comme livrée
            self.repo_demande.mettre_a_jour_statut(demande_id, StatutDemande.LIVREE)

            self.service_transaction.valider()
            return transfert

        except Exception as e:
            self.service_transaction.annuler()
            raise e

    def lister_demandes_en_attente(self, id_entite_fournisseur: int) -> List[DemandeApprovisionnement]:
        """Lister les demandes en attente pour un fournisseur"""
        return self.repo_demande.lister_par_fournisseur_et_statut(
            id_entite_fournisseur, StatutDemande.EN_ATTENTE)


class ServiceRapport:
    """Service pour générer des rapports consolidés"""
    
    def __init__(self, session: Session):
        self.session = session
        self.repo_rapport = RepositoryRapport(session)
        self.repo_vente = RepositoryVente(session)
        self.repo_stock = RepositoryStockEntite(session)
        self.repo_entite = RepositoryEntite(session)

    def generer_rapport_ventes_consolide(self, date_debut: datetime, 
                                         date_fin: datetime, genere_par: int) -> Rapport:
        """Générer un rapport consolidé des ventes"""
        logger.info(f"Génération rapport ventes consolidées - Période: {date_debut} à {date_fin}")
        
        try:
            ventes_par_entite = self.repo_vente.obtenir_ventes_par_entite(date_debut, date_fin)
            
            donnees_rapport = {
                "periode": {
                    "debut": date_debut.isoformat(),
                    "fin": date_fin.isoformat()
                },
                "ventes_par_magasin": [],
                "produits_plus_vendus": [],
                "chiffre_affaires_total": 0
            }

            ca_total = Decimal('0')
            for entite_id, ventes in ventes_par_entite.items():
                entite = self.repo_entite.obtenir_par_id(entite_id)
                ca_entite = sum(vente.total for vente in ventes)
                ca_total += ca_entite
                
                donnees_rapport["ventes_par_magasin"].append({
                    "entite_id": entite_id,
                    "nom": entite.nom,
                    "nombre_ventes": len(ventes),
                    "chiffre_affaires": float(ca_entite)
                })

            donnees_rapport["chiffre_affaires_total"] = float(ca_total)

            rapport = Rapport(
                id=None,
                titre=f"Rapport consolidé des ventes ({date_debut.strftime('%Y-%m-%d')} - {date_fin.strftime('%Y-%m-%d')})",
                type_rapport="VENTES",
                date_generation=datetime.now(),
                date_debut=date_debut,
                date_fin=date_fin,
                contenu_json=json.dumps(donnees_rapport),
                genere_par=genere_par
            )

            rapport_sauve = self.repo_rapport.sauvegarder(rapport)
            logger.info(f"Rapport ventes consolidées généré - ID: {rapport_sauve.id}")
            return rapport_sauve
            
        except Exception as e:
            logger.error(f"Erreur génération rapport ventes: {str(e)}")
            raise

    def generer_rapport_stocks(self, genere_par: int) -> Rapport:
        """Générer un rapport des stocks par entité"""
        logger.info("Génération rapport stocks par entité")
        
        try:
            entites = self.repo_entite.lister_par_type(TypeEntite.MAGASIN)
            centre_logistique = self.repo_entite.obtenir_centre_logistique()
            
            donnees_rapport = {
                "date_generation": datetime.now().isoformat(),
                "stocks_par_entite": [],
                "alertes_rupture": []
            }

            if centre_logistique:
                entites.append(centre_logistique)

            for entite in entites:
                stocks = self.repo_stock.lister_par_entite(entite.id)
                stocks_en_rupture = self.repo_stock.lister_en_rupture(entite.id)
                
                donnees_rapport["stocks_par_entite"].append({
                    "entite_id": entite.id,
                    "nom": entite.nom,
                    "type": entite.type_entite.value,
                    "nombre_produits": len(stocks),
                    "produits_en_rupture": len(stocks_en_rupture)
                })

                for stock in stocks_en_rupture:
                    donnees_rapport["alertes_rupture"].append({
                        "entite": entite.nom,
                        "produit": stock.produit.nom,
                        "stock_actuel": stock.quantite,
                        "seuil_alerte": stock.seuil_alerte
                    })

            rapport = Rapport(
                id=None,
                titre=f"Rapport des stocks ({datetime.now().strftime('%Y-%m-%d')})",
                type_rapport="STOCKS",
                date_generation=datetime.now(),
                date_debut=datetime.now().replace(hour=0, minute=0, second=0),
                date_fin=datetime.now(),
                contenu_json=json.dumps(donnees_rapport),
                genere_par=genere_par
            )

            rapport_sauve = self.repo_rapport.sauvegarder(rapport)
            logger.info(f"Rapport stocks généré - ID: {rapport_sauve.id}, Alertes rupture: {len(donnees_rapport['alertes_rupture'])}")
            return rapport_sauve
            
        except Exception as e:
            logger.error(f"Erreur génération rapport stocks: {str(e)}")
            raise


class ServiceTableauBord:
    """Service pour générer les données du tableau de bord"""
    
    def __init__(self, session: Session):
        self.session = session
        self.repo_vente = RepositoryVente(session)
        self.repo_stock = RepositoryStockEntite(session)
        self.repo_entite = RepositoryEntite(session)

    def obtenir_indicateurs_performance(self) -> List[IndicateurPerformance]:
        """Obtenir les indicateurs de performance pour tous les magasins"""
        logger.info("Calcul des indicateurs de performance")
        
        try:
            magasins = self.repo_entite.lister_par_type(TypeEntite.MAGASIN)
            indicateurs = []

            for magasin in magasins:
                # Calculer les métriques
                ca_actuel = self.repo_vente.calculer_ca_entite(
                    magasin.id, datetime.now() - timedelta(days=7), datetime.now())
                ca_precedent = self.repo_vente.calculer_ca_entite(
                    magasin.id, datetime.now() - timedelta(days=14), 
                    datetime.now() - timedelta(days=7))
                
                nb_ventes = self.repo_vente.compter_ventes_entite(
                    magasin.id, datetime.now() - timedelta(days=7), datetime.now())
                
                stocks_rupture = len(self.repo_stock.lister_en_rupture(magasin.id))
                stocks_surstock = len(self.repo_stock.lister_en_surstock(magasin.id))
                
                # Calculer la tendance
                tendance = Decimal('0')
                if ca_precedent > 0:
                    tendance = ((ca_actuel - ca_precedent) / ca_precedent) * 100

                indicateur = IndicateurPerformance(
                    entite_id=magasin.id,
                    entite_nom=magasin.nom,
                    chiffre_affaires=ca_actuel,
                    nombre_ventes=nb_ventes,
                    produits_en_rupture=stocks_rupture,
                    produits_en_surstock=stocks_surstock,
                    tendance_hebdomadaire=tendance
                )
                indicateurs.append(indicateur)

            logger.info(f"Indicateurs calculés pour {len(indicateurs)} magasins")
            return indicateurs
            
        except Exception as e:
            logger.error(f"Erreur calcul indicateurs: {str(e)}")
            raise

    def detecter_alertes_critiques(self):
        """Détecter les alertes critiques nécessitant une attention immédiate"""
        logger.info("Détection des alertes critiques")
        
        try:
            alertes = []
            
            ruptures_critiques = self.repo_stock.obtenir_ruptures_critiques()
            
            for rupture in ruptures_critiques:
                alerte = {
                    "type": "RUPTURE_CRITIQUE",
                    "niveau": "URGENT",
                    "message": f"Rupture critique: {rupture.produit_nom} dans {rupture.entite_nom}",
                    "entite_id": rupture.entite_id,
                    "produit_id": rupture.produit_id,
                    "date_detection": datetime.now()
                }
                alertes.append(alerte)
            
            logger.info(f"Détectées {len(alertes)} alertes critiques")
            return alertes
            
        except Exception as e:
            logger.error(f"Erreur détection alertes: {str(e)}")
            raise

    def _calculer_tendance(self, entite_id):
        """Calculer la tendance hebdomadaire des ventes"""
        try:
            # Comparer cette semaine vs semaine précédente
            fin_semaine_actuelle = datetime.now().date()
            debut_semaine_actuelle = fin_semaine_actuelle - timedelta(days=7)
            debut_semaine_precedente = debut_semaine_actuelle - timedelta(days=7)
            
            ca_actuel = self.repo_vente.obtenir_ca_periode(entite_id, debut_semaine_actuelle, fin_semaine_actuelle)
            ca_precedent = self.repo_vente.obtenir_ca_periode(entite_id, debut_semaine_precedente, debut_semaine_actuelle)
            
            if ca_precedent and ca_precedent > 0:
                tendance = ((ca_actuel - ca_precedent) / ca_precedent) * 100
                return round(tendance, 1)
            
            return 0.0
            
        except Exception as e:
            logger.warning(f"Erreur calcul tendance pour entité {entite_id}: {str(e)}")
            return 0.0
