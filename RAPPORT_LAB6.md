# Rapport Lab 6
## LOG430 - Architecture Logicielle

## 1. Scénario métier et saga implémentée

### Contexte
Système de commerce électronique multi-magasins avec traitement de commandes distribuées nécessitant une coordination entre 4 microservices : Cart, Inventory, Payment et Order.

### Saga de commande e-commerce
L'objectif est d'orchestrer une transaction distribuée pour le processus de commande client avec garantie de cohérence et compensation automatique en cas d'échec.

**Étapes de la saga**:
1. **Validation du panier** (Cart Service)
   - Validation des articles et calcul des totaux
   - Vérification de la disponibilité du panier

2. **Réservation de stock** (Inventory Service)
   - Réservation temporaire (10 min) des articles
   - Vérification de la disponibilité par magasin

3. **Traitement du paiement** (Payment Service)
   - Autorisation et capture du paiement
   - Génération de l'ID de transaction

4. **Confirmation de commande** (Order Service)
   - Création de la commande finale
   - Conversion de la réservation en vente

## 2. Machine d'état de la saga

### Diagramme d'état PlantUML
![Diagramme de la machine d'état](/docs/uml/images/saga-state-machine.png)

### États principaux
- PENDING → CART_VALIDATED → STOCK_RESERVED → PAYMENT_PROCESSED → ORDER_CONFIRMED → COMPLETED

### États d'échec
- **CART_VALIDATION_FAILED** (échec immédiat)
- **STOCK_RESERVATION_FAILED** (échec avec compensation mineure)
- **PAYMENT_FAILED** (compensation stock)

### États de compensation
- COMPENSATING_STOCK → COMPENSATED → FAILED
- COMPENSATING_PAYMENT → COMPENSATED → FAILED

## 3. Décisions d'architecture (ADR)

### ADR-001: Pattern Saga Orchestrée Synchrone

**Contexte**:
Nécessité de coordonner des transactions distribuées entre 4 microservices avec garanties de cohérence forte.

**Décision**:
Implémentation d'une saga orchestrée synchrone avec un orchestrateur central.

**Rationale**:
- **Synchrone vs Asynchrone**: Simplicité d'implémentation et de debugging
- **Orchestré vs Chorégraphié**: Contrôle centralisé et visibilité globale
- **Timeout et compensation**: Gestion explicite des échecs

**Conséquences**:
- Contrôle centralisé des transactions
- Simplicité de debugging et monitoring
- Compensation automatique
- Point de défaillance unique (orchestrateur)
- Couplage temporel entre services

### ADR-002: Communication via API Gateway Kong

**Contexte**:
L'orchestrateur doit communiquer avec les microservices de manière sécurisée et avec load balancing.

**Décision**:
Utilisation de Kong API Gateway pour toutes les communications inter-services.

**Rationale**:
- **Sécurité**: API Keys et authentification centralisée
- **Load Balancing**: Distribution automatique (3 instances Cart Service)
- **Observabilité**: Métriques centralisées
- **Évolutivité**: Ajout/suppression de services transparent

**Conséquences**:
- Sécurité renforcée
- Load balancing automatique
- Monitoring centralisé
- Latence additionnelle
- Point de défaillance (Gateway)

## 4. Mécanismes de compensation

### Stratégie de compensation
**Pattern**: Backward Recovery avec compensation séquentielle inversée

### Actions de compensation par étape

| Étape échouée | Actions de compensation |
|---------------|------------------------|
| PAYMENT_FAILED | 1. Libérer les réservations de stock |
| ORDER_CONFIRMATION_FAILED | 1. Rembourser le paiement<br>2. Libérer les réservations de stock |

### Garanties de compensation
- **Idempotence**: Chaque action de compensation peut être rejouée
- **Timeout**: 30 secondes maximum par action
- **Retry**: 3 tentatives avec backoff exponentiel
- **Observabilité**: Métriques Prometheus pour chaque compensation

## 5. Monitoring et observabilité

### Métriques Prometheus implémentées

#### Métriques principales
```python
saga_requests_total = Counter('saga_requests_total', ['customer_id', 'status'])
saga_duration_seconds = Histogram('saga_duration_seconds', ['status', 'customer_id'])
saga_errors_total = Counter('saga_errors_total', ['step_type', 'error_type'])
compensation_total = Counter('saga_compensation_total', ['step_type', 'reason'])
```

#### Endpoints de métriques
- **Saga Orchestrator**: `http://localhost:8008/metrics`
- **Prometheus**: `http://localhost:9090`
- **Grafana**: `http://localhost:3000`

### Dashboard Grafana

![Grafana](/docs/uml/images/grafana.png)
