# Documentation Système Microservices POS + E-commerce - Lab 6 & 7

## Vue d'ensemble

Le projet montre l'évolution d'architectures distribuées avancées :
- **Lab 6** : Architecture microservices avec **orchestration saga** pour transactions distribuées
- **Lab 7** : Architecture **événementielle** avec Event Sourcing et CQRS pour gestion réclamations

L'ensemble illustre différents patterns architecturaux pour systèmes distribués modernes.

### Évolution architecturale

**Lab 1-3 : Architecture monolithique**
- Application Flask centralisée 
- Base de données PostgreSQL unique
- Interfaces console et web simples

**Lab 5 : Architecture microservices distribuée**
- **7 microservices autonomes** : Product, Customer, Cart, Order, Inventory, Sales, Reporting
- **Kong API Gateway** : Point d'entrée unique avec load balancing
- **Database per Service** : 7 PostgreSQL + 1 Redis isolés
- **Observabilité stack** : Prometheus + Grafana + dashboards métier

**Lab 6 : Architecture microservices avec Saga Orchestration**
- **9 microservices autonomes** : Product, Customer, Cart, Order, Inventory, Sales, Reporting, Saga Orchestrator, Payment
- **Saga Orchestration** : Coordination synchrone de transactions distribuées
- **Compensation automatique** : Rollback intelligent en cas d'échec
- **Database per Service** : 9 PostgreSQL + 1 Redis isolés
- **Observabilité étendue** : Métriques saga et monitoring transactionnel

**Lab 7 : Architecture événementielle avec Event Sourcing + CQRS**
- **4 services événementiels** : Claims, Notification, Audit, Integration
- **Event Sourcing** : MongoDB Event Store avec persistence immuable
- **CQRS** : Séparation Command/Query avec read models PostgreSQL
- **Pub/Sub messaging** : Redis Streams pour distribution événementielle
- **Intégration inter-architectures** : Pont Lab 6 ↔ Lab 7 avec mode dégradé

## Architecture microservices

### Services métier

| Service | Port | Responsabilité | Base de données |
|---------|------|----------------|-----------------|
| **Product Service** | 8001 | Catalogue produits unifié POS + E-commerce | PostgreSQL (product_db) |
| **Inventory Service** | 8002 | Stocks multi-locations et réservations | PostgreSQL (inventory_db) |
| **Sales Service** | 8003 | Transactions POS magasins physiques | PostgreSQL (sales_db) |
| **Reporting Service** | 8004 | Analytics et BI consolidé cross-canal | PostgreSQL (reporting_db) |
| **Customer Service** | 8005 | Authentification et profils clients | PostgreSQL (customer_db) |
| **Cart Service** | 8006 | Panier e-commerce load-balanced | Redis (cart_cache) |
| **Order Service** | 8007 | Commandes et checkout e-commerce | PostgreSQL (order_db) |
| **Saga Orchestrator** | 8008 | Orchestration saga et compensation | In-Memory (saga_state) |
| **Payment Service** | 8009 | Traitement paiements et remboursements | PostgreSQL (payment_db) |

### Infrastructure

| Composant | Port | Fonction |
|-----------|------|----------|
| **Kong Gateway** | 8080 | API Gateway central, load balancing, auth |
| **Prometheus** | 9090 | Métriques collection et monitoring |
| **Grafana** | 3000 | Dashboards et visualisation |

### Load balancing Kong

**Cart Service high availability** :
- **3 instances** : cart-service-1, cart-service-2, cart-service-3  
- **Algorithme** : least-connections avec health checks
- **Shared state** : Redis cache partagé pour session persistence
- **Failover automatique** : Détection pannes et exclusion instances

## Documentation technique

### 1. Architecture et conception

**[Architecture 4+1 Microservices](architecture-4+1.md)**
- Vue logique : Bounded contexts et services autonomes
- Vue processus : Workflows e-commerce et POS
- Vue déploiement : Infrastructure microservices distribuée
- Vue implémentation : Organisation code et qualité
- Vue cas d'utilisation : Scénarios omnicanaux

**[Choix technologiques](choix-technologiques.md)**
- Kong Gateway vs alternatives
- Database per Service pattern
- Redis pour cache distribué
- Observabilité Prometheus + Grafana
- DevOps et CI/CD strategies

**[Analyse des besoins](analyse-besoins.md)**
- Besoins métier hybride POS + E-commerce
- Exigences non-fonctionnelles microservices
- Contraintes et dépendances
- Plan de migration Lab 1 → Lab 5

### 2. Décisions architecturales (ADRs)

Les ADRs documentent les décisions clés de l'évolution architecturale Lab 1 → Lab 7 :

