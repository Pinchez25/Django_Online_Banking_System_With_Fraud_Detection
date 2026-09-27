from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction

from bank.models import Transaction
from bank.services.notifications import create_alert

logger = logging.getLogger(__name__)


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
            movement = Transaction.objects.create(
                account=account,
                type="D",
                amount=amount,
                status=Transaction.Status.PENDING,
            )
            logger.info("Deposit request created for account_id=%s transaction_id=%s", account.pk, movement.transaction_id)
            create_alert(
                recipient=account,
                title="Deposit submitted for approval",
                body=f"KES {amount:,.2f} has been submitted for approval before being credited to your account.",
                level="warning",
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
                logger.warning("Withdrawal rejected for account_id=%s: insufficient funds", account.pk)
                raise InsufficientFundsError("Insufficient funds.")

            movement = Transaction.objects.create(
                account=account,
                type="W",
                amount=amount,
                status=Transaction.Status.PENDING,
            )
            logger.info("Withdrawal request created for account_id=%s transaction_id=%s", account.pk, movement.transaction_id)
            create_alert(
                recipient=account,
                title="Withdrawal submitted for approval",
                body=f"KES {amount:,.2f} has been submitted for approval before leaving your account.",
                level="warning",
            )

        return MoneyOperationResult(transaction=movement)
