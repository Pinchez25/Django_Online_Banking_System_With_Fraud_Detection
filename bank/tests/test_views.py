from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bank.models import Transaction, TransactionLog
from bank.services.fraud import FraudAssessment
from bank.services.transfers import FraudModelError
from bank.ml.detector import FraudResult


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

    def test_deposit_updates_balance_and_records_transaction(self):
        account = get_user_model().objects.create_user(
            username='depositor', password='password123', email='depositor@example.com', national_id=10003,
            bank_balances=100,
        )
        self.client.force_login(account)

        response = self.client.post(reverse('deposit-money'), {'type': 'D', 'amount': '25.00'})

        account.refresh_from_db()
        self.assertRedirects(response, '/')
        self.assertEqual(account.bank_balances, 125)
        self.assertEqual(Transaction.objects.filter(account=account, type='D').count(), 1)

    def test_withdrawal_updates_balance_and_records_transaction(self):
        account = get_user_model().objects.create_user(
            username='withdrawer', password='password123', email='withdrawer@example.com', national_id=10004,
            bank_balances=100,
        )
        self.client.force_login(account)

        response = self.client.post(reverse('withdraw-money'), {'type': 'W', 'amount': '25.00'})

        account.refresh_from_db()
        self.assertRedirects(response, '/')
        self.assertEqual(account.bank_balances, 75)
        self.assertEqual(Transaction.objects.filter(account=account, type='W').count(), 1)

    @patch('bank.services.transfers.FraudService.assess_transfer')
    def test_fraudulent_transfer_is_blocked_without_recording_success(self, assess_transfer):
        assess_transfer.return_value = FraudAssessment(
            result=FraudResult(
                probability=0.95,
                threshold=0.5,
                model_version="test",
                model_name="test",
            ),
            assessed_at=None,
        )
        account_model = get_user_model()
        sender = account_model.objects.create_user(
            username='sender', password='password123', email='sender@example.com', national_id=10001,
            bank_balances=100,
        )
        recipient = account_model.objects.create_user(
            username='recipient', password='password123', email='recipient@example.com', national_id=10002,
            bank_balances=50,
        )
        self.client.force_login(sender)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('send-money'), {
                'type': 'T',
                'amount': '25.00',
                'recipient': str(recipient.cc_number),
            })

        sender.refresh_from_db()
        recipient.refresh_from_db()
        self.assertRedirects(response, reverse('account-blocked'))
        self.assertTrue(sender.is_blocked)
        self.assertEqual(sender.bank_balances, 100)
        self.assertEqual(recipient.bank_balances, 50)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(TransactionLog.objects.filter(is_fraud=True).count(), 1)

    @patch('bank.services.transfers.FraudService.assess_transfer', side_effect=FraudModelError)
    def test_transfer_is_not_processed_when_fraud_screening_is_unavailable(self, assess_transfer):
        account_model = get_user_model()
        sender = account_model.objects.create_user(
            username='screening-sender', password='password123', email='screening-sender@example.com',
            national_id=10005, bank_balances=100,
        )
        recipient = account_model.objects.create_user(
            username='screening-recipient', password='password123', email='screening-recipient@example.com',
            national_id=10006, bank_balances=50,
        )
        self.client.force_login(sender)

        response = self.client.post(reverse('send-money'), {
            'type': 'T',
            'amount': '25.00',
            'recipient': str(recipient.cc_number),
        })

        sender.refresh_from_db()
        recipient.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fraud screening is unavailable')
        self.assertEqual(sender.bank_balances, 100)
        self.assertEqual(recipient.bank_balances, 50)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(TransactionLog.objects.exists())
        assess_transfer.assert_called_once()