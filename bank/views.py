from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from accounts.models import Account
from .forms import DepositForm, WithdrawForm, SendMoneyForm
from .models import Transaction


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['year'] = datetime.now().year
        context['user_profile_id'] = self.request.user.profile.id
        context['user_profile'] = self.request.user.profile
        context['user_transactions'] = self.request.user.transaction_set.all()
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
        account = self.request.user
        with transaction.atomic():
            account.bank_balances += amount
            account.save()
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
        account = self.request.user
        with transaction.atomic():
            account.bank_balances -= amount
            account.save()
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
            account = self.request.user
            account.bank_balances -= amount
            account.save()

            recipient = Account.objects.get(username=username)
            if not account == recipient:
                recipient.bank_balances += amount
                recipient.save()
                messages.success(self.request, f"Money sent successfully to {str(username).title()}")
            else:
                # TODO: For now re-adding the sent money is a Hacky fix - implement select_update() with atomic
                #  transaction later
                account.bank_balances += amount
                account.save()
                messages.warning(self.request, "You can`t send money to yourself")

        return super(SendMoneyView, self).form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error sending money')
        return super(SendMoneyView, self).form_invalid(form)

# class TransactionHistoryView(LoginRequiredMixin, ListView):
#     model = Transaction
#     template_name = 'bank/transaction-history.html'
#
#     def get_context_data(self, **kwargs):
#         context = super(TransactionHistoryView, self).get_context_data(**kwargs)
#         context['user_transactions'] = self.request.user.transaction_set.all()
#         return context
