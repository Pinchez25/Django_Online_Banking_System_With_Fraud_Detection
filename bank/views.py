from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from accounts.models import Account
from .forms import DepositForm, WithdrawForm, SendMoneyForm
from .models import Transaction
from bank.utils.log_transactions import create_transaction_logs
from ml_model.detect_fraud import detect_fraud, print_fraud_score
from ml_model.report_fraudulent_transactions import report_fraudulent_transactions
from ml_model.block_account import block_account


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_user = get_user_model().objects.get(username=self.request.user)
        context['year'] = datetime.now().year
        context['user_profile_id'] = current_user.profile.id
        context['user_profile'] = current_user.profile
        context['user_transactions'] = current_user.transaction_set.all()
        return context


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'bank/transaction_report.html'
    model = Transaction


class CreateTransactionMixin(LoginRequiredMixin, CreateView):
    template_name = 'bank/create_transaction.html'
    model = Transaction
    success_url = '/'

    def get_form_kwargs(self):
        kwargs = super(CreateTransactionMixin, self).get_form_kwargs()
        kwargs['account'] = self.request.user
        return kwargs


class DepositMoneyView(CreateTransactionMixin):
    form_class = DepositForm

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        with transaction.atomic():
            account = get_user_model().objects.select_for_update().get(username=self.request.user)
            account.bank_balances += amount
            account.save()
            create_transaction_logs(
                sender=account, receiver=None, amount=amount, cc_number=account.cc_number,
                rec_cc_number=None,
                created=datetime.now(), is_fraud=0)
            messages.success(self.request, 'Ksh. {} was deposited to your account'.format(amount))

        return super(DepositMoneyView, self).form_valid(form)

    # if form is invalid show error message and rollback transaction
    def form_invalid(self, form):
        messages.error(self.request, 'Error depositing money')
        return super(DepositMoneyView, self).form_invalid(form)


class WithdrawMoneyView(CreateTransactionMixin):
    form_class = WithdrawForm

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        with transaction.atomic():
            account = get_user_model().objects.select_for_update().get(username=self.request.user)
            account.bank_balances -= amount
            account.save()
            create_transaction_logs(
                sender=account, receiver=None, amount=amount, cc_number=account.cc_number,
                rec_cc_number=None,
                created=datetime.now(), is_fraud=0)
            messages.success(self.request, 'Ksh. {} was withdrawn from your account'.format(amount))

        return super(WithdrawMoneyView, self).form_valid(form)

    # if form is invalid show error message and rollback transaction
    def form_invalid(self, form):
        messages.error(self.request, 'Error withdrawing money')
        return super(WithdrawMoneyView, self).form_invalid(form)


class SendMoneyView(CreateTransactionMixin):
    form_class = SendMoneyForm

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        username = form.cleaned_data.get('recipient')

        with transaction.atomic():
            recipient = Account.objects.select_for_update().get(username=username)
            payor = get_user_model().objects.select_for_update().get(username=self.request.user)
            sender_cc_number = payor.cc_number
            receiver_cc_number = recipient.cc_number

            is_fraud = detect_fraud(sender_cc_number, receiver_cc_number, amount)
            score = print_fraud_score(sender_cc_number, receiver_cc_number, amount)
            print('Score: ', score)
            print(f"Is fraud: {is_fraud}")
            if is_fraud:
                messages.error(self.request, 'Error sending money')
                block_account(self.request)
                report_fraudulent_transactions(recipient.email)
                create_transaction_logs(
                    sender=payor, receiver=recipient, amount=amount, cc_number=sender_cc_number,
                    rec_cc_number=receiver_cc_number,
                    created=datetime.now(), is_fraud=1)
            else:
                payor.bank_balances -= amount
                payor.save()
                recipient.bank_balances += amount
                recipient.save()
                create_transaction_logs(
                    sender=payor, receiver=recipient, amount=amount, cc_number=sender_cc_number,
                    rec_cc_number=receiver_cc_number,
                    created=datetime.now(), is_fraud=0)
                messages.success(self.request, 'Ksh. {} was sent to {}'.format(amount, username))

        return super(SendMoneyView, self).form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error sending money')
        return super(SendMoneyView, self).form_invalid(form)
