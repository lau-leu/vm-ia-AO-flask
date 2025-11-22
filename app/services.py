"""Services métier pour la gestion des documents et la génération d'offres."""
import os
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import (
    Document, GenerationHistory, DocumentType, DocumentStatus,
    get_db_session, init_db
)
from app.document_processor import (
    calculate_file_hash, extract_text, create_word_document,
    extract_key_information
)
from app.ollama_client import (
    OllamaClient, create_quote_generation_prompt, create_analysis_prompt
)
from app.config import UPLOAD_FOLDER, GENERATED_FOLDER


class DocumentService:
    """Service pour la gestion des documents."""

    def __init__(self, db: Session = None):
        self.db = db or get_db_session()

    def upload_document(
        self,
        file_content: bytes,
        original_filename: str,
        document_type: DocumentType,
        reference: str = None,
        title: str = None,
        description: str = None,
        is_template: bool = False
    ) -> Document:
        """
        Uploader et enregistrer un document.

        Args:
            file_content: Contenu binaire du fichier
            original_filename: Nom original du fichier
            document_type: Type de document
            reference: Référence optionnelle
            title: Titre optionnel
            description: Description optionnelle
            is_template: Indique si c'est un modèle

        Returns:
            Le document créé
        """
        # Générer un nom de fichier unique
        file_ext = Path(original_filename).suffix.lower()
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"

        # Déterminer le dossier de destination
        folder = UPLOAD_FOLDER
        file_path = folder / unique_filename

        # Sauvegarder le fichier
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Calculer le hash pour éviter les doublons
        file_hash = calculate_file_hash(str(file_path))

        # Vérifier si le document existe déjà
        existing = self.db.query(Document).filter_by(file_hash=file_hash).first()
        if existing:
            # Supprimer le fichier uploadé car il existe déjà
            os.remove(file_path)
            return existing

        # Extraire le texte
        extracted_text = extract_text(str(file_path))

        # Extraire les informations clés si c'est un appel d'offre
        if document_type == DocumentType.APPEL_OFFRE and not reference:
            key_info = extract_key_information(extracted_text)
            reference = key_info.get('reference') or reference
            title = key_info.get('title') or title

        # Créer l'enregistrement
        document = Document(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=str(file_path),
            file_type=file_ext[1:],  # Sans le point
            document_type=document_type,
            reference=reference or f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            title=title or original_filename,
            description=description,
            extracted_text=extracted_text,
            file_hash=file_hash,
            is_template=is_template,
            status=DocumentStatus.COMPLETED
        )

        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)

        return document

    def get_document(self, document_id: int) -> Optional[Document]:
        """Récupérer un document par son ID."""
        return self.db.query(Document).filter_by(id=document_id).first()

    def get_documents_by_type(
        self,
        document_type: DocumentType,
        is_template: bool = None
    ) -> List[Document]:
        """Récupérer les documents par type."""
        query = self.db.query(Document).filter_by(document_type=document_type)
        if is_template is not None:
            query = query.filter_by(is_template=is_template)
        return query.order_by(Document.created_at.desc()).all()

    def search_documents(self, search_term: str) -> List[Document]:
        """Rechercher des documents par terme."""
        search_pattern = f"%{search_term}%"
        return self.db.query(Document).filter(
            or_(
                Document.title.ilike(search_pattern),
                Document.reference.ilike(search_pattern),
                Document.extracted_text.ilike(search_pattern)
            )
        ).all()

    def delete_document(self, document_id: int) -> bool:
        """Supprimer un document."""
        document = self.get_document(document_id)
        if not document:
            return False

        # Supprimer le fichier physique
        if os.path.exists(document.file_path):
            os.remove(document.file_path)

        # Supprimer l'enregistrement
        self.db.delete(document)
        self.db.commit()
        return True

    def get_all_templates(self) -> List[Document]:
        """Récupérer tous les modèles de rédaction."""
        return self.db.query(Document).filter_by(
            document_type=DocumentType.OFFRE_PRIX,
            is_template=True
        ).all()


