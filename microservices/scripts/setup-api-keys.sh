#!/bin/bash
# Script de configuration des clés API pour Kong
# Point d'entrée unique avec sécurité et authentification

set -e

KONG_ADMIN_URL="http://localhost:8001"
KONG_PROXY_URL="http://localhost:8080"

echo "Configuration de Kong API Gateway - Étape 2"
echo "============================================="

# Fonction pour attendre que Kong soit prêt
wait_for_kong() {
    echo "Attente de Kong Admin API..."
    for i in {1..30}; do
        if curl -s -f "$KONG_ADMIN_URL" > /dev/null 2>&1; then
            echo "Kong Admin API est prêt"
            return 0
        fi
        echo "   Tentative $i/30..."
        sleep 2
    done
    echo "Kong Admin API non accessible après 60s"
    exit 1
}

# Fonction pour créer un consumer
create_consumer() {
    local username=$1
    local custom_id=$2
    local tags=$3
    
    echo "Création du consumer: $username"
    curl -s -X POST "$KONG_ADMIN_URL/consumers" \
        -H "Content-Type: application/json" \
        -d "{
            \"username\": \"$username\",
            \"custom_id\": \"$custom_id\",
            \"tags\": $tags
        }" | jq '.' || echo "Consumer $username déjà existant"
}

# Fonction pour créer une clé API
create_api_key() {
    local consumer=$1
    local key=$2
    local tags=$3
    
    echo "Création de la clé API pour: $consumer"
    curl -s -X POST "$KONG_ADMIN_URL/consumers/$consumer/key-auth" \
        -H "Content-Type: application/json" \
        -d "{
            \"key\": \"$key\",
            \"tags\": $tags
        }" | jq '.' || echo "Clé API pour $consumer déjà existante"
}

# Fonction pour créer un secret JWT
create_jwt_secret() {
    local consumer=$1
    local key=$2
    local secret=$3
    local algorithm="HS256"
    
    echo "Création du secret JWT pour: $consumer"
    curl -s -X POST "$KONG_ADMIN_URL/consumers/$consumer/jwt" \
        -H "Content-Type: application/json" \
        -d "{
            \"key\": \"$key\",
            \"secret\": \"$secret\",
            \"algorithm\": \"$algorithm\"
        }" | jq '.' || echo "Secret JWT pour $consumer déjà existant"
}

# Fonction pour tester l'accès
test_api_access() {
    local endpoint=$1
    local api_key=$2
    local description=$3
    
    echo "Test d'accès: $description"
    response=$(curl -s -w "\n%{http_code}" \
        -H "X-API-Key: $api_key" \
        "$KONG_PROXY_URL$endpoint")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        echo "$description - Succès (200)"
    else
        echo "$description - Échec ($http_code)"
        echo "   Réponse: $body"
    fi
}

# Début de la configuration
wait_for_kong

echo ""
echo "ÉTAPE 1: Création des Consumers"
echo "================================="

# Création des consumers
create_consumer "pos-api-client" "pos-external-api" '["external", "api-client"]'
create_consumer "pos-web-app" "pos-web-interface" '["web", "frontend"]'
create_consumer "pos-mobile-app" "pos-mobile-client" '["mobile", "app"]'
create_consumer "pos-test-client" "pos-automated-tests" '["testing", "automation"]'

echo ""
echo "ÉTAPE 2: Configuration des Clés API"
echo "======================================"

# Création des clés API
create_api_key "pos-api-client" "pos-ext-api-2025-prod-key-secure" '["external", "production"]'
create_api_key "pos-web-app" "pos-web-app-2025-frontend-key" '["web", "frontend"]'
create_api_key "pos-mobile-app" "pos-mobile-2025-app-secure-key" '["mobile", "production"]'
create_api_key "pos-test-client" "pos-test-automation-dev-key-2025" '["testing", "development"]'

echo ""
echo "ÉTAPE 3: Configuration JWT"
echo "============================="

# Création des secrets JWT
create_jwt_secret "pos-api-client" "customer-jwt-issuer" "jwt-customer-secret-2025"
create_jwt_secret "pos-web-app" "web-jwt-issuer" "jwt-customer-secret-2025"
create_jwt_secret "pos-mobile-app" "mobile-jwt-issuer" "jwt-customer-secret-2025"

echo ""
echo "ÉTAPE 4: Tests de Validation"
echo "==============================="

# Tests d'accès avec les clés API
echo "Tests d'accès public (sans authentification):"
curl -s -w " (Status: %{http_code})\n" "$KONG_PROXY_URL/health" -o /dev/null
echo "Health check: $KONG_PROXY_URL/health"

echo ""
echo "Tests d'accès avec clés API:"
test_api_access "/api/v1/products" "pos-web-app-2025-frontend-key" "Produits (Web App)"
test_api_access "/api/v1/categories" "pos-mobile-2025-app-secure-key" "Catégories (Mobile)"
test_api_access "/api/v1/inventory" "pos-ext-api-2025-prod-key-secure" "Inventaire (API externe)"
test_api_access "/api/v1/cart" "pos-test-automation-dev-key-2025" "Panier (Tests auto)"

echo ""
echo "Test d'accès sans clé API (doit échouer):"
response=$(curl -s -w "\n%{http_code}" "$KONG_PROXY_URL/api/v1/products")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "401" ] || [ "$http_code" = "403" ]; then
    echo "Protection API Key fonctionne (HTTP $http_code)"
else
    echo "Protection API Key défaillante (HTTP $http_code)"
fi

echo ""
echo "ÉTAPE 5: Informations de Configuration"
echo "========================================="

echo "Points d'accès principaux:"
echo "   - API Gateway (Proxy): $KONG_PROXY_URL"
echo "   - Kong Admin API: $KONG_ADMIN_URL"
echo "   - Monitoring Grafana: http://localhost:3000"
echo "   - Prometheus: http://localhost:9090"

echo ""
echo "Clés API configurées:"
echo "   - Application externe: pos-ext-api-2025-prod-key-secure"
echo "   - Interface web: pos-web-app-2025-frontend-key"
echo "   - Application mobile: pos-mobile-2025-app-secure-key"
echo "   - Tests automatisés: pos-test-automation-dev-key-2025"

echo ""
echo "Utilisation des clés:"
echo "   curl -H 'X-API-Key: pos-web-app-2025-frontend-key' $KONG_PROXY_URL/api/v1/products"
echo "   curl -H 'api-key: pos-mobile-2025-app-secure-key' $KONG_PROXY_URL/api/v1/cart"

echo ""
echo "Configuration Kong API Gateway terminée avec succès!"
echo "Point d'entrée unique avec sécurité, routage dynamique et logging activés" 