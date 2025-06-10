# ADR 004: Architecture MVC pour l'interface web

## Contexte

Le système devait évoluer d'une architecture 2-tier avec interface console vers une architecture 3-tier avec interface web pour supporter la gestion multi-magasins et les besoins de supervision centralisée.

## Décision

J'ai donc adopté le pattern architectural MVC (Model-View-Controller) pour l'interface web du système multi-magasins, implémenté avec Flask.

## Justification

### Exigences satisfaites
- **Séparation des responsabilités** : Distinction claire entre logique métier, présentation et contrôle
- **Évolutivité** : Support pour interface web avec multiple types d'utilisateurs (admin, logistique, magasins)
- **Maintenabilité** : Code modulaire et extensible
- **Testabilité** : Chaque couche peut être testée indépendamment
- **Réutilisation** : Intégration avec la logique métier existante du Lab 1

### Architecture MVC implémentée

#### **Model** (Couche métier)
- **Entités métier** : `src/domain/entities.py` (Produit, Vente, StockEntite, etc.)
- **Services métier** : `src/domain/services.py` (ServiceVente, ServiceInventaire, ServiceRapport, etc.)
- **Repositories** : `src/persistence/repositories.py` (accès aux données)
- **Models ORM** : `src/persistence/models.py` (SQLAlchemy)

#### **View** (Couche présentation)
- **Templates de base** : `base.html`, `index.html`
- **Templates supervision** : `index.html`, `dashboard.html`

#### **Controller** (Couche contrôle)
- **Contrôleur principal** : `src/web/app.py`
- **Routes par domaine** :
  - Supervision : `/` (accueil), `/dashboard` (indicateurs clés)

## Implémentation réelle

### Structure du projet
```
src/web/
├── app.py              # Contrôleur principal Flask
├── templates/          # Vues HTML
│   ├── index.html      # Page d'accueil
│   ├── dashboard.html  # Tableau de bord
└── __init__.py
```

### Fonctionnalités par Use Case

- **UC1** : Rapports (interface console uniquement)
- **UC2** : Consultation stocks central (interface console uniquement)
- **UC3** : Tableau de bord (`dashboard.html`)
- **UC4** : Gestion produits (interface console uniquement)
- **UC6** : Approvisionnement (interface console uniquement)
- **UC8** : Interface légère (`index.html` + `dashboard.html`)

### Intégration avec l'existant
- Réutilisation des services métier du Lab 1
- Coexistence entre l'interface console (magasins) et l'interface web (supervision)
- Base de données partagée PostgreSQL
- Services communs : ServiceVente, ServiceInventaire, ServiceApprovisionnement

## Conséquences

### Avantages
- **Réutilisation** : pas de duplication de logique métier
- **Séparation claire** : Model (domaine), View (templates), Controller (routes Flask)
- **Multi-interface** : Console pour opérations + Web pour supervision
- **Maintenabilité** : Structure modulaire claire

### Inconvénients à date
- **Contrôleur monolithique** : Toutes les routes dans un seul fichier
- **Pas de framework frontend** : HTML/CSS basique sans JS framework (je ne voulais pas faire trop compliqué pour l'instant)

## Évolutions futures possibles

- Séparation du contrôleur en modules par domaine
- Ajout de fichiers CSS/JS statiques externes
- Intégration d'un framework frontend (Vue.js, React)
- Système de gestion d'utilisateurs pour séparer les accès
- API REST séparée