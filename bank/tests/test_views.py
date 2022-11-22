from django.test import TestCase
from django.urls import reverse


class TestBankViews(TestCase):
    def test_send_money_page(self):
        response = self.client.get(reverse('send-money'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/send/')

    def test_deposit_money_page(self):
        response = self.client.get(reverse('deposit-money'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/deposit/')

    def test_withdraw_money_page(self):
        response = self.client.get(reverse('withdraw-money'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/withdraw/')

    def test_dashboard_page(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/')

