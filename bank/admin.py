from django.contrib import admin
from .models import Transaction, TransactionLogs


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    pass


@admin.register(TransactionLogs)
class TransactionLogsAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'amount', 'cc_number', 'rec_cc_number', 'date', 'is_fraud')
    # all fields are read-only
    readonly_fields = ('sender', 'receiver', 'amount', 'cc_number', 'rec_cc_number', 'date', 'is_fraud')
