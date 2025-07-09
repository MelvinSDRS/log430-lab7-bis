# ADR-011 : Choix de Redis Streams pour la messagerie événementielle

## Statut
Accepté

## Contexte
Besoin d'un système de messagerie Pub/Sub pour l'architecture événementielle du Lab 7. Le système doit supporter :
- Publication d'événements par le Claims Service
- Abonnement de multiples consumers (Notification, Audit, Projection)
- Persistence des messages pour audit et replay
- Distribution de charge avec consumer groups

## Options considérées

### 1. RabbitMQ
**Avantages :**
- Message broker mature et stable
- Garanties de livraison robustes
- Routage complexe avec exchanges
- Interface d'administration complète

**Inconvénients :**
- Composant supplémentaire à gérer
- Latence plus élevée
- Configuration plus complexe
- Ressources additionnelles

### 2. Apache Kafka
**Avantages :**
- Plateforme de streaming haute performance
- Excellente scalabilité
- Durabilité et réplication
- Écosystème riche

**Inconvénients :**
- Complexité de déploiement
- Surdimensionné pour le lab
- Courbe d'apprentissage steep
- Ressources importantes

### 3. Redis Streams
**Avantages :**
- Extension naturelle de Redis existant
- Performance et latence excellentes
- Consumer groups intégrés
- Persistence configurable
- Simplicité d'utilisation

**Inconvénients :**
- Moins de garanties que Kafka
- Pas de réplication native
- Limitations pour très hauts volumes

## Décision

**Redis Streams** est choisi pour la messagerie événementielle car :

1. **Simplicité architecturale** : Extension de Redis déjà utilisé pour le cache
2. **Performance** : Latence très faible adaptée aux événements temps réel
3. **Persistence** : Messages durables pour audit et replay
4. **Consumer Groups** : Distribution de charge native
5. **Intégration** : Réutilisation de l'infrastructure Redis existante

## Conséquences

### Positives
- **Réduction de la complexité** : Moins de composants à gérer
- **Performance optimale** : Latence sub-milliseconde
- **Configuration simplifiée** : Leveraging Redis expertise
- **Coût réduit** : Pas de composant supplémentaire

### Négatives
- **Limitations de débit** : Adapté pour volumes moyens (< 100k messages/sec)
- **Garanties limitées** : Moins robuste que Kafka pour cas critiques
- **Single point of failure** : Pas de réplication native (mitigé par Redis Sentinel)

### Mitigation des risques
- **Monitoring avancé** : Métriques détaillées des streams
- **Backup régulier** : Sauvegarde des données Redis
- **Tests de charge** : Validation des limites de performance
- **Plan de migration** : Évolution possible vers Kafka si nécessaire
