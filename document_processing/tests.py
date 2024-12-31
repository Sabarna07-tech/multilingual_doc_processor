from django.test import TestCase
from django.test import TestCase
from django.contrib.auth.models import User
from .models import Document

class DashboardTest(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')

        # Create test documents
        Document.objects.create(user=self.user, file_name='English Document', language='en', text='Hello World')
        Document.objects.create(user=self.user, file_name='Spanish Document', language='es', text='Hola Mundo')

    def test_search_documents(self):
        response = self.client.get('/dashboard/', {'search': 'English'})
        self.assertContains(response, 'English Document')
        self.assertNotContains(response, 'Spanish Document')

    def test_filter_documents_by_language(self):
        response = self.client.get('/dashboard/', {'language': 'es'})
        self.assertContains(response, 'Spanish Document')
        self.assertNotContains(response, 'English Document')
class ExportDocumentTest(TestCase):
    def setUp(self):
        # Create a test user and document
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.login(username='testuser', password='testpass')
        self.document = Document.objects.create(
            user=self.user,
            file_name='Test Document',
            language='en',
            text='Sample extracted text.',
            translated_text='Translated sample text.'
        )

    def test_export_document(self):
        response = self.client.get(f'/export/{self.document.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Sample extracted text.', response.content.decode())
        self.assertIn('Translated sample text.', response.content.decode())

    def test_export_invalid_document(self):
        response = self.client.get('/export/999/')  # Non-existent document ID
        self.assertEqual(response.status_code, 404)

# Create your tests here.
