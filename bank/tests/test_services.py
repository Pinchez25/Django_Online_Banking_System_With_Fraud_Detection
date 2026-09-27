from decimal import Decimal
from unittest.mock import Mock
import re

from django.test import TestCase, override_settings

from bank.models import Account, Transaction, TransactionLog
from bank.ml.detector import FraudResult
from bank.services.accounts import DepositService, InsufficientFundsError, WithdrawalService
from bank.services.fraud import FraudAssessment
from bank.services.transfers import TransferService


class AccountServiceTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password",
            national_id=10000001,
            bank_balances=Decimal("1000.00"),
        )

    def test_deposit_updates_balance_and_creates_transaction(self):
        DepositService().execute(account=self.account, amount=Decimal("250.00"))
        self.account.refresh_from_db()
        self.assertEqual(self.account.bank_balances, Decimal("1250.00"))
        transaction = Transaction.objects.get(account=self.account, type="D")
        self.assertEqual(len(transaction.transaction_id), 10)
        self.assertRegex(transaction.transaction_id, r"^[A-HJ-NP-Z2-9]{10}$")

    def test_withdrawal_rejects_insufficient_funds(self):
        with self.assertRaises(InsufficientFundsError):
            WithdrawalService().execute(account=self.account, amount=Decimal("1000.01"))


class TransferServiceTests(TestCase):
    def setUp(self):
        self.sender = Account.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="password",
            national_id=10000002,
            bank_balances=Decimal("1000.00"),
        )
        self.receiver = Account.objects.create_user(
            username="receiver",
            email="receiver@example.com",
            password="password",
            national_id=10000003,
            bank_balances=Decimal("100.00"),
        )

    def test_approved_transfer_moves_money_and_creates_transaction(self):
        fraud_service = Mock()
        fraud_service.assess_transfer.return_value = FraudAssessment(
            result=FraudResult(
                probability=0.01,
                threshold=0.5,
                model_version="1.0.0",
                model_name="test",
            ),
            assessed_at=None,
        )

        result = TransferService(fraud_service=fraud_service).execute(
            sender=self.sender,
            receiver=self.receiver,
            amount=Decimal("200.00"),
        )

        self.assertFalse(result.fraud_detected)
        self.sender.refresh_from_db()
        self.receiver.refresh_from_db()
        self.assertEqual(self.sender.bank_balances, Decimal("800.00"))
        self.assertEqual(self.receiver.bank_balances, Decimal("300.00"))
        self.assertEqual(Transaction.objects.filter(account=self.sender, type="T").count(), 1)
        self.assertEqual(TransactionLog.objects.count(), 1)
        self.assertFalse(TransactionLog.objects.get().is_fraud)

    @override_settings(FRAUD_ALERT_EMAIL="alerts@example.com", DEFAULT_FROM_EMAIL="noreply@example.com")
    def test_fraud_blocks_account_and_keeps_audit_record(self):
        fraud_service = Mock()
        fraud_service.assess_transfer.return_value = FraudAssessment(
            result=FraudResult(
                probability=0.99,
                threshold=0.5,
                model_version="1.0.0",
                model_name="test",
            ),
            assessed_at=None,
        )

        with self.captureOnCommitCallbacks(execute=True):
            result = TransferService(fraud_service=fraud_service).execute(
                sender=self.sender,
                receiver=self.receiver,
                amount=Decimal("200.00"),
            )

        self.assertTrue(result.fraud_detected)
        self.sender.refresh_from_db()
        self.assertTrue(self.sender.is_blocked)
        self.assertEqual(self.sender.bank_balances, Decimal("1000.00"))
        self.assertEqual(Transaction.objects.count(), 0)
        log = TransactionLog.objects.get()
        self.assertTrue(log.is_fraud)
        self.assertEqual(log.fraud_probability, 0.99)
