from decimal import Decimal
from unittest.mock import Mock

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase

from bank.admin import TransactionAdmin
from bank.models import Transaction

User = get_user_model()


class DummyMessageRequest(RequestFactory):
    pass


def add_session_and_messages(request):
    setattr(request, "session", {})
    messages = FallbackStorage(request)
    setattr(request, "_messages", messages)
    return request


class TransactionAdminTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.admin = TransactionAdmin(Transaction, self.site)
        self.factory = RequestFactory()

        self.staff_manager = User.objects.create_user(
            username="staff_manager",
            email="manager@example.com",
            password="password",
            national_id=12345001,
            is_staff=True,
        )
        self.staff_manager.user_permissions.add(
            Permission.objects.get(codename="approve_transaction"),
            Permission.objects.get(codename="change_transaction"),
        )

        self.staff_unauthorized = User.objects.create_user(
            username="staff_unauthorized",
            email="unauth@example.com",
            password="password",
            national_id=12345002,
            is_staff=True,
        )

        self.account_alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="password",
            national_id=12345003,
            bank_balances=Decimal("1000.00"),
        )
        self.account_bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="password",
            national_id=12345004,
            bank_balances=Decimal("500.00"),
        )

    def test_approve_selected_transactions_deposit(self):
        txn = Transaction.objects.create(
            account=self.account_alice,
            type="D",
            amount=Decimal("200.00"),
            status=Transaction.Status.PENDING,
        )

        request = self.factory.post("/admin/bank/transaction/")
        request.user = self.staff_manager
        add_session_and_messages(request)

        queryset = Transaction.objects.filter(pk=txn.pk)
        self.admin.approve_selected_transactions(request, queryset)

        txn.refresh_from_db()
        self.account_alice.refresh_from_db()

        self.assertEqual(txn.status, Transaction.Status.APPROVED)
        self.assertEqual(txn.approved_by, self.staff_manager)
        self.assertIsNotNone(txn.approved_at)
        self.assertEqual(self.account_alice.bank_balances, Decimal("1200.00"))

    def test_approve_selected_transactions_transfer(self):
        txn = Transaction.objects.create(
            account=self.account_alice,
            recipient=self.account_bob,
            type="T",
            amount=Decimal("300.00"),
            status=Transaction.Status.PENDING,
        )

        request = self.factory.post("/admin/bank/transaction/")
        request.user = self.staff_manager
        add_session_and_messages(request)

        queryset = Transaction.objects.filter(pk=txn.pk)
        self.admin.approve_selected_transactions(request, queryset)

        txn.refresh_from_db()
        self.account_alice.refresh_from_db()
        self.account_bob.refresh_from_db()

        self.assertEqual(txn.status, Transaction.Status.APPROVED)
        self.assertEqual(self.account_alice.bank_balances, Decimal("700.00"))
        self.assertEqual(self.account_bob.bank_balances, Decimal("800.00"))

    def test_approve_selected_transactions_insufficient_funds_fails_gracefully(self):
        txn = Transaction.objects.create(
            account=self.account_alice,
            type="W",
            amount=Decimal("5000.00"),
            status=Transaction.Status.PENDING,
        )

        request = self.factory.post("/admin/bank/transaction/")
        request.user = self.staff_manager
        add_session_and_messages(request)

        queryset = Transaction.objects.filter(pk=txn.pk)
        self.admin.approve_selected_transactions(request, queryset)

        txn.refresh_from_db()
        self.account_alice.refresh_from_db()

        self.assertEqual(txn.status, Transaction.Status.REJECTED)
        self.assertEqual(self.account_alice.bank_balances, Decimal("1000.00"))

    def test_unauthorized_user_cannot_approve_action(self):
        txn = Transaction.objects.create(
            account=self.account_alice,
            type="D",
            amount=Decimal("200.00"),
            status=Transaction.Status.PENDING,
        )

        # Remove permission / inactive
        self.staff_unauthorized.is_active = True
        self.staff_unauthorized.is_staff = False

        request = self.factory.post("/admin/bank/transaction/")
        request.user = self.staff_unauthorized
        add_session_and_messages(request)

        queryset = Transaction.objects.filter(pk=txn.pk)
        self.admin.approve_selected_transactions(request, queryset)

        txn.refresh_from_db()
        self.assertEqual(txn.status, Transaction.Status.PENDING)
        self.account_alice.refresh_from_db()
        self.assertEqual(self.account_alice.bank_balances, Decimal("1000.00"))

    def test_reject_selected_transactions(self):
        txn = Transaction.objects.create(
            account=self.account_alice,
            type="D",
            amount=Decimal("200.00"),
            status=Transaction.Status.PENDING,
        )

        request = self.factory.post("/admin/bank/transaction/")
        request.user = self.staff_manager
        add_session_and_messages(request)

        queryset = Transaction.objects.filter(pk=txn.pk)
        self.admin.reject_selected_transactions(request, queryset)

        txn.refresh_from_db()
        self.assertEqual(txn.status, Transaction.Status.REJECTED)
        self.assertEqual(txn.approved_by, self.staff_manager)
        self.assertIsNotNone(txn.approved_at)

    def test_save_model_approves_when_status_changed_to_approved(self):
        txn = Transaction.objects.create(
            account=self.account_alice,
            type="D",
            amount=Decimal("150.00"),
            status=Transaction.Status.PENDING,
        )

        request = self.factory.post(f"/admin/bank/transaction/{txn.pk}/change/")
        request.user = self.staff_manager
        add_session_and_messages(request)

        form = Mock()
        form.changed_data = ["status"]
        form.initial = {"status": Transaction.Status.PENDING}

        txn.status = Transaction.Status.APPROVED
        self.admin.save_model(request, txn, form, change=True)

        txn.refresh_from_db()
        self.account_alice.refresh_from_db()

        self.assertEqual(txn.status, Transaction.Status.APPROVED)
        self.assertEqual(txn.approved_by, self.staff_manager)
        self.assertEqual(self.account_alice.bank_balances, Decimal("1150.00"))

    def test_readonly_fields_for_processed_transactions(self):
        pending_txn = Transaction.objects.create(
            account=self.account_alice,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.PENDING,
        )
        approved_txn = Transaction.objects.create(
            account=self.account_alice,
            type="D",
            amount=Decimal("100.00"),
            status=Transaction.Status.APPROVED,
        )

        request = self.factory.get("/admin/bank/transaction/")
        request.user = self.staff_manager

        pending_readonly = self.admin.get_readonly_fields(request, pending_txn)
        approved_readonly = self.admin.get_readonly_fields(request, approved_txn)

        self.assertNotIn("amount", pending_readonly)
        self.assertIn("amount", approved_readonly)
        self.assertIn("status", approved_readonly)
