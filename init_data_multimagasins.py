#!/usr/bin/env python3
"""
Script d'initialisation des données pour le système multi-magasins
Crée les entités, produits, stocks et données de test
"""

import sys
import os
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.persistence.database import get_db_session, create_tables
from src.persistence.models import (
    EntiteModel, CategorieModel, ProduitModel, StockEntiteModel,
    CaisseModel, CaissierModel, VenteModel, LigneVenteModel,
    TypeEntiteEnum
)


def init_entites(session):
    """Initialiser les entités (magasins, centre logistique, maison mère)"""
    print("Création des entités...")
    
    # Vérifier s'il y a déjà des entités pour éviter les doublons
    existing_entites = session.query(EntiteModel).first()
    if existing_entites:
        print("Entités déjà existantes, réutilisation...")
        return session.query(EntiteModel).all()
    
    entites = [
        # Magasins
        EntiteModel(
            nom="POS Vieux-Montréal",
            type_entite=TypeEntiteEnum.MAGASIN,
            adresse="350 Place Jacques-Cartier, Vieux-Montréal, QC H2Y 3B3",
            statut="ACTIVE"
        ),
        EntiteModel(
            nom="POS Plateau Mont-Royal",
            type_entite=TypeEntiteEnum.MAGASIN,
            adresse="4319 Boulevard Saint-Laurent, Plateau Mont-Royal, QC H2W 1Z4",
            statut="ACTIVE"
        ),
        EntiteModel(
            nom="POS Quartier des Spectacles",
            type_entite=TypeEntiteEnum.MAGASIN,
            adresse="175 Rue Sainte-Catherine Ouest, Quartier des Spectacles, QC H2X 1Z8",
            statut="ACTIVE"
        ),
        EntiteModel(
            nom="POS Mile End",
            type_entite=TypeEntiteEnum.MAGASIN,
            adresse="5265 Avenue du Parc, Mile End, QC H2V 4G7",
            statut="ACTIVE"
        ),
        EntiteModel(
            nom="POS Westmount",
            type_entite=TypeEntiteEnum.MAGASIN,
            adresse="1 Westmount Square, Westmount, QC H3Z 2P9",
            statut="ACTIVE"
        ),
        # Centre logistique
        EntiteModel(
            nom="Centre logistique Anjou",
            type_entite=TypeEntiteEnum.CENTRE_LOGISTIQUE,
            adresse="8000 Boulevard Métropolitain Est, Anjou, QC H1K 1A1",
            statut="ACTIVE"
        ),
        # Maison mère
        EntiteModel(
            nom="Siège Social ÉTS",
            type_entite=TypeEntiteEnum.MAISON_MERE,
            adresse="1100 Rue Notre-Dame Ouest, Griffintown, QC H3C 1K3",
            statut="ACTIVE"
        )
    ]
    
    for entite in entites:
        session.add(entite)
    
    session.commit()
    print(f"{len(entites)} entités créées")
    return entites


