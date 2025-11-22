"""Configuration et modèles de la base de données."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

from app.config import DATABASE_URL

# Configuration de l'engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class DocumentType(enum.Enum):
    """Types de documents."""
    APPEL_OFFRE = "appel_offre"  # Modèle d'information (entrée)
    OFFRE_PRIX = "offre_prix"    # Modèle de rédaction (sortie)
    GENERATED = "generated"      # Offre générée


class DocumentStatus(enum.Enum):
    """Statuts des documents."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class Document(Base):
    """Modèle pour les documents stockés."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx, etc.
    document_type = Column(Enum(DocumentType), nullable=False)

    # Métadonnées
    reference = Column(String(100), index=True)
    title = Column(String(500))
    description = Column(Text)

    # Contenu extrait pour l'indexation
    extracted_text = Column(Text)

    # Informations de suivi
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Hash pour éviter les doublons
    file_hash = Column(String(64), unique=True, index=True)

    # Lien avec document parent (pour les offres générées)
    parent_id = Column(Integer, nullable=True)

    # Indicateur de modèle
    is_template = Column(Boolean, default=False)

    def __repr__(self):
        return f"<Document {self.id}: {self.original_filename}>"


class GenerationHistory(Base):
    """Historique des générations d'offres."""
    __tablename__ = "generation_history"

    id = Column(Integer, primary_key=True, index=True)
    source_document_id = Column(Integer, nullable=False)  # Appel d'offre source
    generated_document_id = Column(Integer, nullable=False)  # Offre générée
    templates_used = Column(Text)  # IDs des modèles utilisés (JSON)

    # Détails de la génération
    prompt_used = Column(Text)
    model_used = Column(String(100))
    generation_time = Column(Integer)  # en secondes

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<GenerationHistory {self.id}>"


def init_db():
    """Initialiser la base de données."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Obtenir une session de base de données."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Obtenir une session de base de données (non-générateur)."""
    return SessionLocal()
