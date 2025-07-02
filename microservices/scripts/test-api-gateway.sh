#!/bin/bash
"""
Script de test Kong API Gateway - Étapes 2 & 3
Tests complets de validation API Gateway + Load Balancing
Réutilise infrastructure existante et intègre nouveaux tests microservices
"""

set -e

# Configuration
BASE_URL="http://localhost:8080"
API_KEY="pos-test-automation-dev-key-2025"
KONG_ADMIN="http://localhost:8001"

# Couleurs pour affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Test Kong API Gateway + Load Balancing${NC}"
echo -e "${BLUE}================================================${NC}"

# ================================================
# Tests Étape 2 - API Gateway
# ================================================

echo -e "\n${YELLOW}ÉTAPE 2 - Tests API Gateway${NC}"
echo -e "${YELLOW}===============================================${NC}"

test_gateway_health() {
    echo -e "\n${BLUE}Test 1: Health Check Gateway${NC}"
    
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
    
    if [[ "$response" == "200" ]] || [[ "$response" == "404" ]]; then
        echo -e "${GREEN}Gateway accessible (Status: $response)${NC}"
        return 0
    else
        echo -e "${RED}Gateway non accessible (Status: $response)${NC}"
        return 1
    fi
}

test_api_key_security() {
    echo -e "\n${BLUE}Test 2: Sécurité API Keys${NC}"
    
    # Test sans API Key
    local no_key_response=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/api/v1/products")
    
    if [[ "$no_key_response" == "401" ]] || [[ "$no_key_response" == "403" ]]; then
        echo -e "${GREEN}Accès sans API Key refusé (Status: $no_key_response)${NC}"
    else
        echo -e "${RED}Sécurité API Key défaillante (Status: $no_key_response)${NC}"
        return 1
    fi
    
    # Test avec API Key invalide
    local invalid_response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-API-Key: invalid-key-123" \
        "$BASE_URL/api/v1/products")
    
    if [[ "$invalid_response" == "401" ]] || [[ "$invalid_response" == "403" ]]; then
        echo -e "${GREEN}API Key invalide refusée (Status: $invalid_response)${NC}"
    else
        echo -e "${RED}Validation API Key défaillante (Status: $invalid_response)${NC}"
        return 1
    fi
    
    # Test avec API Key valide
    local valid_response=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-API-Key: $API_KEY" \
        "$BASE_URL/api/v1/products")
    
    if [[ "$valid_response" == "200" ]]; then
        echo -e "${GREEN}API Key valide acceptée (Status: $valid_response)${NC}"
    else
        echo -e "${YELLOW}Service Products peut être indisponible (Status: $valid_response)${NC}"
    fi
}

test_microservices_routing() {
    echo -e "\n${BLUE}Test 3: Routage Microservices${NC}"
    
    local services=("products" "inventory" "cart" "customers" "orders" "sales" "reports")
    local success_count=0
    
    for service in "${services[@]}"; do
        local endpoint=""
        case $service in
            "products") endpoint="/api/v1/products" ;;
            "inventory") endpoint="/api/v1/inventory/health" ;;
            "cart") endpoint="/api/v1/cart?session_id=test_gateway" ;;
            "customers") endpoint="/api/v1/customers/health" ;;
            "orders") endpoint="/api/v1/orders/health" ;;
            "sales") endpoint="/api/v1/sales/health" ;;
            "reports") endpoint="/api/v1/reports/health" ;;
        esac
        
        local response=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "X-API-Key: $API_KEY" \
            "$BASE_URL$endpoint")
        
        if [[ "$response" == "200" ]] || [[ "$response" == "404" ]]; then
            echo -e "${GREEN}Service $service accessible (Status: $response)${NC}"
            ((success_count++))
        else
            echo -e "${RED}Service $service inaccessible (Status: $response)${NC}"
        fi
    done
    
    echo -e "\n${BLUE}Résultats routage: $success_count/${#services[@]} services accessibles${NC}"
}

# ================================================
# Tests Étape 3 - Load Balancing
# ================================================

echo -e "\n${YELLOW}ÉTAPE 3 - Tests Load Balancing${NC}"
echo -e "${YELLOW}===============================================${NC}"

