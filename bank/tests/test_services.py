from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings

from accounts.models import Account
from bank.ml.detector import FraudResult
from bank.models import Notification, Transaction, TransactionLog
from bank.services.accounts import DepositService, InsufficientFundsError, WithdrawalService
from bank.services.fraud import FraudAssessment
from bank.services.service import (
    approve_batch,
    approve_transaction,
    reject_batch,
)
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

    def test_deposit_creates_pending_transaction_until_approved(self):
        DepositService().execute(account=self.account, amount=Decimal("250.00"))
        self.account.refresh_from_db()
        self.assertEqual(self.account.bank_balances, Decimal("1000.00"))
        transaction = Transaction.objects.get(account=self.account, type="D")
        self.assertEqual(transaction.status, Transaction.Status.PENDING)
        self.assertEqual(len(transaction.transaction_id), 10)
        self.assertRegex(transaction.transaction_id, r"^[A-HJ-NP-Z2-9]{10}$")
        notification = Notification.objects.get(recipient=self.account)
        self.assertEqual(notification.kind, Notification.Kind.ALERT)
        self.assertEqual(notification.title, "Deposit submitted for approval")

    def test_manager_can_approve_deposit(self):
        manager = Account.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="password",
            national_id=10000004,
        )
        manager.user_permissions.add(Permission.objects.get(codename="approve_transaction"))

        deposit = DepositService().execute(account=self.account, amount=Decimal("250.00"))
        self.assertEqual(deposit.transaction.status, Transaction.Status.PENDING)

        deposit.transaction.approve(approved_by=manager)
        self.account.refresh_from_db()
        self.assertEqual(self.account.bank_balances, Decimal("1250.00"))
        self.assertEqual(deposit.transaction.status, Transaction.Status.APPROVED)

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

    def test_transfer_creates_pending_transaction_until_approved(self):
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
        self.assertEqual(self.sender.bank_balances, Decimal("1000.00"))
        self.assertEqual(self.receiver.bank_balances, Decimal("100.00"))
        transfer = Transaction.objects.get(account=self.sender, type="T")
        self.assertEqual(transfer.status, Transaction.Status.PENDING)
        self.assertEqual(transfer.recipient_id, self.receiver.pk)
        self.assertEqual(TransactionLog.objects.count(), 1)
        self.assertFalse(TransactionLog.objects.get().is_fraud)
        self.assertEqual(
            Notification.objects.filter(kind=Notification.Kind.ALERT).count(),
            1,
        )

    def test_manager_can_approve_transfer(self):
        manager = Account.objects.create_user(
            username="manager2",
            email="manager2@example.com",
            password="password",
            national_id=10000005,
        )
        manager.user_permissions.add(Permission.objects.get(codename="approve_transaction"))

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
        transfer = result.transaction

        transfer.approve(approved_by=manager)
        self.sender.refresh_from_db()
        self.receiver.refresh_from_db()
        self.assertEqual(self.sender.bank_balances, Decimal("800.00"))
        self.assertEqual(self.receiver.bank_balances, Decimal("300.00"))
        self.assertEqual(transfer.status, Transaction.Status.APPROVED)

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
        self.assertEqual(
            Notification.objects.get(recipient=self.sender).title,
            "Transfer blocked",
        )


