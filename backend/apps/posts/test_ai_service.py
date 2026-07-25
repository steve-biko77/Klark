from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from .ai_service import select_model
from .services import generate_post


@override_settings(MODEL_HAIKU='haiku-test', MODEL_SONNET='sonnet-test')
class SelectModelTest(TestCase):

    def test_single_platform_uses_haiku(self):
        self.assertEqual(select_model('single_platform'), 'haiku-test')

    def test_inline_ai_command_uses_haiku(self):
        self.assertEqual(select_model('inline_command'), 'haiku-test')

    def test_flash_briefing_uses_haiku(self):
        self.assertEqual(select_model('flash_briefing'), 'haiku-test')

    def test_multi_format_uses_sonnet(self):
        self.assertEqual(select_model('multi_format'), 'sonnet-test')

    def test_pdf_ingestion_uses_sonnet(self):
        self.assertEqual(select_model('pdf_ingestion'), 'sonnet-test')

    def test_unknown_task_defaults_to_haiku(self):
        self.assertEqual(select_model('something_unheard_of'), 'haiku-test')


@override_settings(MODEL_HAIKU='haiku-test', MODEL_SONNET='sonnet-test')
class GeneratePostUsesRouterTest(TestCase):

    def _mock_client(self, response_text='Post généré'):
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response_text)]
        mock_message.usage.input_tokens = 123
        mock_message.usage.output_tokens = 45

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        return mock_client

    @patch('apps.posts.services.log_ai_usage')
    @patch('apps.posts.services.anthropic.Anthropic')
    def test_generate_post_uses_haiku_model_from_router(self, mock_anthropic_cls, mock_log):
        mock_anthropic_cls.return_value = self._mock_client()

        result = generate_post(article_title='T', article_content='C', platform='linkedin')

        self.assertEqual(result, 'Post généré')
        call_kwargs = mock_anthropic_cls.return_value.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs['model'], 'haiku-test')

    @patch('apps.posts.services.log_ai_usage')
    @patch('apps.posts.services.anthropic.Anthropic')
    def test_generate_post_logs_usage(self, mock_anthropic_cls, mock_log):
        mock_anthropic_cls.return_value = self._mock_client()

        generate_post(article_title='T', article_content='C', platform='linkedin')

        mock_log.assert_called_once()
        self.assertEqual(mock_log.call_args.kwargs['tokens_in'], 123)
        self.assertEqual(mock_log.call_args.kwargs['tokens_out'], 45)
        self.assertEqual(mock_log.call_args.kwargs['task_type'], 'single_platform')
