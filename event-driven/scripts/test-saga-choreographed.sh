#!/bin/bash

# Test de la saga chorégraphiée
echo "=== Test de la saga chorégraphiée - Remboursement ==="

BASE_URL="http://localhost"
CLAIMS_SERVICE="${BASE_URL}:8101"
REFUND_PAYMENT_SERVICE="${BASE_URL}:8108"
REFUND_INVENTORY_SERVICE="${BASE_URL}:8109"
NOTIFICATION_SERVICE="${BASE_URL}:8102"

# Fonction pour attendre qu'un service soit prêt
wait_for_service() {
    local service_url=$1
    local service_name=$2
    
    echo "Attente du service $service_name..."
    for i in {1..30}; do
        if curl -s -f "$service_url/health" > /dev/null; then
            echo "✓ $service_name est prêt"
            return 0
        fi
        echo "  En attente de $service_name ($i/30)..."
        sleep 2
    done
    echo "✗ $service_name n'est pas disponible"
    return 1
}

# Vérifier que tous les services sont prêts
echo "1. Vérification de l'état des services..."
wait_for_service "$CLAIMS_SERVICE" "Claims Service" || exit 1
wait_for_service "$REFUND_PAYMENT_SERVICE" "Refund Payment Service" || exit 1
wait_for_service "$REFUND_INVENTORY_SERVICE" "Refund Inventory Service" || exit 1
wait_for_service "$NOTIFICATION_SERVICE" "Notification Service" || exit 1

echo -e "\n2. Création d'une réclamation pour test..."

# Créer une réclamation
CLAIM_RESPONSE=$(curl -s -X POST "$CLAIMS_SERVICE/claims" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-saga-$(date +%s)" \
    -d '{
        "customer_id": "customer_saga_001",
        "claim_type": "product_defect",
        "description": "Produit défectueux nécessitant un remboursement",
        "product_id": "product_123"
    }')

CLAIM_ID=$(echo "$CLAIM_RESPONSE" | grep -o '"claim_id":"[^"]*"' | cut -d'"' -f4)
echo "  Réclamation créée avec ID: $CLAIM_ID"

# Traiter la réclamation
echo -e "\n3. Traitement de la réclamation..."

# Affecter la réclamation
echo "  a) Affectation à un agent..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-saga-assign-$(date +%s)" \
    -d '{
        "agent_id": "agent_saga_001"
    }' > /dev/null

sleep 2

# Démarrer le traitement
echo "  b) Démarrage du traitement..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/start" \
    -H "X-Correlation-ID: test-saga-start-$(date +%s)" > /dev/null

sleep 2

# Résoudre la réclamation
echo "  c) Résolution de la réclamation..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/resolve" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-saga-resolve-$(date +%s)" \
    -d '{
        "resolution": "Produit défectueux confirmé, remboursement approuvé"
    }' > /dev/null

sleep 3

echo -e "\n4. Test de la saga chorégraphiée - Cas de succès..."

# Vérifier les niveaux de stock avant le remboursement
echo "  a) Niveau de stock avant remboursement:"
STOCK_BEFORE=$(curl -s "$REFUND_INVENTORY_SERVICE/inventory/product_123")
echo "    $(echo "$STOCK_BEFORE" | grep -o '"stock_level":[0-9]*')"