class TransactionApprovalTests(TestCase):
    def setUp(self):
        self.account = self.create_account(
            email="sender@example.com",
            balance="1000.00",
        )
        self.recipient = self.create_account(
            email="recipient@example.com",
            balance="500.00",
        )

    @staticmethod
    def create_account(email, balance="0.00", username=None):
        if username is None:
            username = email.split("@")[0]
        account = Account.objects.create_user(
            username=username,
            email=email,
            password="test-password",
        )
        account.bank_balances = Decimal(balance)
        account.save(update_fields=["bank_balances"])
        return account

    def create_transaction(
            self,
            transaction_type="D",
            account=None,
            recipient=None,
            amount="100.00",
            status=Transaction.Status.PENDING,
    ):
        return Transaction.objects.create(
            account=account or self.account,
            recipient=recipient,
            type=transaction_type,
            amount=Decimal(amount),
            status=status,
        )

    def test_deposit_is_approved_and_increases_balance(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
            amount="250.00",
        )

        result = approve_transaction(transaction_instance)

        self.account.refresh_from_db()
        transaction_instance.refresh_from_db()

        self.assertEqual(result.pk, transaction_instance.pk)
        self.assertEqual(
            self.account.bank_balances,
            Decimal("1250.00"),
        )
        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.APPROVED,
        )
        self.assertIsNotNone(transaction_instance.approved_at)
        self.assertIsNone(transaction_instance.approved_by)

    def test_withdrawal_is_approved_and_decreases_balance(self):
        transaction_instance = self.create_transaction(
            transaction_type="W",
            amount="250.00",
        )

        approve_transaction(transaction_instance)

        self.account.refresh_from_db()
        transaction_instance.refresh_from_db()

        self.assertEqual(
            self.account.bank_balances,
            Decimal("750.00"),
        )
        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.APPROVED,
        )

    def test_transfer_moves_money_between_accounts(self):
        transaction_instance = self.create_transaction(
            transaction_type="T",
            amount="300.00",
            recipient=self.recipient,
        )

        approve_transaction(transaction_instance)

        self.account.refresh_from_db()
        self.recipient.refresh_from_db()
        transaction_instance.refresh_from_db()

        self.assertEqual(
            self.account.bank_balances,
            Decimal("700.00"),
        )
        self.assertEqual(
            self.recipient.bank_balances,
            Decimal("800.00"),
        )
        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.APPROVED,
        )

    def test_insufficient_withdrawal_is_rejected_and_persists_rejection(self):
        transaction_instance = self.create_transaction(
            transaction_type="W",
            amount="1500.00",
        )

        with self.assertRaisesMessage(
                ValueError,
                "The account does not have enough funds to complete this withdrawal.",
        ):
            approve_transaction(transaction_instance)

        transaction_instance.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.REJECTED,
        )

        self.account.refresh_from_db()

        self.assertEqual(
            self.account.bank_balances,
            Decimal("1000.00"),
        )

    def test_insufficient_transfer_is_rejected_and_persists_rejection(self):
        transaction_instance = self.create_transaction(
            transaction_type="T",
            amount="1500.00",
            recipient=self.recipient,
        )

        with self.assertRaisesMessage(
                ValueError,
                "The account does not have enough funds to complete this transfer.",
        ):
            approve_transaction(transaction_instance)

        transaction_instance.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.REJECTED,
        )

        self.account.refresh_from_db()
        self.recipient.refresh_from_db()

        self.assertEqual(
            self.account.bank_balances,
            Decimal("1000.00"),
        )
        self.assertEqual(
            self.recipient.bank_balances,
            Decimal("500.00"),
        )

    def test_transfer_requires_recipient(self):
        transaction_instance = self.create_transaction(
            transaction_type="T",
            amount="100.00",
        )

        with self.assertRaisesMessage(
                ValueError,
                "Transfer recipient is missing.",
        ):
            approve_transaction(transaction_instance)

        transaction_instance.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.PENDING,
        )

    def test_self_transfer_is_rejected(self):
        transaction_instance = self.create_transaction(
            transaction_type="T",
            amount="100.00",
            recipient=self.account,
        )

        with self.assertRaisesMessage(
                ValueError,
                "An account cannot transfer funds to itself.",
        ):
            approve_transaction(transaction_instance)

        transaction_instance.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.PENDING,
        )
        self.assertEqual(
            self.account.bank_balances,
            Decimal("1000.00"),
        )

    def test_non_pending_transaction_cannot_be_approved(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
            status=Transaction.Status.APPROVED,
        )

        with self.assertRaisesMessage(
                ValueError,
                "Only pending transactions can be approved.",
        ):
            approve_transaction(transaction_instance)

        self.account.refresh_from_db()

        self.assertEqual(
            self.account.bank_balances,
            Decimal("1000.00"),
        )

    def test_rejected_transaction_cannot_be_approved(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
            status=Transaction.Status.REJECTED,
        )

        with self.assertRaisesMessage(
                ValueError,
                "Only pending transactions can be approved.",
        ):
            approve_transaction(transaction_instance)

    def test_failed_transaction_cannot_be_approved(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
            status=Transaction.Status.FAILED,
        )

        with self.assertRaisesMessage(
                ValueError,
                "Only pending transactions can be approved.",
        ):
            approve_transaction(transaction_instance)

    def test_permission_is_required_when_approver_is_supplied(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
            amount="100.00",
        )

        approver = Mock()
        approver.can_approve_transactions.return_value = False

        with self.assertRaises(PermissionDenied):
            approve_transaction(
                transaction_instance,
                approved_by=approver,
            )

        transaction_instance.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.PENDING,
        )
        self.assertEqual(
            self.account.bank_balances,
            Decimal("1000.00"),
        )

    def test_zero_amount_is_rejected(self):
        from bank.services.service import _validate_transaction_amount

        with self.assertRaisesMessage(
                ValueError,
                "Transaction amount must be greater than zero.",
        ):
            _validate_transaction_amount(Decimal("0.00"))

    def test_negative_amount_is_rejected(self):
        from bank.services.service import _validate_transaction_amount

        with self.assertRaisesMessage(
                ValueError,
                "Transaction amount must be greater than zero.",
        ):
            _validate_transaction_amount(Decimal("-100.00"))

    def test_non_finite_amount_is_rejected(self):
        from bank.services.service import _validate_transaction_amount

        with self.assertRaisesMessage(
                ValueError,
                "Transaction amount must be finite.",
        ):
            _validate_transaction_amount(Decimal("NaN"))

    def test_none_amount_is_rejected(self):
        from bank.services.service import _validate_transaction_amount

        with self.assertRaisesMessage(
                ValueError,
                "Transaction amount is required.",
        ):
            _validate_transaction_amount(None)

    def test_unsupported_transaction_type_is_rejected(self):
        transaction_instance = self.create_transaction(
            transaction_type="X",
            amount="100.00",
        )

        with self.assertRaisesMessage(
                ValueError,
                "Unsupported transaction type: X",
        ):
            approve_transaction(transaction_instance)

        transaction_instance.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.PENDING,
        )

    def test_missing_sender_account_is_handled(self):
        import uuid
        from bank.services.service import _lock_account

        with self.assertRaisesMessage(
                ValueError,
                "The account associated with this transaction no longer exists.",
        ):
            _lock_account(uuid.uuid4())

    def test_missing_recipient_account_is_handled(self):
        transaction_instance = self.create_transaction(
            transaction_type="T",
            amount="100.00",
            recipient=self.recipient,
        )

        recipient_id = transaction_instance.recipient_id
        Account.objects.filter(pk=recipient_id).delete()

        transaction_instance.refresh_from_db()

        self.assertIsNone(transaction_instance.recipient_id)

        with self.assertRaisesMessage(
                ValueError,
                "Transfer recipient is missing.",
        ):
            approve_transaction(transaction_instance)

    def test_transaction_approve_method_uses_service(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
            amount="100.00",
        )

        transaction_instance.approve()

        transaction_instance.refresh_from_db()
        self.account.refresh_from_db()

        self.assertEqual(
            transaction_instance.status,
            Transaction.Status.APPROVED,
        )
        self.assertEqual(
            self.account.bank_balances,
            Decimal("1100.00"),
        )

    def test_approved_at_is_set_only_after_approval(self):
        transaction_instance = self.create_transaction(
            transaction_type="D",
        )

        self.assertIsNone(transaction_instance.approved_at)

        approve_transaction(transaction_instance)

        transaction_instance.refresh_from_db()

        self.assertIsNotNone(transaction_instance.approved_at)


