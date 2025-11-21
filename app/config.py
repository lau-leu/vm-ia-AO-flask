"""Configuration de l'application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Chemins de base
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Configuration de la base de données
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'appliweb_ao.db'}"
)

# Configuration Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral-small:latest")

# Dossiers de stockage
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", DATA_DIR / "uploads"))
GENERATED_FOLDER = Path(os.getenv("GENERATED_FOLDER", DATA_DIR / "generated"))
TEMPLATES_FOLDER = Path(os.getenv("TEMPLATES_FOLDER", DATA_DIR / "templates"))

# Limites
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Extensions autorisées
ALLOWED_EXTENSIONS = {
    'appel_offre': ['.pdf', '.docx', '.doc'],
    'offre_prix': ['.docx', '.doc']
}

# Créer les dossiers s'ils n'existent pas
for folder in [UPLOAD_FOLDER, GENERATED_FOLDER, TEMPLATES_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)
