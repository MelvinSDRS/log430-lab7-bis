"""
Modèles Swagger/OpenAPI pour la documentation de l'API
"""

from flask_restx import fields, Model

# Modèles de réponse standardisés
error_model = {
    'timestamp': fields.String(required=True, description='Horodatage de l\'erreur', example='2025-01-01T10:00:00Z'),
    'status': fields.Integer(required=True, description='Code de statut HTTP', example=400),
    'error': fields.String(required=True, description='Type d\'erreur', example='Bad Request'),
    'message': fields.String(required=True, description='Message d\'erreur détaillé', example='Le champ name est requis'),
    'path': fields.String(required=True, description='Chemin de la requête', example='/api/v1/products')
}

# Modèles pour les produits
product_model = {
    'id': fields.Integer(description='Identifiant unique du produit', example=1),
    'nom': fields.String(required=True, description='Nom du produit', example='Café Espresso'),
    'prix': fields.Float(required=True, description='Prix du produit', example=2.50),
    'stock': fields.Integer(description='Stock global du produit', example=100),
    'id_categorie': fields.Integer(required=True, description='Identifiant de la catégorie', example=1),
    'seuil_alerte': fields.Integer(description='Seuil d\'alerte de stock', example=5),
    'description': fields.String(description='Description du produit', example='Café italien fort')
}

product_create_model = {
    'nom': fields.String(required=True, description='Nom du produit', example='Café Espresso'),
    'prix': fields.Float(required=True, description='Prix du produit', example=2.50),
    'stock': fields.Integer(required=True, description='Stock initial', example=100),
    'id_categorie': fields.Integer(required=True, description='Identifiant de la catégorie', example=1),
    'seuil_alerte': fields.Integer(description='Seuil d\'alerte de stock', example=5),
    'description': fields.String(description='Description du produit', example='Café italien fort')
}

product_update_model = {
    'nom': fields.String(description='Nom du produit', example='Café Espresso Premium'),
    'prix': fields.Float(description='Prix du produit', example=2.75),
    'seuil_alerte': fields.Integer(description='Seuil d\'alerte de stock', example=10),
    'description': fields.String(description='Description du produit', example='Café italien premium')
}

# Modèles pour les stocks  
stock_entite_model = {
    'id': fields.Integer(description='Identifiant unique du stock', example=1),
    'id_produit': fields.Integer(required=True, description='Identifiant du produit', example=1),
    'id_entite': fields.Integer(required=True, description='Identifiant de l\'entité', example=1),
    'quantite': fields.Integer(required=True, description='Quantité en stock', example=50),
    'seuil_alerte': fields.Integer(description='Seuil d\'alerte pour cette entité', example=5),
    'produit_nom': fields.String(description='Nom du produit', example='Café Espresso'),
    'entite_nom': fields.String(description='Nom de l\'entité', example='Vieux-Montréal')
}

# Modèles pour les entités
entite_model = {
    'id': fields.Integer(description='Identifiant unique de l\'entité', example=1),
    'nom': fields.String(required=True, description='Nom de l\'entité', example='Vieux-Montréal'),
    'type_entite': fields.String(description='Type d\'entité', example='MAGASIN', enum=['MAGASIN', 'CENTRE_LOGISTIQUE', 'MAISON_MERE']),
    'adresse': fields.String(description='Adresse de l\'entité', example='123 Rue Saint-Paul, Montréal'),
    'statut': fields.String(description='Statut de l\'entité', example='ACTIVE')
}

# Modèles pour les rapports
rapport_request_model = {
    'date_debut': fields.String(required=True, description='Date de début (YYYY-MM-DD)', example='2025-01-01'),
    'date_fin': fields.String(required=True, description='Date de fin (YYYY-MM-DD)', example='2025-01-31'),
    'genere_par': fields.Integer(required=True, description='ID du caissier/gestionnaire', example=1)
}

rapport_model = {
    'id': fields.Integer(description='Identifiant unique du rapport', example=1),
    'titre': fields.String(description='Titre du rapport', example='Rapport consolidé Janvier 2025'),
    'type_rapport': fields.String(description='Type de rapport', example='VENTES_CONSOLIDE'),
    'date_generation': fields.String(description='Date de génération', example='2025-01-31T23:59:59'),
    'date_debut': fields.String(description='Date de début de la période', example='2025-01-01T00:00:00'),
    'date_fin': fields.String(description='Date de fin de la période', example='2025-01-31T23:59:59'),
    'contenu_json': fields.String(description='Contenu du rapport au format JSON'),
    'genere_par': fields.Integer(description='ID du générateur', example=1)
}

# Modèles pour les indicateurs de performance
indicateur_performance_model = {
    'entite_id': fields.Integer(description='Identifiant de l\'entité', example=1),
    'entite_nom': fields.String(description='Nom de l\'entité', example='Vieux-Montréal'),
    'chiffre_affaires': fields.Float(description='Chiffre d\'affaires', example=15678.50),
    'nombre_ventes': fields.Integer(description='Nombre de ventes', example=234),
    'produits_en_rupture': fields.Integer(description='Nombre de produits en rupture', example=3),
    'produits_en_surstock': fields.Integer(description='Nombre de produits en surstock', example=12),
    'tendance_hebdomadaire': fields.Float(description='Tendance hebdomadaire (%)', example=5.2)
}

# Modèles de pagination
pagination_meta_model = {
    'page': fields.Integer(description='Page courante', example=1),
    'per_page': fields.Integer(description='Éléments par page', example=20),
    'total': fields.Integer(description='Total d\'éléments', example=150),
    'pages': fields.Integer(description='Nombre total de pages', example=8),
    'has_prev': fields.Boolean(description='Page précédente disponible', example=False),
    'has_next': fields.Boolean(description='Page suivante disponible', example=True)
}

 