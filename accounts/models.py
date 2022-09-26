from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser
from creditcards.models import CardNumberField
from django.utils.translation import gettext_lazy as _
# import password validator
from django.contrib.auth.password_validation import validate_password
from django.core.validators import MaxValueValidator

USER_TYPES = (
    ('individual', 'Individual'),
    ('business', 'Business'),
    ('joint', 'Joint'),
    ('power of attorney', 'Power of Attorney'),
)
ACCOUNT_TYPES = (
    ('checking', 'Checking'),
    ('savings', 'Savings'),
    ('certificate of deposit', 'Certificate of Deposit'),
    ('money market', 'Money Market'),
)

# class AccountType(models.Model):
#     type = models.CharField(_("Type of Account"), max_length=50, choices=ACCOUNT_TYPES)
#
#     def __str__(self):
#         return self.type


"""
    Account model for a bank account created by a bank official
"""


class Account(AbstractUser):
    account_type = models.CharField(_("Type of Account"), max_length=50, choices=ACCOUNT_TYPES)
    account_number = models.CharField(_("Account Number"), max_length=50, null=True, blank=True)
    user_type = models.CharField(_("User Type"), max_length=50, choices=USER_TYPES, null=True, blank=True)
    email = models.EmailField(_("Email"), unique=True)
    national_id = models.IntegerField(_('National ID'), unique=True, default=0,
                                      validators=[MaxValueValidator(99999999, message="Invalid National ID")])
    bank_balances = models.DecimalField(_('Balance'), max_digits=12, decimal_places=2, default=0.00)

    # account number and national_id should be unique together
    class Meta:
        unique_together = ('account_number', 'national_id')
        db_table = 'auth_user'
        # app_label = 'auth'


"""
    Profile of the account holder
"""


class Profile(models.Model):
    account = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile')
    first_name = models.CharField(_("First Name"), max_length=50)
    last_name = models.CharField(_("Last Name"), max_length=50)
    profile_image = models.ImageField(_('Image'), null=True, blank=True, upload_to='profile_images',
                                      default='default.png')
    phone_number = models.CharField(_("Phone Number"), max_length=50, null=True, blank=True)
    address = models.CharField(_("Address"), max_length=50, null=True, blank=True)
    city = models.CharField(_("City"), max_length=50, null=True, blank=True)
    zip_code = models.CharField(_("Zip Code"), max_length=50, null=True, blank=True)
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    updated = models.DateTimeField(_("Updated"), auto_now=True)

    def __str__(self):
        return self.account.username

    def get_profile_image(self):
        if self.profile_image:
            return self.profile_image.url

    class Meta:
        db_table = 'profile'
        ordering = ['-created']


# class CustomerTypes(models.Model):
#     type = models.CharField(_('Type of Customer'), max_length=50, choices=USER_TYPES, default='individual')
#
#     def __str__(self):
#         return self.type
#     class Meta:
#         db_table = 'customer_types'
#         ordering = ['type']


"""
    Customer model for a bank account created by a customer
    registering for an online banking account account. At the end of registration,
    assign a credit card number which will be used for all transactions.
    
"""


class Customer(models.Model):
    account_number = models.CharField(_("Account Number"), max_length=50)
    password = models.CharField(_("Password"), max_length=50, validators=[validate_password])
    cc_number = CardNumberField(_('Credit Card'), help_text=_('Customer credit card number'), null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.cc_number)

    class Meta:
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')
        db_table = 'customer'
        ordering = ['-created']


