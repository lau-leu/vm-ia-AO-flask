"""Interface Streamlit pour l'application de gestion des appels d'offres."""
import streamlit as st
import os
from datetime import datetime
from pathlib import Path

from app.database import DocumentType, get_db_session, init_db
from app.services import DocumentService, QuoteGenerationService
from app.ollama_client import OllamaClient
from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB

# Configuration de la page
st.set_page_config(
    page_title="AppliWeb-AO - Gestion des Appels d'Offres",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialisation de la base de données
init_db()

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Fonction principale de l'application."""
    # En-tête
    st.markdown('<p class="main-header">📋 AppliWeb-AO</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Gestion et Automatisation des Offres de Prix</p>', unsafe_allow_html=True)

    # Sidebar - Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Menu",
        ["🏠 Accueil", "📤 Upload Documents", "📚 Bibliothèque", "🤖 Générer Offre", "📊 Historique"]
    )

    # Vérification de la connexion Ollama
    ollama = OllamaClient()
    ollama_status = ollama.check_connection()

    if ollama_status:
        st.sidebar.success("✅ Ollama connecté")
        models = ollama.list_models()
        if models:
            st.sidebar.info(f"Modèles: {', '.join(models[:3])}")
    else:
        st.sidebar.error("❌ Ollama non disponible")

    # Routing des pages
    if page == "🏠 Accueil":
        show_home()
    elif page == "📤 Upload Documents":
        show_upload()
    elif page == "📚 Bibliothèque":
        show_library()
    elif page == "🤖 Générer Offre":
        show_generation()
    elif page == "📊 Historique":
        show_history()


def show_home():
    """Page d'accueil."""
    st.header("Bienvenue dans AppliWeb-AO")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📤 Upload")
        st.write("Importez vos appels d'offres et modèles de rédaction")
        if st.button("Aller à l'upload", key="btn_upload"):
            st.session_state.page = "📤 Upload Documents"
            st.rerun()

    with col2:
        st.markdown("### 🤖 Génération IA")
        st.write("Générez automatiquement des offres de prix avec Ollama")
        if st.button("Générer une offre", key="btn_generate"):
            st.session_state.page = "🤖 Générer Offre"
            st.rerun()

    with col3:
        st.markdown("### 📚 Bibliothèque")
        st.write("Consultez et gérez vos documents")
        if st.button("Voir la bibliothèque", key="btn_library"):
            st.session_state.page = "📚 Bibliothèque"
            st.rerun()

    # Statistiques
    st.markdown("---")
    st.subheader("📊 Statistiques")

    db = get_db_session()
    doc_service = DocumentService(db)

    col1, col2, col3, col4 = st.columns(4)

    tenders = doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE)
    templates = doc_service.get_documents_by_type(DocumentType.OFFRE_PRIX, is_template=True)
    generated = doc_service.get_documents_by_type(DocumentType.GENERATED)

    with col1:
        st.metric("Appels d'Offres", len(tenders))
    with col2:
        st.metric("Modèles de Rédaction", len(templates))
    with col3:
        st.metric("Offres Générées", len(generated))
    with col4:
        st.metric("Total Documents", len(tenders) + len(templates) + len(generated))

    db.close()