class BatchApprovalServiceTests(TestCase):
    def setUp(self):
        self.manager = Account.objects.create_user(
            username="batch_manager",
            email="manager@example.com",
            password="password",
            national_id=20000001,
            is_staff=True,
        )
        self.manager.user_permissions.add(
            Permission.objects.get(codename="approve_transaction")
        )

        self.unauthorized_user = Account.objects.create_user(
            username="unauthorized_user",
            email="unauth@example.com",
            password="password",
            national_id=20000002,
        )

        self.user_a = Account.objects.create_user(
            username="user_a",
            email="user_a@example.com",
            password="password",
            national_id=20000003,
            bank_balances=Decimal("1000.00"),
        )
        self.user_b = Account.objects.create_user(
            username="user_b",
            email="user_b@example.com",
            password="password",
            national_id=20000004,
            bank_balances=Decimal("500.00"),
        )

    def test_approve_batch_success(self):
        t1 = Transaction.objects.create(
            account=self.user_a,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.PENDING,
        )
        t2 = Transaction.objects.create(
            account=self.user_a,
            recipient=self.user_b,
            type="T",
            amount=Decimal("200.00"),
            status=Transaction.Status.PENDING,
        )

        result = approve_batch(
            Transaction.objects.filter(pk__in=[t1.pk, t2.pk]),
            approved_by=self.manager,
        )

        self.assertEqual(result.approved_count, 2)
        self.assertEqual(result.error_count, 0)

        t1.refresh_from_db()
        t2.refresh_from_db()
        self.user_a.refresh_from_db()
        self.user_b.refresh_from_db()

        self.assertEqual(t1.status, Transaction.Status.APPROVED)
        self.assertEqual(t2.status, Transaction.Status.APPROVED)
        self.assertEqual(self.user_a.bank_balances, Decimal("900.00"))  # 1000 + 100 - 200
        self.assertEqual(self.user_b.bank_balances, Decimal("700.00"))  # 500 + 200

    def test_approve_batch_with_errors(self):
        t_valid = Transaction.objects.create(
            account=self.user_a,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.PENDING,
        )
        t_invalid = Transaction.objects.create(
            account=self.user_a,
            type="W",
            amount=Decimal("50000.00"),
            status=Transaction.Status.PENDING,
        )

        result = approve_batch(
            Transaction.objects.filter(pk__in=[t_valid.pk, t_invalid.pk]),
            approved_by=self.manager,
        )

        self.assertEqual(result.approved_count, 1)
        self.assertEqual(result.error_count, 1)

        t_valid.refresh_from_db()
        t_invalid.refresh_from_db()
        self.assertEqual(t_valid.status, Transaction.Status.APPROVED)
        self.assertEqual(t_invalid.status, Transaction.Status.REJECTED)

    def test_approve_batch_unauthorized_permission_denied(self):
        t1 = Transaction.objects.create(
            account=self.user_a,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.PENDING,
        )

        with self.assertRaises(PermissionDenied):
            approve_batch(
                Transaction.objects.filter(pk=t1.pk),
                approved_by=self.unauthorized_user,
            )

    def test_reject_batch_success(self):
        t1 = Transaction.objects.create(
            account=self.user_a,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.PENDING,
        )
        t2 = Transaction.objects.create(
            account=self.user_b,
            type="W",
            amount=Decimal("50.00"),
            status=Transaction.Status.PENDING,
        )

        count = reject_batch(
            Transaction.objects.filter(pk__in=[t1.pk, t2.pk]),
            approved_by=self.manager,
        )

        self.assertEqual(count, 2)
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertEqual(t1.status, Transaction.Status.REJECTED)
        self.assertEqual(t1.approved_by, self.manager)
        self.assertIsNotNone(t1.approved_at)
        self.assertEqual(t2.status, Transaction.Status.REJECTED)

    def test_reject_batch_unauthorized_permission_denied(self):
        t1 = Transaction.objects.create(
            account=self.user_a,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.PENDING,
        )

        with self.assertRaises(PermissionDenied):
            reject_batch(
                Transaction.objects.filter(pk=t1.pk),
                approved_by=self.unauthorized_user,
            )

