from django.contrib import admin
from .models import Notification, Transaction, TransactionLog


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "kind", "level", "created_at", "read_at")
    list_filter = ("kind", "level", "created_at")
    search_fields = ("title", "body", "recipient__username", "recipient__email")
    readonly_fields = ("created_at", "read_at")
    list_select_related = ("recipient",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_id", "account", "type", "amount", "date")
    list_filter = ("type",)
    search_fields = ("transaction_id", "account__username", "account__email")
    readonly_fields = ("transaction_id", "date")


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sender_account",
        "receiver_account",
        "amount",
        "is_fraud",
        "fraud_probability",
        "fraud_model_version",
        "date",
    )
    list_filter = ("is_fraud", "fraud_model_version")
    search_fields = (
        "sender_account__username",
        "receiver_account__username",
        "sender_account__email",
        "receiver_account__email",
    )
    readonly_fields = ("date",)
