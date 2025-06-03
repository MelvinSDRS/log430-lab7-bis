# ADR 003: Séparation des Responsabilités

## Contexte

Pour assurer la maintenabilité et l'évolutivité du système, nous devons adopter une architecture avec une séparation claire des responsabilités.

## Décision

J'ai donc adopté une **architecture en trois couches** :

1. **Couche Client** : Point d'entrée et interactions
2. **Couche de Logique Métier** : Services et entités métier
3. **Couche de Persistance** : Accès aux données via ORM

## Conséquences

**Avantages**:
- Modularité et clarté des responsabilités
- Meilleure testabilité des composants
- Possibilité de modifier une couche sans impacter les autres
- Réutilisabilité des composants de la couche métier

**Inconvénients**:
- Complexité initiale plus importante qu'une approche monolithique
- Communication entre couches nécessitant une interface bien définie

## Alternatives considérées

- **Architecture monolithique**: Plus simple mais moins évolutive
- **Architecture MVC**: Plus adaptée pour les interfaces graphiques