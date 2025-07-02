# ADR 007: Migration vers Architecture Microservices avec Database per Service

## Contexte

Le système évoluait d'une architecture monolithique (Lab 1-4) vers les besoins d'un écosystème commercial hybride POS + E-commerce nécessitant :
- **Scalabilité horizontale** pour supporter la croissance e-commerce
- **Autonomie des équipes** de développement per bounded context  
- **Résilience** et fault tolerance pour production
- **Technology diversity** selon les besoins métier spécifiques
- **Independent deployment** cycles per service

## Décision

J'ai décidé de migrer vers une architecture microservices distribuée avec Database per Service pattern comprenant :

### 7 Microservices autonomes
- **Product Service** (Port 8001) : Catalogue produits unifié POS + E-commerce
- **Inventory Service** (Port 8002) : Stocks multi-locations et réservations  
- **Sales Service** (Port 8003) : Transactions POS magasins physiques
- **Reporting Service** (Port 8004) : Analytics et BI consolidé cross-canal
- **Customer Service** (Port 8005) : Authentification et profils clients e-commerce
- **Cart Service** (Port 8006) : Panier e-commerce avec load balancing
- **Order Service** (Port 8007) : Commandes et checkout e-commerce

### Database per Service pattern
- **7 PostgreSQL databases isolées** : Une per service métier
- **1 Redis cache** : Session state partagé Cart Service instances
- **Isolation complète** : Aucun accès direct cross-database
- **Schema evolution indépendante** : Per bounded context

## Justification

### Strategic DDD Patterns appliqués
- **Bounded Contexts** : Chaque service encapsule un domaine métier cohérent
- **Context Mapping** : Relations entre services bien définies
- **Ubiquitous Language** : Vocabulaire métier spécifique per service
- **Anti-corruption Layers** : Isolation des modèles de données

### Tactical DDD Benefits
- **Aggregates** : Cohérence transactionnelle per service boundary
- **Domain Events** : Communication asynchrone inter-services (future)
- **Repository Pattern** : Abstraction persistance per bounded context
- **Domain Services** : Logique métier encapsulée per service

## Alternatives considérées

### Option 1: Monolithe modulaire (rejetée)
**Avantages:**
- Déploiement simplifié
- Transactions ACID cross-modules
- Développement initial plus rapide

**Inconvénients:**
- Coupling fort entre modules métier
- Scaling challenges (tout ou rien)
- Technology stack unique imposée
- Équipes dépendantes pour releases

### Option 2: Shared Database Anti-pattern (rejetée)
**Avantages:**
- Transactions cross-services facilitées
- Requêtes JOIN cross-domains simples

**Inconvénients:**
- Coupling par les données (pire que code coupling)
- Schema evolution bloque tous services
- Single point of failure critique
- Impossible de choisir technology optimal per service

### Option 3: Microservices + Database per Service (choisie)
**Avantages:**
- **Service autonomy** : Deploy, scale, technology per service
- **Fault isolation** : Panne d'un service n'affecte pas les autres
- **Team ownership** : Équipes dédiées per bounded context
- **Technology optimization** : PostgreSQL + Redis selon besoins
- **Schema evolution** : Indépendante per service

**Inconvénients:**
- **Distributed complexity** : Network latency, partial failures
- **Data consistency** : Eventual consistency challenges
- **Operational overhead** : Monitoring, debugging distribué
- **Transaction management** : Saga patterns pour workflows long

## Conséquences

### Positives réalisées

**Performance exceptionnelle** :
- **641x latency improvement** : 5,002ms → 7.8ms (vs Lab 4)
- **37x throughput improvement** : 2.43 → 91.3 req/s
- **0% error rate** : vs 40% Lab 4
- **Load balancing** : Cart Service avec 3 instances + failover

**Scalabilité horizontale** :
- **Independent scaling** : Scale Cart Service instances selon charge
- **Technology optimization** : Redis pour session state, PostgreSQL pour ACID
- **Resource isolation** : 512MB RAM per microservice, 1GB per database

**Résilience production** :
- **Fault tolerance** : Circuit breaker, retry logic, timeouts
- **Health monitoring** : Automated health checks + alerting
- **Graceful degradation** : Fallback strategies per service

### Négatives gérées

**Complexity management** :
- **Kong Gateway** : Centralise communication complexity
- **Observability stack** : Prometheus + Grafana pour monitoring unifié
- **Structured logging** : Correlation IDs pour debugging distribué

**Data consistency** :
- **Bounded context isolation** : Minimise besoins consistency cross-service
- **Eventual consistency** : Acceptable pour analytics (Reporting Service)
- **Strong consistency** : Maintenue within service boundaries

**Operational overhead** :
- **Docker orchestration** : Standardise deployment per service
- **Health checks automation** : Kong + Prometheus monitoring
- **Testing strategy** : Unit (70%) + Integration (20%) + Contract (5%) + E2E (5%)

## Migration strategy réalisée

### Phase 1: Infrastructure microservices
- Kong Gateway deployment (port 8080)
- Database per service setup (7 PostgreSQL + Redis)
- Monitoring stack (Prometheus + Grafana)
- Network isolation (microservices Docker network)

### Phase 2: Core services
- Product Service (catalogue unifié POS + E-commerce)
- Inventory Service (stocks multi-locations)
- Sales Service (POS legacy compatible)

### Phase 3: E-commerce services
- Customer Service (JWT authentication)
- Cart Service (load-balanced avec Redis)
- Order Service (checkout workflow)

### Phase 4: Analytics
- Reporting Service (BI consolidé cross-canal)
- Performance optimization et load testing
- Documentation et formation équipes

## Validation

### Performance targets atteints
- API latency < 200ms p95 (moyenne 7.8ms)
- E-commerce checkout < 2s end-to-end  
- Dashboard load < 1s multi-service aggregation
- Throughput 1000+ concurrent users supported
- Availability 99.9% avec health checks

### Business value delivered
- **Omnichannel experience** : POS + E-commerce unifié
- **Scalability** : Ready pour croissance e-commerce
- **Team autonomy** : Développement indépendant per service
- **Technology diversity** : Optimal stack per bounded context
- **Production readiness** : Monitoring, alerting, resilience patterns

## Evolution future

### Kubernetes migration ready
- **Container-native** : Docker images per service
- **Health probes** : Liveness et readiness standardisés
- **Service mesh ready** : Istio integration potential
- **Auto-scaling** : HPA avec métriques Prometheus

### Event-driven evolution
- **Domain Events** : Async communication inter-services
- **Event Sourcing** : Pour audit et analytics
- **CQRS patterns** : Read/write optimization per service
- **Saga orchestration** : Distributed transactions management 