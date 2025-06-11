from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from .models import (
    ProduitModel, CategorieModel, VenteModel, LigneVenteModel, CaisseModel,
    EntiteModel, StockEntiteModel, DemandeApprovisionnementModel, 
    TransfertStockModel, RapportModel, TypeEntiteEnum, StatutDemandeEnum
)
from ..domain.entities import (
    Produit, Categorie, Vente, LigneVente, Caisse, Entite, StockEntite,
    DemandeApprovisionnement, TransfertStock, Rapport, TypeEntite, StatutDemande
)


class RepositoryProduit:
    def __init__(self, session: Session):
        self.session = session

    def obtenir_par_id(self, produit_id: int) -> Optional[Produit]:
        model = self.session.query(ProduitModel).filter(
            ProduitModel.id == produit_id).first()
        return self._model_to_entity(model) if model else None

    def rechercher(self, critere: str, valeur: str) -> List[Produit]:
        query = self.session.query(ProduitModel)

        if critere == "nom":
            query = query.filter(ProduitModel.nom.ilike(f"%{valeur}%"))
        elif critere == "id":
            query = query.filter(ProduitModel.id == int(valeur))
        elif critere == "categorie":
            query = query.join(CategorieModel).filter(
                CategorieModel.nom.ilike(f"%{valeur}%"))

        models = query.all()
        return [self._model_to_entity(model) for model in models]

    def mettre_a_jour_stock(self, produit_id: int, nouvelle_quantite: int):
        """Mettre à jour le stock global (pour compatibilité)"""
        self.session.query(ProduitModel).filter(
            ProduitModel.id == produit_id).update(
            {"stock": nouvelle_quantite}
        )

    def lister_tous(self) -> List[Produit]:
        """Lister tous les produits"""
        models = self.session.query(ProduitModel).all()
        return [self._model_to_entity(model) for model in models]

    def creer(self, donnees: Dict[str, Any]) -> Produit:
        """Créer un nouveau produit"""
        produit_model = ProduitModel(
            nom=donnees['nom'],
            prix=donnees['prix'],
            stock=donnees['stock'],
            id_categorie=donnees['id_categorie'],
            seuil_alerte=donnees.get('seuil_alerte', 5),
            description=donnees.get('description')
        )
        self.session.add(produit_model)
        self.session.flush()
        return self._model_to_entity(produit_model)

    def mettre_a_jour(self, produit_id: int, donnees: Dict[str, Any]) -> Optional[Produit]:
        """Mettre à jour un produit existant"""
        produit_model = self.session.query(ProduitModel).filter(
            ProduitModel.id == produit_id).first()
        
        if not produit_model:
            return None
        
        for key, value in donnees.items():
            if hasattr(produit_model, key):
                setattr(produit_model, key, value)
        
        self.session.flush()
        return self._model_to_entity(produit_model)

    def supprimer(self, produit_id: int) -> bool:
        """Supprimer un produit"""
        result = self.session.query(ProduitModel).filter(
            ProduitModel.id == produit_id).delete()
        return result > 0

    def _model_to_entity(self, model: ProduitModel) -> Produit:
        categorie = None
        if model.categorie:
            categorie = Categorie(
                id=model.categorie.id,
                nom=model.categorie.nom,
                description=model.categorie.description
            )

        return Produit(
            id=model.id,
            nom=model.nom,
            prix=model.prix,
            stock=model.stock,
            id_categorie=model.id_categorie,
            seuil_alerte=model.seuil_alerte,
            description=model.description,
            categorie=categorie
        )


class RepositoryEntite:
    def __init__(self, session: Session):
        self.session = session

    def obtenir_par_id(self, entite_id: int) -> Optional[Entite]:
        model = self.session.query(EntiteModel).filter(
            EntiteModel.id == entite_id).first()
        return self._model_to_entity(model) if model else None

    def lister_par_type(self, type_entite: TypeEntite) -> List[Entite]:
        models = self.session.query(EntiteModel).filter(
            EntiteModel.type_entite == TypeEntiteEnum(type_entite.value)).all()
        return [self._model_to_entity(model) for model in models]

    def obtenir_centre_logistique(self) -> Optional[Entite]:
        model = self.session.query(EntiteModel).filter(
            EntiteModel.type_entite == TypeEntiteEnum.CENTRE_LOGISTIQUE).first()
        return self._model_to_entity(model) if model else None

    def obtenir_maison_mere(self) -> Optional[Entite]:
        model = self.session.query(EntiteModel).filter(
            EntiteModel.type_entite == TypeEntiteEnum.MAISON_MERE).first()
        return self._model_to_entity(model) if model else None

    def lister_toutes(self) -> List[Entite]:
        models = self.session.query(EntiteModel).all()
        return [self._model_to_entity(model) for model in models]

    def _model_to_entity(self, model: EntiteModel) -> Entite:
        return Entite(
            id=model.id,
            nom=model.nom,
            type_entite=TypeEntite(model.type_entite.value),
            adresse=model.adresse,
            statut=model.statut
        )


