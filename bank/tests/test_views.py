from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bank.models import Notification, Transaction, TransactionLog
from bank.services.fraud import FraudAssessment
from bank.services.transfers import FraudModelError
from bank.ml.detector import FraudResult


class TestBankViews(TestCase):
    def test_send_money_page(self):
        response = self.client.get(reverse('bank:send-money'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/send/')

    def test_deposit_money_page(self):
        response = self.client.get(reverse('bank:deposit-money'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/deposit/')

    def test_withdraw_money_page(self):
        response = self.client.get(reverse('bank:withdraw-money'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/withdraw/')

    def test_dashboard_page(self):
        response = self.client.get(reverse('bank:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/accounts/login/?next=/')

    def test_dashboard_context_data(self):
        account = get_user_model().objects.create_user(
            username='dashboarduser', password='password123', email='dash@example.com', national_id=30001,
        )
        self.client.force_login(account)
        response = self.client.get(reverse('bank:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('summary', response.context)
        self.assertIn('transactions', response.context)
        self.assertIn('cards', response.context)

    def test_deposit_updates_balance_and_records_transaction(self):
        account = get_user_model().objects.create_user(
            username='depositor', password='password123', email='depositor@example.com', national_id=10003,
            bank_balances=100,
        )
        self.client.force_login(account)

        response = self.client.post(reverse('bank:deposit-money'), {'type': 'D', 'amount': '25.00'})

        account.refresh_from_db()
        self.assertRedirects(response, reverse('bank:dashboard'))
        self.assertEqual(account.bank_balances, 125)
        self.assertEqual(Transaction.objects.filter(account=account, type='D').count(), 1)

    def test_withdrawal_updates_balance_and_records_transaction(self):
        account = get_user_model().objects.create_user(
            username='withdrawer', password='password123', email='withdrawer@example.com', national_id=10004,
            bank_balances=100,
        )
        self.client.force_login(account)

        response = self.client.post(reverse('bank:withdraw-money'), {'type': 'W', 'amount': '25.00'})

        account.refresh_from_db()
        self.assertRedirects(response, reverse('bank:dashboard'))
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
            response = self.client.post(reverse('bank:send-money'), {
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

        response = self.client.post(reverse('bank:send-money'), {
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


class NotificationViewTests(TestCase):
    def setUp(self):
        account_model = get_user_model()
        self.account = account_model.objects.create_user(
            username="notification-user",
            password="password123",
            email="notification@example.com",
            national_id=40001,
        )
        self.other_account = account_model.objects.create_user(
            username="other-notification-user",
            password="password123",
            email="other-notification@example.com",
            national_id=40002,
        )

    def test_dashboard_shows_unread_counts_and_only_own_notifications(self):
        alert = Notification.objects.create(
            recipient=self.account,
            kind=Notification.Kind.ALERT,
            title="Account update",
            body="Your account was updated.",
        )
        Notification.objects.create(
            recipient=self.account,
            kind=Notification.Kind.MESSAGE,
            title="Welcome",
            body="Welcome to Kwetu Bank.",
        )
        Notification.objects.create(
            recipient=self.other_account,
            kind=Notification.Kind.ALERT,
            title="Private alert",
            body="Not for this account.",
        )
        self.client.force_login(self.account)

        response = self.client.get(reverse("bank:dashboard"))

        self.assertEqual(response.context["alerts_unread_count"], 1)
        self.assertEqual(response.context["messages_unread_count"], 1)
        self.assertEqual(list(response.context["alerts"]), [alert])
        self.assertNotContains(response, "Private alert")

    def test_mark_read_cannot_change_another_users_notification(self):
        notification = Notification.objects.create(
            recipient=self.other_account,
            kind=Notification.Kind.ALERT,
            title="Private alert",
            body="Private.",
        )
        self.client.force_login(self.account)

        response = self.client.post(
            reverse("bank:notification-read", args=[notification.pk]),
        )

        self.assertEqual(response.status_code, 404)
        notification.refresh_from_db()
        self.assertIsNone(notification.read_at)

    def test_mark_all_read_can_be_limited_to_notification_kind(self):
        alert = Notification.objects.create(
            recipient=self.account,
            kind=Notification.Kind.ALERT,
            title="Account update",
            body="Your account was updated.",
        )
        message = Notification.objects.create(
            recipient=self.account,
            kind=Notification.Kind.MESSAGE,
            title="Welcome",
            body="Welcome to Kwetu Bank.",
        )
        self.client.force_login(self.account)

        response = self.client.post(
            reverse("bank:notifications-read-all"),
            {"kind": Notification.Kind.ALERT},
        )

        self.assertRedirects(response, reverse("bank:notification-center"))
        alert.refresh_from_db()
        message.refresh_from_db()
        self.assertIsNotNone(alert.read_at)
        self.assertIsNone(message.read_at)

    def test_notification_center_lists_only_current_users_notifications(self):
        Notification.objects.create(
            recipient=self.account,
            kind=Notification.Kind.MESSAGE,
            title="Welcome",
            body="Welcome to Kwetu Bank.",
        )
        Notification.objects.create(
            recipient=self.other_account,
            kind=Notification.Kind.MESSAGE,
            title="Private message",
            body="Not for this account.",
        )
        self.client.force_login(self.account)

        response = self.client.get(reverse("bank:notification-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome")
        self.assertNotContains(response, "Private message")