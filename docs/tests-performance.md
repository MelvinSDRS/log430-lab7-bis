# Tests de Performance - Système POS 2-Tier

## Tests implémentés

### 1. Test des opérations de base

**Objectif** : Mesurer les temps de réponse des opérations CRUD fondamentales
- Recherche de produits par ID
- Recherche de produits par nom
- Recherche de produits par catégorie

**Métriques** :
- Temps de réponse moyen
- Temps de réponse médian  
- Temps de réponse maximum

### 2. Test des 3 caisses simultanées

**Objectif** : Valider l'exigence clé du laboratoire (3 caisses travaillant simultanément)
- Simulation de ventes concurrentes sur 3 caisses
- Validation de la cohérence des transactions
- Test de la gestion des stocks en concurrent

**Métriques** :
- Throughput global (ventes/seconde)
- Nombre de ventes réussies vs erreurs
- Temps de traitement par vente
- Performance par caisse

### 3. Test de charge recherches

**Objectif** : Évaluer la capacité du système sous contrainte
- Recherches simultanées depuis plusieurs threads
- Différents types de requêtes (ID, nom, catégorie)
- Simulation de charge réaliste

**Métriques** :
- Throughput de recherche (requêtes/seconde)
- Dégradation des performances sous charge
- Stabilité du système

## Architecture testée

Les tests valident spécifiquement l'architecture 2-tier :
- **Client** : Application console avec sessions SQLAlchemy multiples
- **Serveur** : Base de données PostgreSQL avec transactions ACID

## Exécution

```bash
# Tests complets avec Docker
docker compose exec pos-app-1 python tests/test_performance.py

# Ou directement via le profil test
docker compose --profile test up pos-test
```