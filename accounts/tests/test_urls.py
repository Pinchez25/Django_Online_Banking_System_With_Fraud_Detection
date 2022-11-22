from django.test import TestCase
from ..views import user_login as login, UserRegistrationView
from django.urls import reverse, resolve


class UrlTest(TestCase):
    def test_login_page(self):
        response = self.client.get('/accounts/login/')
        self.assertEqual(response.status_code, 200)

    # check that resolver method matches login view
    def test_login_url_resolves_login_view(self):
        url = reverse('login')
        # print(resolve(url))
        self.assertEquals(resolve(url).func, login)

    def test_logout_page(self):
        response = self.client.get('/accounts/logout/')
        self.assertEqual(response.status_code, 302)

    def test_register_page(self):
        response = self.client.get('/accounts/register/')
        self.assertEqual(response.status_code, 200)

    # check that resolver method matches register view
    def test_register_url_resolves_register_view(self):
        url = reverse('register')
        # print(resolve(url))
        self.assertEquals(resolve(url).func.view_class, UserRegistrationView)

    def test_account_locked_page(self):
        response = self.client.get('/accounts/account-locked/')
        self.assertEqual(response.status_code, 200)

    def test_account_blocked_page(self):
        response = self.client.get('/accounts/account-blocked/')
        self.assertEqual(response.status_code, 200)

    def test_reset_password_page(self):
        response = self.client.get('/accounts/reset_password/')
        self.assertEqual(response.status_code, 200)

    def test_reset_password_sent_page(self):
        response = self.client.get('/accounts/reset_password_sent/')
        self.assertEqual(response.status_code, 200)

    def test_reset_password_complete_page(self):
        response = self.client.get('/accounts/reset_password_complete/')
        self.assertEqual(response.status_code, 200)

    def test_profile_page(self):
        response = self.client.get('/accounts/1/1-profile/')
        self.assertEqual(response.status_code, 302)

    def test_update_profile_page(self):
        response = self.client.get('/accounts/update-profile/1/')
        self.assertEqual(response.status_code, 302)
