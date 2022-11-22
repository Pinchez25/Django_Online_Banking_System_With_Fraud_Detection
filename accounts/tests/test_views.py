from django.test import TestCase
from django.urls import reverse


# Create your tests here.
class TestViews(TestCase):
    def test_login_page(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_logout_page(self):
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/')

    def test_register_page(self):
        response = self.client.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/bank_account_creation.html')

    def test_account_locked_page(self):
        response = self.client.get('/accounts/account-locked/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account_locked.html')

    def test_account_blocked_page(self):
        response = self.client.get('/accounts/account-blocked/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_blocked.html')

    def test_profile_page(self):
        response = self.client.get('/accounts/1/1-profile/')
        self.assertEqual(response.status_code, 302)

    def anonymous_cannot_access_profile_page(self):
        response = self.client.get('/accounts/1/1-profile/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/accounts/1/1-profile/')

    def anonymous_cannot_access_update_profile_page(self):
        response = self.client.get('/accounts/update-profile/1/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/accounts/update-profile/1/')

    def test_update_profile_page(self):
        response = self.client.get('/accounts/update-profile/1/')
        self.assertEqual(response.status_code, 302)

