#!/usr/bin/env python3
"""
Point d'entrée principal du système de point de vente
"""

from src.persistence.database import create_tables
from src.client.console import ApplicationConsole


def main():
    """Fonction principale"""
    print("Initialisation du système de point de vente...")
    
    # Créer les tables si elles n'existent pas
    create_tables()
    
    # Lancer l'application console
    app = ApplicationConsole()
    app.executer()


if __name__ == "__main__":
    main() 