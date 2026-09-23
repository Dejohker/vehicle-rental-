from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ContactMessage


class PublicPageTests(TestCase):
    def test_public_pages_render(self):
        for name in ['core:home', 'core:about', 'core:contact', 'vehicles:list', 'accounts:login', 'accounts:register']:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_contact_message_is_saved(self):
        response = self.client.post(reverse('core:contact'), {
            'name': 'Ada', 'email': 'ada@example.com', 'message': 'Is pickup available today?',
        })
        self.assertRedirects(response, reverse('core:contact'))
        self.assertEqual(ContactMessage.objects.get().message, 'Is pickup available today?')

    def test_invalid_contact_does_not_report_success(self):
        response = self.client.post(reverse('core:contact'), {'name': 'Ada', 'email': 'invalid', 'message': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertIn('message', response.context['form'].errors)
        self.assertFalse(ContactMessage.objects.exists())

    @override_settings(DEBUG=False)
    def test_friendly_not_found_page(self):
        response = self.client.get('/does-not-exist/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, '404.html')