def show_upload():
    """Page d'upload de documents."""
    st.header("📤 Upload de Documents")

    # Sélection du type de document
    doc_type = st.selectbox(
        "Type de document",
        options=["Appel d'Offre", "Modèle de Rédaction (Offre de Prix)"],
        help="Sélectionnez le type de document à uploader"
    )

    is_tender = doc_type == "Appel d'Offre"
    document_type = DocumentType.APPEL_OFFRE if is_tender else DocumentType.OFFRE_PRIX

    # Extensions autorisées
    if is_tender:
        allowed_ext = ALLOWED_EXTENSIONS['appel_offre']
        st.info(f"📎 Formats acceptés: {', '.join(allowed_ext)}")
    else:
        allowed_ext = ALLOWED_EXTENSIONS['offre_prix']
        st.info(f"📎 Formats acceptés: {', '.join(allowed_ext)}")

    # Upload de fichier
    uploaded_file = st.file_uploader(
        "Choisir un fichier",
        type=[ext[1:] for ext in allowed_ext],  # Sans le point
        help=f"Taille maximale: {MAX_FILE_SIZE_MB} MB"
    )

    if uploaded_file:
        # Métadonnées
        st.subheader("Métadonnées")

        col1, col2 = st.columns(2)
        with col1:
            reference = st.text_input(
                "Référence",
                value="",
                help="Référence du document (auto-générée si vide)"
            )
        with col2:
            title = st.text_input(
                "Titre",
                value=uploaded_file.name,
                help="Titre du document"
            )

        description = st.text_area(
            "Description",
            help="Description optionnelle du document"
        )

        is_template = False
        if not is_tender:
            is_template = st.checkbox(
                "Marquer comme modèle de référence",
                value=True,
                help="Les modèles sont utilisés par l'IA pour générer les offres"
            )

        # Bouton d'upload
        if st.button("📤 Uploader le document", type="primary"):
            with st.spinner("Upload en cours..."):
                try:
                    db = get_db_session()
                    doc_service = DocumentService(db)

                    document = doc_service.upload_document(
                        file_content=uploaded_file.getvalue(),
                        original_filename=uploaded_file.name,
                        document_type=document_type,
                        reference=reference if reference else None,
                        title=title,
                        description=description,
                        is_template=is_template
                    )

                    st.success(f"✅ Document uploadé avec succès! (ID: {document.id})")

                    # Afficher les informations extraites
                    with st.expander("📄 Aperçu du contenu extrait"):
                        if document.extracted_text:
                            st.text(document.extracted_text[:2000] + "..." if len(document.extracted_text) > 2000 else document.extracted_text)
                        else:
                            st.warning("Aucun texte extrait")

                    db.close()

                except Exception as e:
                    st.error(f"❌ Erreur lors de l'upload: {str(e)}")


def show_library():
    """Page de la bibliothèque de documents."""
    st.header("📚 Bibliothèque de Documents")

    # Filtres
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.selectbox(
            "Type de document",
            ["Tous", "Appels d'Offres", "Modèles de Rédaction", "Offres Générées"]
        )
    with col2:
        search_term = st.text_input("🔍 Rechercher", "")
    with col3:
        sort_by = st.selectbox("Trier par", ["Date (récent)", "Date (ancien)", "Référence"])

    db = get_db_session()
    doc_service = DocumentService(db)

    # Récupérer les documents
    if search_term:
        documents = doc_service.search_documents(search_term)
    else:
        if filter_type == "Appels d'Offres":
            documents = doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE)
        elif filter_type == "Modèles de Rédaction":
            documents = doc_service.get_documents_by_type(DocumentType.OFFRE_PRIX)
        elif filter_type == "Offres Générées":
            documents = doc_service.get_documents_by_type(DocumentType.GENERATED)
        else:
            documents = (
                doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE) +
                doc_service.get_documents_by_type(DocumentType.OFFRE_PRIX) +
                doc_service.get_documents_by_type(DocumentType.GENERATED)
            )

    # Trier
    if sort_by == "Date (récent)":
        documents.sort(key=lambda x: x.created_at, reverse=True)
    elif sort_by == "Date (ancien)":
        documents.sort(key=lambda x: x.created_at)
    else:
        documents.sort(key=lambda x: x.reference or "")

    # Afficher les documents
    if not documents:
        st.info("Aucun document trouvé")
    else:
        st.write(f"**{len(documents)} document(s) trouvé(s)**")

        for doc in documents:
            with st.expander(f"📄 {doc.title or doc.original_filename} - {doc.reference}"):
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**Type:** {doc.document_type.value}")
                    st.write(f"**Fichier:** {doc.original_filename}")
                    st.write(f"**Date:** {doc.created_at.strftime('%d/%m/%Y %H:%M')}")
                    if doc.description:
                        st.write(f"**Description:** {doc.description}")
                    if doc.is_template:
                        st.write("🏷️ **Modèle de référence**")

                with col2:
                    # Téléchargement
                    if os.path.exists(doc.file_path):
                        with open(doc.file_path, 'rb') as f:
                            st.download_button(
                                "⬇️ Télécharger",
                                data=f.read(),
                                file_name=doc.original_filename,
                                mime="application/octet-stream",
                                key=f"dl_{doc.id}"
                            )

                    # Suppression
                    if st.button("🗑️ Supprimer", key=f"del_{doc.id}"):
                        if doc_service.delete_document(doc.id):
                            st.success("Document supprimé")
                            st.rerun()
                        else:
                            st.error("Erreur lors de la suppression")

                # Aperçu du contenu
                if doc.extracted_text:
                    with st.expander("📝 Aperçu du contenu"):
                        preview = doc.extracted_text[:1500]
                        if len(doc.extracted_text) > 1500:
                            preview += "..."
                        st.text(preview)

    db.close()


