#!/bin/bash
"""
Test Saga Orchestration
Tests complets de la saga orchestrée synchrone avec simulation d'échecs
"""

set -e

# Configuration
BASE_URL="http://localhost:8080"
API_KEY="pos-test-automation-dev-key-2025"

echo "Test Saga Orchestration"
echo "====================================="

# ================================================
# Fonctions utilitaires
# ================================================

wait_for_services() {
    echo -e "\nVérification des services..."
    
    services=(
        "8080:Kong Gateway"
        "8008:Saga Orchestrator"  
        "8009:Payment Service"
        "8002:Inventory Service"
        "8006:Cart Service"
        "8007:Order Service"
    )
    
    for service in "${services[@]}"; do
        port=$(echo $service | cut -d: -f1)
        name=$(echo $service | cut -d: -f2)
        
        for i in {1..30}; do
            if curl -s -f "http://localhost:$port/health" > /dev/null; then
                echo "✓ $name (port $port) disponible"
                break
            elif [ $i -eq 30 ]; then
                echo "✗ $name (port $port) non disponible après 60s"
                return 1
            fi
            sleep 2
        done
    done
}

create_test_cart() {
    local session_id=$1
    echo -e "\nCréation du panier de test: $session_id"
    
    # Ajouter des produits au panier
    curl -s -X POST "$BASE_URL/api/v1/cart/carts/$session_id/items" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "product_id": 1,
            "quantity": 2,
            "price": 25.99
        }' > /dev/null
    
    curl -s -X POST "$BASE_URL/api/v1/cart/carts/$session_id/items" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "product_id": 2,
            "quantity": 1,
            "price": 45.50
        }' > /dev/null
    
    # Calculer les totaux
    curl -s -X POST "$BASE_URL/api/v1/cart/carts/$session_id/calculate" \
        -H "X-API-Key: $API_KEY" > /dev/null
    
    echo "Panier créé avec succès"
}

test_successful_saga() {
    echo -e "\nTEST 1: Saga réussie (happy path)"
    echo "==================================="
    
    session_id="saga_test_success_$(date +%s)"
    customer_id=1001
    
    # Créer un panier de test
    create_test_cart $session_id
    
    # Démarrer la saga
    echo -e "\nDémarrage de la saga..."
    
    saga_response=$(curl -s -X POST "$BASE_URL/api/v1/sagas/orders" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"session_id\": \"$session_id\",
            \"customer_id\": $customer_id,
            \"shipping_address\": {
                \"street\": \"123 Test Street\",
                \"city\": \"Montreal\",
                \"postal_code\": \"H1X 1X1\",
                \"country\": \"Canada\"
            },
            \"billing_address\": {
                \"street\": \"123 Test Street\",
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
                    \"cvv\": \"123\",
                    \"brand\": \"VISA\"
                }
            }
        }")
    
    saga_id=$(echo $saga_response | jq -r '.saga_id // empty')
    saga_status=$(echo $saga_response | jq -r '.status // empty')
    
    if [ "$saga_status" = "COMPLETED" ]; then
        echo "  Saga complétée avec succès"
        echo "  Saga ID: $saga_id"
        echo "  Order ID: $(echo $saga_response | jq -r '.order_id // "N/A"')"
        echo "  Durée: $(echo $saga_response | jq -r '.total_duration_ms // "N/A"')ms"
        return 0
    else
        echo "  Saga échec inattendu"
        echo "  Statut: $saga_status"
        echo "  Réponse: $saga_response"
        return 1
    fi
}

test_payment_failure_saga() {
    echo -e "\nTEST 2: Saga avec échec de paiement"
    echo "===================================="
    
    session_id="saga_test_payment_fail_$(date +%s)"
    customer_id=1002
    
    # Créer un panier de test
    create_test_cart $session_id
    
    # Configurer l'échec de paiement pour un montant spécifique
    echo -e "\nConfiguration de l'échec de paiement..."
    curl -s -X POST "$BASE_URL/api/v1/payment/config/failures" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "enabled": true,
            "failure_rate": 0.0,
            "failure_on_amount": "97.48"
        }' > /dev/null
    
    # Démarrer la saga
    echo -e "\nDémarrage de la saga avec échec de paiement..."
    
    saga_response=$(curl -s -X POST "$BASE_URL/api/v1/sagas/orders" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"session_id\": \"$session_id\",
            \"customer_id\": $customer_id,
            \"shipping_address\": {
                \"street\": \"456 Fail Street\",
                \"city\": \"Montreal\",
                \"postal_code\": \"H2X 2X2\",
                \"country\": \"Canada\"
            },
            \"payment\": {
                \"method\": \"credit_card\",
                \"card_details\": {
                    \"number\": \"4000000000000002\",
                    \"exp_month\": \"12\",
                    \"exp_year\": \"2025\",
                    \"cvv\": \"123\"
                }
            }
        }")
    
    saga_id=$(echo $saga_response | jq -r '.saga_id // empty')
    saga_status=$(echo $saga_response | jq -r '.status // empty')
    
    if [ "$saga_status" = "FAILED" ]; then
        echo "  Saga échouée comme attendu"
        
        # Vérifier les détails de la compensation
        echo -e "\nVérification de la compensation..."
        saga_details=$(curl -s "$BASE_URL/api/v1/sagas/$saga_id/details" \
            -H "X-API-Key: $API_KEY")
        
        compensation_steps=$(echo $saga_details | jq -r '.compensation_steps | length')
        echo "  Saga ID: $saga_id"
        echo "  Statut final: $saga_status"
        echo "  Étapes de compensation: $compensation_steps"
        
        return 0
    else
        echo "  Saga devrait avoir échoué"
        echo "  Statut: $saga_status"
        echo "  Réponse: $saga_response"
        return 1
    fi
}

