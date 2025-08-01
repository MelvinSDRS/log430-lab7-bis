# ADR-013: Adoption du Pattern Saga Chorégraphiée

## Statut
Accepté

## Contexte
Dans le cadre du Lab 7 bis, nous devons implémenter une saga chorégraphiée pour gérer les transactions distribuées de remboursement, en complément de la saga orchestrée du Lab 6. Cette implémentation doit démontrer les différences entre les deux approches et leurs cas d'usage respectifs.

Le processus de remboursement implique :
1. Validation de la réclamation résolue
2. Calcul du montant de remboursement
3. Ajustement du stock (remise en inventaire)
4. Notification du client

## Décision
Nous adoptons le pattern de saga chorégraphiée pour le processus de remboursement, utilisant l'architecture événementielle existante du Lab 7.

### Architecture Choisie
- **Pas d'orchestrateur central** : Chaque service réagit aux événements et publie ses propres événements
- **Communication via Redis Streams** : Utilisation de l'infrastructure événementielle existante
- **Event Sourcing** : Persistance de tous les événements dans MongoDB
- **Idempotence** : Gestion des duplicatas via correlation_id
- **Compensation** : Mécanismes automatiques de rollback

### Flux d'Événements
```
Claims Service → SagaRemboursementDemarree
  ↓
Refund Payment Service → RemboursementCalcule
  ↓
Refund Inventory Service → StockMisAJour
  ↓
Notification Service → SagaRemboursementTerminee
```

## Conséquences

### Avantages
- **Découplage fort** : Pas de point de défaillance unique
- **Évolutivité** : Facilité d'ajout de nouvelles étapes
- **Résilience** : Chaque service peut traiter les échecs indépendamment
- **Performance** : Traitement parallèle possible pour certaines étapes
- **Cohérence avec l'architecture** : Utilise l'Event Sourcing existant

### Inconvénients
- **Complexité de débogage** : Flux distribué plus difficile à tracer
- **Visibilité limitée** : Pas de vue centralisée de l'état de la saga
- **Gestion des timeouts** : Plus complexe sans orchestrateur central
- **Cohérence éventuelle** : Possibilité d'états transitoires incohérents

## Comparaison avec la Saga Orchestrée (Lab 6)

| Aspect | Saga Orchestrée | Saga Chorégraphiée |
|--------|-----------------|-------------------|
| **Coordination** | Centralisée | Distribuée |
| **Visibilité** | Complète | Partielle |
| **Découplage** | Moyen | Fort |
| **Complexité** | Logique centralisée | Logique distribuée |
| **Résilience** | Point unique de défaillance | Résilience distribuée |
| **Performance** | Séquentiel | Potentiellement parallèle |
| **Debugging** | Plus facile | Plus difficile |

## Implémentation Technique

### Services Impliqués
1. **Claims Service** : Déclencheur de la saga
2. **Refund Payment Service** : Calcul des remboursements
3. **Refund Inventory Service** : Gestion des ajustements de stock
4. **Notification Service** : Notifications client et fin de saga

### Événements Définis
- **SagaRemboursementDemarree** : Initiation de la saga
- **RemboursementCalcule** : Montant calculé
- **StockMisAJour** : Inventaire ajusté
- **SagaRemboursementTerminee** : Saga complétée
- **SagaRemboursementEchouee** : Échec de la saga

### Mécanismes de Compensation
- **Idempotence** : Utilisation de correlation_id pour éviter les duplicatas
- **Timeout** : Gestion des services non répondants
- **Rollback** : Événements de compensation automatiques
- **Monitoring** : Métriques Prometheus pour observabilité

## Cas d'Usage Recommandés

### Saga Chorégraphiée (Ce Lab)
- Processus avec peu d'étapes (2-4)
- Services fortement découplés
- Logique métier simple
- Performance critique
- Résilience prioritaire

### Saga Orchestrée (Lab 6)
- Processus complexes avec nombreuses étapes
- Besoins de coordination sophistiquée
- Logique métier complexe
- Visibilité et debugging importants
- Contrôle centralisé requis

## Alternatives Considérées

### 1. Réutilisation de la Saga Orchestrée
**Rejeté** : Ne démontre pas les différences entre les approches

### 2. Saga Chorégraphiée avec Event Sourcing Complet
**Rejeté** : Complexité excessive pour la démonstration

### 3. Saga Hybride
**Rejeté** : Complexité architecturale non justifiée

## Métriques de Succès
- Temps de traitement des remboursements < 5 secondes
- Taux de succès des sagas > 95%
- Idempotence vérifiée sur 100% des cas
- Compensation automatique en cas d'échec
- Observabilité complète via Grafana

## Révision
Cette décision sera révisée après les tests de charge et l'évaluation des performances comparatives entre les deux approches de saga.