# LOG430 - Lab 2 - Système POS Multi-Magasins

## Description

Système de point de vente (POS) **multi-magasins** avec **architecture 3-tier** évoluée. Le système gère maintenant **5 magasins + 1 centre logistique + 1 maison mère** avec interface web de supervision en plus de l'interface console pour les caisses.

## Architecture 3-Tier

- **Tier 1 (Persistance)** : Base de données PostgreSQL centralisée
- **Tier 2 (Logique Métier)** : Services d'approvisionnement, rapports consolidés, tableau de bord
- **Tier 3 (Présentation)** : Interface console (opérations) + Interface web (supervision)

## Entités du Système

- **5 Magasins** : Montréal Centre, Québec, Sherbrooke, Trois-Rivières, Gatineau
- **1 Centre Logistique** : Distribution et gestion des stocks
- **1 Maison Mère** : Supervision et rapports consolidés

## Architecture Console + Web

Le système respecte une **séparation claire des responsabilités** :

- **Interface Console** : Toutes les opérations métier (ventes, rapports, gestion produits, approvisionnements)
- **Interface Web** : Supervision légère uniquement (tableau de bord, monitoring)

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

## Démarrage Rapide

### Prérequis
- Docker Engine 20.10+
- Docker Compose v2.0+

### Lancement (Une seule commande)

```bash
# Démarrer l'architecture complète (serveur + interface web + données multi-magasins)
docker compose up -d

# Accéder à l'interface web de supervision
http://localhost:5000

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
4. Clients console disponibles pour chaque magasin
5. Services prêts : Interface web (supervision) + Interface console (opérations)
6. Aucune intervention manuelle requise

## Utilisation

### Interface Web (Supervision)

Accédez à `http://localhost:5000` pour :
1. **Tableau de bord** : Vue d'ensemble des performances de tous les magasins
2. **Supervision** : Monitoring en temps réel des indicateurs clés

**Note** : Les opérations (rapports, gestion produits, approvisionnements) se font via l'interface console.

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
- **SQLAlchemy** : ORM pour l'abstraction de la persistance
- **Rich** : Interface console améliorée
- **Flask** : Framework web pour l'interface de supervision
- **Docker** : Conteneurisation et déploiement

## Structure du Projet

```
.
├── src/
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
