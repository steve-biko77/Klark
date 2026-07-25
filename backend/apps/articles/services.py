import re

import anthropic
from django.conf import settings


def parse_score(text: str) -> int:
    """Extrait un entier 0-100 de la réponse Claude ; 0 si rien d'exploitable."""
    match = re.search(r'\d+', text)
    if not match:
        return 0
    return max(0, min(100, int(match.group())))


def score_article(article_title: str, article_content: str, persona: str, sector: str = '', style_prompt: str = '') -> int:
    prompt = f"""Tu es un assistant qui évalue la pertinence d'un article pour un utilisateur.

Profil utilisateur :
- Persona : {persona}
- Secteur d'intérêt : {sector or 'non précisé'}
- Style éditorial : {style_prompt or 'non précisé'}

Article à évaluer :
Titre : {article_title}
Contenu : {article_content[:2000]}

Évalue la pertinence de cet article pour ce profil sur une échelle de 0 à 100.
Réponds UNIQUEMENT avec un nombre entier entre 0 et 100, sans aucune explication."""

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=10,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return parse_score(message.content[0].text)