**[ADR-001 : Choix plateforme microservices](adr/001-choix-plateforme.md)**
- Évolution des ADRs Lab 1-4 vers architecture distribuée
- Justifications Kong Gateway et containerisation

**[ADR-002 : Stratégie de persistance](adr/002-strategie-persistence.md)**
- Database per Service pattern
- Redis pour session state distribué

**[ADR-003 : Séparation des responsabilités](adr/003-separation-responsabilites.md)**
- Bounded contexts microservices
- Communication patterns

**[ADR-004 : Architecture MVC](adr/004-architecture-mvc.md)**
- Évolution vers API-first microservices

**[ADR-005 : Framework Flask](adr/005-framework-flask.md)**
- Maintien Flask per service

**[ADR-006 : API REST Flask-RESTX](adr/006-api-rest-flask-restx.md)**
- Standards REST pour inter-service communication

**[ADR-007 : Architecture Microservices](adr/007-architecture-microservices.md)**
- Migration vers architecture microservices avec Database per Service
- Décomposition bounded contexts et autonomie des équipes

**[ADR-008 : Kong Gateway Load Balancing](adr/008-kong-gateway-load-balancing.md)**
- API Gateway avec load balancing et observabilité
- Authentication centralisée et rate limiting

**[ADR-009 : Pattern Saga Orchestrée Synchrone](adr/009-saga-orchestration-pattern.md)**
- Coordination transactions distribuées avec orchestrateur central
- Machine d'état saga et compensation automatique

**[ADR-010 : Communication via API Gateway](adr/010-communication-via-api-gateway.md)**
- Kong Gateway pour communications saga orchestrator
- Load balancing et sécurité centralisée

**[ADR-011 : Redis Streams pour messagerie événementielle](adr/011-redis-streams-messaging.md)**
- Choix Redis Streams pour Pub/Sub
- Performance et simplicité architecturale

**[ADR-012 : Intégration inter-architectures](adr/012-integration-inter-architectures.md)**
- Service de pont Lab 6 ↔ Lab 7
- Mode dégradé et réalisme métier

### 3. Diagrammes UML microservices

**[Diagrammes UML](uml/)**

**Diagrammes de structure** :
- [Classes microservices](uml/images/classes.png) : Domain models per bounded context
- [Composants](uml/images/composants.png) : Architecture microservices et Kong Gateway  
- [Déploiement](uml/images/deploiement.png) : Infrastructure distribuée avec observabilité

