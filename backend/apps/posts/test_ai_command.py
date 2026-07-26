from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from apps.posts.models import Post
from apps.posts.services import AI_COMMANDS, apply_ai_command


def _mock_anthropic_client(text='Post transforme'):
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=text)]
    mock_message.usage.input_tokens = 40
    mock_message.usage.output_tokens = 15
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


class ApplyAiCommandServiceTest(TestCase):

    @patch('apps.posts.services.anthropic.Anthropic')
    def test_all_commands_produce_content(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()
        for command in AI_COMMANDS:
            result = apply_ai_command('Contenu original', command)
            self.assertEqual(result, 'Post transforme')

    @patch('apps.posts.services.anthropic.Anthropic')
    def test_uses_haiku_via_router(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()
        apply_ai_command('Contenu original', 'shorten')
        call_kwargs = mock_anthropic_cls.return_value.messages.create.call_args.kwargs
        self.assertIn('haiku', call_kwargs['model'])

    def test_unknown_command_raises(self):
        with self.assertRaises(ValueError):
            apply_ai_command('Contenu', 'not_a_command')


class PostAICommandViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='aicmduser', password='pass')
        self.client.force_authenticate(user=self.user)
        self.post = Post.objects.create(user=self.user, content='Contenu original', platform='linkedin')

    @patch('apps.posts.services.anthropic.Anthropic')
    def test_shorten_command_returns_new_content(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_anthropic_client()

        response = self.client.post(f'/posts/{self.post.id}/ai-command/', {'command': 'shorten'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Post transforme')

    def test_unknown_command_returns_400(self):
        response = self.client.post(f'/posts/{self.post.id}/ai-command/', {'command': 'bogus'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_run_command_on_other_user_post(self):
        other = User.objects.create_user(username='other4', password='pass')
        post = Post.objects.create(user=other, content='Pas a moi', platform='linkedin')
        response = self.client.post(f'/posts/{post.id}/ai-command/', {'command': 'shorten'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(f'/posts/{self.post.id}/ai-command/', {'command': 'shorten'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
