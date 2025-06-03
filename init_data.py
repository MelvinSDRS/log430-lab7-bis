#!/usr/bin/env python3
"""
Script d'initialisation des données de test
"""

from decimal import Decimal
from src.persistence.database import create_tables, get_db_session
from src.persistence.models import (
    CategorieModel, ProduitModel, CaisseModel, CaissierModel
)


def init_data():
    """Initialiser la base de données avec des données de test"""
    
    create_tables()
    
    session = get_db_session()
    
    try:
        # Vérifier si des données existent déjà
        if session.query(CategorieModel).first():
            print("Les données existent déjà.")
            return
        
        cat_alimentaire = CategorieModel(nom="Alimentaire", description="Produits alimentaires")
        cat_boissons = CategorieModel(nom="Boissons", description="Boissons diverses")
        cat_hygiene = CategorieModel(nom="Hygiène", description="Produits d'hygiène")
        
        session.add_all([cat_alimentaire, cat_boissons, cat_hygiene])
        session.flush()
        
        produits = [
            ProduitModel(nom="Pain", prix=Decimal("1.50"), stock=50, id_categorie=cat_alimentaire.id),
            ProduitModel(nom="Lait", prix=Decimal("1.20"), stock=30, id_categorie=cat_alimentaire.id),
            ProduitModel(nom="Pommes (kg)", prix=Decimal("2.80"), stock=25, id_categorie=cat_alimentaire.id),
            ProduitModel(nom="Eau (1.5L)", prix=Decimal("0.80"), stock=40, id_categorie=cat_boissons.id),
            ProduitModel(nom="Coca-Cola", prix=Decimal("1.90"), stock=35, id_categorie=cat_boissons.id),
            ProduitModel(nom="Jus d'orange", prix=Decimal("2.50"), stock=20, id_categorie=cat_boissons.id),
            ProduitModel(nom="Savon", prix=Decimal("3.20"), stock=15, id_categorie=cat_hygiene.id),
            ProduitModel(nom="Dentifrice", prix=Decimal("4.50"), stock=12, id_categorie=cat_hygiene.id),
        ]
        
        session.add_all(produits)
        
        caisses = [
            CaisseModel(nom="Caisse 1", statut="ACTIVE"),
            CaisseModel(nom="Caisse 2", statut="ACTIVE"),
            CaisseModel(nom="Caisse 3", statut="ACTIVE"),
        ]
        
        session.add_all(caisses)
        
        caissiers = [
            CaissierModel(nom="Melvin Siadous"),
            CaissierModel(nom="Steve Jobs"),
            CaissierModel(nom="Michael Jackson"),
        ]
        
        session.add_all(caissiers)
        session.commit()
        print("Données de test initialisées avec succès!")
        print(f"{len(produits)} produits créés")
        print(f"{len(caisses)} caisses créées")
        print(f"{len(caissiers)} caissiers créés")
        
    except Exception as e:
        session.rollback()
        print(f"Erreur lors de l'initialisation: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    init_data() 