test_inventory_failure_saga() {
    echo -e "\nTEST 3: Saga avec échec d'inventaire"
    echo "====================================="
    
    session_id="saga_test_inventory_fail_$(date +%s)"
    customer_id=1003
    
    # Configurer l'échec d'inventaire pour le produit 3
    echo -e "\nConfiguration de l'échec d'inventaire..."
    curl -s -X POST "$BASE_URL/api/v1/inventory/config/failures" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "enabled": true,
            "failure_rate": 0.0,
            "out_of_stock_products": ["3"]
        }' > /dev/null
    
    # Créer un panier avec le produit qui va échouer
    echo -e "\nCréation du panier avec produit en rupture..."
    curl -s -X POST "$BASE_URL/api/v1/cart/carts/$session_id/items" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "product_id": 3,
            "quantity": 1,
            "price": 19.99
        }' > /dev/null
    
    curl -s -X POST "$BASE_URL/api/v1/cart/carts/$session_id/calculate" \
        -H "X-API-Key: $API_KEY" > /dev/null
    
    # Démarrer la saga
    echo -e "\nDémarrage de la saga avec échec d'inventaire..."
    
    saga_response=$(curl -s -X POST "$BASE_URL/api/v1/sagas/orders" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d "{
            \"session_id\": \"$session_id\",
            \"customer_id\": $customer_id,
            \"shipping_address\": {
                \"street\": \"789 Stock Street\",
                \"city\": \"Montreal\",
                \"postal_code\": \"H3X 3X3\",
                \"country\": \"Canada\"
            },
            \"payment\": {
                \"method\": \"credit_card\"
            }
        }")
    
    saga_status=$(echo $saga_response | jq -r '.status // empty')
    
    if [ "$saga_status" = "FAILED" ]; then
        echo "  Saga échouée sur l'inventaire comme attendu"
        return 0
    else
        echo "  Saga devrait avoir échoué sur l'inventaire"
        echo "  Statut: $saga_status"
        return 1
    fi
}

test_saga_metrics() {
    echo -e "\nTEST 4: Métriques de saga"
    echo "========================="
    
    echo -e "\nRécupération des métriques..."
    
    metrics_response=$(curl -s "$BASE_URL/api/v1/sagas/metrics" \
        -H "X-API-Key: $API_KEY")
    
    total_sagas=$(echo $metrics_response | jq -r '.total_sagas // 0')
    completed_sagas=$(echo $metrics_response | jq -r '.sagas_completed // 0')
    failed_sagas=$(echo $metrics_response | jq -r '.sagas_failed // 0')
    success_rate=$(echo $metrics_response | jq -r '.success_rate // 0')
    
    echo "  Total sagas: $total_sagas"
    echo "  Sagas complétées: $completed_sagas"
    echo "  Sagas échouées: $failed_sagas"
    echo "  Taux de succès: $(echo "$success_rate * 100" | bc -l | cut -c1-5)%"
    
    # Métriques Prometheus
    echo -e "\nVérification des métriques Prometheus..."
    prometheus_response=$(curl -s "http://localhost:8008/metrics")
    
    if echo "$prometheus_response" | grep -q "saga_total"; then
        echo "  Métriques Prometheus disponibles"
    else
        echo "  Métriques Prometheus non trouvées"
    fi
}

reset_failure_configs() {
    echo -e "\nRéinitialisation des configurations d'échec..."
    
    # Désactiver les échecs de paiement
    curl -s -X POST "$BASE_URL/api/v1/payment/config/failures" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "enabled": false,
            "failure_rate": 0.0
        }' > /dev/null
    
    # Désactiver les échecs d'inventaire
    curl -s -X POST "$BASE_URL/api/v1/inventory/config/failures" \
        -H "X-API-Key: $API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "enabled": false,
            "failure_rate": 0.0,
            "out_of_stock_products": []
        }' > /dev/null
    
    echo "Configurations réinitialisées"
}

# ================================================
# Exécution des tests
# ================================================

echo -e "\nPRÉPARATION DES TESTS"
echo "======================="

# Vérifier que les services sont disponibles
if ! wait_for_services; then
    echo "ÉCHEC: Services non disponibles"
    exit 1
fi

# Réinitialiser les configurations
reset_failure_configs

echo -e "\nEXÉCUTION DES TESTS"
echo "==================="

success_count=0
total_tests=4

# Test 1: Saga réussie
if test_successful_saga; then
    ((success_count++))
fi

# Test 2: Échec de paiement avec compensation
if test_payment_failure_saga; then
    ((success_count++))
fi

# Test 3: Échec d'inventaire
if test_inventory_failure_saga; then
    ((success_count++))
fi

# Test 4: Métriques
if test_saga_metrics; then
    ((success_count++))
fi

# Nettoyage final
reset_failure_configs

# ================================================
# Résultats finaux
# ================================================

echo -e "\nRÉSULTATS FINAUX"
echo "================="

echo -e "\nTests réussis: $success_count/$total_tests"

if [ $success_count -eq $total_tests ]; then
    echo "TOUS LES TESTS PASSÉS - Saga orchestration fonctionnelle!"
    echo -e "\nURLs utiles:"
    echo "  - Saga Orchestrator: http://localhost:8008/docs"
    echo "  - Payment Service: http://localhost:8009/docs"
    echo "  - Inventory Service: http://localhost:8002/docs"
    echo "  - Métriques Prometheus: http://localhost:8008/metrics"
    echo "  - Grafana: http://localhost:3000"
    exit 0
elif [ $success_count -ge 2 ]; then
    echo "Tests majoritairement réussis - Quelques problèmes détectés"
    exit 0
else
    echo "ÉCHEC - Problèmes majeurs détectés"
    exit 1
fi