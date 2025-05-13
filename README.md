# LOG430 - Lab 0

## Application Python "Hello World"

Une application simple qui affiche "Hello World" dans la console.

### Exécution

Pour exécuter l'application:

```bash
python3 app.py
```

### Tests unitaires

Les tests unitaires utilisent le framework pytest. Pour exécuter les tests:

```bash
pytest -v
```

### Docker

L'application est conteneurisée avec Docker. Pour construire l'image:

```bash
docker build -t hello-world-app .
```

Pour exécuter l'application dans un conteneur:

```bash
docker run --rm hello-world-app
```

Pour exécuter les tests dans le conteneur:

```bash
docker run --rm hello-world-app pytest -v
```

### Docker Compose

L'application est orchestrée avec Docker Compose pour faciliter son lancement.

Pour lancer l'application:

```bash
docker compose up --build
```

Pour exécuter les tests:

```bash
docker compose --profile test up --build
```

### Intégration Continue (CI/CD)

Ce projet est configuré avec une pipeline CI/CD qui s'exécute automatiquement à chaque push ou pull request.

La pipeline comprend les étapes suivantes:

1. **Lint**: Analyse statique du code avec pylint
2. **Tests**: Exécution des tests unitaires
3. **Build**: Construction de l'image Docker
4. **Publication**: Publication de l'image sur Docker Hub (pour les branches main/master)

Consultez le répertoire `.github/workflows` pour plus de détails sur la configuration.

### Structure du projet

- `app.py` : Programme principal qui affiche le message
- `test_app.py` : Tests unitaires pour l'application
- `Dockerfile` : Instructions pour la création de l'image Docker
- `.dockerignore` : Fichiers à exclure lors de la construction de l'image
- `docker-compose.yml` : Configuration pour l'orchestration avec Docker Compose
- `.github/workflows/ci-cd.yml` : Configuration de la pipeline CI/CD