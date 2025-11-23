#!/bin/bash

set -e

echo "========================================================"
echo "Déploiement Gestion AO sur vm-ia"
echo "========================================================"
echo ""

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "app.py" ]; then
    echo "❌ Erreur: app.py non trouvé."
    exit 1
fi

# Créer l'environnement virtuel
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    python3 -m venv venv
fi

# Activer et installer les dépendances
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Déploiement terminé!"
echo ""
echo "Pour démarrer avec Gunicorn (recommandé):"
echo "  source venv/bin/activate"
echo "  gunicorn -w 4 -b 0.0.0.0:5002 --timeout 180 app:app"
echo ""
echo "L'application sera accessible sur:"
echo "  http://192.168.1.96:5002"
echo "  https://django.leumaire.fr/ao/ (via proxy)"
