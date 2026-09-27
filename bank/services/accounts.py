from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from bank.models import Transaction


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
            account = type(account).objects.select_for_update().get(pk=account.pk)
            account.bank_balances += amount
            account.save(update_fields=["bank_balances"])
            movement = Transaction.objects.create(account=account, type="D", amount=amount)

        return MoneyOperationResult(transaction=movement)


class WithdrawalService:
    @staticmethod
    def execute(*, account, amount: Decimal) -> MoneyOperationResult:
        amount = Decimal(amount)
        if amount <= 0:
            raise MoneyOperationError("Withdrawal amount must be greater than zero.")

        with transaction.atomic():
            account = type(account).objects.select_for_update().get(pk=account.pk)
            if amount > account.bank_balances:
                raise InsufficientFundsError("Insufficient funds.")
            account.bank_balances -= amount
            account.save(update_fields=["bank_balances"])
            movement = Transaction.objects.create(account=account, type="W", amount=amount)

        return MoneyOperationResult(transaction=movement)
