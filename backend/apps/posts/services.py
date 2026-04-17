import anthropic
from django.conf import settings

_PLATFORM_INSTRUCTIONS = {
    'linkedin': 'un post LinkedIn professionnel, engageant, avec des sauts de ligne, maximum 1300 caractères',
    'twitter': 'un tweet percutant, maximum 280 caractères, sans hashtags excessifs',
    'blog': 'une introduction de blog structurée, 3 paragraphes, ton informatif',
}


def generate_post(article_title: str, article_content: str, platform: str = 'linkedin', style_prompt: str = '') -> str:
    instruction = _PLATFORM_INSTRUCTIONS.get(platform, _PLATFORM_INSTRUCTIONS['linkedin'])
    style = f"\nStyle de l'auteur : {style_prompt}" if style_prompt else ''

    prompt = f"""Tu es un expert en création de contenu digital.
A partir de cet article, rédige {instruction}.{style}

Titre de l'article : {article_title}

Contenu : {article_content[:2000]}

Rédige uniquement le post, sans explication ni commentaire."""

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    return message.content[0].text
