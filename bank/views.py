import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from .forms import DepositForm, SendMoneyForm, WithdrawForm
from .models import Transaction
from .services.accounts import DepositService, InsufficientFundsError, MoneyOperationError, WithdrawalService
from .services.transfers import AccountBlockedError, FraudModelError, SelfTransferError, TransferService

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context.update(
            year=timezone.now().year,
            user_profile_id=user.profile.id,
            user_profile=user.profile,
            user_transactions=user.transactions.all(),
        )
        return context


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = "bank/transaction_report.html"
    model = Transaction

    def get_queryset(self):
        return super().get_queryset().filter(account=self.request.user)


class CreateTransactionMixin(LoginRequiredMixin, CreateView):
    template_name = "bank/create_transaction.html"
    model = Transaction
    success_url = reverse_lazy("home")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["account"] = self.request.user
        return kwargs


class DepositMoneyView(CreateTransactionMixin):
    form_class = DepositForm

    def form_valid(self, form):
        try:
            DepositService.execute(account=self.request.user, amount=form.cleaned_data["amount"])
        except MoneyOperationError as error:
            form.add_error("amount", str(error))
            messages.error(self.request, "Error depositing money")
            return self.form_invalid(form)

        messages.success(self.request, f"Ksh. {form.cleaned_data['amount']} was deposited to your account")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Error depositing money")
        return super().form_invalid(form)


class WithdrawMoneyView(CreateTransactionMixin):
    form_class = WithdrawForm

    def form_valid(self, form):
        try:
            WithdrawalService.execute(account=self.request.user, amount=form.cleaned_data["amount"])
        except InsufficientFundsError as error:
            form.add_error("amount", str(error))
            messages.error(self.request, "Error withdrawing money")
            return self.form_invalid(form)
        except MoneyOperationError as error:
            form.add_error("amount", str(error))
            messages.error(self.request, "Error withdrawing money")
            return self.form_invalid(form)

        messages.success(self.request, f"Ksh. {form.cleaned_data['amount']} was withdrawn from your account")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Error withdrawing money")
        return super().form_invalid(form)


class SendMoneyView(CreateTransactionMixin):
    form_class = SendMoneyForm

    def form_valid(self, form):
        try:
            result = TransferService().execute(
                sender=self.request.user,
                receiver=form.cleaned_data["recipient"],
                amount=form.cleaned_data["amount"],
            )
        except SelfTransferError as error:
            form.add_error("recipient", str(error))
            messages.error(self.request, "Error sending money")
            return self.form_invalid(form)
        except InsufficientFundsError as error:
            form.add_error("amount", str(error))
            messages.error(self.request, "Error sending money")
            return self.form_invalid(form)
        except AccountBlockedError as error:
            messages.error(self.request, str(error))
            return self.form_invalid(form)
        except FraudModelError:
            form.add_error("amount", "Fraud screening is unavailable. The transfer was not processed.")
            messages.error(self.request, "Error sending money")
            return self.form_invalid(form)

        if result.fraud_detected:
            messages.error(self.request, "The transfer was blocked by the fraud detection system.")
            logout(self.request)
            return redirect("account-blocked")

        messages.success(
            self.request,
            f"Ksh. {form.cleaned_data['amount']} was sent to {form.cleaned_data['recipient'].username}",
        )
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        return super().form_invalid(form)


# Update these later

SUMMARY = {
    "total_balance": "482,650.00",
    "balance_change": "2.4%",
    "account_number": "0112 4483 6621",
    "account_type": "Premium current account",
    "savings_total": "156,200.00",
    "savings_goal": "3 active goals",
    "loans_total": "64,000.00",
    "loan_due": "3 Oct 2026",
    "national_id": "3xxxxx78",
}

USER = {
    "first_name": "Amina",
    "full_name": "Amina Wanjiru",
    "initials": "AW",
    "tier": "Gold member",
}

ALERTS = [
    {"title": "Unusual login detected", "detail": "New device in Nairobi", "time": "10m ago", "level": "warning"},
    {"title": "Loan instalment due soon", "detail": "KES 8,200 due 3 Oct", "time": "2h ago", "level": "info"},
    {"title": "Card frozen", "detail": "Virtual card ending 4471", "time": "1d ago", "level": "danger"},
]

MESSAGES = [
    {"sender": "Jumla Support", "preview": "Your dispute #JB-2291 has been resolved.", "time": "1h ago"},
    {"sender": "Relationship Manager", "preview": "Let's review your savings plan this week.", "time": "Yesterday"},
]

