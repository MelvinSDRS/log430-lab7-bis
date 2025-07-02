# Choix Technologiques - Architecture Microservices

## Évolution architecturale (Lab 1 → Lab 5)

### Lab 1-3 : Architecture monolithique
- **Python + Flask** : Application monolithique
- **PostgreSQL unique** : Base de données centralisée
- **Interface web MVC** : Supervision simple
- **API REST Flask-RESTX** : Extension Lab 3

### Lab 5 : Architecture microservices distribuée
- **7 microservices indépendants** : Product, Customer, Cart, Order, Inventory, Sales, Reporting
- **Kong API Gateway** : Point d'entrée unique avec load balancing
- **Database per Service** : 7 PostgreSQL + 1 Redis isolés
- **Docker orchestration** : Déploiement containerisé avancé
- **Observabilité stack** : Prometheus + Grafana

## API Gateway

**Choix : Kong Gateway** (nouveau Lab 5)

Justification :
- **Point d'entrée unique** : Centralisation de toutes les API calls
- **Load balancing avancé** : Support multiple instances avec failover automatique
- **Authentication robuste** : API Key + JWT pour différents types clients
- **Rate limiting** : Protection DDoS et fair usage (100/min, 1000/hour)
- **Health monitoring** : Circuit breaker et detection pannes automatique
- **Plugin ecosystem** : CORS, logging, metrics, transformations
- **Performance** : Nginx-based, optimisé pour haute charge
- **Standards** : OpenAPI/Swagger documentation intégrée

### Configuration Kong Lab 5
- **Port d'écoute** : 8080 (point d'entrée unique)
- **Upstreams** : Load balancing Cart Service (3 instances)
- **Algorithme** : least-connections pour distribution optimale
- **Health checks** : GET /health toutes les 15 secondes
- **Failover** : Exclusion automatique instances unhealthy
- **CORS** : Configuration pour applications web (localhost:3000, 3001, 5000)

## Microservices

**Choix : Flask per service** (évolution Lab 5)

Justification :
- **Simplicité** : Framework léger et adapté microservices
- **Autonomie** : Chaque service peut évoluer indépendamment
- **Performance** : Overhead minimal per service
- **Écosystème** : Compatible avec stack existante Python
- **Developer experience** : Courbe d'apprentissage réduite
- **Testing** : Isolation complète pour tests unitaires

### Stack par microservice
- **Python 3.11+** : Langage principal maintenu
- **Flask** : Framework web léger
- **SQLAlchemy** : ORM pour services avec PostgreSQL
- **Redis client** : Pour Cart Service (cache distribué)
- **Requests** : Communication HTTP inter-services
- **Health checks** : Endpoint `/health` standardisé

## Persistance microservices

**Choix : Database per Service pattern**

Justification :
- **Isolation des données** : Aucun accès direct cross-database
- **Autonomie des équipes** : Schema evolution indépendante
- **Scalabilité** : Optimisation per service
- **Fault tolerance** : Panne d'un service n'affecte pas les autres
- **Technology diversity** : Choix optimal per bounded context

### Databases par service
- **Product Service** : PostgreSQL (product_db) - CRUD performant
- **Customer Service** : PostgreSQL (customer_db) - Relations complexes
- **Inventory Service** : PostgreSQL (inventory_db) - Transactions ACID
- **Sales Service** : PostgreSQL (sales_db) - Historique ventes
- **Reporting Service** : PostgreSQL (reporting_db) - Analytics
- **Order Service** : PostgreSQL (order_db) - Workflow commandes
- **Cart Service** : Redis (cart_cache) - Session state haute performance

**Ports dédiés per database :**
- Product DB : 5433
- Customer DB : 5434
- Inventory DB : 5435
- Sales DB : 5436
- Reporting DB : 5437
- Order DB : 5438
- Cart Cache : 6380

## Cache distribué

**Choix : Redis pour Cart Service** (nouveau Lab 5)

