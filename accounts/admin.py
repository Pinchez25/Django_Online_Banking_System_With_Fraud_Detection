from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib import messages
from django.utils.translation import ngettext

from .forms import AccountRegistrationForm
from .models import Account, Profile


@admin.register(Account)
class AccountAdmin(UserAdmin):
    form = AccountRegistrationForm
    list_display = ['username', 'account_type', 'user_type', 'email',
                    'national_id', 'cc_number', 'bank_balances']
    list_filter = ['account_type', 'user_type']
    search_fields = ['username', 'email', 'national_id']
    list_per_page = 25
    actions = ["deactivate_selected_accounts"]

    @admin.action(description="Deactivate selected accounts")
    def deactivate_selected_accounts(self, request, queryset):
        count = 0
        for account in queryset.iterator():
            if account.is_active:
                account.deactivate()
                count += 1
        self.message_user(
            request,
            ngettext(
                "%d account was deactivated.",
                "%d accounts were deactivated.",
                count,
            ) % count,
            messages.SUCCESS,
        )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone_number', 'address', 'city']
    list_filter = ['account']
    # search_fields = ['first_name', 'last_name', 'phone_number', 'address', 'city']
    search_fields = ("account__username", "account__email", "first_name", "last_name")
    list_per_page = 25
