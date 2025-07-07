#!/bin/bash
"""
Générateur de métriques saga en continu
Pour alimenter Prometheus et Grafana avec des données dynamiques
"""

echo "Démarrage du générateur de métriques saga"
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000"
echo "Génération de sagas toutes les 15 secondes..."
echo ""

counter=1
while true; do
    timestamp=$(date +%s)
    session_id="metrics_gen_${timestamp}_${counter}"
    customer_id=$((4000 + counter))
    
    echo "[$counter] Saga: $session_id (Customer: $customer_id)"
    
    # Create cart
    curl -s -X POST "http://localhost:8006/api/v1/carts/$session_id/items" \
      -H "Content-Type: application/json" \
      -d "{
        \"product_id\": $((counter % 5 + 1)),
        \"quantity\": $((counter % 3 + 1)),
        \"price\": $((10 + counter % 20)).99
      }" > /dev/null
    
    # Calculate cart
    curl -s -X POST "http://localhost:8006/api/v1/carts/$session_id/calculate" > /dev/null
    
    # Start saga
    saga_response=$(curl -s -X POST "http://localhost:8008/api/v1/sagas/orders" \
      -H "Content-Type: application/json" \
      -d "{
        \"session_id\": \"$session_id\",
        \"customer_id\": $customer_id,
        \"shipping_address\": {
          \"street\": \"Generator St $counter\",
          \"city\": \"Montreal\",
          \"postal_code\": \"H1X 1X1\",
          \"country\": \"Canada\"
        },
        \"payment\": {
          \"method\": \"credit_card\",
          \"card_details\": {
            \"number\": \"4111111111111111\",
            \"exp_month\": \"12\",
            \"exp_year\": \"2025\",
            \"cvv\": \"123\"
          }
        }
      }")
    
    # Extract status for display
    status=$(echo "$saga_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 2>/dev/null || echo "UNKNOWN")
    echo "    ↳ Status: $status"
    
    # Show current metrics count
    if (( counter % 5 == 0 )); then
        total_sagas=$(curl -s "http://localhost:8008/metrics" | grep -c "saga_requests_total{")
        echo "     Total sagas metrics: $total_sagas"
    fi
    
    counter=$((counter + 1))
    
    # Stop after 50 sagas to avoid infinite loop
    if (( counter > 50 )); then
        echo ""
        echo "50 sagas générées. Arrêt du générateur."
        echo "Vérifiez Prometheus/Grafana pour voir les métriques."
        break
    fi
    
    sleep 15
done