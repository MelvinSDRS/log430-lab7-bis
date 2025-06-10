# ADR 005: Framework web Flask

## Contexte

Pour implémenter l'architecture MVC et l'interface web du système multi-magasins, je devais choisir un framework web Python adapté aux besoins du projet.

## Décision

J'ai décidé d'utiliser **Flask** comme framework web pour l'interface MVC du système multi-magasins.

## Justification

### Critères de sélection
- **Simplicité** : Framework léger et facile à apprendre
- **Flexibilité** : Permet une architecture MVC personnalisée
- **Intégration** : Compatible avec SQLAlchemy (déjà utilisé)
- **Écosystème Python** : Cohérent avec la stack technique existante

### Adéquation aux besoins
- **Interface web minimale** : Flask convient parfaitement aux besoins UC8
- **Rapports et tableaux de bord** : Support natif des templates HTML
- **Intégration avec l'existant** : Réutilisation directe des services métier
- **Déploiement Docker** : Compatible avec la conteneurisation existante

## Implémentation réelle

### Structure Flask implémentée
```
src/web/
├── app.py              # Application Flask monolithique
├── templates/          # Templates Jinja2
│   ├── index.html      # Page d'accueil
│   ├── dashboard.html  # Tableau de bord supervision
└── __init__.py
```

### Configuration Flask utilisée
- **Flask core** : `Flask, render_template, request, redirect, url_for, flash, jsonify`
- **Jinja2** : Moteur de templates (inclus avec Flask)
- **Logging** : Système de logs avec rotation des fichiers
- **Factory pattern** : Fonction `create_app()` pour configuration

### Architecture simplifiée
- **Un seul fichier contrôleur** : `app.py` avec toutes les routes
- **Templates organisés** : Par domaine métier (admin, logistique, magasin)
- **Intégration directe** : Avec les services du domaine existants

## Conséquences

### Avantages réalisés
- **Courbe d'apprentissage faible** : Framework simple et bien documenté
- **Réutilisation** : Intégration directe avec SQLAlchemy et les services existants
- **Flexibilité architecturale** : Implémentation MVC selon nos besoins
- **Performance suffisante** : Adapté aux besoins de supervision
- **Déploiement simple** : Un seul fichier Python principal

### Inconvénients à date
- **Contrôleur monolithique** : Toutes les routes dans un seul fichier
- **Pas d'extensions avancées** : Pas de gestion d'utilisateurs, formulaires simples
- **CSS intégré** : Pas de fichiers statiques séparés (par simplicité)

### Défis techniques résolus
- **Sessions multi-conteneurs** : Gestion propre des sessions de base de données
- **Gestion d'erreurs** : Handlers 404/500 personnalisés
- **Logging** : Système de logs rotatifs pour production et développement
- **Factory pattern** : Configuration propre de l'application

## Alternative considérée

### Django
- **Avantages** : Framework complet avec ORM intégré, admin interface
- **Inconvénients** : Trop lourd pour nos besoins, ORM différent de SQLAlchemy
- **Verdict** : Surdimensionné pour l'interface web minimale requise

## Évolutions futures possibles

- Séparation du contrôleur en modules par domaine
- Ajout d'extensions Flask (Flask-Login, Flask-WTF)
- Fichiers CSS/JS statiques externes
- Système de gestion d'utilisateurs
- API REST séparée 