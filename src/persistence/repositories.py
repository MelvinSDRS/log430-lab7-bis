from typing import List, Optional
from sqlalchemy.orm import Session
from .models import (ProduitModel, CategorieModel, VenteModel,
                     LigneVenteModel, CaisseModel)
from ..domain.entities import Produit, Categorie, Vente, Caisse


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
        self.session.query(ProduitModel).filter(
            ProduitModel.id == produit_id).update(
            {"stock": nouvelle_quantite}
        )

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
            categorie=categorie
        )


class RepositoryVente:
    def __init__(self, session: Session):
        self.session = session

    def sauvegarder(self, vente: Vente) -> Vente:
        vente_model = VenteModel(
            horodatage=vente.horodatage,
            id_caisse=vente.id_caisse,
            id_caissier=vente.id_caissier,
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

    def _model_to_entity(self, model: VenteModel) -> Vente:
        return Vente(
            id=model.id,
            horodatage=model.horodatage,
            id_caisse=model.id_caisse,
            id_caissier=model.id_caissier,
            statut=model.statut,
            lignes=[]
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

    def _model_to_entity(self, model: CaisseModel) -> Caisse:
        return Caisse(
            id=model.id,
            nom=model.nom,
            statut=model.statut
        )