def init_categories_produits(session):
    """Initialiser les catégories et produits"""
    print("Création des catégories et produits...")
    
    # Catégories
    categories = [
        CategorieModel(nom="Électronique", description="Appareils électroniques et accessoires"),
        CategorieModel(nom="Vêtements", description="Vêtements et accessoires de mode"),
        CategorieModel(nom="Alimentation", description="Produits alimentaires et boissons"),
        CategorieModel(nom="Maison & Jardin", description="Articles pour la maison et le jardin"),
        CategorieModel(nom="Sport & Loisirs", description="Équipements sportifs et de loisirs")
    ]
    
    for categorie in categories:
        session.add(categorie)
    session.commit()
    
    # Produits
    produits = [
        # Électronique
        ProduitModel(nom="iPhone 16 Pro Max", prix=Decimal("1299.99"), stock=0, seuil_alerte=5, id_categorie=1, description="Smartphone haut de gamme avec écran 6.7 pouces, puce A18 Pro et appareil photo professionnel"),
        ProduitModel(nom="MacBook Air", prix=Decimal("1099.99"), stock=0, seuil_alerte=3, id_categorie=1, description="Ordinateur portable ultra-fin avec puce M2, 13 pouces, parfait pour le travail et les études"),
        ProduitModel(nom="AirPods Pro", prix=Decimal("259.99"), stock=0, seuil_alerte=10, id_categorie=1, description="Écouteurs sans fil avec réduction de bruit active et audio spatial"),
        ProduitModel(nom="iPad", prix=Decimal("449.99"), stock=0, seuil_alerte=5, id_categorie=1, description="Tablette polyvalente pour créativité, productivité et divertissement"),
        
        # Vêtements
        ProduitModel(nom="T-shirt", prix=Decimal("19.99"), stock=0, seuil_alerte=20, id_categorie=2, description="T-shirt en coton bio, coupe classique, disponible en plusieurs couleurs"),
        ProduitModel(nom="Jean", prix=Decimal("59.99"), stock=0, seuil_alerte=15, id_categorie=2, description="Jean slim en denim de qualité supérieure, coupe moderne et confortable"),
        ProduitModel(nom="Veste d'hiver", prix=Decimal("129.99"), stock=0, seuil_alerte=8, id_categorie=2, description="Veste chaude et imperméable, isolation thermique avancée"),
        ProduitModel(nom="Baskets", prix=Decimal("89.99"), stock=0, seuil_alerte=12, id_categorie=2, description="Chaussures de sport confortables, semelle amortissante, design moderne"),
        
        # Alimentation
        ProduitModel(nom="Café", prix=Decimal("12.99"), stock=0, seuil_alerte=25, id_categorie=3, description="Café arabica bio, torréfaction artisanale, arôme intense et équilibré"),
        ProduitModel(nom="Chocolat Noir", prix=Decimal("4.99"), stock=0, seuil_alerte=30, id_categorie=3, description="Chocolat noir 70% cacao, commerce équitable, saveur riche"),
        ProduitModel(nom="Thé Vert", prix=Decimal("8.99"), stock=0, seuil_alerte=20, id_categorie=3, description="Thé vert bio de haute qualité, riche en antioxydants"),
        ProduitModel(nom="Miel", prix=Decimal("15.99"), stock=0, seuil_alerte=15, id_categorie=3, description="Miel naturel de fleurs sauvages, production locale artisanale"),
        
        # Maison & Jardin
        ProduitModel(nom="Aspirateur Dyson", prix=Decimal("299.99"), stock=0, seuil_alerte=5, id_categorie=4, description="Aspirateur sans sac cyclonique, puissance élevée, filtration HEPA"),
        ProduitModel(nom="Plante Verte", prix=Decimal("24.99"), stock=0, seuil_alerte=10, id_categorie=4, description="Plante d'intérieur dépolluante, facile d'entretien, pot inclus"),
        ProduitModel(nom="Lampe LED", prix=Decimal("39.99"), stock=0, seuil_alerte=8, id_categorie=4, description="Lampe de bureau LED réglable, faible consommation, éclairage naturel"),
        
        # Sport & Loisirs
        ProduitModel(nom="Ballon Football", prix=Decimal("29.99"), stock=0, seuil_alerte=15, id_categorie=5, description="Ballon de football officiel, cuir synthétique, taille 5"),
        ProduitModel(nom="Raquette Tennis", prix=Decimal("79.99"), stock=0, seuil_alerte=8, id_categorie=5, description="Raquette de tennis adulte, cadre en graphite, équilibrée"),
        ProduitModel(nom="Vélo VTT", prix=Decimal("499.99"), stock=0, seuil_alerte=3, id_categorie=5, description="VTT tout-terrain, 21 vitesses, suspension avant, cadre aluminium")
    ]
    
    for produit in produits:
        session.add(produit)
    session.commit()
    
    print(f"{len(categories)} catégories et {len(produits)} produits créés")
    return categories, produits


def init_stocks(session, entites, produits):
    """Initialiser les stocks par entité"""
    print("Répartition des stocks par entité...")
    
    magasins = [e for e in entites if e.type_entite == TypeEntiteEnum.MAGASIN]
    centre_logistique = next(e for e in entites if e.type_entite == TypeEntiteEnum.CENTRE_LOGISTIQUE)
    
    stocks_created = 0
    
    # Stocks du centre logistique
    for produit in produits:
        stock_central = StockEntiteModel(
            id_produit=produit.id,
            id_entite=centre_logistique.id,
            quantite=100,
            seuil_alerte=20
        )
        session.add(stock_central)
        stocks_created += 1
    
    # Stocks des magasins
    import random
    random.seed(42)
    
    for magasin in magasins:
        for produit in produits:
            # Quantité aléatoire entre 5 et 50 pour chaque produit dans chaque magasin
            quantite = random.randint(5, 50)
            
            # Quelques produits en rupture pour tester les alertes
            if random.random() < 0.1:  # 10% de chance d'être en rupture
                quantite = random.randint(0, 2)
            
            stock_magasin = StockEntiteModel(
                id_produit=produit.id,
                id_entite=magasin.id,
                quantite=quantite,
                seuil_alerte=produit.seuil_alerte
            )
            session.add(stock_magasin)
            stocks_created += 1
    
    session.commit()
    print(f"{stocks_created} stocks créés")


