#!/usr/bin/env python3
"""
Point d'entrée principal du système de point de vente
"""

import os
from src.persistence.database import create_tables


def main():
    """Fonction principale"""
    print("Initialisation du système de point de vente...")
    
    # Créer les tables si elles n'existent pas
    create_tables()
    
    # Déterminer le mode de lancement selon la variable d'environnement
    app_mode = os.getenv('APP_MODE', 'console')
    
    if app_mode == 'api':
        print("Lancement de l'API REST...")
        from src.api.app import create_api_app
        app = create_api_app()
        app.run(host='0.0.0.0', port=8000, debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true')
    else:
        print("Lancement de l'interface console...")
        from src.client.console import ApplicationConsole
    app = ApplicationConsole()
    app.executer()


if __name__ == "__main__":
    main() 