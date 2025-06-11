# Analyse des besoins - Système multi-magasins

## Évolution des besoins (Lab 1 → Lab 2 → Lab 3)

### Contexte initial (Lab 1)
Système de point de vente pour un magasin avec 3 caisses simultanées.

### Extension Lab 2
Entreprise avec 5 magasins, 1 centre logistique et 1 maison mère nécessitant :
- Gestion simultanée et cohérente de plusieurs magasins
- Consultation centralisée des stocks et transactions
- Synchronisation fiable des données
- Rapports consolidés pour l'administration
- Interface web pour supervision

### Extension Lab 3 (API REST)
Exposition des fonctionnalités via API REST pour applications externes :
- Intégration avec systèmes tiers (ERP, applications mobiles, etc.)
- Accès programmatique aux données et fonctionnalités
- Documentation standardisée (Swagger/OpenAPI)
- Authentification sécurisée pour applications externes

## Besoins fonctionnels (MoSCoW)

### Must Have (Essentiel)

**UC1 – Générer un rapport consolidé des ventes**
- **Acteur** : Gestionnaire maison mère / Application externe
- **Description** : Génère un rapport détaillé contenant les ventes par magasin, produits les plus vendus, et stocks restants
- **Objectif** : Planification et décisions stratégiques
- **Statut** : ✅ Implémenté (interface console + API REST `/api/v1/reports/sales/consolidated`)

**UC2 – Consulter le stock central et déclencher un réapprovisionnement**
- **Acteur** : Employé magasin / Application externe
- **Description** : Consulte le stock du centre logistique et initie une demande d'approvisionnement
- **Objectif** : Éviter les ruptures de stock locales
- **Statut** : ✅ Implémenté (interface console + API REST `/api/v1/stocks`)

**UC3 – Visualiser les performances des magasins dans un tableau de bord**
- **Acteur** : Gestionnaire maison mère / Application externe
- **Description** : Accède à un tableau de bord avec indicateurs clés (CA par magasin, alertes rupture, surstock, tendances)
- **Objectif** : Supervision en temps réel
- **Statut** : ✅ Implémenté (interface web + API REST `/api/v1/stores/performances`)

### Should Have (Souhaitable)

**UC4 – Mettre à jour les produits depuis la maison mère**
- **Acteur** : Responsable maison mère / Application externe
- **Description** : Modifie les informations d'un produit (nom, prix, description, catégorie, seuil). Les changements sont synchronisés automatiquement dans tous les magasins
- **Objectif** : Cohérence des données produits
- **Statut** : ✅ Implémenté (interface console + API REST `/api/v1/products`)

**UC6 – Approvisionner un magasin depuis le centre logistique**
- **Acteur** : Responsable logistique
- **Description** : Valide une commande de réapprovisionnement avec transfert de stock
- **Objectif** : Gestion optimisée des stocks
- **Statut** : ✅ Implémenté (interface console depuis centre logistique)

### Could Have (Facultatif)

**UC7 – Détecter les ruptures critiques**
- **Acteur** : Système
- **Description** : Détecte et affiche les ruptures de stock dans les rapports et tableaux de bord
- **Objectif** : Visibilité sur les ruptures
- **Statut** : ⚠️ Partiellement implémenté (détection + affichage, pas d'alertes automatiques)

**UC8 – Interface web minimale pour gestionnaires**
- **Acteur** : Gestionnaire
- **Description** : Interface web légère pour accès à distance aux indicateurs clés du système : ventes, stocks, alertes
- **Objectif** : Visibilité rapide sans accès direct au système interne
- **Statut** : ✅ Implémenté (interface web légère)

## Besoins non-fonctionnels

### Performance ✅
- Support de 5 magasins simultanés + centre logistique
- Synchronisation des données en temps quasi-réel
- Interface web responsive
- API REST avec pagination et filtrage

### Fiabilité ✅
- Cohérence des données entre toutes les entités
- Gestion des sessions de base de données
- Gestion d'erreurs avec rollback
- Validation des données API avec messages d'erreur standardisés

### Sécurité ⚠️
- API REST : Authentification Bearer token (`pos-api-token-2025`)
- API REST : Configuration CORS restrictive
- **Non implémenté** : Authentification des utilisateurs console/web
- **Non implémenté** : Autorisation basée sur les rôles

### Maintenabilité ✅
- Architecture MVC pour séparation des responsabilités
- Code modulaire et extensible
- Documentation ADR complète
- Documentation API automatique (Swagger/OpenAPI)

### Évolutivité ✅
- Architecture préparée pour extensions futures
- Possibilité d'ajouter de nouveaux magasins
- Structure modulaire des services
- API versionnée (`/api/v1/`)

### Portabilité ✅
- Déploiement via conteneurisation Docker
- Fonctionnement multi-plateforme
- Base de données PostgreSQL standard
- API REST standard (Flask-RESTX)

## Répartition des interfaces

### Interface Console
**Fonctionnalités opérationnelles et de gestion :**
- **UC1** - Génération de rapports (maison mère)
- **UC2** - Consultation stock central + demandes approvisionnement (magasins)
- **UC4** - Gestion des produits (maison mère)
- **UC6** - Traitement des demandes d'approvisionnement (centre logistique)
- Fonctionnalités POS existantes (Lab 1)

### Interface Web
**Supervision légère à distance uniquement :**
- **UC3** - Tableau de bord avec indicateurs clés
- **UC8** - Interface minimaliste pour accès distant
- Aucune fonction opérationnelle (pas de formulaires de gestion)

### Interface API REST
**Intégrations et applications externes :**
- **UC1** - Rapports consolidés via `POST /api/v1/reports/sales/consolidated`
- **UC2** - Consultation stocks via `GET /api/v1/stocks?store_id=X`
- **UC3** - Performances magasins via `GET /api/v1/stores/performances`
- **UC4** - Gestion produits via `GET/POST/PUT/DELETE /api/v1/products`
- Documentation interactive via Swagger UI (`/api/docs`)
- Authentification Bearer token sécurisée

### Justification de cette répartition
Cette approche respecte l'esprit du sujet original où l'interface web était destinée à être **légère** et **complémentaire**. L'API REST ajoute une troisième dimension pour les intégrations externes sans impacter les interfaces existantes.

## Contraintes

### Techniques ✅
- Architecture 3-tier avec couche de services centralisés
- Interface web MVC simplifiée avec Flask (UC3 + UC8 uniquement)
- Interface console étendue pour fonctionnalités opérationnelles
- API REST Flask-RESTX avec documentation Swagger automatique
- Utilisation d'un ORM (SQLAlchemy) pour l'abstraction de persistance
- Synchronisation des données entre entités distribuées

### Organisationnelles ✅
- Continuité avec le système Lab 1 existant (réutilisation des services)
- Interface console enrichie selon le type d'entité (magasin/maison mère/centre logistique)
- Interface web légère pour supervision à distance uniquement
- API REST pour intégrations externes avec applications tierces
- Séparation claire des responsabilités entre console (opérations), web (supervision) et API (intégrations)

### Environnement ✅
- Déploiement via Docker et Docker Compose
- Support de 5 magasins + centre logistique + maison mère
- Interface web accessible via navigateur standard
- Interface console adaptée à chaque type d'entité
- API REST accessible via HTTP sur port 8000 avec documentation interactive