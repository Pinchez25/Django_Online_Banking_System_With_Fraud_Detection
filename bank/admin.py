from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _, ngettext

from .models import Notification, Transaction, TransactionLog
from .services.service import (
    approve_batch,
    approve_transaction,
    reject_batch,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "recipient", "kind", "level", "created_at", "read_at")
    list_filter = ("kind", "level", "created_at")
    search_fields = ("title", "body", "recipient__username", "recipient__email")
    readonly_fields = ("created_at", "read_at")
    list_select_related = ("recipient",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_id",
        "account",
        "recipient",
        "type",
        "amount",
        "status",
        "approved_by",
        "approved_at",
        "date",
    )
    list_filter = ("status", "type", "date")
    search_fields = (
        "transaction_id",
        "account__username",
        "account__email",
        "recipient__username",
        "recipient__email",
    )
    readonly_fields = ("transaction_id", "date", "approved_at", "approved_by")
    list_select_related = ("account", "recipient", "approved_by")
    actions = ["approve_selected_transactions", "reject_selected_transactions"]

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status != Transaction.Status.PENDING:
            return readonly + ["account", "recipient", "type", "amount", "status"]
        return readonly

    @admin.action(description=_("Approve selected transactions"))
    def approve_selected_transactions(self, request, queryset):
        if not request.user.can_approve_transactions():
            self.message_user(
                request,
                _("You do not have permission to approve transactions."),
                messages.ERROR,
            )
            return

        result = approve_batch(
            queryset=queryset, approved_by=request.user
        )

        if result.approved_count > 0:
            self.message_user(
                request,
                ngettext(
                    "%d transaction was successfully approved.",
                    "%d transactions were successfully approved.",
                    result.approved_count,
                )
                % result.approved_count,
                messages.SUCCESS,
            )
        if result.error_count > 0:
            self.message_user(
                request,
                ngettext(
                    "%d transaction could not be approved due to validation errors.",
                    "%d transactions could not be approved due to validation errors.",
                    result.error_count,
                )
                % result.error_count,
                messages.WARNING,
            )
        if result.approved_count == 0 and result.error_count == 0:
            self.message_user(
                request,
                _("No pending transactions were selected for approval."),
                messages.INFO,
            )

    @admin.action(description=_("Reject selected transactions"))
    def reject_selected_transactions(self, request, queryset):
        if not request.user.can_approve_transactions():
            self.message_user(
                request,
                _("You do not have permission to reject transactions."),
                messages.ERROR,
            )
            return

        updated_count = reject_batch(
            queryset=queryset, approved_by=request.user
        )

        if updated_count > 0:
            self.message_user(
                request,
                ngettext(
                    "%d transaction was rejected.",
                    "%d transactions were rejected.",
                    updated_count,
                )
                % updated_count,
                messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                _("No pending transactions were selected for rejection."),
                messages.INFO,
            )

    def save_model(self, request, obj, form, change):
        if change and "status" in form.changed_data and obj.status == Transaction.Status.APPROVED:
            original_status = form.initial.get("status")
            if original_status == Transaction.Status.PENDING:
                obj.status = Transaction.Status.PENDING
                try:
                    approve_transaction(
                        obj, approved_by=request.user
                    )
                    return
                except ValueError as e:
                    self.message_user(request, str(e), level=messages.ERROR)
                    return
        super().save_model(request, obj, form, change)


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
    list_select_related = ("sender_account", "receiver_account")
