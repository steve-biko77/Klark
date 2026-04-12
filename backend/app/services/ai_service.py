import anthropic
from app.core.config import settings

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

def generate_post(article_title: str, article_content: str, platform: str = "linkedin", style_prompt: str = "") -> str:

    platform_instructions = {
        "linkedin": "un post LinkedIn professionnel, engageant, avec des sauts de ligne, maximum 1300 caracteres",
        "twitter": "un tweet percutant, maximum 280 caracteres, sans hashtags excessifs",
        "blog": "une introduction de blog structuree, 3 paragraphes, ton informatif",
    }

    instruction = platform_instructions.get(platform, platform_instructions["linkedin"])

    style = f"\nStyle de l'auteur : {style_prompt}" if style_prompt else ""

    prompt = f"""Tu es un expert en creation de contenu digital.

A partir de cet article, redige {instruction}.{style}

Titre de l'article : {article_title}

Contenu : {article_content[:2000]}

Redige uniquement le post, sans explication ni commentaire."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return message.content[0].text