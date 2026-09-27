from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .fraud import FraudService
from ..ml.detector import FraudModelUnavailable
from ..models import Transaction, TransactionLog


class TransferError(Exception):
    pass


class SelfTransferError(TransferError):
    pass


class InsufficientFundsError(TransferError):
    pass


class AccountBlockedError(TransferError):
    pass


class FraudModelError(TransferError):
    pass


@dataclass(frozen=True, slots=True)
class TransferResult:
    transaction: Transaction | None
    fraud_detected: bool
    fraud_probability: float | None = None


class TransferService:
    def __init__(self, fraud_service: FraudService | None = None):
        self.fraud_service = fraud_service or FraudService()

    def execute(self, *, sender, receiver, amount: Decimal) -> TransferResult:
        amount = Decimal(amount)
        if amount <= 0:
            raise TransferError("Transfer amount must be greater than zero.")
        if sender.pk == receiver.pk:
            raise SelfTransferError("You cannot transfer money to your own account.")

        result: TransferResult

        # Always acquire account locks in primary-key order. This prevents two
        # concurrent transfers in opposite directions from taking locks in
        # different orders and unnecessarily deadlocking.
        with transaction.atomic():
            locked_accounts = (
                type(sender).objects.select_for_update()
                .filter(pk__in=[sender.pk, receiver.pk])
                .order_by("pk")
            )
            accounts = {account.pk: account for account in locked_accounts}
            payor = accounts[sender.pk]
            beneficiary = accounts[receiver.pk]

            if payor.is_blocked:
                raise AccountBlockedError("The sending account is blocked.")
            if amount > payor.bank_balances:
                raise InsufficientFundsError("Insufficient funds.")

            try:
                assessment = self.fraud_service.assess_transfer(
                    sender=payor,
                    receiver=beneficiary,
                    amount=amount,
                )
            except FraudModelUnavailable as error:
                # Do not allow a model/inference failure to move money.
                raise FraudModelError("Fraud screening is unavailable; transfer was not processed.") from error

            fraud = assessment.result
            TransactionLog.objects.create(
                sender_account=payor,
                receiver_account=beneficiary,
                amount=amount,
                is_fraud=fraud.is_fraud,
                fraud_probability=fraud.probability,
                fraud_model_version=fraud.model_version,
                fraud_threshold=fraud.threshold,
            )

            if fraud.is_fraud:
                payor.is_blocked = True
                payor.save(update_fields=["is_blocked"])
                self._schedule_fraud_alert(payor.email, fraud.probability)
                result = TransferResult(
                    transaction=None,
                    fraud_detected=True,
                    fraud_probability=fraud.probability,
                )
            else:
                payor.bank_balances -= amount
                beneficiary.bank_balances += amount
                payor.save(update_fields=["bank_balances"])
                beneficiary.save(update_fields=["bank_balances"])

                transfer = Transaction.objects.create(
                    account=payor,
                    type="T",
                    amount=amount,
                )
                result = TransferResult(
                    transaction=transfer,
                    fraud_detected=False,
                    fraud_probability=fraud.probability,
                )

        return result

    @staticmethod
    def _schedule_fraud_alert(email: str, probability: float) -> None:
        recipient = getattr(settings, "FRAUD_ALERT_EMAIL", "")
        if not recipient:
            return

        transaction.on_commit(
            lambda: send_mail(
                subject="Fraudulent transaction blocked",
                message=(
                    f"A transfer for {email} was blocked by the fraud detector. "
                    f"Fraud probability: {probability:.4f}."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=True,
            )
        )
