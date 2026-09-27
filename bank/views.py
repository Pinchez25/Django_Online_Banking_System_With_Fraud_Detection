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
from .services.dashboard import get_dashboard_context
from .services.notifications import publish_notification_snapshot
from .services.transfers import AccountBlockedError, FraudModelError, SelfTransferError, TransferService

logger = logging.getLogger(__name__)


def _dashboard_context(request, **extra):
    return get_dashboard_context(request, **extra)


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
            logger.info("Deposit form submitted by account_id=%s", self.request.user.pk)
            DepositService.execute(account=self.request.user, amount=form.cleaned_data["amount"])
        except MoneyOperationError as error:
            logger.warning("Deposit failed for account_id=%s: %s", self.request.user.pk, str(error))
            form.add_error("amount", str(error))
            messages.error(self.request, "Error depositing money")
            return self.form_invalid(form)

        messages.success(self.request, "Your deposit request has been submitted for approval.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Error depositing money")
        return super().form_invalid(form)


class WithdrawMoneyView(CreateTransactionMixin):
    form_class = WithdrawForm

    def form_valid(self, form):
        try:
            logger.info("Withdrawal form submitted by account_id=%s", self.request.user.pk)
            WithdrawalService.execute(account=self.request.user, amount=form.cleaned_data["amount"])
        except InsufficientFundsError as error:
            logger.warning("Withdrawal rejected for account_id=%s: %s", self.request.user.pk, str(error))
            form.add_error("amount", str(error))
            messages.error(self.request, "Error withdrawing money")
            return self.form_invalid(form)
        except MoneyOperationError as error:
            logger.warning("Withdrawal failed for account_id=%s: %s", self.request.user.pk, str(error))
            form.add_error("amount", str(error))
            messages.error(self.request, "Error withdrawing money")
            return self.form_invalid(form)

        messages.success(self.request, "Your withdrawal request has been submitted for approval.")
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        messages.error(self.request, "Error withdrawing money")
        return super().form_invalid(form)


class SendMoneyView(CreateTransactionMixin):
    form_class = SendMoneyForm

    def form_valid(self, form):
        try:
            logger.info("Transfer form submitted by account_id=%s", self.request.user.pk)
            result = TransferService().execute(
                sender=self.request.user,
                receiver=form.cleaned_data["recipient"],
                amount=form.cleaned_data["amount"],
            )
        except SelfTransferError as error:
            logger.warning("Self-transfer rejected for account_id=%s: %s", self.request.user.pk, str(error))
            form.add_error("recipient", str(error))
            messages.error(self.request, "Error sending money")
            return self.form_invalid(form)
        except InsufficientFundsError as error:
            logger.warning("Transfer rejected for account_id=%s: %s", self.request.user.pk, str(error))
            form.add_error("amount", str(error))
            messages.error(self.request, "Error sending money")
            return self.form_invalid(form)
        except AccountBlockedError as error:
            logger.warning("Blocked transfer attempt by account_id=%s: %s", self.request.user.pk, str(error))
            messages.error(self.request, str(error))
            return self.form_invalid(form)
        except FraudModelError:
            logger.exception("Fraud model failure during transfer for account_id=%s", self.request.user.pk)
            form.add_error("amount", "Fraud screening is unavailable. The transfer was not processed.")
            messages.error(self.request, "Error sending money")
            return self.form_invalid(form)

        if result.fraud_detected:
            logger.warning("Fraud transfer blocked for account_id=%s", self.request.user.pk)
            messages.error(self.request, "The transfer was blocked by the fraud detection system.")
            logout(self.request)
            return redirect("accounts:account-blocked")

        messages.success(
            self.request,
            "Your transfer request has been submitted for approval.",
        )
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        return super().form_invalid(form)


# @login_required
def settings_view(request):
    if request.method == "POST":
        messages.success(request, "Your preferences have been saved.")
        return redirect("settings")
    context = _dashboard_context(request)
    return render(request, "settings.html", context)
