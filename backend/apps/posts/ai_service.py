import logging

from django.conf import settings

logger = logging.getLogger('ai_usage')

# Sonnet réservé aux tâches lourdes : génération multi-plateforme simultanée,
# analyse de PDF/transcription longue, ou demande explicitement "approfondie".
# Tout le reste (mono-plateforme, commandes /ai, briefing flash) reste sur
# Haiku pour rester sous les ~3s de réponse attendues.
_SONNET_TASKS = {'multi_format', 'pdf_ingestion', 'deep_analysis'}


def select_model(task_type: str) -> str:
    if task_type in _SONNET_TASKS:
        return settings.MODEL_SONNET
    return settings.MODEL_HAIKU


def log_ai_usage(model: str, tokens_in: int, tokens_out: int, task_type: str, user_id) -> None:
    logger.info(
        'model=%s tokens_in=%s tokens_out=%s task_type=%s user_id=%s',
        model, tokens_in, tokens_out, task_type, user_id,
    )
