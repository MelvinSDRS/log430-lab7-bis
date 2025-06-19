# ADR 006: API REST avec Flask-RESTX et Architecture DDD

## Contexte

Nous devons exposer les fonctionnalités principales via une API REST pour permettre l'intégration avec des applications externes.

## Décision

J'ai décidé d'utiliser Flask-RESTX pour l'API REST avec une architecture Domain-Driven Design (DDD) pour organiser la logique métier de cette interface spécifiquement.

## Options considérées

### Option 1: FastAPI
**Avantages:**
- Performance supérieure (asynchrone par défaut)
- Type hints Python natifs et validation automatique
- Documentation OpenAPI interactive

**Inconvénients:**
- Rupture avec l'architecture Flask existante
- Peut-être trop avancé pour notre utilisation

### Option 2: Flask-RESTX avec DDD (choisi)
**Avantages:**
- Cohérence architecturale avec l'interface web Flask existante
- Architecture métier structurée avec DDD pour l'API
- Documentation Swagger automatique intégrée
- Séparation claire des responsabilités métier

**Inconvénients:**
- Performance moindre que FastAPI pour les charges très élevées
- Pas d'asynchrone natif

## Justification

1. **Cohérence technique** : Nous utilisions déjà Flask pour l'interface web de supervision, utiliser Flask-RESTX maintient une stack technique homogène.

2. **Architecture métier structurée** : L'API bénéficie d'une organisation DDD avec Value Objects, Aggregates et Domain Services pour une logique métier plus robuste et maintenable.

3. **Pragmatisme** : Pour un système POS avec charge modérée comme le notre, les gains de performance de FastAPI ne justifient pas la complexité additionnelle.

4. **Séparation des préoccupations** : L'API peut évoluer indépendamment avec sa propre architecture métier tout en réutilisant l'infrastructure existante.

5. **Maintenabilité** : Une seule technologie web (Flask) à maintenir avec une architecture métier claire pour l'API.

## Conséquences

### Positives
- Architecture métier robuste et maintenable pour l'API
- Value Objects pour validation métier intégrée
- Domain Events pour découplage futur
- Documentation Swagger automatique
- Réutilisation de l'infrastructure existante

### Négatives
- Performance limitée pour de très gros volumes (non critique dans notre cas)
- Pas de support WebSockets natif (peut être ajouté si nécessaire)
- Complexité supplémentaire par rapport à une approche anémique

## Architecture DDD de l'API

L'API utilise une architecture Domain-Driven Design organisée en bounded contexts :

### Bounded Contexts
- **Product Catalog** : Gestion des produits avec logique métier riche
- **Shared Kernel** : Value Objects et Domain Events partagés

### Building Blocks DDD
- **Value Objects** : Money, ProductName, ProductId, StockQuantity avec validation métier
- **Aggregates** : Product comme racine d'agrégat avec logique encapsulée  
- **Domain Services** : Services métier pour logique transversale
- **Domain Events** : ProductCreated, ProductUpdated, ProductDeleted
- **Repository Adapters** : Interface avec l'infrastructure legacy

### Infrastructure
- **Adapters** : Pont avec les repositories et services existants
- **Application Services** : Orchestration des cas d'usage
- **Event Handling** : Système de publication/souscription d'événements

## Notes d'implémentation

L'API REST implémentée expose :
- 4 cas d'usage principaux : rapports consolidés, consultation stocks, performances magasins, gestion produits
- Authentification par token simple
- Documentation Swagger accessible via `/api/docs`
- Standards RESTful : HATEOAS, pagination, codes HTTP appropriés
- Architecture DDD pour le bounded context Product Catalog 