def show_generation():
    """Page de génération d'offres."""
    st.header("🤖 Génération Automatique d'Offres")

    # Vérifier Ollama
    ollama = OllamaClient()
    if not ollama.check_connection():
        st.error("❌ Ollama n'est pas disponible. Veuillez le démarrer pour utiliser cette fonctionnalité.")
        st.code("ollama serve", language="bash")
        return

    db = get_db_session()
    doc_service = DocumentService(db)
    generation_service = QuoteGenerationService(db)

    # Sélection de l'appel d'offre
    tenders = doc_service.get_documents_by_type(DocumentType.APPEL_OFFRE)

    if not tenders:
        st.warning("⚠️ Aucun appel d'offre disponible. Veuillez d'abord uploader un appel d'offre.")
        return

    st.subheader("1️⃣ Sélectionner l'Appel d'Offre")

    tender_options = {f"{t.reference} - {t.title}": t.id for t in tenders}
    selected_tender = st.selectbox(
        "Appel d'offre source",
        options=list(tender_options.keys())
    )
    tender_id = tender_options[selected_tender]

    # Afficher l'aperçu
    tender = doc_service.get_document(tender_id)
    if tender:
        with st.expander("📄 Aperçu de l'appel d'offre"):
            if tender.extracted_text:
                st.text(tender.extracted_text[:2000] + "..." if len(tender.extracted_text) > 2000 else tender.extracted_text)

    # Analyse de l'appel d'offre
    if st.button("🔍 Analyser l'appel d'offre"):
        #with st.spinner("Analyse en cours..."):
            #try:
                #analysis = generation_service.analyze_tender(tender_id)
                #st.subheader("📊 Analyse")
                #st.markdown(analysis['analysis'])
            #except Exception as e:
                #st.error(f"Erreur lors de l'analyse: {str(e)}")
        st.subheader("📊 Analyse en cours...")

        # Créer un conteneur pour l'affichage en temps réel
        analysis_container = st.empty()
        full_analysis = ""

        try:
            # Utiliser le streaming pour afficher en temps réel
            for chunk in generation_service.analyze_tender_stream(tender_id):
                full_analysis += chunk
                # Mettre à jour l'affichage à chaque morceau reçu
                analysis_container.markdown(full_analysis + "▌")  # ▌ pour montrer que c'est en cours

            # Affichage final sans le curseur
            analysis_container.markdown(full_analysis)
            st.success("✅ Analyse terminée!")

        except Exception as e:
            st.error(f"Erreur lors de l'analyse: {str(e)}")

    st.markdown("---")

    # Sélection des modèles
    st.subheader("2️⃣ Sélectionner les Modèles de Rédaction")

    templates = doc_service.get_all_templates()

    if not templates:
        st.warning("⚠️ Aucun modèle de rédaction disponible. L'IA utilisera ses connaissances générales.")
        template_ids = []
    else:
        template_options = {f"{t.reference} - {t.title}": t.id for t in templates}
        selected_templates = st.multiselect(
            "Modèles à utiliser (optionnel)",
            options=list(template_options.keys()),
            default=list(template_options.keys()),
            help="Sélectionnez les modèles dont l'IA doit s'inspirer"
        )
        template_ids = [template_options[t] for t in selected_templates]

    st.markdown("---")

    # Contexte supplémentaire
    st.subheader("3️⃣ Contexte Supplémentaire (optionnel)")
    additional_context = st.text_area(
        "Instructions ou informations complémentaires",
        help="Ajoutez des instructions spécifiques pour la génération"
    )

    st.markdown("---")

    # Génération
    st.subheader("4️⃣ Générer l'Offre")

    if st.button("🚀 Générer l'Offre de Prix", type="primary"):
        #with st.spinner("Génération en cours... Cela peut prendre quelques minutes."):
            #try:
                #generated_doc = generation_service.generate_quote(
                    #tender_document_id=tender_id,
                    #template_ids=template_ids if template_ids else None,
                    #additional_context=additional_context
                #)

                #st.success(f"✅ Offre générée avec succès!")

                # Téléchargement
                #if os.path.exists(generated_doc.file_path):
                    #with open(generated_doc.file_path, 'rb') as f:
                        #st.download_button(
                            #"⬇️ Télécharger l'offre générée",
                            #data=f.read(),
                            #file_name=generated_doc.original_filename,
                            #mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            #type="primary"
                        #)
        st.info("🔄 Génération en cours... Vous pouvez suivre la progression en temps réel ci-dessous.")

        # Conteneur pour affichage en temps réel
        generation_container = st.empty()
        status_container = st.empty()
        full_content = ""
        generated_doc = None

        try:
            # Utiliser le streaming pour afficher en temps réel
            for chunk, doc, metadata in generation_service.generate_quote_stream(
                    tender_document_id=tender_id,
                    template_ids=template_ids if template_ids else None,
                    additional_context=additional_context
            ):
                if metadata['status'] == 'generating':
                    full_content += chunk
                    # Mettre à jour l'affichage avec un curseur
                    generation_container.markdown(full_content + "▌")
                    # Afficher le nombre de caractères générés
                    status_container.info(f"📝 {len(full_content)} caractères générés...")
                elif metadata['status'] == 'completed':
                    generated_doc = doc
                    # Affichage final sans le curseur
                    generation_container.markdown(full_content)
                    status_container.success(f"✅ Offre générée avec succès en {metadata['time']} secondes!")

            # Téléchargement
            if generated_doc and os.path.exists(generated_doc.file_path):
                with open(generated_doc.file_path, 'rb') as f:
                    st.download_button(
                        "⬇️ Télécharger l'offre générée",
                        data=f.read(),
                        file_name=generated_doc.original_filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary"
                    )
                # Aperçu
                #with st.expander("📄 Aperçu du contenu généré"):
                    #if generated_doc.extracted_text:
                        #st.text(generated_doc.extracted_text)

            #except Exception as e:
                #st.error(f"❌ Erreur lors de la génération: {str(e)}")

            # Aperçu
            if generated_doc:
                with st.expander("📄 Aperçu du contenu généré"):
                    if generated_doc.extracted_text:
                        st.text(generated_doc.extracted_text)

        except Exception as e:
            st.error(f"❌ Erreur lors de la génération: {str(e)}")
    db.close()


def show_history():
    """Page d'historique des générations."""
    st.header("📊 Historique des Générations")

    db = get_db_session()
    generation_service = QuoteGenerationService(db)
    doc_service = DocumentService(db)

    history = generation_service.get_generation_history()

    if not history:
        st.info("Aucune génération effectuée pour le moment.")
        return

    for h in history:
        source_doc = doc_service.get_document(h.source_document_id)
        generated_doc = doc_service.get_document(h.generated_document_id)

        if source_doc and generated_doc:
            with st.expander(f"🕒 {h.created_at.strftime('%d/%m/%Y %H:%M')} - {source_doc.reference}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Source:**", source_doc.title)
                    st.write("**Modèle IA:**", h.model_used)
                    st.write("**Durée:**", f"{h.generation_time}s")

                with col2:
                    if os.path.exists(generated_doc.file_path):
                        with open(generated_doc.file_path, 'rb') as f:
                            st.download_button(
                                "⬇️ Télécharger",
                                data=f.read(),
                                file_name=generated_doc.original_filename,
                                mime="application/octet-stream",
                                key=f"hist_dl_{h.id}"
                            )

    db.close()


if __name__ == "__main__":
    main()
