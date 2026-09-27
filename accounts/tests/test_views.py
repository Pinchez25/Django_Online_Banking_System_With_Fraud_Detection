from django.test import TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model


# Create your tests here.
class TestViews(TestCase):
    def test_login_page(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')

    def test_logout_page(self):
        response = self.client.get(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/')

    def test_register_page(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/register.html')

    def test_account_locked_page(self):
        response = self.client.get('/accounts/account-locked/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account_locked.html')

    def test_account_blocked_page(self):
        response = self.client.get('/accounts/account-blocked/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/account_blocked.html')

    def test_profile_page(self):
        response = self.client.get(reverse('accounts:profile-detail'))
        self.assertEqual(response.status_code, 302)

    def test_anonymous_cannot_access_profile_page(self):
        response = self.client.get(reverse('accounts:profile-detail'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/accounts/profile/')

    def anonymous_cannot_access_update_profile_page(self):
        response = self.client.get(reverse('accounts:profile-update'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/accounts/profile/edit/')

    def test_update_profile_page(self):
        response = self.client.get(reverse('accounts:profile-update'))
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

        response = self.client.get(reverse('accounts:profile-detail'))

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

        response = self.client.get(reverse('accounts:profile-update'))

        self.assertEqual(response.status_code, 404)

    def test_wrong_password_redirects_without_server_error(self):
        get_user_model().objects.create_user(
            username='login-user', password='password123', email='login@example.com', national_id=20005,
        )

        response = self.client.post(reverse('accounts:login'), {
            'email': 'login@example.com',
            'password': 'incorrect-password',
        })

        self.assertRedirects(response, reverse('accounts:login'))


class ProfileWorkflowTests(TestCase):
    def setUp(self):
        self.account = get_user_model().objects.create_user(
            username="profile-customer",
            email="profile-customer@example.com",
            password="correct-password",
            national_id=91234568,
        )
        self.client.force_login(self.account)

    def test_profile_page_displays_persisted_customer_data(self):
        profile = self.account.profile
        profile.first_name = "Amina"
        profile.last_name = "Wanjiru"
        profile.phone_number = "+254700000001"
        profile.postal_code = "00100"
        profile.save()

        response = self.client.get(reverse("accounts:profile-detail"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amina Wanjiru")
        self.assertContains(response, "Hi, Amina")
        self.assertContains(response, "00100")
        self.assertContains(response, self.account.email)

    def test_profile_update_saves_postal_code_and_multiple_kin(self):
        response = self.client.post(
            reverse("accounts:profile-update"),
            {
                "first_name": "Amina",
                "last_name": "Wanjiru",
                "phone_number": "+254700000001",
                "address": "Kilimani",
                "city": "Nairobi",
                "postal_code": "00100",
                "next_of_kin-TOTAL_FORMS": "2",
                "next_of_kin-INITIAL_FORMS": "0",
                "next_of_kin-MIN_NUM_FORMS": "0",
                "next_of_kin-MAX_NUM_FORMS": "1000",
                "next_of_kin-0-full_name": "Wanjiku Mwangi",
                "next_of_kin-0-relationship": "parent",
                "next_of_kin-0-phone_number": "+254700000001",
                "next_of_kin-0-email": "",
                "next_of_kin-1-full_name": "Kamau Mwangi",
                "next_of_kin-1-relationship": "sibling",
                "next_of_kin-1-phone_number": "+254700000002",
                "next_of_kin-1-email": "kamau@example.com",
            },
        )

        self.assertRedirects(response, reverse("accounts:profile-detail"))
        profile = self.account.profile
        self.assertEqual(profile.postal_code, "00100")
        self.assertEqual(profile.next_of_kin.count(), 2)
        self.assertEqual(
            list(profile.next_of_kin.values_list("full_name", flat=True)),
            ["Wanjiku Mwangi", "Kamau Mwangi"],
        )

    def test_account_deactivation_requires_password_and_retains_records(self):
        url = reverse("accounts:account-deactivate")
        invalid_response = self.client.post(url, {"password": "wrong-password", "confirm": "on"})

        self.assertEqual(invalid_response.status_code, 200)
        self.account.refresh_from_db()
        self.assertTrue(self.account.is_active)

        response = self.client.post(url, {"password": "correct-password", "confirm": "on"})

        self.assertRedirects(response, reverse("accounts:login"))
        self.account.refresh_from_db()
        self.assertFalse(self.account.is_active)
        self.assertIsNotNone(self.account.deactivated_at)
        self.assertTrue(get_user_model().objects.filter(pk=self.account.pk).exists())
        self.assertTrue(get_user_model().objects.get(pk=self.account.pk).profile)

