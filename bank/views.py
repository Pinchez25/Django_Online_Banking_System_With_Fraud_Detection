import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from .forms import DepositForm, SendMoneyForm, WithdrawForm
from .models import Notification, Transaction
from .services.accounts import DepositService, InsufficientFundsError, MoneyOperationError, WithdrawalService
from .services.notifications import publish_notification_snapshot
from .services.transfers import AccountBlockedError, FraudModelError, SelfTransferError, TransferService

logger = logging.getLogger(__name__)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_dashboard_context(self.request))
        return context


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = "bank/transaction_report.html"
    model = Transaction

    def get_queryset(self):
        return super().get_queryset().filter(account=self.request.user)


class NotificationCenterView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "bank/notification_center.html"
    context_object_name = "notifications"
    paginate_by = 25

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        kind = self.request.GET.get("kind")
        if kind in Notification.Kind.values:
            queryset = queryset.filter(kind=kind)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_dashboard_context(self.request))
        kind = self.request.GET.get("kind")
        context["active_notification_kind"] = kind if kind in Notification.Kind.values else ""
        return context


@login_required
@require_POST
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=["read_at"])
    return redirect("bank:notification-center")


@login_required
@require_POST
def mark_all_notifications_read(request):
    queryset = Notification.objects.filter(recipient=request.user, read_at__isnull=True)
    kind = request.POST.get("kind")
    if kind in Notification.Kind.values:
        queryset = queryset.filter(kind=kind)
    queryset.update(read_at=timezone.now())
    publish_notification_snapshot(request.user.pk)
    return redirect("bank:notification-center")


class CreateTransactionMixin(LoginRequiredMixin, CreateView):
    template_name = "bank/create_transaction.html"
    model = Transaction

    def get_success_url(self):
        return reverse("bank:dashboard")

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



def get_dashboard_data(user):
    # Placeholder implementation
    profile = getattr(user, 'profile', None)

    unread_alerts = Notification.objects.filter(
        recipient=user,
        kind=Notification.Kind.ALERT,
        read_at__isnull=True,
    )
    unread_messages = Notification.objects.filter(
        recipient=user,
        kind=Notification.Kind.MESSAGE,
        read_at__isnull=True,
    )

    return {
        "summary": {
            "total_balance": str(user.bank_balances),
            "balance_change": "0%",
            "account_number": "N/A",
            "account_type": "Personal account",
            "savings_total": "0.00",
            "savings_goal": "0 active goals",
            "loans_total": "0.00",
            "loan_due": "N/A",
            "national_id": str(user.national_id),
        },
        "alerts": unread_alerts[:5],
        "alerts_unread_count": unread_alerts.count(),
        "messages_list": unread_messages[:5],
        "messages_unread_count": unread_messages.count(),
        "transactions": user.transactions.all(),
        "cards": [],
        "spending": {
            "total": "0",
            "categories": [],
        },
        "beneficiaries": [],
        "profile": {
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "email": user.email,
        },
        "notification_settings": [
            {"label": "Transaction alerts", "hint": "Get notified for every debit or credit", "enabled": True},
            {"label": "Low balance warnings", "hint": "Alert when balance drops below KES 5,000", "enabled": True},
            {"label": "Marketing emails", "hint": "Product news, offers and surveys", "enabled": False},
            {"label": "SMS notifications", "hint": "Mirror alerts to your registered phone number", "enabled": True},
        ],
        "security": {
            "password_changed": "N/A",
            "two_factor_enabled": False,
            "biometric_enabled": False,
        },
        "preferences": {"currency": "KES", "language": "English", "statement_delivery": "Email"},
    }

def _dashboard_context(request, **extra):
    user_data = get_dashboard_data(request.user)
    context = {
        "summary": user_data["summary"],
        "alerts": user_data["alerts"],
        "alerts_unread_count": user_data["alerts_unread_count"],
        "messages_list": user_data["messages_list"],
        "messages_unread_count": user_data["messages_unread_count"],
        "transactions": user_data["transactions"],
        "cards": user_data["cards"],
        "spending": user_data["spending"],
        "beneficiaries": user_data["beneficiaries"],
        "profile": user_data["profile"],
        "current_year": timezone.now().year,
        "today": timezone.now().strftime("%A, %d %B %Y"),
        "notification_settings": user_data["notification_settings"],
        "security": user_data["security"],
        "preferences": user_data["preferences"],
    }
    context.update(extra)
    return context

# @login_required
def settings_view(request):
    if request.method == "POST":
        messages.success(request, "Your preferences have been saved.")
        return redirect("settings")
    context = _dashboard_context(request)
    return render(request, "settings.html", context)