def init_caisses_caissiers(session, entites):
    """Initialiser les caisses et caissiers"""
    print("Création des caisses et caissiers...")
    
    # Vérifier s'il y a déjà des caisses pour éviter les doublons
    existing_caisses = session.query(CaisseModel).first()
    if existing_caisses:
        print("Caisses déjà existantes, nettoyage des doublons...")
        session.query(CaissierModel).delete()
        session.query(CaisseModel).delete()
        session.commit()
    
    magasins = [e for e in entites if e.type_entite == TypeEntiteEnum.MAGASIN]
    
    caisses_created = 0
    caissiers_created = 0
    
    for i, magasin in enumerate(magasins, 1):
        # 2 caisses par magasin
        for j in range(1, 3):
            caisse = CaisseModel(
                nom=f"Caisse {j}",
                statut="ACTIVE",
                id_entite=magasin.id
            )
            session.add(caisse)
            caisses_created += 1
        
        # 3 caissiers par magasin
        caissiers_noms = [
            f"Melvin Siadous - {magasin.nom}",
            f"Michael Jordan - {magasin.nom}",
            f"Steve Jobs - {magasin.nom}"
        ]
        
        for nom in caissiers_noms:
            caissier = CaissierModel(
                nom=nom,
                id_entite=magasin.id
            )
            session.add(caissier)
            caissiers_created += 1
    
    session.commit()
    print(f"{caisses_created} caisses et {caissiers_created} caissiers créés")


def init_ventes_demo(session, entites, produits):
    """Créer quelques ventes de démonstration"""
    print("💰 Création de ventes de démonstration...")
    
    magasins = [e for e in entites if e.type_entite == TypeEntiteEnum.MAGASIN]

    caisses = session.query(CaisseModel).all()
    caissiers = session.query(CaissierModel).all()
    
    import random
    random.seed(42)
    
    ventes_created = 0
    
    # Créer des ventes sur les 7 derniers jours
    for day_offset in range(7):
        date_vente = datetime.now() - timedelta(days=day_offset)
        
        # 5-15 ventes par jour réparties sur tous les magasins
        nb_ventes_jour = random.randint(5, 15)
        
        for _ in range(nb_ventes_jour):
            magasin = random.choice(magasins)
            
            caisses_magasin = [c for c in caisses if c.id_entite == magasin.id]
            caissiers_magasin = [c for c in caissiers if c.id_entite == magasin.id]
            
            if not caisses_magasin or not caissiers_magasin:
                continue
            
            caisse = random.choice(caisses_magasin)
            caissier = random.choice(caissiers_magasin)
            
            # Créer la vente
            vente = VenteModel(
                horodatage=date_vente.replace(
                    hour=random.randint(9, 19),
                    minute=random.randint(0, 59)
                ),
                id_caisse=caisse.id,
                id_caissier=caissier.id,
                id_entite=magasin.id,
                statut="COMPLETEE"
            )
            session.add(vente)
            session.flush()
            
            # Ajouter 1-5 produits à la vente
            nb_produits = random.randint(1, 5)
            produits_vente = random.sample(produits, nb_produits)
            
            for produit in produits_vente:
                quantite = random.randint(1, 3)
                ligne_vente = LigneVenteModel(
                    id_vente=vente.id,
                    id_produit=produit.id,
                    qte=quantite
                )
                session.add(ligne_vente)
            
            ventes_created += 1
    
    session.commit()
    print(f"{ventes_created} ventes de démonstration créées")


def main():
    """Fonction principale d'initialisation"""
    print("Initialisation du système multi-magasins...")
    print("=" * 50)
    
    try:
        # Créer les tables
        print("Création des tables de base de données...")
        create_tables()
        print("Tables créées")
        
        # Obtenir une session
        session = get_db_session()
        
        try:
            # Initialiser les données
            entites = init_entites(session)
            categories, produits = init_categories_produits(session)
            init_stocks(session, entites, produits)
            init_caisses_caissiers(session, entites)
            init_ventes_demo(session, entites, produits)
            
            print("=" * 50)
            print("Initialisation terminée avec succès!")
            print()
            print("Résumé de l'architecture déployée:")
            print(f"   - 5 Magasins")
            print(f"   - 1 Centre logistique")
            print(f"   - 1 Maison mère")
            print(f"   - {len(produits)} Produits")
            print(f"   - Stocks répartis dans toutes les entités")
            print(f"   - Caisses et caissiers configurés")
            print(f"   - Données de ventes de démonstration")
            print()
            print("Accès aux interfaces:")
            print("   - Interface web administrative: http://localhost:5000")
            print("   - Interfaces Console Magasins: docker-compose exec pos-magasin-X bash")
            
        finally:
            session.close()
            
    except Exception as e:
        print(f"Erreur lors de l'initialisation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 