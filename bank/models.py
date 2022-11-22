import random
import string

from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import Account
from django.conf import settings

TRANSACTION_TYPES = (
    ('D', 'Deposit'),
    ('W', 'Withdrawal'),
    ('T', 'Transfer'),
)


# function to generate unique transaction id
def generate_unique_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))


class Transaction(models.Model):
    transaction_id = models.CharField(max_length=16, default=generate_unique_id, unique=True,
                                      verbose_name=_("Transaction ID"))
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("Account"))
    type = models.CharField(_('Type of Transaction'), max_length=1, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=12, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date"))

    def __str__(self):
        return str(self.transaction_id)
