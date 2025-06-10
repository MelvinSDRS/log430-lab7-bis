# Système de Point de Vente Multi-Magasins - Documentation

Bienvenue dans la documentation du système de point de vente multi-magasins développé pour le laboratoire 2 de LOG430. Cette application est conçue comme un système de gestion centralisé pour une entreprise possédant cinq magasins, un centre de logistique et une maison mère.

## Évolution du système

### Lab 1 → Lab 2
- **Lab 1** : Architecture client/serveur 2-tier pour un magasin (3 caisses)
- **Lab 2** : Architecture 3-tier multi-magasins avec interface web MVC

## Structure de la documentation

### Analyse des besoins
- [Analyse des Besoins Fonctionnels et Non-Fonctionnels](analyse-besoins.md)

### Architecture
- [Architecture 4+1](architecture-4+1.md)

### Décisions d'architecture (ADR)
- [ADR 001: Choix de la Plateforme](adr/001-choix-plateforme.md)
- [ADR 002: Stratégie de Persistance](adr/002-strategie-persistence.md)
- [ADR 003: Séparation des Responsabilités](adr/003-separation-responsabilites.md)
- [ADR 004: Architecture MVC pour Interface Web](adr/004-architecture-mvc.md)
- [ADR 005: Framework Web Flask](adr/005-framework-flask.md)

### Technologies
- [Choix Technologiques](choix-technologiques.md)

### Tests et validation
- [Tests de Performance](tests-performance.md)

## Vision du projet

Ce système multi-magasins est conçu pour être évolutif, maintenir la cohérence des données entre les différentes entités (magasins, centre logistique, maison mère) et fournir une supervision centralisée. L'architecture MVC permet une séparation claire des responsabilités et prépare l'évolution vers des interfaces web plus avancées.