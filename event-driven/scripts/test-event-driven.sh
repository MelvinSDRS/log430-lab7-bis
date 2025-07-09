#!/bin/bash

# Test de l'architecture événementielle Lab 7
echo "=== Test de l'architecture événementielle ==="

BASE_URL="http://localhost"
CLAIMS_SERVICE="${BASE_URL}:8101"
NOTIFICATION_SERVICE="${BASE_URL}:8102"
AUDIT_SERVICE="${BASE_URL}:8103"
PROJECTION_SERVICE="${BASE_URL}:8104"
QUERY_SERVICE="${BASE_URL}:8105"
EVENT_STORE_SERVICE="${BASE_URL}:8106"

# Fonction pour attendre qu'un service soit prêt
wait_for_service() {
    local service_url=$1
    local service_name=$2
    
    echo "Attente du service $service_name..."
    while ! curl -s -f "$service_url/health" > /dev/null; do
        echo "  En attente de $service_name ($service_url)..."
        sleep 2
    done
    echo " $service_name est prêt"
}

# Vérifier que tous les services sont prêts
echo "1. Vérification de l'état des services..."
wait_for_service "$CLAIMS_SERVICE" "Claims Service"
wait_for_service "$NOTIFICATION_SERVICE" "Notification Service"
wait_for_service "$AUDIT_SERVICE" "Audit Service"
wait_for_service "$PROJECTION_SERVICE" "Projection Service"
wait_for_service "$QUERY_SERVICE" "Query Service"
wait_for_service "$EVENT_STORE_SERVICE" "Event Store Service"

echo -e "\n2. Test du flux complet de réclamation..."

# Créer une réclamation
echo "  a) Création d'une réclamation..."
CLAIM_RESPONSE=$(curl -s -X POST "$CLAIMS_SERVICE/claims" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-correlation-$(date +%s)" \
    -d '{
        "customer_id": "customer_001",
        "claim_type": "product_defect",
        "description": "Le produit présente un défaut de fabrication",
        "product_id": "product_123"
    }')

CLAIM_ID=$(echo "$CLAIM_RESPONSE" | grep -o '"claim_id":"[^"]*"' | cut -d'"' -f4)
echo "    Réclamation créée avec ID: $CLAIM_ID"

# Attendre que les événements soient traités
echo "  b) Attente du traitement des événements (5s)..."
sleep 5

# Vérifier que la réclamation apparaît dans le query service
echo "  c) Vérification de la réclamation dans le Query Service..."
QUERY_RESPONSE=$(curl -s "$QUERY_SERVICE/claims/$CLAIM_ID")
echo "    Réclamation trouvée: $(echo "$QUERY_RESPONSE" | grep -o '"status":"[^"]*"')"

# Affecter la réclamation
echo "  d) Affectation de la réclamation à un agent..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-correlation-assign-$(date +%s)" \
    -d '{
        "agent_id": "agent_001"
    }' > /dev/null

sleep 3

# Démarrer le traitement
echo "  e) Démarrage du traitement..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/start" \
    -H "X-Correlation-ID: test-correlation-start-$(date +%s)" > /dev/null

sleep 3

# Résoudre la réclamation
echo "  f) Résolution de la réclamation..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/resolve" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-correlation-resolve-$(date +%s)" \
    -d '{
        "resolution": "Produit remplacé et excuses présentées au client"
    }' > /dev/null

sleep 3

# Fermer la réclamation
echo "  g) Fermeture de la réclamation..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/close" \
    -H "X-Correlation-ID: test-correlation-close-$(date +%s)" > /dev/null

sleep 5

echo -e "\n3. Vérification des projections et de l'audit..."

