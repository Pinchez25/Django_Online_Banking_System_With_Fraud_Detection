from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    # list_display = ('transaction_id', 'type', 'amount', 'date')
    # list_filter = ('type', 'customer')
    # search_fields = ('transaction_id', 'type', 'customer__first_name', 'customer__last_name')
    # ordering = ('-date',)
    pass
