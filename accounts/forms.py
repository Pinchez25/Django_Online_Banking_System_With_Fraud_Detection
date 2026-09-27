from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Account, Profile


class BootstrapFormMixin:
    """Adds a crispy-forms helper and Bootstrap widget classes to every field on the form."""

    submit_label = "Save"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = "form-select" if isinstance(field.widget,
                                                    (forms.Select, forms.SelectMultiple)) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            field.widget.attrs["class"] = f'{field.widget.attrs.get("class", "")} {css_class}'.strip()

        self.helper = FormHelper(self)
        self.helper.form_method = "post"
        self.helper.add_input(Submit("submit", self.submit_label, css_class="btn btn-primary"))


class AccountRegistrationForm(BootstrapFormMixin, UserCreationForm):
    """Sign-up form; relies on UserCreationForm for password validation and hashing."""

    submit_label = "Create account"

    class Meta(UserCreationForm.Meta):
        model = Account
        fields = ("username", "email", "national_id", "account_type", "user_type")


class AccountUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Lets a customer edit their own non-sensitive account fields.

    Deliberately excludes national_id, cc_number, bank_balances and is_blocked —
    those are staff-managed and belong in the admin site, not self-service.
    """

    submit_label = "Update account"

    class Meta:
        model = Account
        fields = ("username", "email", "account_type", "user_type")


class ProfileUpdateForm(BootstrapFormMixin, forms.ModelForm):
    submit_label = "Update profile"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper.form_enctype = "multipart/form-data"  # required for the profile_image field

    class Meta:
        model = Profile
        fields = (
            "first_name",
            "last_name",
            "profile_image",
            "phone_number",
            "address",
            "city",
            "zip_code",
        )


class CustomAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    submit_label = "Log in"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = "Email"
