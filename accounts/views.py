import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeDoneView,
    PasswordChangeView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, UpdateView

from .forms import (
    AccountRegistrationForm,
    AccountUpdateForm,
    CustomAuthenticationForm,
    ProfileUpdateForm,
)
from .models import Account, Profile
from .utils import get_login_agent, process_profile_image

logger = logging.getLogger(__name__)


class AccountRegisterView(CreateView):
    """Signs a customer up. Profile creation is handled by the post_save
    signal in signals.py, not here — see AccountsConfig.ready()."""

    model = Account
    form_class = AccountRegistrationForm
    template_name = "registration/register.html"
    success_url = reverse_lazy("accounts:profile-detail")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        logger.info("New account registered: %s", self.object.pk)
        messages.success(self.request, f"Welcome, {self.object.email} — your account is ready.")
        return response


class AccountLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Account logged in: %s", self.request.user.pk)
        get_login_agent(self.request)
        messages.success(self.request, f"Welcome back, {self.request.user.email}.")
        return response

    def form_invalid(self, form):
        logger.warning("Failed login attempt for email: %s", form.cleaned_data.get("username", "unknown"))
        return super().form_invalid(form)


class AccountLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            logger.info("Account logged out: %s", request.user.pk)
            messages.info(request, "You have been logged out.")
        return super().dispatch(request, *args, **kwargs)


class AccountProfileDetailView(LoginRequiredMixin, DetailView):
    """Read-only view of the logged-in customer's account and profile, in a single query."""

    model = Account
    template_name = "profile.html"
    context_object_name = "account"

    def get_object(self, queryset=None):
        return Account.objects.select_related("profile").get(pk=self.request.user.pk)


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    """Lets a customer edit their own account fields (username, email, account/user type)."""

    model = Account
    form_class = AccountUpdateForm
    template_name = "profile_form.html"
    success_url = reverse_lazy("accounts:profile-detail")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Account %s updated fields: %s", self.object.pk, form.changed_data)
        messages.success(self.request, "Your account details have been updated.")
        return response


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Lets a customer edit their own profile, resizing any newly uploaded photo."""

    model = Profile
    form_class = ProfileUpdateForm
    template_name = "profile_form.html"
    success_url = reverse_lazy("accounts:profile-detail")

    def get_object(self, queryset=None):
        return Profile.objects.select_related("account").get(account_id=self.request.user.pk)

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Profile %s updated fields: %s", self.object.pk, form.changed_data)
        if "profile_image" in form.changed_data and self.object.profile_image:
            process_profile_image(self.object.profile_image.path, 300, 300)
        messages.success(self.request, "Your profile has been updated.")
        return response


class AccountDeactivateView(LoginRequiredMixin, DeleteView):
    """Deactivates rather than hard-deletes the account, preserving banking records."""

    model = Account
    template_name = "accounts/account_confirm_delete.html"
    success_url = reverse_lazy("accounts:login")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        account = self.get_object()
        account.is_active = False
        account.save(update_fields=["is_active"])
        logger.warning("Account deactivated: %s", account.pk)
        messages.info(self.request, "Your account has been deactivated.")
        return redirect(self.success_url)


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("accounts:password-change-done")

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Password changed for account: %s", self.request.user.pk)
        messages.success(self.request, "Your password has been changed.")
        return response


class AccountPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "registration/password_change_done.html"


class AccountPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    html_email_template_name = "accounts/emails/password_reset_email.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password-reset-done")

    def form_valid(self, form):
        logger.info("Password reset requested for email domain: %s", form.cleaned_data["email"].split("@")[-1])
        return super().form_valid(form)


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "registration/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password-reset-complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Password reset completed for account: %s", form.user.pk)
        return response


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "registration/password_reset_complete.html"
