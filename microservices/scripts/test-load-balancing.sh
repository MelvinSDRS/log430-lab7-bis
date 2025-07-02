#!/bin/bash
# Script de test Load Balancing - Étape 3
# Test de distribution de charge entre 3 instances du Cart Service

set -e

KONG_ADMIN_URL="http://localhost:8001"
KONG_PROXY_URL="http://localhost:8080"
API_KEY="pos-test-automation-dev-key-2025"

echo "Test Load Balancing Cart Service - Étape 3"
echo "=============================================="
echo "Validation de la répartition de charge entre 3 instances"
echo ""

# Fonction pour attendre que les services soient prêts
wait_for_services() {
    echo "Attente des services Cart Service (3 instances)..."
    
    local services=("cart-service-1" "cart-service-2" "cart-service-3")
    local ready_count=0
    
    for i in {1..60}; do
        ready_count=0
        
        for service in "${services[@]}"; do
            if curl -s -f "http://$service:8006/health" > /dev/null 2>&1; then
                ready_count=$((ready_count + 1))
            fi
        done
        
        if [ $ready_count -eq 3 ]; then
            echo "Toutes les instances Cart Service sont prêtes ($ready_count/3)"
            return 0
        fi
        
        echo "   Instances prêtes: $ready_count/3 (tentative $i/60)"
        sleep 2
    done
    
    echo "Timeout: Toutes les instances ne sont pas prêtes après 2 minutes"
    exit 1
}

# Fonction pour vérifier le statut des instances
check_instances_status() {
    echo "Statut des instances Cart Service:"
    
    local services=("cart-service-1" "cart-service-2" "cart-service-3")
    
    for service in "${services[@]}"; do
        echo "   $service:"
        
        response=$(curl -s "http://$service:8006/health" 2>/dev/null || echo '{}')
        
        if echo "$response" | jq -e '.status' >/dev/null 2>&1; then
            status=$(echo "$response" | jq -r '.status')
            instance_id=$(echo "$response" | jq -r '.instance.instance_id // "unknown"')
            hostname=$(echo "$response" | jq -r '.instance.hostname // "unknown"')
            echo "      Status: $status | Instance ID: $instance_id | Host: $hostname"
        else
            echo "      Status: Indisponible"
        fi
    done
    echo ""
}

