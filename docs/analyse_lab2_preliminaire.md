# Analyse préliminaire avant le développement du Lab 2

Dans ce document, j’analyse les laboratoires précédents (Lab 0 et Lab 1) afin d’orienter la conception et le développement du Lab 2. Je m’appuie sur ce que j’ai observé et mis en place pour justifier mes choix d’architecture. Cette analyse est également guidée par les principes du Domain-Driven Design (DDD).

## Résumé des solutions développées aux Labs 0 et 1

Lors du Lab 0, j’ai mis en place un prototype minimal. Mon objectif était d’avoir un point de départ fonctionnel simple, basé sur Flask. L’application reposait sur un fichier unique `app.py` avec un stockage en mémoire. À ce stade, je n’avais pas encore introduit de séparation entre les couches métier, technique ou de présentation. L’ensemble était monolithique et peu évolutif, ce qui était acceptable pour un premier jet.

Avec le Lab 1, j’ai franchi une étape importante vers une architecture plus propre. J’ai introduit une structure en couches, en isolant le domaine métier (`src/domain`), la persistance (`src/persistence`) et l’interface utilisateur. J’ai modélisé des entités via des `dataclass`, comme `Produit`, `Categorie` ou encore `Vente`, et j’ai mis en place des services métiers rudimentaires, notamment un `ServiceTransaction`.

## Éléments à conserver, modifier ou refactorer

Je considère que l’architecture modulaire introduite au Lab 1 est une base solide, que je souhaite conserver et enrichir. Cette séparation m’a permis d’avoir un code plus maintenable et testable.

En revanche, je constate que les services métiers doivent évoluer pour traiter des cas plus complexes. Pour répondre aux besoins du Lab 2, j’ai prévu de refactorer ces services afin d’y intégrer la gestion du stock multi-entité, les transferts de stock, les demandes d’approvisionnement et les indicateurs de seuils.

Concernant les entités, je vais devoir élargir le modèle existant en y intégrant des notions d’entité physique (magasin, centre logistique) et de gestion de stock localisé. Je compte également revoir le script d’initialisation pour créer plusieurs magasins et simuler des scénarios plus proches de la réalité. Enfin, je devrai adapter les tests pour prendre en compte ces nouveaux comportements métier.

## Nouvelles exigences et défis architecturaux## Nouvelles exigences et défis architecturaux

Le Lab 2 introduit de nouvelles exigences auxquelles je vais devoir répondre. Il me faudra d’abord prendre en charge la gestion simultanée de plusieurs magasins ainsi que d’un centre logistique, chacun disposant de son propre niveau de stock. Je prévois également d’implémenter des processus logistiques tels que les transferts de stock et les demandes d’approvisionnement. Enfin, je devrai concevoir un système de suivi de la performance s’appuyant sur des indicateurs métiers.

Ces nouvelles fonctionnalités s’accompagnent de défis techniques et architecturaux. Je vais devoir concevoir des services capables d’enchaîner plusieurs opérations tout en garantissant la cohérence des données, notamment lors des transferts et validations. Il me faudra aussi organiser mon code de manière à assurer une séparation claire des responsabilités entre les couches. Je compte porter une attention particulière à la flexibilité du modèle, afin qu’il reste extensible et adapté à d’éventuelles évolutions.

## Réflexion Domain-Driven Design (DDD)

En m’appuyant sur les principes du DDD, je prévois d’identifier et de structurer plusieurs sous-domaines fonctionnels dans mon système. Cette approche devrait m’aider à clarifier les responsabilités métier et à mieux compartimenter le code.

Le premier sous-domaine que j’envisage est celui du catalogue produit, dédié à la gestion des produits et des catégories. Un deuxième sous-domaine concernera le point de vente, incluant les ventes, les caisses et les lignes de vente. Je vais également modéliser un sous-domaine pour la gestion de stock localisé, avec un suivi par entité (magasin ou centre logistique). Enfin, un quatrième sous-domaine portera sur la logistique, en lien avec les transferts de stock et les demandes d’approvisionnement.

Je compte représenter ces sous-domaines dans mon code par des entités spécifiques, des services métiers dédiés et des éléments de configuration tels que des énumérations (par exemple `TypeEntite` ou `StatutDemande`). En structurant ainsi le modèle, je souhaite favoriser l’indépendance des modules et préparer le terrain pour une évolution vers une architecture plus modulaire, voire orientée microservices si le besoin se fait sentir.
