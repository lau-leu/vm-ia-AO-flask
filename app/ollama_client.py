"""Client pour l'intégration avec Ollama."""
import json
import time
from typing import Optional, Generator
import requests
import httpx

from app.config import OLLAMA_BASE_URL, OLLAMA_MODEL


class OllamaClient:
    """Client pour interagir avec l'API Ollama."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or OLLAMA_BASE_URL
        self.model = model or OLLAMA_MODEL

    def check_connection(self) -> bool:
        """Vérifier si Ollama est accessible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        """Lister les modèles disponibles."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception:
            return []

    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 16384
    ) -> str:
        """
        Générer une réponse avec Ollama.

        Args:
            prompt: Le prompt utilisateur
            system_prompt: Instructions système
            temperature: Température de génération
            max_tokens: Nombre maximum de tokens

        Returns:
            Le texte généré
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens, # Nombre maximum de tokens à générer
                "num_ctx": 16384  # Contexte étendu pour mieux comprendre
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
            #with httpx.stream(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=7200  #300 = 5 minutes timeout 1800 30 minutes 7200 2hrs
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                raise Exception(f"Erreur Ollama: {response.status_code} - {response.text}")

        except requests.exceptions.Timeout:
            raise Exception("Timeout: La génération a pris trop de temps")
        except requests.exceptions.ConnectionError:
            raise Exception(f"Impossible de se connecter à Ollama sur {self.base_url}")

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Générer une réponse en streaming.

        Yields:
            Morceaux de texte au fur et à mesure
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": 16384,  # Nombre maximum de tokens à générer
                "num_ctx": 16384  # Contexte étendu
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            # Configuration du timeout pour httpx (2 heures pour toutes les opérations)
            timeout = httpx.Timeout(
                connect=30.0,  # 30 secondes pour établir la connexion
                read=7200.0,  # 2 heures pour lire les données
                write=30.0,  # 30 secondes pour écrire
                pool=30.0  # 30 secondes pour obtenir une connexion du pool
            )
            # with httpx.stream(
            # 'POST',
            # f"{self.base_url}/api/generate",
            # json=payload,
            # timeout=timeout
            # ) as response:

            with httpx.stream(
                'POST',
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout
            ) as response:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if 'response' in data:
                            yield data['response']
                        if data.get('done', False):
                            break
        except Exception as e:
            yield f"\nErreur lors de la génération: {str(e)}"


def create_quote_generation_prompt(
    tender_content: str,
    templates_content: list,
    additional_context: str = ""
) -> tuple:
    """
    Créer le prompt pour la génération d'une offre de prix.

    Args:
        tender_content: Contenu de l'appel d'offre
        templates_content: Liste des contenus des modèles de rédaction
        additional_context: Contexte supplémentaire

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    system_prompt = """Tu es un expert en rédaction d'offres commerciales et de réponses aux appels d'offres.
Ta tâche est de générer une offre de prix professionnelle et complète en français.

Règles à suivre:
1. Analyser attentivement l'appel d'offre pour identifier les exigences, critères et données clés
2. Utiliser la structure et le style des modèles de rédaction fournis
3. Adapter le contenu aux spécificités de l'appel d'offre
4. Inclure toutes les sections nécessaires (présentation, méthodologie, planning, budget, etc.)
5. Utiliser un ton professionnel et convaincant
6. Structurer clairement avec des titres et sous-titres (utiliser le format Markdown)

Format de sortie:
- Utiliser des titres avec # pour les sections principales
- Utiliser des listes à puces pour les énumérations
- Être précis et concis tout en étant complet
"""

    # Construire le contenu des modèles
    templates_text = ""
    if templates_content:
        templates_text = "\n\n---\nMODÈLES DE RÉDACTION DE RÉFÉRENCE:\n\n"
        for i, template in enumerate(templates_content, 1):
            templates_text += f"=== Modèle {i} ===\n{template}\n\n"

    user_prompt = f"""APPEL D'OFFRE À ANALYSER:

{tender_content}

{templates_text}

{f"CONTEXTE SUPPLÉMENTAIRE: {additional_context}" if additional_context else ""}

Génère maintenant une offre de prix complète et professionnelle en réponse à cet appel d'offre.
L'offre doit être structurée, détaillée et adaptée aux exigences spécifiques mentionnées."""

    return system_prompt, user_prompt


def create_analysis_prompt(tender_content: str) -> tuple:
    """
    Créer le prompt pour l'analyse d'un appel d'offre.

    Returns:
        Tuple (system_prompt, user_prompt)
    """
    system_prompt = """Tu es un expert en analyse d'appels d'offres.
Analyse le document fourni et extrais les informations clés de manière structurée."""

    user_prompt = f"""Analyse l'appel d'offre suivant et extrais:
1. Référence du marché
2. Objet/Titre
3. Date limite de réponse
4. Budget estimé (si mentionné)
5. Critères de sélection principaux
6. Exigences techniques clés
7. Documents à fournir
8. Points d'attention particuliers

DOCUMENT:

{tender_content}

Fournis une analyse structurée et concise."""

    return system_prompt, user_prompt
