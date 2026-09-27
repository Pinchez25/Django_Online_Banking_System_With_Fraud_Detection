from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count

from bank.models import TransactionLog


class TransactionFeatureBuilder:
    """Build exactly the behavioural features expected by the trained model.

    Features are calculated from transactions that happened before the transaction
    being scored. The current transaction is not present in TransactionLog yet.
    Account primary keys are used as behavioural identities; raw card numbers are
    deliberately not model inputs.
    """

    FEATURE_COLUMNS = (
        "transaction_amount",
        "transaction_hour",
        "transaction_day_of_week",
        "is_weekend",
        "sender_transaction_count",
        "receiver_transaction_count",
        "sender_average_amount",
        "receiver_average_amount",
        "sender_unique_receivers",
        "receiver_unique_senders",
        "amount_vs_sender_average",
        "amount_vs_receiver_average",
    )

    def build(self, *, sender, receiver, amount: Decimal, transaction_date):
        previous_logs = TransactionLog.objects.filter(date__lt=transaction_date)

        sender_stats = previous_logs.filter(sender_account=sender).aggregate(
            transaction_count=Count("id"),
            average_amount=Avg("amount"),
            unique_receivers=Count("receiver_account", distinct=True),
        )
        receiver_stats = previous_logs.filter(receiver_account=receiver).aggregate(
            transaction_count=Count("id"),
            average_amount=Avg("amount"),
            unique_senders=Count("sender_account", distinct=True),
        )

        sender_count = sender_stats["transaction_count"] or 0
        receiver_count = receiver_stats["transaction_count"] or 0
        sender_average = sender_stats["average_amount"] or Decimal("0")
        receiver_average = receiver_stats["average_amount"] or Decimal("0")
        amount = Decimal(amount)

        return {
            "transaction_amount": float(amount),
            "transaction_hour": transaction_date.hour,
            "transaction_day_of_week": transaction_date.weekday(),
            "is_weekend": int(transaction_date.weekday() >= 5),
            "sender_transaction_count": sender_count,
            "receiver_transaction_count": receiver_count,
            "sender_average_amount": float(sender_average),
            "receiver_average_amount": float(receiver_average),
            "sender_unique_receivers": sender_stats["unique_receivers"] or 0,
            "receiver_unique_senders": receiver_stats["unique_senders"] or 0,
            "amount_vs_sender_average": (
                float(amount / sender_average) if sender_average > 0 else 0.0
            ),
            "amount_vs_receiver_average": (
                float(amount / receiver_average) if receiver_average > 0 else 0.0
            ),
        }
