from django.test import TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model


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
        response = self.client.get(reverse('profile', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_cannot_access_profile_page(self):
        response = self.client.get(reverse('profile', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/accounts/1/profile/')

    def anonymous_cannot_access_update_profile_page(self):
        response = self.client.get('/accounts/update-profile/1/')
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/accounts/update-profile/1/')

    def test_update_profile_page(self):
        response = self.client.get('/accounts/update-profile/1/')
        self.assertEqual(response.status_code, 302)

    def test_user_cannot_view_another_accounts_profile(self):
        account_model = get_user_model()
        owner = account_model.objects.create_user(
            username='profile-owner', password='password123', email='owner@example.com', national_id=20001,
        )
        other = account_model.objects.create_user(
            username='profile-other', password='password123', email='other@example.com', national_id=20002,
        )
        self.client.force_login(other)

        response = self.client.get(reverse('profile', kwargs={'pk': owner.profile.pk}))

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_edit_another_accounts_profile(self):
        account_model = get_user_model()
        owner = account_model.objects.create_user(
            username='edit-owner', password='password123', email='edit-owner@example.com', national_id=20003,
        )
        other = account_model.objects.create_user(
            username='edit-other', password='password123', email='edit-other@example.com', national_id=20004,
        )
        self.client.force_login(other)

        response = self.client.get(reverse('update-profile', kwargs={'pk': owner.profile.pk}))

        self.assertEqual(response.status_code, 404)

    def test_wrong_password_redirects_without_server_error(self):
        get_user_model().objects.create_user(
            username='login-user', password='password123', email='login@example.com', national_id=20005,
        )

        response = self.client.post(reverse('login'), {
            'email': 'login@example.com',
            'password': 'incorrect-password',
        })

        self.assertRedirects(response, reverse('login'))

