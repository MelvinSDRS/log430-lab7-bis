# Pipeline CI/CD - POS Multi-Magasins

Ce dossier contient la configuration de la pipeline CI/CD pour le système de point de vente multi-magasins avec architecture 3-tier (Console + Web + Base de données).

## Architecture de la Pipeline

La pipeline est divisée en 4 jobs qui s'exécutent séquentiellement :

### 1. **Tests & Code Quality**
- **Linting** : Vérification de la qualité du code avec `flake8`
- **Tests unitaires** : Exécution des tests avec `pytest` et couverture de code
- **Initialisation DB** : Test de l'initialisation de la base de données `pos_multimagasins` avec données multi-magasins

### 2. **Docker Build & Integration Test**
- **Construction** : Build de l'image Docker optimisée
- **Test basique** : Vérification que l'image fonctionne correctement
- **Test d'architecture complète** : 
  - Démarrage de l'architecture complète (PostgreSQL + 5 magasins + interface web)
  - Test de connectivité base de données multi-magasins
  - Validation de l'architecture 3-tier (Console/Web/DB)
  - Test d'accessibilité de l'interface web de supervision
  - Vérification des entités (5 magasins + centre logistique + maison mère)

### 3. **Docker Push** (seulement sur main/master)
- **Publication** : Push sur Docker Hub des images taguées

### 4. **Success Notification**
- **Notification** : Confirmation du succès de la pipeline

## Déclencheurs

- **Push** sur les branches `main` ou `master`
- **Pull Request** vers `main` ou `master`

## Tests d'Intégration

La pipeline teste maintenant l'architecture multi-magasins complète :
- ✅ **PostgreSQL** : Démarrage et santé du serveur avec base `pos_multimagasins`
- ✅ **5 Interfaces Console** : Démarrage des applications de magasins
- ✅ **Interface Web** : Application Flask pour supervision (maison mère/centre logistique)
- ✅ **Initialisation automatique** : Vérification des données multi-magasins
- ✅ **Architecture 3-tier** : Validation Console + Web + Base de données
- ✅ **Tests multi-entités** : Vérification de 10 caisses et 7 entités
- ✅ **Connectivité web** : Test d'accessibilité de l'interface de supervision

## Secrets nécessaires

- `DOCKERHUB_USERNAME` : Votre nom d'utilisateur Docker Hub
- `DOCKERHUB_TOKEN` : Votre token d'accès Docker Hub (pas votre mot de passe)

## Images publiées

Après un push réussi sur main/master, les images suivantes sont disponibles :

```bash
docker pull melvinsdrs/pos-system:latest
docker pull melvinsdrs/pos-system:<commit-sha>
```

## Avantages de cette Pipeline

1. **Validation complète** : Teste l'architecture 3-tier multi-magasins réelle
2. **Architecture** : Valide la séparation Console (opérations) / Web (supervision)
3. **Tests multi-entités** : Vérifie la gestion de 5 magasins + centre + maison mère
4. **Cohérence Docker** : Utilise la même configuration que le déploiement
5. **Tests d'intégration** : Valide le workflow automatique complet
6. **Variables d'environnement** : Teste l'assignation correcte des entités par conteneur
7. **Optimisation** : Cache Docker pour des builds plus rapides