import random
import string

from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import Customer

TRANSACTION_TYPES = (
    ('D', 'Deposit'),
    ('W', 'Withdrawal'),
    ('T', 'Transfer'),
)


# function to generate unique transaction id
def generate_unique_id():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))


class Transaction(models.Model):
    transaction_id = models.CharField(max_length=16, default=generate_unique_id, unique=True)
    type = models.CharField(_('Type of Transaction'), max_length=1, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(_('Amount'), max_digits=12, decimal_places=2)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    date = models.DateField(auto_now=True)

    def __str__(self):
        return self.transaction_id
