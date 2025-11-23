"""Application Flask pour la gestion des appels d'offres."""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

from werkzeug.middleware.proxy_fix import ProxyFix
import os
import json
from datetime import datetime
from pathlib import Path
import time

from app.database import DocumentType, get_db_session, init_db
from app.services import DocumentService, QuoteGenerationService
from app.ollama_client import OllamaClient
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, UPLOAD_FOLDER, GENERATED_FOLDER


# Middleware pour gérer le proxy et X-Forwarded-Prefix
class PrefixMiddleware:
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        # Récupérer le préfixe du header X-Forwarded-Prefix
        prefix = environ.get('HTTP_X_FORWARDED_PREFIX', self.prefix)
        if prefix:
            environ['SCRIPT_NAME'] = prefix
            # Ajuster PATH_INFO
            path_info = environ.get('PATH_INFO', '')
            if path_info.startswith(prefix):
                environ['PATH_INFO'] = path_info[len(prefix):]
        return self.app(environ, start_response)


# Initialisation de Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024  # En bytes

# Appliquer le middleware pour gérer le proxy
app.wsgi_app = PrefixMiddleware(app.wsgi_app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

CORS(app)

# Initialisation de la base de données
init_db()


@app.context_processor
def inject_ollama_status():
    """Inject Ollama status into all templates."""
    ollama = OllamaClient()
    ollama_status = ollama.check_connection()
    return dict(ollama_status=ollama_status)


@app.route('/')
def index():
    """Page d'accueil."""
    db = get_db_session()
    doc_service = DocumentService(db)

    tenders = doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE)
    templates = doc_service.get_documents_by_type(DocumentType.OFFRE_PRIX, is_template=True)
    generated = doc_service.get_documents_by_type(DocumentType.GENERATED)

    stats = {
        'tenders': len(tenders),
        'templates': len(templates),
        'generated': len(generated),
        'total': len(tenders) + len(templates) + len(generated)
    }

    db.close()

    # Vérifier la connexion Ollama
    ollama = OllamaClient()
    ollama_status = ollama.check_connection()
    ollama_models = ollama.list_models() if ollama_status else []

    return render_template('index.html',
                         stats=stats,
                         ollama_status=ollama_status,
                         ollama_models=ollama_models[:3] if ollama_models else [])


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Page d'upload de documents."""
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            doc_type = request.form.get('doc_type')
            file = request.files.get('file')
            reference = request.form.get('reference', '').strip()
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            is_template = request.form.get('is_template') == 'on'

            if not file or file.filename == '':
                flash('Aucun fichier sélectionné', 'error')
                return redirect(url_for('upload'))

            # Déterminer le type de document
            is_tender = doc_type == 'tender'
            document_type = DocumentType.APPEL_OFFRE if is_tender else DocumentType.OFFRE_PRIX

            # Vérifier l'extension
            allowed_ext = ALLOWED_EXTENSIONS['appel_offre'] if is_tender else ALLOWED_EXTENSIONS['offre_prix']
            file_ext = os.path.splitext(file.filename)[1].lower()

            if file_ext not in allowed_ext:
                flash(f'Extension de fichier non autorisée. Extensions acceptées: {", ".join(allowed_ext)}', 'error')
                return redirect(url_for('upload'))

            # Upload du document
            db = get_db_session()
            doc_service = DocumentService(db)

            document = doc_service.upload_document(
                file_content=file.read(),
                original_filename=file.filename,
                document_type=document_type,
                reference=reference if reference else None,
                title=title if title else file.filename,
                description=description if description else None,
                is_template=is_template if not is_tender else False
            )

            db.close()

            flash(f'Document uploadé avec succès! (ID: {document.id})', 'success')
            return redirect(url_for('library'))

        except Exception as e:
            flash(f'Erreur lors de l\'upload: {str(e)}', 'error')
            return redirect(url_for('upload'))

    # GET request
    return render_template('upload.html',
                         max_size=MAX_FILE_SIZE_MB,
                         allowed_ext=ALLOWED_EXTENSIONS)


@app.route('/library')
def library():
    """Page de la bibliothèque de documents."""
    # Récupérer les filtres
    filter_type = request.args.get('type', 'all')
    search_term = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'date_desc')

    db = get_db_session()
    doc_service = DocumentService(db)

    # Récupérer les documents selon les filtres
    if search_term:
        documents = doc_service.search_documents(search_term)
    else:
        if filter_type == 'tenders':
            documents = doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE)
        elif filter_type == 'templates':
            documents = doc_service.get_documents_by_type(DocumentType.OFFRE_PRIX)
        elif filter_type == 'generated':
            documents = doc_service.get_documents_by_type(DocumentType.GENERATED)
        else:  # all
            documents = (
                doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE) +
                doc_service.get_documents_by_type(DocumentType.OFFRE_PRIX) +
                doc_service.get_documents_by_type(DocumentType.GENERATED)
            )

    # Trier
    if sort_by == 'date_desc':
        documents.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == 'date_asc':
        documents.sort(key=lambda x: x.created_at)
    elif sort_by == 'reference':
        documents.sort(key=lambda x: x.reference or '')

    db.close()

    return render_template('library.html',
                         documents=documents,
                         filter_type=filter_type,
                         search_term=search_term,
                         sort_by=sort_by)