**Diagrammes de comportement** :
- [Cas d'utilisation](uml/images/cas_utilisation.png) : Scénarios POS + E-commerce
- [Séquence e-commerce](uml/images/sequence_vente.png) : Processus checkout complet
- [Séquence reporting](uml/images/sequence_rapport.png) : Agrégation multi-services
- [Séquence load balancing](uml/images/sequence_tableau_bord.png) : Cart Service failover

**Diagrammes Saga Orchestration** :
- [Machine d'état Saga](uml/images/saga-state-machine.png) : États et transitions saga
- [Séquence saga succès](uml/images/saga-sequence-success.png) : Flux nominal de commande

**Diagrammes Event-Driven Architecture (Lab 7)** :
- [Composants événementiels](uml/composants.puml) : Architecture Event Sourcing + CQRS
- [Déploiement Lab 7](uml/deploiement.puml) : Infrastructure événementielle
- [Séquence réclamations](uml/sequence_claims_events.puml) : Flux événementiel complet

## Architecture événementielle (Lab 7)

### Services événementiels

**Claims Service (8101)** : Producteur d'événements
- Gestion cycle de vie des réclamations
- Publication d'événements métier (5 types)
- API REST pour commandes (Command Side CQRS)

**Notification Service (8102)** : Abonné notifications
- Traitement événements pour notifications email/SMS
- Consumer Redis Streams avec groupes

**Audit Service (8103)** : Abonné audit et conformité
- Création piste d'audit complète
- Enregistrement tous événements avec métriques

**Integration Service (8107)** : Pont Lab 6 ↔ Lab 7
- Enrichissement réclamations avec contexte commandes/clients
- Mode dégradé si Lab 6 indisponible

### Infrastructure événementielle

**Redis Streams (6381)** : Backbone Pub/Sub
- Distribution événements avec streams nommés
- Consumer groups pour livraison garantie
- Backpressure et replay capabilities

**MongoDB Event Store (27018)** : Persistence Event Sourcing
- Stockage immuable des événements
- Capacité replay pour reconstruction d'état
- Index optimisés par aggregate_id et event_type

**PostgreSQL Read Models (5439)** : CQRS Query Side
- Projections dénormalisées pour lectures optimisées
- Mise à jour asynchrone via événements

## Déploiement et utilisation

### Démarrage rapide

```bash
# Cloner le repository
git clone <repository-url>
cd log430-lab6

# Lab 6 - Déploiement microservices avec saga
cd microservices/
docker-compose up -d

# Lab 7 - Déploiement architecture événementielle  
cd event-driven/
docker-compose up -d

# Vérification santé services
curl http://localhost:8080/health          # Lab 6 Kong Gateway
curl http://localhost:8101/health          # Lab 7 Claims Service
```

### Points d'accès

**Lab 6 - Kong API Gateway** : http://localhost:8080
- Point d'entrée unique pour tous les services
- Documentation OpenAPI : http://localhost:8080/docs
- Health check global : http://localhost:8080/health

**Lab 7 - Services événementiels** :
- **Claims Service** : http://localhost:8101/docs
- **Notification Service** : http://localhost:8102/health
- **Audit Service** : http://localhost:8103/health
- **Integration Service** : http://localhost:8107/health

**Observabilité stack** :
- **Grafana Lab 6** : http://localhost:3000 (Kong + Microservices)
- **Grafana Lab 7** : http://localhost:3001 (Event-Driven Dashboard)
- **Prometheus Lab 6** : http://localhost:9090
- **Prometheus Lab 7** : http://localhost:9091
- **Kong Admin API** : http://localhost:8001

### Tests de performance

```bash
# Tests k6 load balancing Cart Service
cd load_tests/k6/
k6 run lab5-fair-comparison-15vu-test.js
k6 run lab5-fair-comparison-100vu-test.js
```

**Résultats Lab 5 vs Lab 4** :
- **Latency** : 641x amélioration (5,002ms → 7.8ms)
- **Throughput** : 37x amélioration (2.43 → 91.3 req/s)  
- **Error rate** : 0% vs 40% Lab 4
- **Observabilité** : 76% MTTR amélioration

## Guides d'utilisation

### Pour développeurs

**Structure microservice standard** :
```
service/
├── app.py              # Flask application
├── models/             # Database models  
├── services/           # Business logic
├── api/               # REST endpoints
├── database.py        # Database configuration
├── requirements.txt   # Dependencies
├── Dockerfile         # Container image
└── tests/             # Service tests
```

**Communication inter-services** :
- **Synchrone** : HTTP REST via Kong Gateway
- **Service-to-service** : Direct HTTP pour performance
- **Shared state** : Redis pour Cart Service instances
- **Event-driven** : Future évolution consistency patterns

### Pour administrateurs

**Monitoring et alerting** :
- **Service health** : Health checks automatiques Kong + Prometheus
- **Performance metrics** : Response times, throughput, error rates
- **Business metrics** : Conversion rates, cart abandonment, revenue
- **Infrastructure** : Resource utilization per service

**Scaling et maintenance** :
- **Horizontal scaling** : Scale services individuellement
- **Database per service** : Backup et maintenance isolés
- **Rolling updates** : Déploiement sans interruption
- **Health checks** : Validation automatique déploiements

## Évolution et roadmap

### Kubernetes migration ready

L'architecture microservices Lab 5 est **Kubernetes-ready** :
- **Container-native** : Docker images per service
- **Health probes** : Liveness et readiness checks
- **Service mesh ready** : Istio integration potential
- **Auto-scaling** : HPA avec métriques Prometheus

### Cloud-native features

- **12-factor app compliance** : Configuration, stateless design
- **Observability** : Three pillars (metrics, logging, tracing)
- **Resilience patterns** : Circuit breaker, retry logic, timeouts
- **Security** : mTLS, RBAC, secrets management

## Performance et métriques

### Targets de performance atteints

- **API latency** : < 200ms p95 (moyenne 7.8ms)
- **E-commerce checkout** : < 2s end-to-end
- **Dashboard load** : < 1s agrégation multi-services  
- **Throughput** : 1000+ users concurrent (testé 100 VU)
- **Availability** : 99.9% uptime avec health checks

### Comparaison Lab 4 → Lab 5

| Métrique | Lab 4 | Lab 5 | Amélioration |
|----------|--------|--------|--------------|
| **Latency moyenne** | 5,002ms | 7.8ms | **641x faster** |
| **Throughput** | 2.43 req/s | 91.3 req/s | **37x higher** |
| **Error rate** | 40% | 0% | **100% improvement** |
| **MTTR** | 8.2s | 2.0s | **76% faster** |

## Conclusion

L'**architecture microservices Lab 5** représente l'aboutissement d'une évolution mature vers un **système cloud-native production-ready**, optimisé pour un contexte **e-commerce moderne avec support POS legacy**. Kong Gateway assure une **gouvernance API centralisée** tout en permettant l'**autonomie et scalabilité** des services métier.