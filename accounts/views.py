import logging

from django.contrib import messages
from django.contrib.auth import login, logout
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
from django.db import transaction
from django.db.models import prefetch_related_objects
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, FormView, TemplateView, UpdateView

from .forms import (
    AccountDeactivationForm,
    AccountRegistrationForm,
    AccountUpdateForm,
    CustomAuthenticationForm,
    NextOfKinFormSet,
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
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:profile-detail")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        logger.info("New account registered: %s", self.object.pk)
        messages.success(self.request, f"Welcome, {self.object.email} — your account is ready.")
        return response


class AccountLoginView(LoginView):
    template_name = "accounts/login.html"
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
        account = self.request.user
        prefetch_related_objects([account.profile], "next_of_kin")
        return account

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = self.object.profile
        return context


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
    """Updates a customer's profile and next-of-kin contacts together."""

    model = Profile
    form_class = ProfileUpdateForm
    template_name = "profile_form.html"
    success_url = reverse_lazy("accounts:profile-detail")

    def get_object(self, queryset=None):
        return self.request.user.profile

    def get_formset(self):
        return NextOfKinFormSet(
            data=self.request.POST if self.request.method == "POST" else None,
            instance=self.object,
            prefix="next_of_kin",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_profile_form"] = True
        formset = getattr(self, "next_of_kin_formset", None)
        context["next_of_kin_formset"] = formset if formset is not None else self.get_formset()
        return context

    def form_valid(self, form):
        formset = NextOfKinFormSet(
            self.request.POST,
            instance=form.instance,
            prefix="next_of_kin",
        )
        if not formset.is_valid():
            self.next_of_kin_formset = formset
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()
            formset.instance = self.object
            formset.save()

        logger.info("Profile %s updated fields: %s", self.object.pk, form.changed_data)
        if "profile_image" in form.changed_data and self.object.profile_image:
            process_profile_image(self.object.profile_image.path, 300, 300)
        messages.success(self.request, "Your profile has been updated.")
        return redirect(self.get_success_url())


class AccountDeactivateView(LoginRequiredMixin, FormView):
    """Soft-deactivates an account after password confirmation."""

    form_class = AccountDeactivationForm
    template_name = "accounts/account_confirm_delete.html"
    success_url = reverse_lazy("accounts:login")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        account = self.request.user
        account.deactivate()
        logger.warning("Account deactivated: %s", account.pk)
        logout(self.request)
        messages.info(self.request, "Your account has been deactivated.")
        return super().form_valid(form)


class AccountPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("accounts:password-change-done")

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Password changed for account: %s", self.request.user.pk)
        messages.success(self.request, "Your password has been changed.")
        return response


class AccountPasswordChangeDoneView(LoginRequiredMixin, PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


class AccountPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    html_email_template_name = "accounts/emails/password_reset_email.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password-reset-done")

    def form_valid(self, form):
        logger.info("Password reset requested for email domain: %s", form.cleaned_data["email"].split("@")[-1])
        return super().form_valid(form)


class AccountPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class AccountPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password-reset-complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info("Password reset completed for account: %s", form.user.pk)
        return response


class AccountPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class AccountBlockedView(TemplateView):
    """Shown when the fraud detector blocks a transfer."""

    template_name = "accounts/account_blocked.html"
