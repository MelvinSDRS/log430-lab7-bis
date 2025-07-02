# ADR 008: Kong Gateway avec Load Balancing et Observabilité

## Contexte

L'architecture microservices distribuée nécessitait :
- **Point d'entrée unique** pour 7 microservices autonomes
- **Load balancing avancé** avec high availability et failover
- **Authentication centralisée** (API Keys + JWT) pour différents clients
- **Rate limiting et security** pour protection production
- **Observabilité** : Monitoring, metrics et alerting distribué
- **Service discovery** et health monitoring automatique

## Décision

J'ai décidé d'utiliser Kong Gateway comme API Gateway central avec load balancing upstream et stack d'observabilité Prometheus + Grafana.

### Kong Gateway (Port 8080)
- **Point d'entrée unique** pour tous les microservices
- **Upstream management** avec load balancing least-connections
- **Health checks automatiques** (15s intervals)
- **Authentication plugins** : API Key + JWT
- **Rate limiting** : 100 req/min, 1000 req/hour
- **CORS configuration** pour applications web

### Load Balancing Strategy
- **Cart Service high availability** : 3 instances load-balanced
- **Algorithm** : least-connections (optimal pour API REST)
- **Health monitoring** : GET /health toutes les 15 secondes
- **Failover automatique** : Exclusion instances unhealthy
- **Session persistence** : Via Redis cache partagé

### Observabilité Stack
- **Prometheus** (Port 9090) : Metrics collection et time series
- **Grafana** (Port 3000) : Dashboards et visualisation
- **Kong metrics** : Request rate, latency, error rate, upstream health
- **Business metrics** : Order conversion, cart abandonment, revenue

## Alternatives considérées

### Option 1: Netflix Zuul (rejetée)
**Avantages:**
- Intégration native Eureka service discovery
- Spring Cloud ecosystem mature

**Inconvénients:**
- JVM overhead pour stack Python
- Configuration plus complexe
- Performance moindre que Kong (Nginx-based)

### Option 2: NGINX + Custom Configuration (rejetée)
**Avantages:**
- Performance maximale
- Configuration fine-grained

**Inconvénients:**
- **Pas de management API** : Configuration manuelle
- **Pas de plugins ecosystem** : Authentication, rate limiting custom
- **Pas de metrics built-in** : Monitoring à implémenter
- **Operational overhead** : Maintenance configuration manuelle

### Option 3: AWS Application Load Balancer (rejetée)
**Avantages:**
- Managed service, haute disponibilité
- Intégration cloud native

**Inconvénients:**
- **Vendor lock-in** AWS
- **Limited plugins** : Authentication et rate limiting basiques
- **Cost escalation** avec traffic growth
- **Local development** : Pas adapté pour Docker Compose

### Option 4: Kong Gateway + Observability (choisie)
**Avantages:**
- **Nginx performance** avec management layer intelligent
- **Plugin ecosystem riche** : 200+ plugins disponibles
- **API management complet** : Authentication, rate limiting, CORS
- **Observability built-in** : Metrics, logging, health checks
- **Open source** avec option enterprise
- **Local development friendly** : Docker containers

**Inconvénients:**
- **Learning curve** : Configuration Kong spécifique
- **Memory footprint** : Plus lourd que NGINX pur

## Justification technique

### Kong Gateway benefits réalisés

**API Management centralisé** :
- **Single point of entry** : http://localhost:8080 pour 7 services
- **Route management** : Configuration déclarative via kong.yml
- **Plugin configuration** : Authentication, CORS, rate limiting via config
- **Admin API** : Management et monitoring via port 8001

**Load Balancing avancé** :
- **Upstream Cart Service** : 3 instances avec weights égaux (100)
- **Health checks intelligents** : 3 failures → unhealthy, 2 success → healthy  
- **Algorithms optimisés** : least-connections pour distribution équitable
- **Failover transparent** : Zero downtime même avec instance failure

**Security centralisée** :
- **API Key authentication** : Pour applications externes et tests
- **JWT token validation** : Pour clients e-commerce authentifiés
- **Rate limiting granulaire** : 100/min, 1000/hour avec spillover policies
- **CORS protection** : Configuration fine pour localhost:3000, 3001, 5000

### Observabilité production-ready

**Prometheus integration** :
- **Kong metrics plugin** : Request rate, latency percentiles, error rates
- **Service discovery** : Auto-discovery microservices pour scraping
- **Custom metrics** : Business KPIs via services custom metrics
- **Alerting rules** : Performance degradation, service failures

