from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from bank.models import Transaction
from bank.services.notifications import create_alert


class MoneyOperationError(Exception):
    pass


class InsufficientFundsError(MoneyOperationError):
    pass


@dataclass(frozen=True, slots=True)
class MoneyOperationResult:
    transaction: Transaction


class DepositService:
    @staticmethod
    def execute(*, account, amount: Decimal) -> MoneyOperationResult:
        amount = Decimal(amount)
        if amount <= 0:
            raise MoneyOperationError("Deposit amount must be greater than zero.")

        with transaction.atomic():
            account = get_user_model().objects.select_for_update().get(pk=account.pk)
            account.bank_balances += amount
            account.save(update_fields=["bank_balances"])
            movement = Transaction.objects.create(account=account, type="D", amount=amount)
            create_alert(
                recipient=account,
                title="Deposit received",
                body=f"KES {amount:,.2f} was deposited to your account.",
                level="success",
            )

        return MoneyOperationResult(transaction=movement)


class WithdrawalService:
    @staticmethod
    def execute(*, account, amount: Decimal) -> MoneyOperationResult:
        amount = Decimal(amount)
        if amount <= 0:
            raise MoneyOperationError("Withdrawal amount must be greater than zero.")

        with transaction.atomic():
            account = get_user_model().objects.select_for_update().get(pk=account.pk)
            if amount > account.bank_balances:
                raise InsufficientFundsError("Insufficient funds.")
            account.bank_balances -= amount
            account.save(update_fields=["bank_balances"])
            movement = Transaction.objects.create(account=account, type="W", amount=amount)
            create_alert(
                recipient=account,
                title="Withdrawal completed",
                body=f"KES {amount:,.2f} was withdrawn from your account.",
                level="warning",
            )

        return MoneyOperationResult(transaction=movement)
