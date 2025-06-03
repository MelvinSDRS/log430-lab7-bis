# ADR 002: Stratégie de Persistance

## Contexte

Le système de point de vente nécessite une solution de persistance des données fiable et adaptée à une architecture client/serveur 2-tier avec 3 caisses travaillant simultanément.

## Décision

J'ai décidé d'utiliser **PostgreSQL** comme système de gestion de base de données serveur, avec **SQLAlchemy** comme ORM pour l'abstraction de la couche de persistance.

## Justification

Cette décision répond aux exigences d'une **architecture client/serveur 2-tier** où :
- Le **serveur** est la base de données PostgreSQL dans un conteneur dédié
- Les **clients** sont 3 applications console qui se connectent au serveur

## Conséquences

**Avantages**:
- **Architecture client/serveur vraie**: Base de données dans un conteneur séparé
- **Accès concurrent optimal**: PostgreSQL gère nativement les accès simultanés
- **Transactions ACID robustes**: Gestion avancée des verrous et transactions
- **Cohérence des données**: Garantie entre les 3 caisses simultanées
- **Scalabilité**: Possibilité d'ajouter facilement plus de clients
- **Abstraction via ORM**: SQLAlchemy facilite la maintenance

**Inconvénients**:
- Complexité accrue: Nécessite un serveur de base de données séparé
- Dépendance réseau: Les clients dépendent de la connectivité au serveur
- Configuration plus complexe que SQLite

## Alternatives considérées

- **SQLite**: Plus simple mais ne permet pas une vraie architecture client/serveur
- **MongoDB**: Flexibilité du schéma mais moins adapté pour les relations complexes
- **MySQL/MariaDB**: Alternatives viables mais PostgreSQL offre de meilleures performances pour les transactions concurrentes

## Implémentation

L'architecture est déployée via Docker Compose avec :
- Un conteneur PostgreSQL dédié (serveur)
- 3 conteneurs clients indépendants
- Health checks pour assurer la disponibilité du serveur 