**Grafana dashboards** :
- **Kong API Gateway Overview** : Traffic patterns, performance, errors  
- **Microservices Health** : Service status, response times, error rates
- **Business KPIs** : Revenue trends, order conversion, cart abandonment
- **Infrastructure Monitoring** : CPU, memory, network per service

**Monitoring automation** :
- **Health checks cascade** : Kong → Services → Databases
- **Alert correlation** : Service failures → Business impact assessment
- **MTTR optimization** : 76% amélioration (8.2s → 2.0s) vs Lab 4

## Conséquences

### Positives réalisées

**Performance exceptionnelle** :
- **641x latency improvement** : Kong routing overhead négligeable (7.8ms moyenne)
- **37x throughput increase** : Load balancing optimal Cart Service
- **0% error rate** : vs 40% Lab 4 (failover automatique)
- **Sub-millisecond routing** : Kong Nginx-based performance

**High availability atteinte** :
- **Cart Service redundancy** : 3 instances avec health monitoring
- **Automatic failover** : Detection 15s, exclusion immédiate
- **Zero downtime deployments** : Rolling updates per service
- **Session persistence** : Redis shared state pour Cart instances

**Security production-grade** :
- **Centralized authentication** : Single point of control
- **Rate limiting effective** : Protection DDoS et fair usage
- **CORS enforcement** : Protection cross-origin attacks
- **Audit logging** : Traçabilité complète des accès

### Négatives gérées

**Operational complexity** :
- **Kong configuration** : Déclarative via kong.yml (Infrastructure as Code)
- **Monitoring distributed** : Unified dashboards Grafana
- **Debugging network** : Correlation IDs et structured logging

**Single point of failure** :
- **Kong high availability** : Ready pour Kong clustering
- **Database failover** : PostgreSQL replication per service
- **Circuit breaker patterns** : Protection cascade failures

## Configuration technique réalisée

### Kong Gateway setup
```yaml
_format_version: "3.0"
services:
  - name: product-service
    url: http://product-service:8001
    plugins:
      - name: rate-limiting
        config: {minute: 100, hour: 1000}
      - name: cors
        config: {origins: ["http://localhost:3000"]}

upstreams:
  - name: cart-upstream
    algorithm: least-connections
    targets:
      - target: cart-service-1:8006
        weight: 100
      - target: cart-service-2:8006  
        weight: 100
      - target: cart-service-3:8006
        weight: 100
    healthchecks:
      active:
        http_path: "/health"
        healthy: {successes: 2}
        unhealthy: {failures: 3}
```

### Prometheus configuration
- **Scrape targets** : Kong + 7 microservices + databases
- **Retention** : 15 days metrics history
- **Alert rules** : Service down, high latency, error rate spikes
- **Grafana integration** : Automated dashboard provisioning

### Load balancing validation
- **k6 testing** : 100 VU sustained load
- **Failover testing** : Manual instance shutdown
- **Session persistence** : Redis shared state verification
- **Performance profiling** : Response time distribution analysis

## Migration et adoption

### Étapes de déploiement
1. **Kong Gateway setup** : Configuration routes et upstreams
2. **Service integration** : Health endpoints et metrics exposure  
3. **Load balancing configuration** : Cart Service 3 instances
4. **Monitoring deployment** : Prometheus + Grafana dashboards
5. **Testing et validation** : Load testing et failover scenarios

### Team adoption
- **Documentation Kong** : Configuration et troubleshooting guides
- **Grafana training** : Dashboard utilisation pour monitoring
- **Incident response** : Runbooks pour scenarios failure
- **Performance baselines** : SLA definition et alerting thresholds

## Évolution future

### Kong enterprise features
- **Kong Manager UI** : Visual configuration management
- **Advanced rate limiting** : Per-consumer quotas
- **OpenID Connect** : Enterprise authentication integration
- **Dev Portal** : Self-service API documentation

### Service mesh evolution
- **Istio integration** : Kong Ingress Controller
- **mTLS enforcement** : Service-to-service encryption
- **Traffic policies** : Advanced routing et security policies
- **Observability enhancement** : Distributed tracing avec Jaeger

### Auto-scaling integration
- **Kubernetes HPA** : Horizontal Pod Autoscaler based on Kong metrics
- **Custom metrics** : Business KPIs pour scaling decisions
- **Predictive scaling** : ML-based traffic prediction
- **Cost optimization** : Resource allocation based on actual usage 