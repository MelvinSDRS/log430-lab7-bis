# Choix Technologiques

## Langage de programmation

**Choix: Python 3.9+**

Justification:
- Simplicité et lisibilité pour faciliter la maintenance
- Écosystème riche de bibliothèques pour accélérer le développement
- Portabilité multi-plateforme
- Intégration facile avec différents systèmes de bases de données
- Typage optionnel via annotations pour améliorer la qualité du code

## Base de données

**Choix: PostgreSQL + SQLAlchemy (ORM)**

Justification:
- PostgreSQL: Base de données serveur robuste pour architecture client/serveur 2-tier
- SQLAlchemy: Abstraction de la couche de persistance via un ORM
- Support des connexions multiples simultanées (3 caisses)
- Garanties ACID pour les transactions financières
- Scalabilité pour évolutions futures

## Tests

**Choix: Pytest**

Justification:
- Framework de test simple et puissant
- Support pour les tests unitaires et d'intégration
- Facilité d'exécution et d'automatisation

## Containerisation

**Choix: Docker + Docker Compose**

Justification:
- Facilité de déploiement et de configuration
- Isolation des dépendances
- Portabilité entre différents environnements

## Documentation

**Choix: Markdown**

Justification:
- Format simple et lisible pour la documentation
- Facilité de maintenance et de mise à jour
- Intégration possible avec le versionnement de code