# Vérifier l'état final dans le Query Service
echo "  a) État final de la réclamation:"
FINAL_STATE=$(curl -s "$QUERY_SERVICE/claims/$CLAIM_ID")
echo "    $(echo "$FINAL_STATE" | grep -o '"status":"[^"]*"')"
echo "    $(echo "$FINAL_STATE" | grep -o '"resolution":"[^"]*"')"

# Vérifier les notifications
echo "  b) Notifications envoyées:"
NOTIFICATIONS=$(curl -s "$NOTIFICATION_SERVICE/notifications/stats")
echo "    $NOTIFICATIONS"

# Vérifier l'audit
echo "  c) Entrées d'audit pour cette réclamation:"
AUDIT_ENTRIES=$(curl -s "$AUDIT_SERVICE/audit/claims/$CLAIM_ID")
AUDIT_COUNT=$(echo "$AUDIT_ENTRIES" | grep -o '"count":[0-9]*' | cut -d':' -f2)
echo "    Nombre d'entrées d'audit: $AUDIT_COUNT"

# Vérifier les statistiques
echo "  d) Statistiques client:"
CUSTOMER_STATS=$(curl -s "$QUERY_SERVICE/stats/customers?customer_id=customer_001")
echo "    $CUSTOMER_STATS"

echo -e "\n4. Test du replay d'événements..."

# Tester le replay depuis l'Event Store
echo "  a) Replay des événements depuis l'Event Store:"
REPLAY_RESULT=$(curl -s "$EVENT_STORE_SERVICE/replay/$CLAIM_ID")
EVENTS_COUNT=$(echo "$REPLAY_RESULT" | grep -o '"events_count":[0-9]*' | cut -d':' -f2)
echo "    Nombre d'événements rejoués: $EVENTS_COUNT"

# Tester le replay depuis le Claims Service
echo "  b) Replay depuis le Claims Service:"
CLAIMS_REPLAY=$(curl -s "$CLAIMS_SERVICE/claims/$CLAIM_ID/replay")
echo "    $(echo "$CLAIMS_REPLAY" | grep -o '"reconstructed_from_events":[^,]*')"

echo -e "\n5. Test de la recherche et des requêtes CQRS..."

# Test de recherche
echo "  a) Recherche textuelle:"
SEARCH_RESULT=$(curl -s "$QUERY_SERVICE/search?q=défaut")
SEARCH_COUNT=$(echo "$SEARCH_RESULT" | grep -o '"count":[0-9]*' | cut -d':' -f2)
echo "    Résultats trouvés: $SEARCH_COUNT"

# Test du dashboard
echo "  b) Résumé du dashboard:"
DASHBOARD=$(curl -s "$QUERY_SERVICE/dashboard")
TOTAL_CLAIMS=$(echo "$DASHBOARD" | grep -o '"total_claims":[0-9]*' | cut -d':' -f2)
echo "    Total des réclamations: $TOTAL_CLAIMS"

echo -e "\n6. Vérification des métriques Prometheus..."

# Vérifier les métriques de quelques services
echo "  a) Métriques du Claims Service:"
CLAIMS_METRICS=$(curl -s "$CLAIMS_SERVICE/metrics" | grep "events_published_total" | head -3)
echo "    $CLAIMS_METRICS"

echo "  b) Métriques du Query Service:"
QUERY_METRICS=$(curl -s "$QUERY_SERVICE/metrics" | grep "queries_executed_total" | head -3)
echo "    $QUERY_METRICS"

echo -e "\n=== Test terminé avec succès! ==="
echo ""
echo "Pour surveiller l'architecture en temps réel:"
echo "  - Grafana: http://localhost:3001 (admin/admin123)"
echo "  - Prometheus: http://localhost:9091"
echo ""
echo "APIs disponibles:"
echo "  - Claims Service: http://localhost:8101/docs"
echo "  - Notification Service: http://localhost:8102/docs"
echo "  - Audit Service: http://localhost:8103/docs"
echo "  - Projection Service: http://localhost:8104/docs"
echo "  - Query Service: http://localhost:8105/docs"
echo "  - Event Store Service: http://localhost:8106/docs"