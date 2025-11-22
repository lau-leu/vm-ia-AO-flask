# AppliWeb-AO

Application web de gestion et d'automatisation des offres de prix en réponse aux appels d'offres.

## Fonctionnalités

- **Gestion des Documents**
  - Upload de fichiers Word/PDF (appels d'offres et modèles)
  - Extraction automatique du contenu textuel
  - Classification par type de document
  - Évitement des doublons par hash

- **Génération Automatique d'Offres**
  - Analyse des appels d'offres avec Ollama
  - Génération d'offres de prix basée sur les modèles existants
  - Export au format Word (.docx)

- **Interface Utilisateur**
  - Interface web Flask moderne et responsive
  - Visualisation et recherche de documents
  - Téléchargement des fichiers générés
  - Historique des générations
  - Streaming en temps réel des générations IA (SSE)

## Prérequis

- Python 3.9+
- Ollama (pour la génération IA)
- PostgreSQL ou SQLite (par défaut)

## Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd appliweb-AO
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer l'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

5. **Installer et démarrer Ollama**
```bash
# Installer Ollama: https://ollama.ai
ollama serve
ollama pull llama3.2
```

## Utilisation

**Lancer l'application:**
```bash
python run.py
```

L'application sera accessible sur http://localhost:5000

**Variables d'environnement optionnelles pour le démarrage:**
```bash
# Changer le port (par défaut: 5000)
PORT=8080 python run.py

# Activer le mode debug
FLASK_DEBUG=true python run.py

# Changer l'hôte (par défaut: 0.0.0.0)
HOST=127.0.0.1 python run.py
```

## Structure du Projet

```
appliweb-AO/
├── app/
│   ├── __init__.py
│   ├── config.py              # Configuration
│   ├── database.py            # Modèles SQLAlchemy
│   ├── document_processor.py  # Traitement Word/PDF
│   ├── ollama_client.py       # Client Ollama
│   ├── services.py            # Logique métier
│   ├── flask_app.py           # Application Flask
│   ├── templates/             # Templates HTML Jinja2
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── upload.html
│   │   ├── library.html
│   │   ├── generate.html
│   │   └── history.html
│   └── static/                # Fichiers statiques
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── generate.js
├── data/
│   ├── uploads/               # Documents uploadés
│   ├── generated/             # Offres générées
│   └── templates/             # Modèles de rédaction
├── requirements.txt
├── .env.example
├── run.py
└── README.md
```

## Configuration

Variables d'environnement (.env):

| Variable | Description | Défaut |
|----------|-------------|--------|
| DATABASE_URL | URL de connexion à la base de données | sqlite:///./data/appliweb_ao.db |
| OLLAMA_BASE_URL | URL du serveur Ollama | http://localhost:11434 |
| OLLAMA_MODEL | Modèle à utiliser | llama3.2 |
| MAX_FILE_SIZE_MB | Taille maximale des fichiers | 50 |

## Stack Technique

- **Framework Web**: Flask 3.0
- **Frontend**: HTML5, Bootstrap 5, JavaScript (SSE)
- **Backend/IA**: Ollama (avec streaming SSE)
- **Base de données**: SQLAlchemy (PostgreSQL/SQLite)
- **Traitement de fichiers**: python-docx, PyPDF2, pdfplumber

## Fonctionnalités Techniques

- **Server-Sent Events (SSE)**: Streaming en temps réel des générations IA
- **Bootstrap 5**: Interface responsive et moderne
- **Upload de fichiers**: Gestion sécurisée des uploads avec validation
- **Context Processor**: Status Ollama disponible dans tous les templates
- **Flash Messages**: Notifications utilisateur pour les actions
- **Error Handling**: Gestion des erreurs 413 (fichiers trop volumineux)

## Workflow

1. **Upload des modèles** - Importer des exemples d'offres de prix comme modèles de rédaction
2. **Upload d'un appel d'offre** - Importer le document à analyser
3. **Génération** - L'IA analyse l'appel d'offre et génère une offre de prix
4. **Téléchargement** - Récupérer le document Word généré

## Licence

MIT
