# LOG430 - Lab 4 - Système POS Multi-Magasins

## Description

Système de point de vente (POS) **multi-magasins** avec **architecture 3-tier** évoluée. Le système gère **5 magasins + 1 centre logistique + 1 maison mère** avec interface web de supervision, interface console pour les caisses, et API REST pour applications externes.

## Architecture 3-Tier

- **Tier 1 (Persistance)** : Base de données PostgreSQL centralisée
- **Tier 2 (Logique Métier)** : Services d'approvisionnement, rapports consolidés, tableau de bord
- **Tier 3 (Présentation)** : Interface console (opérations) + Interface web (supervision) + API REST (intégrations)

## Entités du Système

- **5 Magasins** : Montréal Centre, Québec, Sherbrooke, Trois-Rivières, Gatineau
- **1 Centre Logistique** : Distribution et gestion des stocks
- **1 Maison Mère** : Supervision et rapports consolidés

## Architecture Multi-Interface

Le système respecte une **séparation claire des responsabilités** :

- **Interface Console** : Toutes les opérations métier (ventes, rapports, gestion produits, approvisionnements)
- **Interface Web** : Supervision légère uniquement (tableau de bord, monitoring)
- **API REST** : Exposition des fonctionnalités pour applications externes

Cette séparation garantit des performances optimales et une maintenance facilitée.

## Fonctionnalités

### Interface Console (Opérations Métier)
**Fonctionnalités de base (tous magasins) :**
- Rechercher un produit (par identifiant, nom ou catégorie)
- Enregistrer une vente avec gestion des stocks par entité
- Gérer les retours (annuler une vente)
- Consulter l'état du stock local et central

**Fonctionnalités spécifiques par type d'entité :**
- **Magasins** : Créer des demandes d'approvisionnement au centre logistique
- **Maison Mère** : Génération de rapports consolidés, gestion globale des produits
- **Centre Logistique** : Traitement des demandes d'approvisionnement inter-magasins

### Interface Web (Supervision)
- **Tableau de bord** : Indicateurs de performance en temps réel
- **Supervision** : Vue d'ensemble des magasins et alertes
- **Interface minimaliste** : Focus sur la supervision, pas les opérations

### API REST (Intégrations)
- **4 cas d'usage principaux** : Rapports consolidés, consultation stocks, performances, gestion produits
- **Documentation Swagger** : Interface interactive à `http://localhost:8000/api/docs`
- **Authentification token** : Sécurité pour applications externes
- **Standards RESTful** : HATEOAS, pagination, codes HTTP appropriés

## Optimisations de performance

Le système intègre des optimisations avancées pour haute performance et résilience :

### Cache Redis distribué
- **Gain** : -51% de latence sur endpoints complexes (1972ms → 965ms)
- **Hit rate** : 99.25% sous charge élevée
- **Endpoints cachés** : `/stores/performances`, `/reports/dashboard`, `/products`, `/stocks`
- **TTL adaptatif** : 3-15 min selon la criticité des données

### Load Balancer NGINX
- **Stratégie** : Round Robin (optimale sous toutes charges)
- **Scaling** : 2-4 instances API selon la charge
- **Seuil critique** : Efficace uniquement au-delà de 80 utilisateurs simultanés
- **Résilience** : Tolérance aux pannes avec redirection automatique

### Architecture Adaptative
- **< 50 VUs** : Instance unique + Cache Redis (simplicité optimale)
- **> 80 VUs** : Load Balancer + Cache distribué (performance maximale)
- **Monitoring** : Prometheus + Grafana pour observabilité complète

## Démarrage Rapide

### Prérequis
- Docker Engine 20.10+
- Docker Compose v2.0+

### Lancement (Une seule commande)

```bash
# Démarrer l'architecture complète (serveur + interface web + API REST + données multi-magasins)
docker compose up -d

# Démarrer avec optimisations de performance (Load Balancer + Cache Redis + Monitoring)
docker compose --profile performance up -d

# Accéder aux interfaces
http://localhost:5000                 # Interface web de supervision
http://localhost:8000/api/docs        # API REST (documentation Swagger)
http://localhost:8080                 # Load Balancer NGINX (si profil performance)
http://localhost:3000                 # Grafana (monitoring - si profil performance)

# Accéder à l'API REST et sa documentation
http://localhost:8000/api/docs        # Documentation Swagger interactive
http://localhost:8000/api/v1/         # API REST (nécessite token: pos-api-token-2025)

# Accéder aux interfaces console des magasins (5 magasins disponibles)
docker compose exec pos-magasin-1 python main.py  # Magasin 1 - Vieux-Montréal
docker compose exec pos-magasin-2 python main.py  # Magasin 2 - Plateau Mont-Royal  
docker compose exec pos-magasin-3 python main.py  # Magasin 3 - Quartier des Spectacles
docker compose exec pos-magasin-4 python main.py  # Magasin 4 - Mile End
docker compose exec pos-magasin-5 python main.py  # Magasin 5 - Westmount
```

