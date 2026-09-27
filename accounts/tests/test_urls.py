from django.test import TestCase
from django.urls import reverse, resolve

from accounts.views import AccountBlockedView


class UrlTest(TestCase):
    def test_login_page(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_login_url_resolves_login_view(self):
        url = reverse('accounts:login')
        self.assertEqual(resolve(url).func.view_class.__name__, "AccountLoginView")

    def test_logout_page(self):
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)

    def test_register_page(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_register_url_resolves_register_view(self):
        url = reverse('accounts:register')
        self.assertEqual(resolve(url).func.view_class.__name__, "AccountRegisterView")

    def test_account_locked_page(self):
        response = self.client.get('/accounts/account-locked/')
        self.assertEqual(response.status_code, 200)

    def test_account_blocked_page(self):
        response = self.client.get(reverse('accounts:account-blocked'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_blocked.html')

    def test_account_blocked_url_resolves_view(self):
        url = reverse('accounts:account-blocked')
        self.assertEqual(resolve(url).func.view_class, AccountBlockedView)

    def test_reset_password_page(self):
        response = self.client.get(reverse('accounts:password-reset'))
        self.assertEqual(response.status_code, 200)

    def test_reset_password_sent_page(self):
        response = self.client.get(reverse('accounts:password-reset-done'))
        self.assertEqual(response.status_code, 200)

    def test_reset_password_complete_page(self):
        response = self.client.get(reverse('accounts:password-reset-complete'))
        self.assertEqual(response.status_code, 200)

    def test_profile_page(self):
        response = self.client.get(reverse('accounts:profile-detail'))
        self.assertEqual(response.status_code, 302)

    def test_update_profile_page(self):
        response = self.client.get(reverse('accounts:profile-update'))
        self.assertEqual(response.status_code, 302)