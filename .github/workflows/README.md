# Pipeline CI/CD - POS System

Ce dossier contient la configuration de la pipeline CI/CD pour le système de point de vente avec architecture client/serveur 2-tier.

## Architecture de la Pipeline

La pipeline est divisée en 4 jobs qui s'exécutent séquentiellement :

### 1. **Tests & Code Quality**
- **Linting** : Vérification de la qualité du code avec `flake8`
- **Tests unitaires** : Exécution des tests avec `pytest` et couverture de code
- **Initialisation DB** : Test de l'initialisation de la base de données PostgreSQL

### 2. **Docker Build & Integration Test**
- **Construction** : Build de l'image Docker optimisée
- **Test basique** : Vérification que l'image fonctionne correctement
- **Test d'architecture complète** : 
  - Démarrage de l'architecture complète (PostgreSQL + 3 clients)
  - Test de connectivité base de données
  - Exécution des tests dans l'environnement Docker
  - Validation de l'initialisation automatique

### 3. **Docker Push** (seulement sur main/master)
- **Publication** : Push sur Docker Hub des images taguées

### 4. **Success Notification**
- **Notification** : Confirmation du succès de la pipeline

## Déclencheurs

- **Push** sur les branches `main` ou `master`
- **Pull Request** vers `main` ou `master`

## Tests d'Intégration

La pipeline teste maintenant l'architecture complète :
- ✅ **PostgreSQL** : Démarrage et santé du serveur
- ✅ **3 Clients** : Démarrage des applications client
- ✅ **Initialisation automatique** : Vérification des données de test
- ✅ **Connectivité** : Test de connexion client/serveur
- ✅ **Tests complets** : Exécution de tous les tests (10 tests)

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

1. **Validation complète** : Teste l'architecture 2-tier réelle
2. **Cohérence Docker** : Utilise la même configuration que le déploiement
3. **Tests d'intégration** : Valide le workflow automatique complet
4. **Optimisation** : Cache Docker pour des builds plus rapides