# ADR-009: Pattern Saga Orchestrée Synchrone

## Statut
Accepté

## Contexte
Nécessité de coordonner des transactions distribuées entre 4 microservices (Cart, Inventory, Payment, Order) avec garanties de cohérence forte pour le processus de commande e-commerce.

Le système doit assurer :
- Cohérence des données à travers les services
- Compensation automatique en cas d'échec
- Observabilité complète des transactions
- Gestion des timeouts et pannes partielles

## Décision
Implémentation d'une saga orchestrée synchrone avec un orchestrateur central (Saga Orchestrator Service).

### Choix d'architecture
- **Synchrone vs Asynchrone** : Communication synchrone HTTP REST
- **Orchestré vs Chorégraphié** : Pattern orchestration avec contrôle centralisé
- **État saga** : Machine d'état explicite avec persistance in-memory
- **Compensation** : Backward recovery avec actions inverses séquentielles

## Rationale

### Avantages du pattern orchestré synchrone
1. **Simplicité d'implémentation** : Logique centralisée dans l'orchestrateur
2. **Debugging facilité** : Visibilité complète de l'état de la transaction
3. **Contrôle centralisé** : Gestion explicite des timeouts et erreurs
4. **Observabilité** : Métriques centralisées et traçabilité end-to-end
5. **Compensation déterministe** : Actions de rollback prédictibles

### Alternatives considérées

#### Pattern Saga Chorégraphié
- **Rejeté** : Complexité de debugging et observabilité distribuée
- **Risque** : Difficile de maintenir la cohérence globale

#### Pattern Saga Asynchrone avec événements
- **Rejeté** : Complexité additionnelle pour un cas d'usage simple
- **Overkill** : Communication synchrone suffisante pour les latences requises

## Conséquences

### Positives
- **Contrôle centralisé** des transactions distribuées
- **Simplicité de debugging** et monitoring
- **Compensation automatique** avec garanties ACID distribuées
- **État explicite** : Machine d'état claire et observable
- **Métriques détaillées** : Observabilité Prometheus intégrée

### Négatives
- **Point de défaillance unique** : L'orchestrateur devient critique
- **Couplage temporel** : Services doivent être disponibles synchroniquement
- **Latence** : Communication séquentielle plus lente que parallèle
- **Scalabilité** : État in-memory limite la scalabilité horizontale

### Mitigations
- **High availability** : Health checks et restart automatique
- **Timeouts configurables** : Éviter les blocages
- **Circuit breaker** : Isolation des pannes de services
- **Monitoring** : Alertes sur performance et disponibilité
