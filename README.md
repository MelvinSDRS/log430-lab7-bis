# LOG430 - Lab 1 - Système de Point de Vente

## Description

Système de point de vente (POS) pour un petit magasin de quartier avec **architecture client/serveur 2-tier**. L'application permet de gérer les opérations de base d'un système de caisse avec support pour 3 caisses simultanées.

## Architecture

- **Serveur (Tier 1)** : Base de données PostgreSQL dans un conteneur dédié
- **Clients (Tier 2)** : 3 applications console indépendantes qui se connectent au serveur

## Fonctionnalités

- Rechercher un produit (par identifiant, nom ou catégorie)
- Enregistrer une vente (sélection de produits et calcul du total)
- Gérer les retours (annuler une vente)
- Consulter l'état du stock des produits
- Gestion des transactions pour garantir la cohérence des données

## Démarrage Rapide

### Prérequis
- Docker Engine 20.10+
- Docker Compose v2.0+

### Lancement (Une seule commande)

```bash
# Démarrer l'architecture complète (serveur + 3 clients)
docker compose up -d

# Accéder aux clients
docker compose exec pos-app-1 python main.py  # Client 1
docker compose exec pos-app-2 python main.py  # Client 2  
docker compose exec pos-app-3 python main.py  # Client 3
```

### Workflow Automatique

Le système démarre **complètement automatiquement** :
1. PostgreSQL démarre et devient healthy (~11 secondes)
2. Base de données initialisée automatiquement (8 produits, 3 caisses, 3 caissiers)
3. 3 clients démarrent et attendent la sélection de caisse
4. **Aucune intervention manuelle** requise

## Utilisation

### Configuration Multi-Caisses

Au démarrage, chaque client permet de :
1. **Sélectionner votre caisse** (parmi 3 caisses disponibles)
2. **Choisir votre identité de caissier** (Alice, Bob, ou Claire)

### Interface

L'application présente un menu avec les options suivantes :
1. **Rechercher un produit** : Recherche par ID, nom ou catégorie
2. **Ajouter au panier** : Ajouter des produits au panier courant
3. **Voir le panier** : Afficher le contenu du panier avec le total
4. **Finaliser la vente** : Traiter la vente et mettre à jour les stocks
5. **Retourner une vente** : Annuler une vente existante
6. **Quitter** : Fermer l'application

## Tests

```bash
# Exécuter tous les tests (10 tests : 7 unitaires + 3 performance)
docker compose --profile test up pos-test
```

## Commandes Utiles

```bash
# Arrêter tous les services
docker compose down

# Arrêter et supprimer les volumes (reset complet)
docker compose down -v

# Voir les logs
docker compose logs -f

# Vérifier l'état des conteneurs
docker compose ps
```

## Technologies

- **Python 3.11** : Langage de programmation
- **PostgreSQL** : Base de données serveur
- **SQLAlchemy** : ORM pour l'abstraction de la persistance
- **Rich** : Interface console améliorée
- **Docker** : Conteneurisation et déploiement

## Structure du Projet

```
.
├── src/
│   ├── client/           # Interface console
│   ├── domain/           # Logique métier
│   └── persistence/      # Accès aux données
├── tests/                # Tests unitaires et performance
├── docs/                 # Documentation complète
├── main.py              # Point d'entrée
├── init_data.py         # Initialisation des données
└── docker-compose.yml   # Configuration Docker
```

## Documentation Complète

La documentation détaillée incluant les diagrammes UML et les décisions d'architecture est disponible dans le dossier `docs/`.
