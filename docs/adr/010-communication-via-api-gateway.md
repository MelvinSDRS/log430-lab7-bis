# ADR-010: Communication via API Gateway Kong pour Saga Orchestration

## Statut
Accepté

## Contexte
L'orchestrateur saga doit communiquer avec 4 microservices (Cart, Inventory, Payment, Order) de manière sécurisée, avec load balancing et observabilité complète.

Contraintes :
- Sécurité : Authentification et autorisation centralisées
- Performance : Load balancing automatique (3 instances Cart Service)
- Observabilité : Métriques centralisées pour transactions saga
- Évolutivité : Ajout/suppression de services transparent

## Décision
Utilisation de Kong API Gateway pour toutes les communications entre le Saga Orchestrator et les microservices participants.

### Architecture de communication
```
Saga Orchestrator → Kong Gateway → Microservices
                      ↓
                 Load Balancing
                 Authentication
                 Metrics Collection
```

## Rationale

### Avantages Kong Gateway pour saga
1. **Sécurité centralisée** : API Keys et JWT gérés au niveau gateway
2. **Load balancing automatique** : Distribution intelligente (3 instances Cart)
3. **Observabilité unifiée** : Métriques Kong + métriques saga
4. **Routing intelligent** : Gestion des versions et déploiements
5. **Circuit breaker** : Isolation des pannes de services

### Alternatives considérées

#### Communication directe service-to-service
- **Rejeté** : Complexité de sécurité et load balancing
- **Problème** : Observabilité fragmentée

#### Service mesh (Istio)
- **Rejeté** : Complexité excessive pour le contexte Lab
- **Overkill** : Kong Gateway suffisant pour les besoins

#### Load balancer simple (NGINX)
- **Rejeté** : Manque de fonctionnalités API Gateway
- **Limitation** : Pas d'authentification intégrée

## Conséquences

### Positives
- **Sécurité renforcée** : Authentification centralisée et audit trails
- **Load balancing automatique** : Distribution optimale de charge
- **Monitoring centralisé** : Métriques Kong + Prometheus
- **Évolutivité transparente** : Ajout de services sans changement code
- **Debugging facilité** : Logs centralisés des communications saga

### Négatives
- **Latence additionnelle** : +15-25ms par requête via gateway
- **Point de défaillance** : Kong Gateway devient critique
- **Complexité infrastructure** : Configuration et maintenance Kong
- **Coupling** : Dépendance à Kong pour toutes communications

### Mitigations
- **High availability Kong** : Déploiement multi-instance avec health checks
- **Circuit breaker** : Timeouts configurables et fallback
- **Monitoring Kong** : Métriques détaillées et alertes
- **Fallback direct** : Communication directe en cas d'urgence