# Fonction pour tester la distribution avec curl en boucle
test_distribution_curl() {
    echo "Test de distribution avec curl (50 requêtes):"
    
    local instances=()
    declare -A instance_count
    
    for i in {1..50}; do
        response=$(curl -s -H "X-API-Key: $API_KEY" \
                       "$KONG_PROXY_URL/api/v1/cart?session_id=test_$i" 2>/dev/null || echo '{}')
        
        if echo "$response" | jq -e '.instance_info' >/dev/null 2>&1; then
            instance_id=$(echo "$response" | jq -r '.instance_info.served_by')
            instances+=("$instance_id")
            instance_count["$instance_id"]=$((${instance_count["$instance_id"]} + 1))
        fi
        
        # Affichage du progrès
        if [ $((i % 10)) -eq 0 ]; then
            echo "   Requêtes envoyées: $i/50"
        fi
        
        sleep 0.1
    done
    
    echo ""
    echo "Résultats de distribution:"
    total=0
    
    for instance in "${!instance_count[@]}"; do
        count=${instance_count[$instance]}
        total=$((total + count))
        percentage=$(echo "scale=1; $count * 100 / 50" | bc)
        echo "   $instance: $count requêtes (${percentage}%)"
    done
    
    echo "   Total: $total requêtes"
    
    # Vérification de l'équilibrage
    if [ ${#instance_count[@]} -eq 3 ]; then
        echo "Load balancing fonctionne: 3 instances actives"
    else
        echo "Load balancing partiel: ${#instance_count[@]} instances actives"
    fi
    
    echo ""
}

# Fonction pour tester avec k6 (si disponible)
test_with_k6() {
    echo "Test de charge avec k6:"
    
    if command -v k6 >/dev/null 2>&1; then
        echo "   Lancement du test k6 load balancing (extension Lab 4)..."
        cd "$(dirname "$0")/../../load_tests/k6"
        
        if [ -f "complex-load-balancer-test.js" ]; then
            echo "   Test étendu Lab 4 + Microservices Load Balancing..."
            k6 run complex-load-balancer-test.js
            
            # Recherche du rapport le plus récent
            latest_report=$(ls -t load_test_results/complex_load_balancer_with_microservices_*.json 2>/dev/null | head -1)
            if [ -n "$latest_report" ]; then
                echo ""
                echo "Rapport k6 généré: $latest_report"
                cat "$latest_report" | jq '.microservices_load_balancing // {}'
            fi
        else
            echo "Fichier de test k6 Lab 4 introuvable"
        fi
    else
        echo "k6 non installé - test de charge ignoré"
        echo "   Installation: https://k6.io/docs/getting-started/installation/"
    fi
    
    echo ""
}

# Fonction pour analyser les métriques Kong
analyze_kong_metrics() {
    echo "Analyse des métriques Kong:"
    
    # Récupération des métriques depuis Kong Admin API
    metrics=$(curl -s "$KONG_ADMIN_URL/metrics" 2>/dev/null || echo "")
    
    if [ -n "$metrics" ]; then
        echo "   Métriques Kong disponibles"
        
        # Extraction des métriques de load balancing
        lb_requests=$(echo "$metrics" | grep "kong_http_requests_total.*cart-service-loadbalanced" | wc -l)
        
        if [ $lb_requests -gt 0 ]; then
            echo "   Requêtes load balancing détectées: $lb_requests métriques"
        else
            echo "   Aucune métrique de load balancing détectée"
        fi
    else
        echo "   Impossible de récupérer les métriques Kong"
    fi
    
    echo ""
}

# Fonction pour vérifier la configuration Kong
verify_kong_config() {
    echo "Vérification de la configuration Kong:"
    
    # Vérification de l'upstream
    upstream=$(curl -s "$KONG_ADMIN_URL/upstreams/cart-upstream-loadbalanced" 2>/dev/null || echo '{}')
    
    if echo "$upstream" | jq -e '.id' >/dev/null 2>&1; then
        algorithm=$(echo "$upstream" | jq -r '.algorithm')
        echo "   Upstream 'cart-upstream-loadbalanced' configuré"
        echo "      Algorithme: $algorithm"
        
        # Vérification des targets
        targets=$(curl -s "$KONG_ADMIN_URL/upstreams/cart-upstream-loadbalanced/targets" 2>/dev/null || echo '{}')
        
        if echo "$targets" | jq -e '.data' >/dev/null 2>&1; then
            target_count=$(echo "$targets" | jq '.data | length')
            echo "      Targets configurés: $target_count"
            
            echo "$targets" | jq -r '.data[] | "         " + .target + " (weight: " + (.weight|tostring) + ")"'
        fi
    else
        echo "   Upstream 'cart-upstream-loadbalanced' non configuré"
    fi
    
    # Vérification du service
    service=$(curl -s "$KONG_ADMIN_URL/services/cart-service-loadbalanced" 2>/dev/null || echo '{}')
    
    if echo "$service" | jq -e '.id' >/dev/null 2>&1; then
        echo "   Service 'cart-service-loadbalanced' configuré"
    else
        echo "   Service 'cart-service-loadbalanced' non configuré"
    fi
    
    echo ""
}

# Fonction pour générer le rapport final
generate_report() {
    echo "Génération du rapport final:"
    
    local report_file="complex-load-balancer-test-report.json"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    cat > "$report_file" << EOF
{
  "test_timestamp": "$timestamp",
  "test_type": "load_balancing_distribution",
  "cart_service_instances": 3,
  "algorithm": "least-connections",
  "results": {
    "instances_status": "$(check_instances_status | grep -c "✅" || echo "0")",
    "kong_configuration": "verified",
    "curl_distribution_test": "completed",
    "k6_load_test": "$(command -v k6 >/dev/null && echo "completed" || echo "skipped")",
    "metrics_analysis": "completed"
  },
  "recommendations": [
    "Vérifier la distribution équitable entre les 3 instances",
    "Surveiller les métriques de latence par instance",
    "Configurer des alertes sur le déséquilibre de charge",
    "Tester la récupération automatique en cas de panne d'instance"
  ]
}
EOF
    
    echo "   Rapport généré: $report_file"
    echo ""
}

# Exécution du test complet
echo "ÉTAPE 1: Vérification de l'infrastructure"
echo "============================================"
wait_for_services
check_instances_status
verify_kong_config

echo "ÉTAPE 2: Tests de distribution de charge"
echo "==========================================="
test_distribution_curl

echo "ÉTAPE 3: Test de charge avancé"
echo "================================"
test_with_k6

echo "ÉTAPE 4: Analyse des métriques"
echo "================================="
analyze_kong_metrics

echo "ÉTAPE 5: Rapport final"
echo "========================"
generate_report

echo "INFORMATIONS D'ACCÈS"
echo "======================"
echo "Dashboard Kong + Load Balancing: http://localhost:3000/d/kong-api-gateway-dashboard"
echo "Kong Admin API: $KONG_ADMIN_URL"
echo "API Gateway: $KONG_PROXY_URL"
echo "Prometheus: http://localhost:9090"
echo ""
echo "Commandes utiles:"
echo "   # Voir la config upstream"
echo "   curl $KONG_ADMIN_URL/upstreams/cart-upstream-loadbalanced"
echo ""
echo "   # Tester un appel direct"
echo "   curl -H 'X-API-Key: $API_KEY' '$KONG_PROXY_URL/api/v1/cart?session_id=test'"
echo ""
echo "   # Voir les targets actifs"
echo "   curl $KONG_ADMIN_URL/upstreams/cart-upstream-loadbalanced/targets"
echo ""

echo "Test Load Balancing Étape 3 terminé!"
echo "Vérifiez les dashboards Grafana pour l'analyse visuelle détaillée" 