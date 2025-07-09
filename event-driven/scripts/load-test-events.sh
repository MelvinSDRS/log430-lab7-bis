#!/bin/bash

# Test de charge pour l'architecture événementielle
echo "=== Test de charge - Architecture événementielle ==="

BASE_URL="http://localhost"
CLAIMS_SERVICE="${BASE_URL}:8101"

# Paramètres du test
NUM_CLAIMS=${1:-10}
CONCURRENT_REQUESTS=${2:-3}

echo "Génération de $NUM_CLAIMS réclamations avec $CONCURRENT_REQUESTS requêtes concurrentes..."

# Types de réclamations
CLAIM_TYPES=("product_defect" "delivery_issue" "billing_error" "service_complaint")
CUSTOMERS=("customer_001" "customer_002" "customer_003" "customer_004" "customer_005")
AGENTS=("agent_001" "agent_002" "agent_003")

# Fonction pour créer et traiter une réclamation
process_claim() {
    local claim_num=$1
    local customer_id=${CUSTOMERS[$((RANDOM % ${#CUSTOMERS[@]}))]}
    local claim_type=${CLAIM_TYPES[$((RANDOM % ${#CLAIM_TYPES[@]}))]}
    local agent_id=${AGENTS[$((RANDOM % ${#AGENTS[@]}))]}
    local correlation_id="load-test-$claim_num-$(date +%s)"
    
    echo "  Traitement de la réclamation $claim_num..."
    
    # Créer la réclamation
    local claim_response=$(curl -s -X POST "$CLAIMS_SERVICE/claims" \
        -H "Content-Type: application/json" \
        -H "X-Correlation-ID: $correlation_id" \
        -d "{
            \"customer_id\": \"$customer_id\",
            \"claim_type\": \"$claim_type\",
            \"description\": \"Réclamation générée automatiquement #$claim_num\",
            \"product_id\": \"product_$(($claim_num % 10))\"
        }")
    
    local claim_id=$(echo "$claim_response" | grep -o '"claim_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$claim_id" ]; then
        echo "    Réclamation $claim_num créée: $claim_id"
        
        # Attendre un peu
        sleep 1
        
        # Affecter à un agent
        curl -s -X POST "$CLAIMS_SERVICE/claims/$claim_id" \
            -H "Content-Type: application/json" \
            -H "X-Correlation-ID: $correlation_id-assign" \
            -d "{\"agent_id\": \"$agent_id\"}" > /dev/null
        
        sleep 1
        
        # Démarrer le traitement
        curl -s -X POST "$CLAIMS_SERVICE/claims/$claim_id/start" \
            -H "X-Correlation-ID: $correlation_id-start" > /dev/null
        
        # Simuler un délai de traitement variable
        sleep $((RANDOM % 3 + 1))
        
        # Résoudre la réclamation
        curl -s -X POST "$CLAIMS_SERVICE/claims/$claim_id/resolve" \
            -H "Content-Type: application/json" \
            -H "X-Correlation-ID: $correlation_id-resolve" \
            -d "{\"resolution\": \"Résolution automatique pour réclamation #$claim_num\"}" > /dev/null
        
        sleep 1
        
        # 80% de chance de fermer la réclamation
        if [ $((RANDOM % 10)) -lt 8 ]; then
            curl -s -X POST "$CLAIMS_SERVICE/claims/$claim_id/close" \
                -H "X-Correlation-ID: $correlation_id-close" > /dev/null
        fi
        
        echo "    Réclamation $claim_num traitée complètement"
    else
        echo "    Erreur lors de la création de la réclamation $claim_num"
    fi
}

# Heure de début
START_TIME=$(date +%s)

# Lancer les réclamations en parallèle
for i in $(seq 1 $NUM_CLAIMS); do
    # Limiter le nombre de processus concurrents
    while [ $(jobs -r | wc -l) -ge $CONCURRENT_REQUESTS ]; do
        sleep 0.5
    done
    
    process_claim $i &
done

# Attendre que tous les processus se terminent
wait

# Heure de fin
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "=== Résultats du test de charge ==="
echo "Réclamations générées: $NUM_CLAIMS"
echo "Durée totale: ${DURATION}s"
echo "Débit: $(echo "scale=2; $NUM_CLAIMS / $DURATION" | bc) réclamations/seconde"

# Attendre que tous les événements soient traités
echo ""
echo "Attente du traitement complet des événements (10s)..."
sleep 10

# Afficher les statistiques finales
echo ""
echo "=== Statistiques finales ==="

# Statistiques des notifications
echo "Notifications:"
curl -s "$BASE_URL:8102/notifications/stats" | jq . 2>/dev/null || curl -s "$BASE_URL:8102/notifications/stats"

echo ""
echo "Audit:"
curl -s "$BASE_URL:8103/audit/stats" | jq . 2>/dev/null || curl -s "$BASE_URL:8103/audit/stats"

echo ""
echo "Dashboard:"
curl -s "$BASE_URL:8105/dashboard" | jq '.summary' 2>/dev/null || curl -s "$BASE_URL:8105/dashboard"

echo ""
echo "=== Test de charge terminé ==="