Justification :
- **Performance** : Accès sub-millisecond pour session state
- **Shared state** : 3 instances Cart Service partagent même cache
- **Expiration automatique** : TTL pour nettoyage sessions
- **Data structures** : Hash maps optimales pour panier
- **Persistence** : Append-only file pour recovery
- **Memory management** : LRU eviction policy (512MB max)

### Configuration Redis avancée
- **Password protection** : `cart-cache-secret-2025`
- **Persistence** : AOF + RDB snapshots
- **Memory policy** : allkeys-lru pour éviction automatique
- **TCP keepalive** : 300s pour connexions persistantes
- **Max memory** : 512MB avec politique LRU

## Load Balancing

**Choix : Kong Upstream avec least-connections** (nouveau Lab 5)

Justification :
- **Distribution optimale** : Based on active connections count
- **High availability** : 3 instances Cart Service actives
- **Health monitoring** : Détection pannes automatique
- **Session stickiness** : Via Redis shared state
- **Zero downtime** : Failover transparent
- **Auto scaling ready** : Ajout/suppression instances dynamique

### Stratégie de load balancing
- **Algorithm** : least-connections (optimal pour API REST)
- **Health checks** : HTTP GET /health every 15s
- **Failure detection** : 3 consecutive failures → unhealthy
- **Recovery detection** : 2 consecutive success → healthy
- **Weight distribution** : Equal weight (100) per instance

## Observabilité et monitoring

**Choix : Prometheus + Grafana stack** (nouveau Lab 5)

Justification :
- **Industry standard** : Solutions éprouvées microservices
- **Multi-dimensional metrics** : Labels pour segmentation fine
- **Time series DB** : Optimisé pour métriques temporelles
- **Alerting** : AlertManager pour notifications proactives
- **Visualization** : Dashboards Grafana interactifs
- **Service discovery** : Auto-discovery services via Kong

### Métriques collectées
- **Kong Gateway** : Request rate, latency, error rate, upstream health
- **Microservices** : Response time, throughput, error count, health status
- **Business metrics** : Order conversion, cart abandonment, revenue
- **Infrastructure** : CPU, memory, disk, network per service

### Dashboards Grafana
- **Kong API Gateway Overview** : Traffic patterns, performance, errors
- **Microservices Health** : Service status, response times, error rates
- **Business KPIs** : Revenue trends, order metrics, customer activity
- **Infrastructure Monitoring** : Resource utilization, capacity planning

## Communication inter-services

**Choix : HTTP REST synchrone** (Lab 5)

Justification :
- **Simplicité** : Standard web bien maîtrisé
- **Debugging** : Facilité de troubleshooting
- **Tooling** : Support outillage existant (Postman, curl, etc.)
- **Standards** : RESTful APIs avec conventions claires
- **Error handling** : HTTP status codes standardisés
- **Documentation** : OpenAPI/Swagger automatique

### Patterns de communication
- **External clients → Kong Gateway** : HTTPS avec API Key/JWT
- **Kong → Microservices** : HTTP avec load balancing
- **Service-to-service** : HTTP direct pour performance
- **Shared state** : Redis pour Cart Service instances
- **Event-driven** : Future évolution pour consistency patterns

## Sécurité microservices

**Choix : Kong centralized authentication**

Justification :
- **Single point of control** : Gestion auth centralisée
- **Multiple auth methods** : API Key pour APIs, JWT pour clients
- **Rate limiting** : Protection DDoS et fair usage
- **CORS configuration** : Protection cross-origin attacks
- **Audit logging** : Traçabilité complète des accès

### Stratégie de sécurité
- **API Keys** : Pour applications externes et tests automatisés
- **JWT tokens** : Pour authentification clients e-commerce
- **HTTPS termination** : SSL/TLS au niveau Kong Gateway
- **Network isolation** : Services backend non exposés directement
- **Database security** : Credentials uniques per service

## Containerisation et orchestration

**Choix : Docker + Docker Compose** (évolué Lab 5)

