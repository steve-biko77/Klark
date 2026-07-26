import anthropic
from django.conf import settings

from .ai_service import log_ai_usage, select_model

_PLATFORM_INSTRUCTIONS = {
    'linkedin': 'un post LinkedIn professionnel, engageant, avec des sauts de ligne, maximum 1300 caractères',
    'twitter': 'un tweet percutant, maximum 280 caractères, sans hashtags excessifs',
    'blog': 'une introduction de blog structurée, 3 paragraphes, ton informatif',
}


def generate_post(article_title: str, article_content: str, platform: str = 'linkedin',
                   style_prompt: str = '', user_id=None, task_type: str = 'single_platform') -> str:
    instruction = _PLATFORM_INSTRUCTIONS.get(platform, _PLATFORM_INSTRUCTIONS['linkedin'])
    style = f"\nStyle de l'auteur : {style_prompt}" if style_prompt else ''

    prompt = f"""Tu es un expert en création de contenu digital.
A partir de cet article, rédige {instruction}.{style}

Titre de l'article : {article_title}

Contenu : {article_content[:2000]}

Rédige uniquement le post, sans explication ni commentaire."""

    model = select_model(task_type)
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model,
        tokens_in=message.usage.input_tokens,
        tokens_out=message.usage.output_tokens,
        task_type=task_type,
        user_id=user_id,
    )
    return message.content[0].text


AI_COMMAND_INSTRUCTIONS = {
    'shorten': "Réduis ce post d'environ 30% en gardant l'essentiel du message, sans perdre le sens.",
    'expand': "Développe ce post avec plus de détails et des exemples concrets, en gardant la cohérence.",
    'tone:formal': "Reformule ce post dans un ton plus professionnel et formel.",
    'tone:casual': "Reformule ce post dans un ton plus décontracté et accessible.",
    'angle:question': "Transforme le hook (première ligne) de ce post en question ouverte percutante, garde le reste du post inchangé.",
    'angle:stat': "Réécris le hook (première ligne) de ce post en l'introduisant par un chiffre ou une statistique marquante, garde le reste du post inchangé.",
    'hashtags': "Ajoute 5 hashtags pertinents à la toute fin de ce post, sans modifier le reste du texte.",
}

AI_COMMANDS = frozenset(AI_COMMAND_INSTRUCTIONS.keys())


def apply_ai_command(content: str, command: str, style_prompt: str = '', user_id=None) -> str:
    """Applique une commande /ai (shorten, expand, tone:*, angle:*, hashtags) au
    contenu d'un post existant, via Claude Haiku (routeur SCRUM-29)."""
    instruction = AI_COMMAND_INSTRUCTIONS.get(command)
    if not instruction:
        raise ValueError(f"Commande /ai inconnue : {command}")

    style = f"\nStyle de l'auteur à respecter : {style_prompt}" if style_prompt else ''
    prompt = f"""Voici un post existant :

{content}

Instruction : {instruction}{style}

Réponds uniquement avec le nouveau texte du post, sans explication ni commentaire."""

    model = select_model('inline_command')
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )
    log_ai_usage(
        model=model,
        tokens_in=message.usage.input_tokens,
        tokens_out=message.usage.output_tokens,
        task_type='inline_command',
        user_id=user_id,
    )
    return message.content[0].text.strip()