TRANSACTIONS = [
    {"date": "26 Sep 2026", "description": "Java House - Westlands", "reference": "TXN882014", "type": "purchase", "amount": "1,240.00", "direction": "debit", "status": "completed"},
    {"date": "25 Sep 2026", "description": "Salary - Cloudoon Ltd", "reference": "TXN881972", "type": "transfer", "amount": "145,000.00", "direction": "credit", "status": "completed"},
    {"date": "24 Sep 2026", "description": "KPLC token purchase", "reference": "TXN881840", "type": "bill", "amount": "2,000.00", "direction": "debit", "status": "completed"},
    {"date": "23 Sep 2026", "description": "Transfer to John Mwangi", "reference": "TXN881602", "type": "transfer", "amount": "5,500.00", "direction": "debit", "status": "completed"},
    {"date": "21 Sep 2026", "description": "Loan instalment", "reference": "TXN881190", "type": "loan", "amount": "8,200.00", "direction": "debit", "status": "pending"},
    {"date": "19 Sep 2026", "description": "Naivas Supermarket", "reference": "TXN880933", "type": "purchase", "amount": "3,860.50", "direction": "debit", "status": "completed"},
    {"date": "17 Sep 2026", "description": "M-Pesa deposit", "reference": "TXN880711", "type": "deposit", "amount": "10,000.00", "direction": "credit", "status": "completed"},
    {"date": "14 Sep 2026", "description": "DSTV subscription", "reference": "TXN880402", "type": "bill", "amount": "3,200.00", "direction": "debit", "status": "failed"},
]

CARDS = [
    {"scheme": "visa", "masked_number": "4521 •••• •••• 8890", "holder": "Amina Wanjiru", "expiry": "09/29"},
    {"scheme": "mastercard", "masked_number": "5412 •••• •••• 4471", "holder": "Amina Wanjiru", "expiry": "02/28"},
]

SPENDING = {
    "total": "58,420",
    "categories": [
        {"name": "Groceries", "percent": 32, "colour": "#1F6F50"},
        {"name": "Bills & utilities", "percent": 24, "colour": "#C99A3B"},
        {"name": "Transport", "percent": 18, "colour": "#3C7A64"},
        {"name": "Dining out", "percent": 14, "colour": "#B3402A"},
        {"name": "Other", "percent": 12, "colour": "#8C8672"},
    ],
}

BENEFICIARIES = [
    {"name": "John Mwangi", "bank": "Jumla Bank", "masked_account": "••••6621"},
    {"name": "Grace Achieng", "bank": "KCB", "masked_account": "••••1187"},
    {"name": "Peter Otieno", "bank": "Equity Bank", "masked_account": "••••9043"},
]


PROFILE = {
    "first_name": "Amina",
    "last_name": "Wanjiru",
    "full_name": "Amina Wanjiru",
    "initials": "AW",
    "email": "amina.wanjiru@example.com",
    "phone": "+254 722 000 000",
    "national_id": "30021147",
    "date_of_birth": "14 May 1994",
    "date_of_birth_iso": "1994-05-14",
    "occupation": "Software developer",
    "address": "Kilimani, Nairobi",
    "next_of_kin": "John Wanjiru",
    "member_since": "2022",
}

NOTIFICATION_SETTINGS = [
    {"label": "Transaction alerts", "hint": "Get notified for every debit or credit", "enabled": True},
    {"label": "Low balance warnings", "hint": "Alert when balance drops below KES 5,000", "enabled": True},
    {"label": "Marketing emails", "hint": "Product news, offers and surveys", "enabled": False},
    {"label": "SMS notifications", "hint": "Mirror alerts to your registered phone number", "enabled": True},
]

SECURITY = {
    "password_changed": "14 Aug 2026",
    "two_factor_enabled": True,
    "biometric_enabled": False,
    "sessions": [
        {"device": "iPhone 15 · Jumla app", "location": "Nairobi, KE", "last_active": "Active now", "is_current": True},
        {"device": "Chrome on Windows", "location": "Nairobi, KE", "last_active": "2 days ago", "is_current": False},
    ],
}

PREFERENCES = {"currency": "KES", "language": "English", "statement_delivery": "Email"}

def _dashboard_context(request, **extra):
    context = {
        "summary": SUMMARY,
        "user_data": USER,
        "alerts": ALERTS,
        "messages_list": MESSAGES,
        "current_year": 2026,
        "today": "Sunday, 27 September 2026",
    }
    context.update(extra)
    return context

# @login_required
def settings_view(request):
    if request.method == "POST":
        messages.success(request, "Your preferences have been saved.")
        return redirect("settings")
    context = _dashboard_context(
        request,
        notification_settings=NOTIFICATION_SETTINGS,
        security=SECURITY,
        preferences=PREFERENCES,
    )
    return render(request, "settings.html", context)
