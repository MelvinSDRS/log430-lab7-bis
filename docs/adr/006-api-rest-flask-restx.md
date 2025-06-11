# ADR 006: API REST avec Flask-RESTX

## Contexte

Nous devons exposer les fonctionnalités principales via une API REST pour permettre l'intégration avec des applications externes.

## Décision

J'ai décidé d'utiliser Flask-RESTX plutôt que FastAPI pour implémenter l'API REST.

## Options considérées

### Option 1: FastAPI
**Avantages:**
- Performance supérieure (asynchrone par défaut)
- Type hints Python natifs et validation automatique
- Documentation OpenAPI interactive

**Inconvénients:**
- Rupture avec l'architecture Flask existante
- Peut-être trop avancé pour notre utilisation

### Option 2: Flask-RESTX (choisi)
**Avantages:**
- Cohérence architecturale avec l'interface web Flask existante
- Réutilisation directe des services métier du Lab 2
- Documentation Swagger automatique intégrée

**Inconvénients:**
- Performance moindre que FastAPI pour les charges très élevées
- Pas d'asynchrone natif

## Justification

1. **Cohérence technique** : Nous utilisions déjà Flask pour l'interface web de supervision, utiliser Flask-RESTX maintient une stack technique homogène.

2. **Réutilisation optimale** : Les services métier existants (ServiceProduit, ServiceVente, ServiceRapport) peuvent être directement intégrés sans refactoring.

3. **Pragmatisme** : Pour un système POS avec charge modérée comme le notre, les gains de performance de FastAPI ne justifient pas la complexité additionnelle.

4. **Time-to-market** : Etant déjà familier avec Flask, l'implémentation est plus rapide et plus sûre.

5. **Maintenabilité** : Une seule technologie web (Flask) à maintenir plutôt que deux stacks différents.

## Conséquences

### Positives
- Développement rapide
- Architecture cohérente et unifiée
- Réutilisation maximale du code existant
- Documentation Swagger automatique

### Négatives
- Performance limitée pour de très gros volumes (non critique dans notre cas)
- Pas de support WebSockets natif (peut être ajouté si nécessaire)

## Notes d'implémentation

L'API REST implémentée expose :
- 4 cas d'usage principaux : rapports consolidés, consultation stocks, performances magasins, gestion produits
- Authentification par token simple
- Documentation Swagger accessible via `/api/docs`
- Standards RESTful : HATEOAS, pagination, codes HTTP appropriés 