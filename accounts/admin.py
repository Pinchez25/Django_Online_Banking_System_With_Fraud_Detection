from django.contrib import admin
from .models import Account, Profile, Customer
from .forms import AccountCreationForm


@admin.register(Account)
class UserAdmin(admin.ModelAdmin):
    form = AccountCreationForm
    list_display = ['username', 'account_type', 'user_type', 'email',
                    'national_id', 'account_number']
    list_filter = ['account_type', 'user_type']
    search_fields = ['username', 'email', 'national_id']
    list_per_page = 25


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone_number', 'address', 'city']
    list_filter = ['account']
    search_fields = ['first_name', 'last_name', 'phone_number', 'address', 'city']
    list_per_page = 25


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_per_page = 25
