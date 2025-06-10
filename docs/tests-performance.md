# Tests de Performance - Système POS Multi-Magasins Console + Web

## Tests implémentés

### 1. Test des opérations de base multi-magasins

**Objectif** : Mesurer les temps de réponse des opérations dans un environnement multi-magasins
- Recherche de produits par ID dans différentes entités
- Consultation des stocks par entité (magasin vs centre logistique)
- Recherche de produits par nom et catégorie avec filtrage par entité

**Métriques** :
- Temps de réponse moyen par type d'entité
- Temps de réponse médian pour les requêtes inter-entités
- Temps de réponse maximum pour les rapports consolidés

### 2. Test de charge multi-magasins (5 magasins simultanés)

**Objectif** : Valider l'exigence clé du Lab 2 (5 magasins + centre logistique + maison mère)
- Simulation de ventes concurrentes sur les 5 magasins (15 caisses)
- Test de consultation de stock central simultanée
- Création de demandes d'approvisionnement en parallèle
- Validation de la cohérence des stocks inter-entités

**Métriques** :
- Throughput global par magasin (ventes/seconde)
- Performance des demandes d'approvisionnement
- Temps de génération des rapports consolidés
- Latence de synchronisation entre entités

### 3. Test de performance des services métier

**Objectif** : Évaluer les services du Lab 2 selon leur interface
- **ServiceApprovisionnement** : Création et traitement des demandes (console)
- **ServiceRapport** : Génération de rapports consolidés (console)
- **ServiceTableauBord** : Calcul des indicateurs pour supervision (web)

**Métriques** :
- Temps de génération d'un rapport consolidé via console (< 2s)
- Throughput des demandes d'approvisionnement via console
- Performance des indicateurs du tableau de bord web (< 1s)

### 4. Test de supervision web légère

**Objectif** : Valider l'interface web de supervision uniquement
- Accès au tableau de bord (UC3) depuis la maison mère
- Rafraîchissement automatique des indicateurs
- Interface minimaliste sans surcharge

**Métriques** :
- Temps de réponse du dashboard (< 1s)
- Performance du calcul des indicateurs
- Fluidité de l'interface de supervision

### 5. Test de résistance base de données

**Objectif** : Valider les optimisations de performance
- Test des index composites sur les requêtes critiques
- Performance des requêtes de rapports consolidés
- Concurrent access sur les stocks multi-entités

**Métriques** :
- Performance des index optimisés (idx_vente_entite_date, idx_stock_entite_produit)
- Temps d'exécution des requêtes complexes
- Gestion des verrous pour les transactions distribuées

## Architecture testée

Les tests valident spécifiquement l'architecture 3-tier multi-magasins :

**Tier 1 - Persistance :**
- PostgreSQL centralisé avec index optimisés
- Transactions ACID pour cohérence multi-entités

**Tier 2 - Services Métier :**
- Services partagés entre toutes les entités
- Gestion des demandes d'approvisionnement
- Génération de rapports consolidés

**Tier 3 - Présentation :**
- Interface console pour opérations (5 magasins + centre logistique + maison mère)
- Interface web pour supervision légère (maison mère uniquement)
- Séparation claire des responsabilités

## Exigences de performance

### Cibles Lab 2
- **Rapports consolidés** : < 2 secondes pour 5 magasins (console)
- **Concurrent access** : Support de 15 caisses simultanées
- **Tableau de bord web** : Temps de réponse < 1 seconde
- **Demandes d'approvisionnement** : Traitement en temps quasi-réel (console)

### Seuils critiques
- **Ventes simultanées** : 15 caisses sans dégradation
- **Génération rapports** : Maximum 5 secondes pour période 1 mois
- **Consultation stocks** : < 1 seconde pour requêtes inter-entités

## Exécution

```bash
# Tests complets avec environnement multi-magasins
docker compose up -d postgres
docker compose run --rm init-data
python tests/test_performance.py

# Tests interface console (fonctionnalités opérationnelles)
python tests/test_console_performance.py

# Tests interface web (supervision légère)
docker compose up -d
curl -w "@curl-format.txt" http://localhost:5000/dashboard

# Tests de charge avec plusieurs magasins
python tests/test_charge_multimagasins.py
```

## Tests par interface

### Interface Console
- **UC1** : Performance génération rapports consolidés
- **UC2** : Temps de consultation stock central  
- **UC4** : Performance gestion produits
- **UC6** : Throughput traitement demandes approvisionnement
- **Lab1** : Performance ventes, recherches, retours

### Interface Web
- **UC3** : Temps de réponse tableau de bord
- **UC8** : Fluidité supervision légère
- **Performance** : Calcul indicateurs en temps réel

## Résultats attendus

### Performance optimisée
- **Requêtes indexées** : Amélioration 80% sur les rapports consolidés
- **Architecture 3-tier** : Séparation efficace des responsabilités
- **Concurrent access** : Zéro conflits sur 15 caisses simultanées

### Améliorations Lab 2
- **Index composites** : Performance requêtes critiques optimisée
- **Services découplés** : Réutilisation et performance améliorées
- **Séparation console/web** : Interfaces optimisées selon leurs responsabilités