class RepositoryStockEntite:
    def __init__(self, session: Session):
        self.session = session

    def obtenir_par_produit_et_entite(self, id_produit: int, id_entite: int) -> Optional[StockEntite]:
        model = self.session.query(StockEntiteModel).filter(
            and_(StockEntiteModel.id_produit == id_produit,
                 StockEntiteModel.id_entite == id_entite)).first()
        return self._model_to_entity(model) if model else None

    def lister_par_entite(self, id_entite: int) -> List[StockEntite]:
        models = self.session.query(StockEntiteModel).filter(
            StockEntiteModel.id_entite == id_entite).all()
        return [self._model_to_entity(model) for model in models]

    def lister_en_rupture(self, id_entite: int) -> List[StockEntite]:
        models = self.session.query(StockEntiteModel).filter(
            and_(StockEntiteModel.id_entite == id_entite,
                 StockEntiteModel.quantite <= StockEntiteModel.seuil_alerte)).all()
        return [self._model_to_entity(model) for model in models]

    def lister_en_surstock(self, id_entite: int, seuil_surstock: int = 100) -> List[StockEntite]:
        models = self.session.query(StockEntiteModel).filter(
            and_(StockEntiteModel.id_entite == id_entite,
                 StockEntiteModel.quantite > seuil_surstock)).all()
        return [self._model_to_entity(model) for model in models]

    def lister_tous(self) -> List[StockEntite]:
        models = self.session.query(StockEntiteModel).all()
        return [self._model_to_entity(model) for model in models]

    def obtenir_ruptures_critiques(self) -> List[StockEntite]:
        """Obtenir tous les stocks en rupture critique (quantité <= seuil d'alerte)"""
        models = self.session.query(StockEntiteModel).filter(
            StockEntiteModel.quantite <= StockEntiteModel.seuil_alerte
        ).all()
        return [self._model_to_entity(model) for model in models]

    def mettre_a_jour_quantite(self, stock_id: int, nouvelle_quantite: int):
        self.session.query(StockEntiteModel).filter(
            StockEntiteModel.id == stock_id).update(
            {"quantite": nouvelle_quantite}
        )

    def creer_stock_entite(self, id_produit: int, id_entite: int, quantite: int, seuil_alerte: int = 5):
        stock_model = StockEntiteModel(
            id_produit=id_produit,
            id_entite=id_entite,
            quantite=quantite,
            seuil_alerte=seuil_alerte
        )
        self.session.add(stock_model)
        self.session.flush()
        return self._model_to_entity(stock_model)

    def _model_to_entity(self, model: StockEntiteModel) -> StockEntite:
        produit = None
        if model.produit:
            produit = Produit(
                id=model.produit.id,
                nom=model.produit.nom,
                prix=model.produit.prix,
                stock=model.produit.stock,
                id_categorie=model.produit.id_categorie,
                seuil_alerte=model.produit.seuil_alerte
            )

        entite = None
        if model.entite:
            entite = Entite(
                id=model.entite.id,
                nom=model.entite.nom,
                type_entite=TypeEntite(model.entite.type_entite.value),
                adresse=model.entite.adresse,
                statut=model.entite.statut
            )

        return StockEntite(
            id=model.id,
            id_produit=model.id_produit,
            id_entite=model.id_entite,
            quantite=model.quantite,
            seuil_alerte=model.seuil_alerte,
            produit=produit,
            entite=entite
        )


