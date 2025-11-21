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
  - Interface Streamlit intuitive
  - Visualisation et recherche de documents
  - Téléchargement des fichiers générés
  - Historique des générations

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
# ou
streamlit run app/streamlit_app.py
```

L'application sera accessible sur http://localhost:8501

## Structure du Projet

```
appliweb-AO/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration
│   ├── database.py         # Modèles SQLAlchemy
│   ├── document_processor.py   # Traitement Word/PDF
│   ├── ollama_client.py    # Client Ollama
│   ├── services.py         # Logique métier
│   └── streamlit_app.py    # Interface utilisateur
├── data/
│   ├── uploads/            # Documents uploadés
│   ├── generated/          # Offres générées
│   └── templates/          # Modèles de rédaction
├── config/
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

- **Frontend**: Streamlit
- **Backend/IA**: Ollama
- **Base de données**: SQLAlchemy (PostgreSQL/SQLite)
- **Traitement de fichiers**: python-docx, PyPDF2, pdfplumber

## Workflow

1. **Upload des modèles** - Importer des exemples d'offres de prix comme modèles de rédaction
2. **Upload d'un appel d'offre** - Importer le document à analyser
3. **Génération** - L'IA analyse l'appel d'offre et génère une offre de prix
4. **Téléchargement** - Récupérer le document Word généré

## Licence

MIT
