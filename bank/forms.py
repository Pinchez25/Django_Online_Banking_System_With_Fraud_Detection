from django.forms import ModelForm, HiddenInput, ValidationError, CharField
from django.conf import settings
from accounts.models import Account
from .models import Transaction


class TransactionForm(ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'amount']

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account')
        super(TransactionForm, self).__init__(*args, **kwargs)
        self.fields['type'].disabled = True
        self.fields['type'].widget = HiddenInput()
        self.fields['amount'].widget.attrs.update({'placeholder': 'Enter the amount to transact ...'})

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance = self.account.bank_balances
        return super(TransactionForm, self).save()


class DepositForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')

        if amount < settings.MINIMUM_DEPOSIT_AMOUNT:
            raise ValidationError(f"You need to deposit at least Ksh.{settings.MINIMUM_DEPOSIT_AMOUNT}")

        return amount

    def get_initial_for_field(self, field, field_name):
        if field_name == 'type':
            return 'D'
        return super(DepositForm, self).get_initial_for_field(field, field_name)


class WithdrawForm(TransactionForm):
    def clean_amount(self):
        account = self.account

        balance = account.bank_balances
        amount = self.cleaned_data.get('amount')

        if amount > balance:
            raise ValidationError(
                f'You have Ksh. {balance} in your account.'
                'You can\'t withdraw more than your account balance'
            )
        if amount > settings.MAXIMUM_WITHDRAW_AMOUNT:
            raise ValidationError(f"Withdraw limit is Ksh.{settings.MAXIMUM_WITHDRAW_AMOUNT}")

        if amount < settings.MINIMUM_WITHDRAW_AMOUNT:
            raise ValidationError(f"You need to withdraw at least Ksh.{settings.MINIMUM_WITHDRAW_AMOUNT}")

        return amount

    def get_initial_for_field(self, field, field_name):
        if field_name == 'type':
            return 'W'
        return super(WithdrawForm, self).get_initial_for_field(field, field_name)


class SendMoneyForm(TransactionForm):
    recipient = CharField(max_length=50, required=True)

    def __init__(self, *args, **kwargs):
        super(SendMoneyForm, self).__init__(*args, **kwargs)
        self.fields['recipient'].widget.attrs.update({'placeholder': 'Enter the credit card number of recipient ...'})

    def get_initial_for_field(self, field, field_name):
        if field_name == 'type':
            return 'T'
        return super(SendMoneyForm, self).get_initial_for_field(field, field_name)

    def clean_recipient(self):
        try:
            recipient = Account.objects.get(cc_number=self.cleaned_data.get('recipient'))
        except Account.DoesNotExist:
            raise ValidationError(f"User with this credit card number doesn't exist")

        return recipient

    def clean_amount(self):
        balance = self.account.bank_balances
        amount = self.cleaned_data.get('amount')

        if amount < settings.MINIMUM_TRANSACTION_AMOUNT:
            raise ValidationError(""
                                  f"The minimum transaction amount is Ksh.{settings.MINIMUM_TRANSACTION_AMOUNT}")

        if amount > settings.MAXIMUM_TRANSACTION_AMOUNT:
            raise ValidationError(""
                                  f"The maximum transaction amount is Ksh.{settings.MAXIMUM_TRANSACTION_AMOUNT}")

        if amount > balance:
            raise ValidationError(''
                                  'You don`t have enough cash in your account to complete this transaction.\n'
                                  f'Your balance is Ksh.{balance}')
        return amount