class QuoteGenerationService:
    """Service pour la génération automatique d'offres de prix."""

    def __init__(self, db: Session = None):
        self.db = db or get_db_session()
        self.doc_service = DocumentService(self.db)
        self.ollama = OllamaClient()

    def analyze_tender(self, document_id: int) -> dict:
        """
        Analyser un appel d'offre.

        Returns:
            Dictionnaire avec l'analyse
        """
        document = self.doc_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} non trouvé")

        system_prompt, user_prompt = create_analysis_prompt(document.extracted_text)
        analysis = self.ollama.generate(user_prompt, system_prompt)

        return {
            'document_id': document_id,
            'reference': document.reference,
            'analysis': analysis
        }

    def analyze_tender_stream(self, document_id: int):
        """
        Analyser un appel d'offre en streaming (temps réel).

        Yields:
            Morceaux de texte au fur et à mesure
        """
        document = self.doc_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} non trouvé")

        system_prompt, user_prompt = create_analysis_prompt(document.extracted_text)

        for chunk in self.ollama.generate_stream(user_prompt, system_prompt):
            yield chunk

    def generate_quote(
        self,
        tender_document_id: int,
        template_ids: List[int] = None,
        additional_context: str = "",
        output_filename: str = None
    ) -> Document:
        """
        Générer une offre de prix à partir d'un appel d'offre.

        Args:
            tender_document_id: ID du document d'appel d'offre
            template_ids: IDs des modèles à utiliser
            additional_context: Contexte supplémentaire
            output_filename: Nom du fichier de sortie

        Returns:
            Le document d'offre généré
        """
        start_time = time.time()

        # Récupérer l'appel d'offre
        tender = self.doc_service.get_document(tender_document_id)
        if not tender:
            raise ValueError(f"Appel d'offre {tender_document_id} non trouvé")

        # Récupérer les modèles
        templates_content = []
        if template_ids:
            for tid in template_ids:
                template = self.doc_service.get_document(tid)
                if template and template.extracted_text:
                    templates_content.append(template.extracted_text)
        else:
            # Utiliser tous les modèles disponibles
            templates = self.doc_service.get_all_templates()
            templates_content = [t.extracted_text for t in templates if t.extracted_text]

        # Créer le prompt
        system_prompt, user_prompt = create_quote_generation_prompt(
            tender.extracted_text,
            templates_content,
            additional_context
        )

        # Générer l'offre avec Ollama
        generated_content = self.ollama.generate(user_prompt, system_prompt)

        # Créer le fichier Word
        if not output_filename:
            output_filename = f"Offre_{tender.reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"

        output_path = GENERATED_FOLDER / output_filename

        create_word_document(
            content=generated_content,
            title=f"Offre de Prix - {tender.reference}",
            reference=tender.reference,
            output_path=str(output_path)
        )

        # Enregistrer le document généré
        with open(output_path, 'rb') as f:
            generated_doc = self.doc_service.upload_document(
                file_content=f.read(),
                original_filename=output_filename,
                document_type=DocumentType.GENERATED,
                reference=f"OFF-{tender.reference}",
                title=f"Offre générée pour {tender.reference}",
                description=f"Offre automatiquement générée à partir de l'appel d'offre {tender.reference}"
            )

        # Mettre à jour le parent_id
        generated_doc.parent_id = tender_document_id
        self.db.commit()

        # Enregistrer l'historique
        generation_time = int(time.time() - start_time)
        history = GenerationHistory(
            source_document_id=tender_document_id,
            generated_document_id=generated_doc.id,
            templates_used=json.dumps(template_ids or []),
            prompt_used=user_prompt[:5000],  # Limiter la taille
            model_used=self.ollama.model,
            generation_time=generation_time
        )
        self.db.add(history)
        self.db.commit()

        return generated_doc

    def generate_quote_stream(
            self,
            tender_document_id: int,
            template_ids: List[int] = None,
            additional_context: str = ""
    ):
        """
        Générer une offre de prix en streaming (temps réel).

        Yields:
            Tuple (chunk_text, document_or_none, metadata)
            - chunk_text: morceau de texte généré
            - document_or_none: Document final (None pendant génération)
            - metadata: dict avec infos de progression
        """
        start_time = time.time()

        # Récupérer l'appel d'offre
        tender = self.doc_service.get_document(tender_document_id)
        if not tender:
            raise ValueError(f"Appel d'offre {tender_document_id} non trouvé")

        # Récupérer les modèles
        templates_content = []
        if template_ids:
            for tid in template_ids:
                template = self.doc_service.get_document(tid)
                if template and template.extracted_text:
                    templates_content.append(template.extracted_text)
        else:
            templates = self.doc_service.get_all_templates()
            templates_content = [t.extracted_text for t in templates if t.extracted_text]

        # Créer le prompt
        system_prompt, user_prompt = create_quote_generation_prompt(
            tender.extracted_text,
            templates_content,
            additional_context
        )

        # Générer l'offre avec streaming
        full_content = ""
        for chunk in self.ollama.generate_stream(user_prompt, system_prompt):
            full_content += chunk
            yield chunk, None, {'status': 'generating'}

        # Une fois terminé, créer le document Word
        output_filename = f"Offre_{tender.reference}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        output_path = GENERATED_FOLDER / output_filename

        create_word_document(
            content=full_content,
            title=f"Offre de Prix - {tender.reference}",
            reference=tender.reference,
            output_path=str(output_path)
        )

        # Enregistrer le document généré
        with open(output_path, 'rb') as f:
            generated_doc = self.doc_service.upload_document(
                file_content=f.read(),
                original_filename=output_filename,
                document_type=DocumentType.GENERATED,
                reference=f"OFF-{tender.reference}",
                title=f"Offre générée pour {tender.reference}",
                description=f"Offre automatiquement générée à partir de l'appel d'offre {tender.reference}"
            )

        generated_doc.parent_id = tender_document_id
        self.db.commit()

        # Enregistrer l'historique
        generation_time = int(time.time() - start_time)
        history = GenerationHistory(
            source_document_id=tender_document_id,
            generated_document_id=generated_doc.id,
            templates_used=json.dumps(template_ids or []),
            prompt_used=user_prompt[:5000],
            model_used=self.ollama.model,
            generation_time=generation_time
        )
        self.db.add(history)
        self.db.commit()

        # Retourner le document final
        yield "", generated_doc, {'status': 'completed', 'time': generation_time}

    def get_generation_history(self, document_id: int = None) -> List[GenerationHistory]:
        """Récupérer l'historique des générations."""
        query = self.db.query(GenerationHistory)
        if document_id:
            query = query.filter_by(source_document_id=document_id)
        return query.order_by(GenerationHistory.created_at.desc()).all()


# Initialiser la base de données au chargement du module
init_db()