Justification :
- **Isolation** : Containers indépendants per service
- **Portabilité** : Environnements consistents dev → prod
- **Resource management** : Allocation CPU/memory per service
- **Service discovery** : Docker networks pour communication
- **Health checks** : Monitoring intégré container-level
- **Scalability** : Ready pour Kubernetes migration

### Architecture container Lab 5
- **7 microservices** : Un container per service
- **7 PostgreSQL** : Databases isolées per service
- **1 Redis** : Cache partagé Cart Service
- **Kong Gateway** : Container API gateway
- **Prometheus + Grafana** : Monitoring stack
- **Networks** : microservices-network isolé

### Ressources par container
- **Microservices** : 512MB RAM, 0.5 CPU per service
- **Databases** : 1GB RAM, 1 CPU per PostgreSQL
- **Redis** : 512MB RAM (configured), 0.25 CPU
- **Kong** : 1GB RAM, 1 CPU pour handling traffic
- **Monitoring** : 2GB RAM total pour Prometheus + Grafana

## Tests et qualité

**Choix : Strategy microservices testing**

### Pyramid testing microservices
- **Unit tests** : Per service business logic (70%)
- **Integration tests** : Database + API endpoints (20%)
- **Contract tests** : API compatibility entre services (5%)
- **End-to-end tests** : User journeys via Kong Gateway (5%)

### Tools de testing
- **pytest** : Framework testing Python maintenu
- **requests** : HTTP client pour integration tests
- **testcontainers** : Database testing avec containers
- **k6** : Load testing pour performance validation
- **Postman/Newman** : API contract testing

### Continuous testing
- **Service-level CI** : Tests automatisés per service
- **Contract validation** : API compatibility checks
- **Performance regression** : SLA validation automated
- **Security scanning** : Vulnerability assessment containers

## Performance et scalabilité

### Optimisations microservices
- **Database indexing** : Index optimisés per service workload
- **Connection pooling** : Réutilisation connexions database
- **Response caching** : Kong-level caching pour GET requests
- **Compression** : Gzip pour réduire network overhead
- **Async processing** : Background jobs pour reports

### Scaling strategies
- **Horizontal scaling** : Multiple instances per service
- **Load balancing** : Kong upstream management
- **Database read replicas** : Pour services read-heavy
- **Cache scaling** : Redis cluster pour Cart Service
- **CDN ready** : Static assets optimization

### Performance targets Lab 5
- **API latency** : < 200ms p95 single service calls
- **E-commerce checkout** : < 2s end-to-end process
- **Dashboard loading** : < 1s multi-service aggregation
- **Throughput** : 1000+ concurrent users supported
- **Availability** : 99.9% uptime avec health checks

## DevOps et CI/CD

### Deployment strategy
- **Independent deployment** : Per service release cycles
- **Blue-green deployment** : Zero-downtime updates
- **Canary releases** : Gradual rollout risk mitigation
- **Rollback capability** : Quick revert per service
- **Health checks** : Automated deployment validation

### Infrastructure as Code
- **Docker Compose** : Local development + testing
- **Environment config** : Variables per service/environment
- **Secret management** : Secure credential handling
- **Backup automation** : Database backup strategies
- **Log aggregation** : Centralized logging solution

## Migration path et évolutivité

### Kubernetes readiness
- **Microservices** : Container-ready pour K8s migration
- **Service mesh** : Istio integration potential
- **Auto-scaling** : HPA ready avec métriques Prometheus
- **Service discovery** : K8s native service discovery
- **Ingress controller** : Kong Ingress Controller available

### Cloud-native features
- **12-factor app** : Microservices suivent best practices
- **Stateless design** : Shared state via Redis external
- **Configuration externalization** : Environment-based config
- **Health endpoints** : Kubernetes health probes ready
- **Graceful shutdown** : SIGTERM handling per service

## Conclusion

L'architecture microservices Lab 5 avec Kong Gateway représente une évolution mature vers un système cloud-native, scalable et résilient, prêt pour production e-commerce avec support legacy POS intégré. 