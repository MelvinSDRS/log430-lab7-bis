# ADR 001: Choix de la Plateforme

## Contexte

Le système de point de vente (POS) doit être une application simple, robuste et autonome pour un petit magasin de quartier.

## Décision

J'ai décidé d'utiliser **Python** comme langage de programmation principal.

## Conséquences

**Avantages**:
- Simplicité et lisibilité facilitant la maintenance
- Écosystème riche et nombreux packages tiers disponibles
- Portabilité multi-plateforme
- Intégration facile avec différents types de bases de données

**Inconvénients**:
- Performance potentiellement moindre par rapport aux langages compilés
- Distribution aux utilisateurs finaux plus complexe

## Alternatives considérées

- **Java** : Plus verbeux, nécessite une JVM
- **C#/.NET** : Moins portable pour une utilisation multi-plateforme, jamais expérimenté personnellement
- **JavaScript/Node.js** : Moins adapté pour une application cliente locale