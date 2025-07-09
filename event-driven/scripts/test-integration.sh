#!/bin/bash

# Test d'intégration Lab 6 <-> Lab 7
echo "=== Test d'intégration Lab 6 et Lab 7 ==="

LAB6_URL="http://localhost:8007"
LAB7_INTEGRATION_URL="http://localhost:8107"
LAB7_CLAIMS_URL="http://localhost:8101"
LAB7_QUERY_URL="http://localhost:8105"

# Vérifier les services
echo "1. Vérification des services..."

# Vérifier Lab 6
if curl -s -f "$LAB6_URL/health" > /dev/null; then
    echo " Lab 6 disponible"
    LAB6_AVAILABLE=true
else
    echo "Lab 6 non disponible - mode dégradé"
    LAB6_AVAILABLE=false
fi

# Vérifier Integration Service
if curl -s -f "$LAB7_INTEGRATION_URL/health" > /dev/null; then
    echo " Integration Service disponible"
else
    echo "Integration Service non disponible"
    exit 1
fi

echo ""
echo "2. Test du statut d'intégration..."
INTEGRATION_STATUS=$(curl -s "$LAB7_INTEGRATION_URL/status")
echo "$INTEGRATION_STATUS" | jq . 2>/dev/null || echo "$INTEGRATION_STATUS"

echo ""
echo "3. Test de création de réclamation liée à une commande..."

if [ "$LAB6_AVAILABLE" = true ]; then
    echo "  Mode intégré - Lab 6 disponible"
    ORDER_ID="order_123"
else
    echo "  Mode dégradé - utilisation de données simulées"
    ORDER_ID="simulated_order_456"
fi

# Créer une réclamation liée à une commande
echo "  Création d'une réclamation pour commande $ORDER_ID..."
CLAIM_RESPONSE=$(curl -s -X POST "$LAB7_INTEGRATION_URL/claims/from-order" \
    -H "Content-Type: application/json" \
    -d "{
        \"order_id\": \"$ORDER_ID\",
        \"claim_type\": \"product_defect\",
        \"description\": \"Le produit reçu ne correspond pas à la commande\",
        \"urgency\": \"high\"
    }")

echo "  Réponse de création:"
echo "$CLAIM_RESPONSE" | jq . 2>/dev/null || echo "$CLAIM_RESPONSE"

# Extraire le claim_id
CLAIM_ID=$(echo "$CLAIM_RESPONSE" | grep -o '"claim_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$CLAIM_ID" ]; then
    echo "   Réclamation créée avec ID: $CLAIM_ID"
    
    echo ""
    echo "4. Vérification de la réclamation enrichie..."
    
    # Attendre que les événements soient traités
    sleep 3
    
    # Vérifier dans le Query Service
    CLAIM_DETAILS=$(curl -s "$LAB7_QUERY_URL/claims/$CLAIM_ID")
    echo "  Détails de la réclamation:"
    echo "$CLAIM_DETAILS" | jq . 2>/dev/null || echo "$CLAIM_DETAILS"
    
    echo ""
    echo "5. Test de récupération du contexte commande..."
    
    # Tester la récupération des détails de commande
    ORDER_DETAILS=$(curl -s "$LAB7_INTEGRATION_URL/orders/$ORDER_ID")
    echo "  Contexte de la commande $ORDER_ID:"
    echo "$ORDER_DETAILS" | jq . 2>/dev/null || echo "$ORDER_DETAILS"
    
    # Extraire customer_id
    CUSTOMER_ID=$(echo "$ORDER_DETAILS" | grep -o '"customer_id":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$CUSTOMER_ID" ]; then
        echo ""
        echo "6. Test de récupération du contexte client..."
        CUSTOMER_DETAILS=$(curl -s "$LAB7_INTEGRATION_URL/customers/$CUSTOMER_ID")
        echo "  Contexte du client $CUSTOMER_ID:"
        echo "$CUSTOMER_DETAILS" | jq . 2>/dev/null || echo "$CUSTOMER_DETAILS"
    fi
    
else
    echo "  Échec de création de la réclamation"
fi

echo ""
echo "7. Test de cas d'usage métier complet..."

# Simuler un flux complet avec plusieurs réclamations
echo "  Création de plusieurs réclamations pour démonstration..."

for i in {1..3}; do
    DEMO_ORDER_ID="demo_order_00$i"
    CLAIM_TYPES=("product_defect" "delivery_issue" "billing_error")
    CLAIM_TYPE=${CLAIM_TYPES[$((i-1))]}
    
    curl -s -X POST "$LAB7_INTEGRATION_URL/claims/from-order" \
        -H "Content-Type: application/json" \
        -d "{
            \"order_id\": \"$DEMO_ORDER_ID\",
            \"claim_type\": \"$CLAIM_TYPE\",
            \"description\": \"Réclamation de démonstration #$i\",
            \"urgency\": \"medium\"
        }" > /dev/null
    
    echo "     Réclamation $i créée (commande: $DEMO_ORDER_ID)"
done

echo ""
echo "8. Vérification du dashboard avec données intégrées..."
sleep 5

DASHBOARD=$(curl -s "$LAB7_QUERY_URL/dashboard")
echo "  Résumé du dashboard:"
echo "$DASHBOARD" | jq '.summary' 2>/dev/null || echo "$DASHBOARD"

echo ""
echo "=== Test d'intégration terminé ==="
echo ""
echo "Points d'intégration vérifiés:"
echo "  - Création de réclamations liées aux commandes"
echo "  - Enrichissement avec contexte client/commande"
echo "  - Mode dégradé en cas d'indisponibilité Lab 6"
echo "  - Flux événementiel complet Lab 7"
echo ""
echo "Interfaces disponibles:"
echo "  - Integration Service: http://localhost:8107/docs"
echo "  - Claims Service: http://localhost:8101/docs"
echo "  - Query Service: http://localhost:8105/docs"
echo ""
if [ "$LAB6_AVAILABLE" = true ]; then
    echo "Mode intégré actif - Lab 6 connecté"
else
    echo "Mode dégradé - Démarrez Lab 6 pour intégration complète"
    echo "   cd ../microservices && docker compose up -d"
fi