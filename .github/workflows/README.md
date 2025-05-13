# Pipeline CI/CD

Ce dossier contient la configuration de la pipeline CI/CD pour l'application Hello World.

## Étapes de la pipeline

1. **Lint** : Vérifie la qualité syntaxique et stylistique du code via pylint.
2. **Tests unitaires** : Exécute les tests unitaires avec pytest. Si les tests échouent, la pipeline s'arrête.
3. **Build** : Construction de l'image Docker de l'application si les étapes précédentes sont réussies.
4. **Publication** : Publication de l'image Docker sur Docker Hub (uniquement lors des pushs sur main/master).

## Secrets nécessaires

Pour que la publication sur Docker Hub fonctionne, vous devez configurer les secrets suivants dans votre dépôt GitHub :

- `DOCKERHUB_USERNAME` : Votre nom d'utilisateur Docker Hub
- `DOCKERHUB_TOKEN` : Votre token d'accès Docker Hub (pas votre mot de passe) 