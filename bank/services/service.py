from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from accounts.models import Account
from bank.models import Transaction
from bank.services.utils import TRANSACTION_TYPES

logger = logging.getLogger(__name__)

_TRANSACTION_TYPE_CODES = {transaction_type[0] for transaction_type in TRANSACTION_TYPES}


@dataclass(frozen=True, slots=True)
class BatchApprovalResult:
    approved_count: int
    error_count: int


def _validate_transaction_amount(amount):
    """Validate the transaction amount before modifying any database state."""
    if amount is None:
        raise ValueError("Transaction amount is required.")

    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    if not amount.is_finite():
        raise ValueError("Transaction amount must be finite.")

    if amount <= Decimal("0"):
        raise ValueError("Transaction amount must be greater than zero.")


def _lock_account(account_id):
    """Lock and return an account row."""
    try:
        return (
            Account.objects
            .select_for_update()
            .get(pk=account_id)
        )
    except Account.DoesNotExist:
        raise ValueError(
            "The account associated with this transaction no longer exists."
        )


def _lock_transfer_accounts(sender_id, recipient_id):
    """Lock transfer accounts in deterministic primary-key order."""
    if sender_id == recipient_id:
        raise ValueError("An account cannot transfer funds to itself.")

    locked_accounts = {}

    for account_id in sorted((sender_id, recipient_id)):
        try:
            locked_accounts[account_id] = (
                Account.objects
                .select_for_update()
                .get(pk=account_id)
            )
        except Account.DoesNotExist:
            raise ValueError(
                "The transfer account no longer exists."
            )

    return (
        locked_accounts[sender_id],
        locked_accounts[recipient_id],
    )


def _reject_transaction(transaction_instance, message):
    """Persist a transaction as REJECTED and return the error to raise once committed."""
    transaction_instance.status = Transaction.Status.REJECTED
    transaction_instance.save(update_fields=["status"])
    return ValueError(message)


def _assert_not_self_approval(transaction_instance, approved_by):
    """Prevent an account holder from approving their own transaction."""
    if approved_by is None:
        return

    restricted_account_ids = {transaction_instance.account_id}
    if transaction_instance.recipient_id is not None:
        restricted_account_ids.add(transaction_instance.recipient_id)

    if approved_by.id in restricted_account_ids:
        raise PermissionDenied(
            "Users are not allowed to approve their own transactions."
        )


def approve_transaction(transaction_instance, approved_by=None):
    """Approve a pending transaction and apply its balance changes.

    The transaction row is locked first to prevent concurrent approval of the
    same transaction.

    For transfers, sender and recipient accounts are locked individually in
    deterministic primary-key order to prevent deadlocks when simultaneous
    transfers occur in opposite directions.

    Insufficient-funds transactions are persisted as REJECTED before the
    corresponding ValueError is raised.
    """
    rejection_error = None

    with transaction.atomic():
        try:
            transaction_instance = (
                Transaction.objects
                .select_for_update()
                .get(pk=transaction_instance.pk)
            )
        except Transaction.DoesNotExist:
            raise ValueError("The transaction no longer exists.")

        if transaction_instance.status != Transaction.Status.PENDING:
            raise ValueError("Only pending transactions can be approved.")

        if approved_by is not None and not approved_by.can_approve_transactions():
            raise PermissionDenied(
                "This user is not allowed to approve transactions."
            )

        _assert_not_self_approval(transaction_instance, approved_by)

        if transaction_instance.type not in _TRANSACTION_TYPE_CODES:
            raise ValueError(
                f"Unsupported transaction type: {transaction_instance.type}"
            )

        _validate_transaction_amount(transaction_instance.amount)

        if transaction_instance.type == "T":
            if transaction_instance.recipient_id is None:
                raise ValueError("Transfer recipient is missing.")

            account, recipient = _lock_transfer_accounts(
                transaction_instance.account_id,
                transaction_instance.recipient_id,
            )

            if account.bank_balances < transaction_instance.amount:
                rejection_error = _reject_transaction(
                    transaction_instance,
                    "The account does not have enough funds to complete this transfer.",
                )
            else:
                account.bank_balances -= transaction_instance.amount
                recipient.bank_balances += transaction_instance.amount

                account.save(update_fields=["bank_balances"])
                recipient.save(update_fields=["bank_balances"])

        else:
            account = _lock_account(transaction_instance.account_id)

            if (
                    transaction_instance.type == "W"
                    and account.bank_balances < transaction_instance.amount
            ):
                rejection_error = _reject_transaction(
                    transaction_instance,
                    "The account does not have enough funds to complete this withdrawal.",
                )

            elif transaction_instance.type == "D":
                account.bank_balances += transaction_instance.amount
                account.save(update_fields=["bank_balances"])

            elif transaction_instance.type == "W":
                account.bank_balances -= transaction_instance.amount
                account.save(update_fields=["bank_balances"])

        if rejection_error is None:
            transaction_instance.status = Transaction.Status.APPROVED
            transaction_instance.approved_by = approved_by
            transaction_instance.approved_at = timezone.now()
            transaction_instance.save(
                update_fields=[
                    "status",
                    "approved_by",
                    "approved_at",
                ]
            )

    if rejection_error is not None:
        raise rejection_error

    return transaction_instance


def approve_batch(queryset, approved_by=None) -> BatchApprovalResult:
    """Approve a batch of pending transactions.

    Transactions are filtered to only pending ones, with accounts and recipients
    prefetched to minimize database queries.
    """
    if approved_by is not None and not approved_by.can_approve_transactions():
        raise PermissionDenied("This user is not allowed to approve transactions.")

    pending_txns = queryset.filter(status=Transaction.Status.PENDING).select_related(
        "account", "recipient"
    )
    approved_count = 0
    error_count = 0

    for txn in pending_txns:
        try:
            approve_transaction(txn, approved_by=approved_by)
            approved_count += 1
        except (ValueError, PermissionDenied) as exc:
            logger.warning("Failed to approve transaction %s: %s", txn.pk, exc)
            error_count += 1

    return BatchApprovalResult(approved_count=approved_count, error_count=error_count)


def reject_batch(queryset, approved_by=None) -> int:
    """Reject a batch of pending transactions."""
    if approved_by is not None and not approved_by.can_approve_transactions():
        raise PermissionDenied("This user is not allowed to reject transactions.")

    pending_txns = queryset.filter(status=Transaction.Status.PENDING)
    return pending_txns.update(
        status=Transaction.Status.REJECTED,
        approved_by=approved_by,
        approved_at=timezone.now(),
    )