@app.route('/download/<int:doc_id>')
def download(doc_id):
    """Télécharger un document."""
    db = get_db_session()
    doc_service = DocumentService(db)

    document = doc_service.get_document(doc_id)

    if not document or not os.path.exists(document.file_path):
        db.close()
        flash('Document non trouvé', 'error')
        return redirect(url_for('library'))

    db.close()

    return send_file(
        document.file_path,
        as_attachment=True,
        download_name=document.original_filename
    )


@app.route('/delete/<int:doc_id>', methods=['POST'])
def delete(doc_id):
    """Supprimer un document."""
    db = get_db_session()
    doc_service = DocumentService(db)

    if doc_service.delete_document(doc_id):
        flash('Document supprimé avec succès', 'success')
    else:
        flash('Erreur lors de la suppression', 'error')

    db.close()

    return redirect(url_for('library'))


@app.route('/generate', methods=['GET', 'POST'])
def generate():
    """Page de génération d'offres."""
    # Vérifier Ollama
    ollama = OllamaClient()
    if not ollama.check_connection():
        flash('Ollama n\'est pas disponible. Veuillez le démarrer pour utiliser cette fonctionnalité.', 'error')
        return render_template('generate.html',
                             ollama_available=False,
                             tenders=[],
                             templates=[])

    db = get_db_session()
    doc_service = DocumentService(db)

    tenders = doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE)
    templates = doc_service.get_all_templates()

    db.close()

    if not tenders:
        flash('Aucun appel d\'offre disponible. Veuillez d\'abord uploader un appel d\'offre.', 'warning')

    return render_template('generate.html',
                         ollama_available=True,
                         tenders=tenders,
                         templates=templates)


@app.route('/api/analyze/<int:tender_id>')
def analyze_tender(tender_id):
    """Analyser un appel d'offre avec streaming SSE."""
    def generate():
        db = get_db_session()
        generation_service = QuoteGenerationService(db)

        try:
            for chunk in generation_service.analyze_tender_stream(tender_id):
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            db.close()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/generate-quote', methods=['POST'])
def generate_quote():
    """Générer une offre avec streaming SSE."""
    data = request.get_json()
    tender_id = data.get('tender_id')
    template_ids = data.get('template_ids', [])
    additional_context = data.get('additional_context', '')

    def generate():
        db = get_db_session()
        generation_service = QuoteGenerationService(db)

        try:
            start_time = time.time()
            generated_doc = None

            for chunk, doc, metadata in generation_service.generate_quote_stream(
                tender_document_id=tender_id,
                template_ids=template_ids if template_ids else None,
                additional_context=additional_context
            ):
                if metadata['status'] == 'generating':
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                elif metadata['status'] == 'completed':
                    generated_doc = doc
                    elapsed_time = time.time() - start_time
                    yield f"data: {json.dumps({'type': 'done', 'doc_id': doc.id, 'filename': doc.original_filename, 'time': round(elapsed_time, 2)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            db.close()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/history')
def history():
    """Page d'historique des générations."""
    db = get_db_session()
    generation_service = QuoteGenerationService(db)
    doc_service = DocumentService(db)

    history_list = generation_service.get_generation_history()

    # Enrichir avec les documents source et générés
    enriched_history = []
    for h in history_list:
        source_doc = doc_service.get_document(h.source_document_id)
        generated_doc = doc_service.get_document(h.generated_document_id)

        if source_doc and generated_doc:
            enriched_history.append({
                'id': h.id,
                'created_at': h.created_at,
                'source_title': source_doc.title,
                'source_reference': source_doc.reference,
                'generated_filename': generated_doc.original_filename,
                'generated_id': generated_doc.id,
                'model_used': h.model_used,
                'generation_time': h.generation_time,
                'file_exists': os.path.exists(generated_doc.file_path)
            })

    db.close()

    return render_template('history.html', history=enriched_history)


@app.route('/api/document/<int:doc_id>')
def get_document(doc_id):
    """API pour récupérer les informations d'un document."""
    db = get_db_session()
    doc_service = DocumentService(db)

    document = doc_service.get_document(doc_id)

    if not document:
        db.close()
        return jsonify({'error': 'Document non trouvé'}), 404

    doc_data = {
        'id': document.id,
        'title': document.title,
        'reference': document.reference,
        'extracted_text': document.extracted_text[:2000] if document.extracted_text else ''
    }

    db.close()

    return jsonify(doc_data)


@app.template_filter('datetime_format')
def datetime_format(value, format='%d/%m/%Y %H:%M'):
    """Filtre Jinja2 pour formater les dates."""
    if value is None:
        return ""
    return value.strftime(format)


@app.errorhandler(413)
def request_entity_too_large(error):
    """Gérer les fichiers trop volumineux."""
    flash(f'Fichier trop volumineux. Taille maximale: {MAX_FILE_SIZE_MB} MB', 'error')
    return redirect(url_for('upload'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
