# LOG430 - Lab 0

## Application Python "Hello World"

Une application simple qui affiche "Hello World" dans la console.

## Architecture et structure du projet

Ce projet est construit selon une architecture simple avec les composants suivants :

- **Application principale** : Un script Python minimaliste qui affiche "Hello World"
- **Tests unitaires** : Tests pour valider le comportement de l'application
- **Conteneurisation** : Docker pour l'isolation et la portabilité 
- **Orchestration** : Docker Compose pour la gestion des conteneurs
- **CI/CD** : Pipeline d'intégration et déploiement continu via GitHub Actions

La structure du projet est organisée comme suit :

```
.
├── app.py                   # Application principale
├── test_app.py              # Tests unitaires
├── Dockerfile               # Instructions pour la création de l'image Docker
├── .dockerignore            # Fichiers à exclure lors de la construction de l'image
├── docker-compose.yml       # Configuration pour l'orchestration avec Docker Compose
├── .github/workflows/       # Configuration de la pipeline CI/CD
│   └── ci-cd.yml            # Définition de la pipeline
│   └── README.md            # Documentation de la pipeline
└── README.md                # Documentation du projet
```

## Guide de démarrage

### Cloner le projet

```bash
# Clonez le dépôt
git clone https://github.com/VOTRE_USERNAME/log430-lab0.git

# Accédez au répertoire du projet
cd log430-lab0
```

### Exécution

Pour exécuter l'application localement:

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

Pour construire et lancer l'application:

```bash
docker compose up --build
```

Pour exécuter les tests:

```bash
docker compose --profile test up --build
```

## Intégration Continue (CI/CD)

Ce projet est configuré avec une pipeline CI/CD qui s'exécute automatiquement à chaque push ou pull request.

La pipeline comprend les étapes suivantes:

1. **Lint**: Analyse statique du code avec pylint
2. **Tests**: Exécution des tests unitaires
3. **Build**: Construction de l'image Docker
4. **Publication**: Publication de l'image sur Docker Hub (pour les branches main/master)

Consultez le répertoire `.github/workflows` pour plus de détails sur la configuration.

### Exécution réussie de la pipeline CI/CD

![Capture d'écran de la pipeline CI/CD](https://github.com/user-attachments/assets/f60d2607-1c55-4c17-83a4-0c92bf87bcc6)