class RepositoryVente:
    def __init__(self, session: Session):
        self.session = session

    def sauvegarder(self, vente: Vente) -> Vente:
        vente_model = VenteModel(
            horodatage=vente.horodatage,
            id_caisse=vente.id_caisse,
            id_caissier=vente.id_caissier,
            id_entite=vente.id_entite,
            statut=vente.statut
        )

        self.session.add(vente_model)
        self.session.flush()

        for ligne in vente.lignes:
            ligne_model = LigneVenteModel(
                id_vente=vente_model.id,
                id_produit=ligne.produit.id,
                qte=ligne.qte
            )
            self.session.add(ligne_model)

        vente.id = vente_model.id
        return vente

    def obtenir_par_id(self, vente_id: int) -> Optional[Vente]:
        model = self.session.query(VenteModel).filter(
            VenteModel.id == vente_id).first()
        return self._model_to_entity(model) if model else None

    def marquer_comme_retournee(self, vente_id: int):
        self.session.query(VenteModel).filter(
            VenteModel.id == vente_id).update({"statut": "RETOURNEE"})

    def obtenir_ventes_par_entite(self, date_debut: datetime, date_fin: datetime) -> Dict[int, List[Vente]]:
        """Obtenir les ventes groupées par entité pour une période"""
        models = self.session.query(VenteModel).filter(
            and_(VenteModel.horodatage >= date_debut,
                 VenteModel.horodatage <= date_fin,
                 VenteModel.statut == "COMPLETEE")).all()
        
        ventes_par_entite = {}
        for model in models:
            vente = self._model_to_entity(model)
            if vente.id_entite not in ventes_par_entite:
                ventes_par_entite[vente.id_entite] = []
            ventes_par_entite[vente.id_entite].append(vente)
        
        return ventes_par_entite

    def calculer_ca_entite(self, id_entite: int, date_debut: datetime, date_fin: datetime) -> Decimal:
        """Calculer le chiffre d'affaires d'une entité pour une période"""
        result = self.session.query(
            func.sum(ProduitModel.prix * LigneVenteModel.qte)
        ).join(LigneVenteModel).join(VenteModel).filter(
            and_(VenteModel.id_entite == id_entite,
                 VenteModel.horodatage >= date_debut,
                 VenteModel.horodatage <= date_fin,
                 VenteModel.statut == "COMPLETEE")
        ).scalar()
        
        return result or Decimal('0')

    def compter_ventes_entite(self, id_entite: int, date_debut: datetime, date_fin: datetime) -> int:
        """Compter le nombre de ventes d'une entité pour une période"""
        return self.session.query(VenteModel).filter(
            and_(VenteModel.id_entite == id_entite,
                 VenteModel.horodatage >= date_debut,
                 VenteModel.horodatage <= date_fin,
                 VenteModel.statut == "COMPLETEE")
        ).count()

    def _model_to_entity(self, model: VenteModel) -> Vente:
        lignes = []
        for ligne_model in model.lignes:
            produit = Produit(
                id=ligne_model.produit.id,
                nom=ligne_model.produit.nom,
                prix=ligne_model.produit.prix,
                stock=ligne_model.produit.stock,
                id_categorie=ligne_model.produit.id_categorie,
                seuil_alerte=ligne_model.produit.seuil_alerte
            )
            ligne = LigneVente(produit=produit, qte=ligne_model.qte)
            lignes.append(ligne)

        return Vente(
            id=model.id,
            horodatage=model.horodatage,
            id_caisse=model.id_caisse,
            id_caissier=model.id_caissier,
            id_entite=model.id_entite,
            statut=model.statut,
            lignes=lignes
        )


class RepositoryDemandeApprovisionnement:
    def __init__(self, session: Session):
        self.session = session

    def sauvegarder(self, demande: DemandeApprovisionnement) -> DemandeApprovisionnement:
        demande_model = DemandeApprovisionnementModel(
            id_entite_demandeur=demande.id_entite_demandeur,
            id_entite_fournisseur=demande.id_entite_fournisseur,
            id_produit=demande.id_produit,
            quantite_demandee=demande.quantite_demandee,
            quantite_approuvee=demande.quantite_approuvee,
            statut=StatutDemandeEnum(demande.statut.value),
            date_demande=demande.date_demande,
            date_traitement=demande.date_traitement,
            commentaire=demande.commentaire
        )

        self.session.add(demande_model)
        self.session.flush()
        demande.id = demande_model.id
        return demande

    def obtenir_par_id(self, demande_id: int) -> Optional[DemandeApprovisionnement]:
        model = self.session.query(DemandeApprovisionnementModel).filter(
            DemandeApprovisionnementModel.id == demande_id).first()
        return self._model_to_entity(model) if model else None

    def lister_par_fournisseur_et_statut(self, id_fournisseur: int, 
                                         statut: StatutDemande) -> List[DemandeApprovisionnement]:
        models = self.session.query(DemandeApprovisionnementModel).filter(
            and_(DemandeApprovisionnementModel.id_entite_fournisseur == id_fournisseur,
                 DemandeApprovisionnementModel.statut == StatutDemandeEnum(statut.value))).all()
        return [self._model_to_entity(model) for model in models]

    def mettre_a_jour_statut(self, demande_id: int, nouveau_statut: StatutDemande,
                             quantite_approuvee: int = None, commentaire: str = None):
        update_data = {"statut": StatutDemandeEnum(nouveau_statut.value)}
        if quantite_approuvee is not None:
            update_data["quantite_approuvee"] = quantite_approuvee
        if commentaire is not None:
            update_data["commentaire"] = commentaire
        if nouveau_statut != StatutDemande.EN_ATTENTE:
            update_data["date_traitement"] = datetime.now()

        self.session.query(DemandeApprovisionnementModel).filter(
            DemandeApprovisionnementModel.id == demande_id).update(update_data)

    def _model_to_entity(self, model: DemandeApprovisionnementModel) -> DemandeApprovisionnement:
        return DemandeApprovisionnement(
            id=model.id,
            id_entite_demandeur=model.id_entite_demandeur,
            id_entite_fournisseur=model.id_entite_fournisseur,
            id_produit=model.id_produit,
            quantite_demandee=model.quantite_demandee,
            quantite_approuvee=model.quantite_approuvee,
            statut=StatutDemande(model.statut.value),
            date_demande=model.date_demande,
            date_traitement=model.date_traitement,
            commentaire=model.commentaire
        )