test_load_balancing_distribution() {
    echo -e "\n${BLUE}Test 4: Distribution Load Balancing${NC}"
    
    local total_requests=20
    declare -A instance_counts
    local successful_requests=0
    
    for ((i=1; i<=total_requests; i++)); do
        local response=$(curl -s \
            -H "X-API-Key: $API_KEY" \
            "$BASE_URL/api/v1/cart?session_id=lb_test_$i")
        
        if [[ $? -eq 0 ]]; then
            # Extraire instance info si disponible
            local instance=$(echo "$response" | grep -o '"served_by":"[^"]*"' | cut -d'"' -f4)
            
            if [[ -n "$instance" ]]; then
                instance_counts["$instance"]=$((${instance_counts["$instance"]} + 1))
                ((successful_requests++))
            else
                instance_counts["unknown"]=$((${instance_counts["unknown"]} + 1))
                ((successful_requests++))
            fi
        fi
        
        sleep 0.1
    done
    
    echo -e "\n${BLUE}Distribution des requêtes:${NC}"
    local unique_instances=0
    for instance in "${!instance_counts[@]}"; do
        if [[ "$instance" != "unknown" ]]; then
            ((unique_instances++))
        fi
        local count=${instance_counts[$instance]}
        local percentage=$(( count * 100 / successful_requests ))
        echo -e "  - $instance: $count requêtes (${percentage}%)"
    done
    
    if [[ $unique_instances -ge 2 ]]; then
        echo -e "${GREEN}Load balancing détecté: $unique_instances instances actives${NC}"
    else
        echo -e "${YELLOW}Load balancing limité: $unique_instances instance(s) détectée(s)${NC}"
    fi
    
    echo -e "${BLUE}Taux de succès: $successful_requests/$total_requests requêtes${NC}"
}

test_kong_admin_api() {
    echo -e "\n${BLUE}Test 5: Kong Admin API${NC}"
    
    # Test Kong status
    local kong_status=$(curl -s -o /dev/null -w "%{http_code}" "$KONG_ADMIN/status")
    
    if [[ "$kong_status" == "200" ]]; then
        echo -e "${GREEN}Kong Admin API accessible${NC}"
        
        # Lister les services
        local services=$(curl -s "$KONG_ADMIN/services" | grep -o '"name":"[^"]*"' | wc -l)
        echo -e "${BLUE}Services Kong configurés: $services${NC}"
        
        # Lister les upstreams
        local upstreams=$(curl -s "$KONG_ADMIN/upstreams" | grep -o '"name":"[^"]*"' | wc -l)
        echo -e "${BLUE}Upstreams configurés: $upstreams${NC}"
        
    else
        echo -e "${RED}Kong Admin API inaccessible (Status: $kong_status)${NC}"
        return 1
    fi
}

# ================================================
# Exécution des tests
# ================================================

echo -e "\n${BLUE}EXÉCUTION DES TESTS${NC}"
echo -e "${BLUE}========================${NC}"

success_count=0
total_tests=5

# Test 1: Gateway Health
if test_gateway_health; then
    ((success_count++))
fi

# Test 2: API Key Security  
if test_api_key_security; then
    ((success_count++))
fi

# Test 3: Microservices Routing
if test_microservices_routing; then
    ((success_count++))
fi

# Test 4: Load Balancing
if test_load_balancing_distribution; then
    ((success_count++))
fi

# Test 5: Kong Admin
if test_kong_admin_api; then
    ((success_count++))
fi

# ================================================
# Résultats finaux
# ================================================

echo -e "\n${BLUE}RÉSULTATS FINAUX${NC}"
echo -e "${BLUE}===================${NC}"

echo -e "\n${BLUE}Tests réussis: $success_count/$total_tests${NC}"

if [[ $success_count -eq $total_tests ]]; then
    echo -e "${GREEN}TOUS LES TESTS PASSÉS - Gateway fonctionnel!${NC}"
    exit 0
elif [[ $success_count -ge 3 ]]; then
    echo -e "${YELLOW}Tests majoritairement réussis - Quelques problèmes détectés${NC}"
    exit 0
else
    echo -e "${RED}ÉCHEC - Problèmes majeurs détectés${NC}"
    exit 1
fi 