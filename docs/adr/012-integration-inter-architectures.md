# ADR-012 : Intégration Lab 6 ↔ Lab 7 avec service de pont

## Statut
Accepté

## Contexte
Besoin de relier les réclamations du Lab 7 aux commandes/clients du Lab 6 pour un réalisme métier, tout en préservant l'indépendance pédagogique des deux architectures.

Dans un système réel, les réclamations clients sont naturellement liées aux commandes passées. Cette intégration permet de :
- **Contextualiser** les réclamations avec l'historique de commande
- **Enrichir** les notifications avec des détails pertinents
- **Tracer** le parcours client de la commande à la résolution
- **Analyser** les corrélations entre types de commandes et réclamations

## Options considérées

### 1. Fusion des architectures
**Description :** Migrer les services Lab 6 vers l'architecture événementielle Lab 7

**Avantages :**
- Architecture unifiée
- Cohérence technique
- Simplicité de maintenance

**Inconvénients :**
- Perte de la valeur pédagogique comparative
- Complexité de migration énorme
- Risque de régression
- Objectifs labs distincts compromis

### 2. Base de données partagée
**Description :** Accès direct aux données Lab 6 depuis Lab 7

**Avantages :**
- Simplicité d'accès aux données
- Performance optimale
- Pas de réseau entre architectures

**Inconvénients :**
- Couplage fort des données
- Violation des principes microservices
- Difficultés de versioning
- Risque de corruption de données

### 3. Service d'intégration
**Description :** Pont API entre les deux labs avec mode dégradé

**Avantages :**
- Préservation de l'indépendance
- Découplage architectural
- Flexibilité d'évolution
- Réalisme enterprise

**Inconvénients :**
- Complexité additionnelle
- Gestion des modes dégradés
- Latence réseau
- Point de défaillance potentiel

### 4. Événements inter-architectures
**Description :** Bus d'événements global entre Lab 6 et Lab 7

**Avantages :**
- Découplage maximal
- Extensibilité future
- Cohérence avec Lab 7

**Inconvénients :**
- Complexité de synchronisation
- Gestion de la cohérence éventuelle
- Risque de désynchronisation
- Overhead événementiel

## Décision

**Service d'intégration (Integration Service)** est choisi avec :

### Architecture d'intégration
```
┌─────────────────┐                    ┌─────────────────┐
│   Lab 6 (POS)   │                    │Lab 7 (Claims)   │
│                 │                    │                 │
│  Order Service  │◄───────────────────┤Integration Svc  │
│Customer Service │    API Calls       │  (Port 8107)    │
│                 │  (read-only)       │                 │
└─────────────────┘                    └─────────────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │ Claims Service  │
                                       │  + Event Bus    │
                                       └─────────────────┘
```

### Modes de fonctionnement

#### Mode intégré (Lab 6 disponible)
- Récupération des détails de commande/client en temps réel
- Enrichissement automatique des réclamations
- Notifications avec contexte complet
- Analytics cross-architecture

#### Mode dégradé (Lab 6 indisponible)
- Données simulées pour maintenir le service
- Graceful degradation sans interruption
- Préservation des fonctionnalités core Lab 7
- Logging des tentatives d'intégration

## Justification de la décision

### Critères décisionnels
1. **Indépendance pédagogique** : Architectures restent autonomes
2. **Réalisme métier** : Réclamations contextualisées
3. **Flexibilité** : Évolution indépendante possible
4. **Résilience** : Fonctionnement sans dépendance critique
5. **Complexité maîtrisée** : Implémentation progressive

### Avantages de l'approche
- **Réalisme métier accru** avec réclamations contextualisées
- **Démonstration de patterns** d'intégration enterprise
- **Préservation de l'indépendance** architecturale
- **Base pour futures extensions** cross-architecture
- **Pédagogie enrichie** avec cas d'usage réels

## Conséquences

### Positives
- **Valeur business** : Réclamations liées aux commandes
- **Patterns enterprise** : Démonstration d'intégration réelle
- **Flexibilité** : Fonctionnement avec ou sans Lab 6
- **Extensibilité** : Base pour futures intégrations
- **Résilience** : Mode dégradé automatique

### Négatives
- **Complexité additionnelle** : Gestion des modes dégradés
- **Latence réseau** : Appels API synchrones
- **Dépendance optionnelle** : Gestion des timeouts
- **Monitoring complexe** : Observabilité cross-architecture

### Mitigation des risques
- **Timeouts configurables** : Éviter les blocages
- **Circuit breaker** : Protection contre les pannes
- **Fallback data** : Données simulées en mode dégradé
- **Monitoring dédié** : Métriques d'intégration