# Démarrer la saga de remboursement
echo "  b) Démarrage de la saga de remboursement..."
SAGA_CORRELATION_ID="saga-success-$(date +%s)"
REFUND_RESPONSE=$(curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/refund" \
    -H "X-Correlation-ID: $SAGA_CORRELATION_ID")

echo "    $(echo "$REFUND_RESPONSE" | grep -o '"message":"[^"]*"')"

# Attendre que la saga se termine
echo "  c) Attente de la completion de la saga (15s)..."
sleep 15

# Vérifier les résultats
echo "  d) Vérification des résultats de la saga:"

# Vérifier le statut du remboursement
REFUND_STATUS=$(curl -s "$REFUND_PAYMENT_SERVICE/refunds/$CLAIM_ID")
if echo "$REFUND_STATUS" | grep -q '"status":"completed"'; then
    echo "    ✓ Remboursement calculé avec succès"
else
    echo "    ✗ Échec du calcul de remboursement"
fi

# Vérifier l'ajustement de stock
STOCK_AFTER=$(curl -s "$REFUND_INVENTORY_SERVICE/inventory/product_123")
echo "    Stock après remboursement: $(echo "$STOCK_AFTER" | grep -o '"stock_level":[0-9]*')"

# Vérifier les notifications
NOTIFICATION_STATS=$(curl -s "$NOTIFICATION_SERVICE/notifications/stats")
TOTAL_NOTIFICATIONS=$(echo "$NOTIFICATION_STATS" | grep -o '"total_notifications":[0-9]*' | cut -d':' -f2)
echo "    Notifications envoyées: $TOTAL_NOTIFICATIONS"

echo -e "\n5. Test de la saga chorégraphiée - Cas d'échec..."

# Créer une nouvelle réclamation pour test d'échec
CLAIM_RESPONSE_FAIL=$(curl -s -X POST "$CLAIMS_SERVICE/claims" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-ID: test-saga-fail-$(date +%s)" \
    -d '{
        "customer_id": "customer_saga_002",
        "claim_type": "product_defect",
        "description": "Test d'échec de saga",
        "product_id": "product_non_eligible"
    }')

CLAIM_ID_FAIL=$(echo "$CLAIM_RESPONSE_FAIL" | grep -o '"claim_id":"[^"]*"' | cut -d'"' -f4)
echo "  Réclamation de test d'échec créée: $CLAIM_ID_FAIL"

# Traitement rapide pour arriver à la résolution
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID_FAIL" \
    -H "Content-Type: application/json" \
    -d '{"agent_id": "agent_saga_002"}' > /dev/null

sleep 1

curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID_FAIL/start" > /dev/null

sleep 1

curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID_FAIL/resolve" \
    -H "Content-Type: application/json" \
    -d '{"resolution": "Test d'échec"}' > /dev/null

sleep 2

# Démarrer la saga qui devrait échouer
echo "  Démarrage de la saga qui devrait échouer..."
SAGA_FAIL_CORRELATION_ID="saga-fail-$(date +%s)"
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID_FAIL/refund" \
    -H "X-Correlation-ID: $SAGA_FAIL_CORRELATION_ID" > /dev/null

sleep 10

# Vérifier l'échec
REFUND_STATUS_FAIL=$(curl -s "$REFUND_PAYMENT_SERVICE/refunds/$CLAIM_ID_FAIL")
if echo "$REFUND_STATUS_FAIL" | grep -q '"status":"failed"'; then
    echo "    ✓ Échec de saga détecté correctement"
else
    echo "    ✗ Échec de saga non détecté"
fi

echo -e "\n6. Vérification des métriques..."

# Métriques du Payment Service
echo "  a) Métriques du Refund Payment Service:"
PAYMENT_METRICS=$(curl -s "$REFUND_PAYMENT_SERVICE/metrics" | grep "refunds_calculated_total" | head -1)
echo "    $PAYMENT_METRICS"

# Métriques du Inventory Service
echo "  b) Métriques du Refund Inventory Service:"
INVENTORY_METRICS=$(curl -s "$REFUND_INVENTORY_SERVICE/metrics" | grep "stock_adjustments_total" | head -1)
echo "    $INVENTORY_METRICS"

# Statistiques des services
echo "  c) Statistiques des services:"
PAYMENT_STATS=$(curl -s "$REFUND_PAYMENT_SERVICE/refunds/stats")
echo "    Payment Service: $PAYMENT_STATS"

INVENTORY_STATS=$(curl -s "$REFUND_INVENTORY_SERVICE/inventory/stats")
echo "    Inventory Service: $(echo "$INVENTORY_STATS" | grep -o '"total_adjustments":[0-9]*')"

echo -e "\n7. Test de la résilience et de l'idempotence..."

# Test d'idempotence - envoyer le même événement deux fois
echo "  a) Test d'idempotence..."
curl -s -X POST "$CLAIMS_SERVICE/claims/$CLAIM_ID/refund" \
    -H "X-Correlation-ID: $SAGA_CORRELATION_ID" > /dev/null

sleep 5

# Vérifier qu'il n'y a pas de duplication
DUPLICATE_CHECK=$(curl -s "$REFUND_PAYMENT_SERVICE/refunds/stats")
echo "    Vérification de non-duplication: $(echo "$DUPLICATE_CHECK" | grep -o '"total_completed":[0-9]*')"

echo -e "\n=== Test terminé avec succès! ==="
echo ""
echo "Résumé de la saga chorégraphiée:"
echo "1. Claims Service → SagaRemboursementDemarree"
echo "2. Refund Payment Service → RemboursementCalcule"
echo "3. Refund Inventory Service → StockMisAJour"
echo "4. Notification Service → SagaRemboursementTerminee"
echo ""
echo "Pour surveiller les sagas en temps réel:"
echo "  - Grafana: http://localhost:3001 (admin/admin123)"
echo "  - Prometheus: http://localhost:9091"
echo ""
echo "APIs des services saga:"
echo "  - Claims Service: http://localhost:8101/docs"
echo "  - Refund Payment Service: http://localhost:8108/docs"
echo "  - Refund Inventory Service: http://localhost:8109/docs"
echo "  - Notification Service: http://localhost:8102/docs"