### Workflow Automatique

Le système démarre complètement automatiquement :
1. PostgreSQL démarre et devient healthy
2. Base de données initialisée avec 7 entités et données de démonstration
3. Interface web Flask démarre sur le port 5000
4. API REST Flask-RESTX démarre sur le port 8000
5. Clients console disponibles pour chaque magasin
6. Services prêts : Interface web (supervision) + Interface console (opérations) + API REST (intégrations)
7. Aucune intervention manuelle requise

## Utilisation

### Interface Web (Supervision)

Accédez à `http://localhost:5000` pour :
1. **Tableau de bord** : Vue d'ensemble des performances de tous les magasins
2. **Supervision** : Monitoring en temps réel des indicateurs clés

**Note** : Les opérations (rapports, gestion produits, approvisionnements) se font via l'interface console.

### API REST (Intégrations)

Accédez à `http://localhost:8000/api/docs` pour :
1. **Documentation interactive Swagger** : Tester l'API directement
2. **Authentification** : Utiliser le token `pos-api-token-2025`
3. **4 cas d'usage** : Rapports, Stocks, Performances, Produits

**Endpoints principaux** :
- `GET /api/v1/reports/consolidated-sales` : Rapports de ventes consolidés
- `GET /api/v1/stocks?store_id=X` : Consultation des stocks par magasin
- `GET /api/v1/stores/performances` : Performances globales des magasins
- `GET/POST/PUT/DELETE /api/v1/products` : Gestion complète des produits

### Interface Console (Magasins)

Au démarrage de chaque client :
1. **Sélectionner votre entité** (parmi les 7 entités disponibles)
2. **Choisir votre caisse** (si magasin)
3. **Sélectionner votre identité de caissier**

Menu principal :
1. **Rechercher un produit** : Recherche par ID, nom ou catégorie
2. **Ajouter au panier** : Ajouter des produits au panier courant
3. **Voir le panier** : Afficher le contenu du panier avec le total
4. **Finaliser la vente** : Traiter la vente et mettre à jour les stocks
5. **Retourner une vente** : Annuler une vente existante
6. **Consulter stock central** : Voir les stocks du centre logistique
7. **Demander approvisionnement** : Créer une demande au centre
8. **Fonctions spécialisées** : Selon le type d'entité (rapports, gestion produits, etc.)
9. **Quitter** : Fermer l'application

## Tests

```bash
# Exécuter tous les tests (unitaires + services + performance)
docker compose --profile test up pos-test
```

## Commandes Utiles

```bash
# Arrêter tous les services
docker compose down

# Arrêter et supprimer les volumes (reset complet)
docker compose down -v

# Voir les logs d'un service spécifique
docker compose logs -f web-admin

# Voir les logs de l'application
tail -f pos_multimagasins.log

# Vérifier l'état des conteneurs
docker compose ps
```

## Technologies

- **Python 3.11** : Langage de programmation
- **PostgreSQL** : Base de données serveur
- **Redis 7** : Cache distribué
- **NGINX** : Load balancer
- **SQLAlchemy** : ORM pour l'abstraction de la persistance
- **Rich** : Interface console améliorée
- **Flask** : Framework web pour l'interface de supervision
- **Flask-RESTX** : Extension Flask pour API REST avec documentation Swagger
- **Prometheus + Grafana** : Monitoring et observabilité
- **Docker** : Conteneurisation et déploiement

## Structure du Projet

```
.
├── src/
│   ├── api/              # API REST
│   ├── client/           # Interface console (caisses)
│   ├── domain/           # Logique métier
│   └── persistence/      # Accès aux données
│   └── web/              # Interface web Flask
├── tests/                # Tests unitaires, services et performance
├── docs/                 # Documentation complète
├── main.py              # Point d'entrée console
├── init_data.py         # Initialisation des données
└── docker-compose.yml   # Configuration Docker
```

## Documentation Complète

La documentation détaillée incluant les diagrammes UML et les décisions d'architecture est disponible dans le dossier `docs/`.
