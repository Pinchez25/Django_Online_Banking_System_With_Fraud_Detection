from django.test import TestCase
from django.urls import reverse


class TestBankUrls(TestCase):
    def test_dashboard_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)

    def test_deposit_page(self):
        response = self.client.get(reverse('deposit-money'))
        self.assertEqual(response.status_code, 302)

    def test_withdraw_page(self):
        response = self.client.get(reverse('withdraw-money'))
        self.assertEqual(response.status_code, 302)

    def test_send_page(self):
        response = self.client.get(reverse('send-money'))
        self.assertEqual(response.status_code, 302)

