import secrets
import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Account

TRANSACTION_TYPES = (
    ("D", "Deposit"),
    ("W", "Withdrawal"),
    ("T", "Transfer"),
)

# Crockford-style Base32 alphabet: excludes ambiguous characters such as 0/O and 1/I.
TRANSACTION_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TRANSACTION_REFERENCE_LENGTH = 10


def generate_transaction_id():
    """Generate a short, opaque, cryptographically random transaction reference.

    Ten Base32 characters provide 50 bits of randomness while remaining short enough
    for a customer-facing transaction code. The database UNIQUE constraint is the
    final authority on uniqueness; generation is intentionally independent of
    transaction volume and does not expose an account's transaction count.
    """
    return "".join(
        secrets.choice(TRANSACTION_REFERENCE_ALPHABET)
        for _ in range(TRANSACTION_REFERENCE_LENGTH)
    )


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending approval")
        APPROVED = "approved", _("Approved")
        REJECTED = "rejected", _("Rejected")
        FAILED = "failed", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(
        _("Transaction ID"),
        max_length=TRANSACTION_REFERENCE_LENGTH,
        default=generate_transaction_id,
        unique=True,
        editable=False,
        db_index=True,
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name=_("Account"),
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transactions",
        verbose_name=_("Recipient"),
    )
    type = models.CharField(_("Type of Transaction"), max_length=1, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    status = models.CharField(
        _("Status"),
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transactions",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    class Meta:
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["account", "-date"], name="txn_account_date_idx"),
        ]
        permissions = [("approve_transaction", "Can approve bank transactions")]

    def __str__(self):
        return self.transaction_id

    def approve(self, approved_by=None):
        if self.status != self.Status.PENDING:
            raise ValueError("Only pending transactions can be approved.")

        if approved_by is not None and not approved_by.has_perm("bank.approve_transaction"):
            raise PermissionDenied("This user is not allowed to approve transactions.")

        account = self.account

        if self.type == "D":
            account.bank_balances += self.amount
            account.save(update_fields=["bank_balances"])
        elif self.type == "W":
            if self.amount > account.bank_balances:
                self.status = self.Status.REJECTED
                self.save(update_fields=["status"])
                raise ValueError("The account does not have enough funds to complete this withdrawal.")
            account.bank_balances -= self.amount
            account.save(update_fields=["bank_balances"])
        elif self.type == "T":
            if self.recipient is None:
                raise ValueError("Transfer recipient is missing.")
            if account.bank_balances < self.amount:
                self.status = self.Status.REJECTED
                self.save(update_fields=["status"])
                raise ValueError("The account does not have enough funds to complete this transfer.")
            account.bank_balances -= self.amount
            recipient = self.recipient
            recipient.bank_balances += self.amount
            account.save(update_fields=["bank_balances"])
            recipient.save(update_fields=["bank_balances"])
        else:
            raise ValueError(f"Unsupported transaction type: {self.type}")

        self.status = self.Status.APPROVED
        self.approved_by = approved_by
        self.approved_at = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_at"])
        return self


class TransactionLog(models.Model):
    """Audit record for a money movement or a blocked transfer attempt."""

    sender_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_transaction_logs",
    )
    receiver_account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_transaction_logs",
    )
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))
    is_fraud = models.BooleanField(_("Fraud"), default=False)
    fraud_probability = models.FloatField(null=True, blank=True)
    fraud_model_version = models.CharField(max_length=50, null=True, blank=True)
    fraud_threshold = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = _("Transaction Log")
        verbose_name_plural = _("Transaction Logs")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["sender_account", "-date"], name="txlog_sender_date_idx"),
            models.Index(fields=["receiver_account", "-date"], name="txlog_receiver_date_idx"),
            models.Index(fields=["is_fraud", "-date"], name="txlog_fraud_date_idx"),
        ]

    def __str__(self):
        return str(self.pk)


class Notification(models.Model):
    class Kind(models.TextChoices):
        ALERT = "alert", _("Alert")
        MESSAGE = "message", _("Message")

    class Level(models.TextChoices):
        INFO = "info", _("Information")
        SUCCESS = "success", _("Success")
        WARNING = "warning", _("Warning")
        DANGER = "danger", _("Urgent")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=10, choices=Kind.choices)
    level = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    sender_name = models.CharField(max_length=100, blank=True, default="Kwetu Bank")
    title = models.CharField(max_length=120)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "kind", "read_at", "-created_at"],
                name="notif_user_kind_read_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title}"
