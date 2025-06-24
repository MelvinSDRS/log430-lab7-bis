# Analyse préalable - Étape 1
## Test de charge avec endpoints complexes et observabilité de base

**Date de l'analyse :** 23 juin 2025
**Environnement :** Docker compose

### Contexte

Cette analyse présente les résultats du test de charge sur les endpoints complexes de l'API POS multi-magasins, réalisé dans le cadre de l'étape 1 du laboratoire 4. L'objectif est d'établir une baseline de performance avec des endpoints réalistes avant les optimisations (load balancer et cache Redis).

### Configuration du test

#### Outils utilisés
- **k6** : Outil de test de charge
- **Prometheus** : Collecte de métriques
- **Grafana** : Visualisation et dashboards
- **Logging** : Traçabilité des requêtes

#### Scénarios de test

**Test baseline endpoints complexes**
- Montée progressive : 3 → 8 → 15 → 8 → 0 utilisateurs virtuels
- Durée : 3m30s (+ 30s graceful stop)
- Endpoints testés : `/api/v1/stores/performances`, `/api/v1/reports/dashboard`
- Complexité : Agrégations multi-magasins, calculs de CA, indicateurs de performance
- Fréquence : 1 itération toutes les 6-8 secondes par utilisateur

**Pertinence des endpoints choisis :**
Ces endpoints permettent d'évaluer l'impact des optimisations sur des charges métier réelles :
- **Charge faible (15 VUs)** : Simule un usage bureautique standard
- **Charge élevée (100+ VUs)** : Simule des pics d'activité (fin de journée, reporting)
- **Complexité CPU** : 30+ requêtes SQL par appel révèlent les goulots d'étranglement

### Résultats du test baseline

#### **1. Latence**
| Métrique | Valeur | Seuil | Statut |
|----------|--------|--------|--------|
| Temps moyen | **1972.71 ms** | < 3000ms | BON |
| Médiane (P50) | **1024.22 ms** | < 2000ms | BON |
| **P95** | **6369.75 ms** | < 6000ms | LIMITE |
| Maximum | **8389.97 ms** | < 10000ms | BON |

#### **2. Trafic**
| Métrique | Valeur | Statut |
|----------|--------|--------|
| **Requêtes totales** | **405** | OK |
| **RPS moyen** | **1.84 req/sec** | STABLE |
| Durée du test | 216 secondes | OK |
| Iterations | 135 | OK |

#### **3. Erreurs**
| Métrique | Valeur | Seuil | Statut |
|----------|--------|--------|--------|
| **Taux d'erreur** | **0.00%** | < 5% | PARFAIT |
| Requêtes échouées | **0** | Minimum | PARFAIT |
| Requêtes réussies | **405** | Maximum | OK |

#### **4. Complexité des endpoints**

**Endpoint `/stores/performances`:**
- Temps moyen : ~1000ms
- Opérations : Calculs CA, stocks, tendances pour 5 magasins
- Requêtes SQL : 6+ par magasin (30+ requêtes totales)

**Endpoint `/reports/dashboard`:**
- Temps moyen : ~800ms
- Opérations : Agrégation indicateurs multi-magasins
- Complexité : Jointures et calculs statistiques

### Observabilité implémentée

#### **Logging**
- Format JSON avec trace IDs
- Métriques par requête (durée, status, taille)
- Traçabilité complète des requêtes
- Rotation automatique des logs

#### **Métriques Prometheus**
- 4 Golden Signals exposés
- Métriques système (CPU, RAM)
- Métriques applicatives
- Health checks automatiques

#### **Dashboards Grafana**
- Dashboard personnalisé pour les Golden Signals
- Visualisation temps réel
- Alertes configurées

### Baseline de performance

| **Golden signal** | **Valeur baseline** | **Seuil acceptable** | **Analyse** |
|-------------------|---------------------|----------------------|-------------|
| **Latence P95** | 6369.75 ms | < 6000 ms | À la limite (endpoints très complexes) |
| **Trafic RPS** | 1.84 req/sec | Variable | Baseline établie |
| **Erreurs** | 0.00% | < 5% | Parfait |
| **Latence Moyenne** | 1972.71 ms | < 3000 ms | Bon |

### Prochaines étapes et contexte d'optimisation

**Optimisations à tester :**
1. **Load balancing** : Efficacité variable selon la charge (overhead à 15 VUs, indispensable à 100+ VUs)
2. **Cache Redis** : Impact majeur constant attendu indépendamment de la charge

**Stratégie d'évaluation :**
- **Tests charge faible** : Validation overhead et compromis performance/résilience
- **Tests charge élevée** : Validation scalabilité et points de rupture
- **Endpoints complexes** : Révélation des vrais goulots d'étranglement

### Contexte technique

**Complexité justifiée des temps de réponse :**
- Endpoint `stores/performances` : 5 magasins × 6 requêtes = 30+ opérations SQL
- Calculs d'agrégation en temps réel (CA, stocks, tendances)
- Aucune mise en cache = recalcul complet à chaque requête
- Base de référence pour mesurer l'impact des optimisations selon la charge

**Pertinence pour l'évaluation d'architecture :**
Ces endpoints permettent de comprendre pourquoi l'efficacité du load balancer dépend de la charge : sous-utilisation à faible charge vs distribution optimale à forte charge.
