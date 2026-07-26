import io

import fitz
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from apps.articles.models import Article
from apps.articles.services import extract_pdf_text


def _make_pdf_bytes(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


class ExtractPdfTextTest(TestCase):

    def test_extracts_text_from_pdf(self):
        pdf_bytes = _make_pdf_bytes('Bonjour depuis un PDF de test')
        text = extract_pdf_text(io.BytesIO(pdf_bytes))
        self.assertIn('Bonjour depuis un PDF de test', text)

    def test_raises_on_invalid_pdf(self):
        with self.assertRaises(Exception):
            extract_pdf_text(io.BytesIO(b'not a real pdf'))


class PostIngestViewTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='ingestuser', password='pass')
        self.client.force_authenticate(user=self.user)

    def test_ingest_pdf_creates_article(self):
        pdf_bytes = _make_pdf_bytes('Contenu du rapport annuel de la banque centrale.')
        upload = SimpleUploadedFile('rapport.pdf', pdf_bytes, content_type='application/pdf')

        response = self.client.post('/posts/ingest/', {'file': upload}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('rapport annuel', response.data['content'])
        self.assertTrue(Article.objects.filter(source__user=self.user).exists())

    def test_ingest_text_creates_article(self):
        response = self.client.post('/posts/ingest/', {
            'text': 'Transcription de la conférence de presse sur les taux directeurs.',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('conférence de presse', response.data['content'])

    def test_content_truncated_to_4000_chars(self):
        long_text = 'a' * 5000
        response = self.client.post('/posts/ingest/', {'text': long_text}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['content']), 4000)

    def test_rejects_text_over_10000_chars(self):
        response = self.client.post('/posts/ingest/', {'text': 'a' * 10001}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_empty_request(self):
        response = self.client.post('/posts/ingest/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_rejects_invalid_pdf(self):
        bad_file = SimpleUploadedFile('bad.pdf', b'not a real pdf', content_type='application/pdf')
        response = self.client.post('/posts/ingest/', {'file': bad_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post('/posts/ingest/', {'text': 'x'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
