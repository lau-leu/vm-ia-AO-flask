#!/usr/bin/env python3
"""Script de lancement de l'application AppliWeb-AO."""
import os
import sys

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Lancer l'application Flask."""
    from app.flask_app import app

    port = int(os.environ.get('PORT', 5002))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    print(f"Démarrage de l'application Flask sur http://{host}:{port}")
    print("Appuyez sur Ctrl+C pour arrêter")

    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main()