class RepositoryTransfertStock:
    def __init__(self, session: Session):
        self.session = session

    def sauvegarder(self, transfert: TransfertStock) -> TransfertStock:
        transfert_model = TransfertStockModel(
            id_entite_source=transfert.id_entite_source,
            id_entite_destination=transfert.id_entite_destination,
            id_produit=transfert.id_produit,
            quantite=transfert.quantite,
            date_transfert=transfert.date_transfert,
            id_demande_approvisionnement=transfert.id_demande_approvisionnement
        )

        self.session.add(transfert_model)
        self.session.flush()
        transfert.id = transfert_model.id
        return transfert

    def lister_par_entite(self, id_entite: int) -> List[TransfertStock]:
        models = self.session.query(TransfertStockModel).filter(
            or_(TransfertStockModel.id_entite_source == id_entite,
                TransfertStockModel.id_entite_destination == id_entite)).all()
        return [self._model_to_entity(model) for model in models]

    def _model_to_entity(self, model: TransfertStockModel) -> TransfertStock:
        return TransfertStock(
            id=model.id,
            id_entite_source=model.id_entite_source,
            id_entite_destination=model.id_entite_destination,
            id_produit=model.id_produit,
            quantite=model.quantite,
            date_transfert=model.date_transfert,
            id_demande_approvisionnement=model.id_demande_approvisionnement
        )


class RepositoryRapport:
    def __init__(self, session: Session):
        self.session = session

    def sauvegarder(self, rapport: Rapport) -> Rapport:
        rapport_model = RapportModel(
            titre=rapport.titre,
            type_rapport=rapport.type_rapport,
            date_generation=rapport.date_generation,
            date_debut=rapport.date_debut,
            date_fin=rapport.date_fin,
            contenu_json=rapport.contenu_json,
            genere_par=rapport.genere_par
        )

        self.session.add(rapport_model)
        self.session.flush()
        rapport.id = rapport_model.id
        return rapport

    def lister_par_type(self, type_rapport: str) -> List[Rapport]:
        models = self.session.query(RapportModel).filter(
            RapportModel.type_rapport == type_rapport).order_by(
            RapportModel.date_generation.desc()).all()
        return [self._model_to_entity(model) for model in models]

    def obtenir_par_id(self, rapport_id: int) -> Optional[Rapport]:
        model = self.session.query(RapportModel).filter(
            RapportModel.id == rapport_id).first()
        return self._model_to_entity(model) if model else None

    def lister_tous(self) -> List[Rapport]:
        models = self.session.query(RapportModel).order_by(RapportModel.date_generation.desc()).all()
        return [self._model_to_entity(model) for model in models]

    def supprimer(self, rapport_id: int) -> bool:
        result = self.session.query(RapportModel).filter(
            RapportModel.id == rapport_id).delete()
        return result > 0

    def _model_to_entity(self, model: RapportModel) -> Rapport:
        return Rapport(
            id=model.id,
            titre=model.titre,
            type_rapport=model.type_rapport,
            date_generation=model.date_generation,
            date_debut=model.date_debut,
            date_fin=model.date_fin,
            contenu_json=model.contenu_json,
            genere_par=model.genere_par
        )


class RepositoryCaisse:
    def __init__(self, session: Session):
        self.session = session

    def obtenir_par_id(self, caisse_id: int) -> Optional[Caisse]:
        model = self.session.query(CaisseModel).filter(
            CaisseModel.id == caisse_id).first()
        return self._model_to_entity(model) if model else None

    def lister_actives(self) -> List[Caisse]:
        models = self.session.query(CaisseModel).filter(
            CaisseModel.statut == "ACTIVE").all()
        return [self._model_to_entity(model) for model in models]

    def lister_par_entite(self, id_entite: int) -> List[Caisse]:
        models = self.session.query(CaisseModel).filter(
            and_(CaisseModel.id_entite == id_entite,
                 CaisseModel.statut == "ACTIVE")).all()
        return [self._model_to_entity(model) for model in models]

    def _model_to_entity(self, model: CaisseModel) -> Caisse:
        return Caisse(
            id=model.id,
            nom=model.nom,
            statut=model.statut,
            id_entite=model.id_entite
        )
