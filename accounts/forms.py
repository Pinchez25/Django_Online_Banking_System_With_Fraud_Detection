from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.forms import Select, EmailField, CharField, EmailInput, PasswordInput, ModelForm, Form

from .models import Profile


# class OnlineBankAccountCreationForm(ModelForm):
#     confirm_password = CharField()
#     captcha = ReCaptchaField()
#
#     class Meta:
#         model = Customer
#         fields = ['account_number', 'password', 'confirm_password']
#         widgets = {
#             'password': PasswordInput(),
#             'confirm_password': PasswordInput(),
#         }
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             'account_number',
#             Row(
#                 Column('password', css_class='col-md-6 mb-0'),
#                 Column('confirm_password', css_class='col-md-6 mb-0'),
#
#             ),
#             'captcha',
#             Submit('submit', 'Submit', css_class='btn btn-primary  btn-block', id="btnSubmit")
#         )
#
#     # ensure password and confirm_password are the same
#     def clean(self):
#         cleaned_data = super().clean()
#         password = cleaned_data.get('password')
#         account_number = cleaned_data.get('account_number')
#         confirm_password = cleaned_data.get('confirm_password')
#         if password != confirm_password:
#             raise ValidationError("Passwords do not match")
#
#         # make sure account_number exists in Account model
#         if not get_user_model().objects.filter(account_number=account_number).exists():
#             raise ValidationError(
#                 "Account number does not exist.You have to be a customer of this bank to create an online bank
#                 account")


class AccountCreationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ['username', 'account_type', 'user_type', 'password1', 'password2', 'email', 'national_id']
        widgets = {
            'account_type': Select(),
            'user_type': Select(),
        }

    def __init__(self, *args, **kwargs):
        super(AccountCreationForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'email',
            'national_id',
            Row(
                Column('account_type', css_class='col-md-6 mb-0'),
                Column('user_type', css_class='col-md-6 mb-0'),
            ),
            Row(
                Column('password1', css_class='col-md-6 mb-0'),
                Column('password2', css_class='col-md-6 mb-0'),
            ),
            Submit('submit', 'Register', css_class='btn btn-primary btn-user btn-block', id="btnSubmit")
        )
        # for name, field in self.fields.items():
        #     field.widget.attrs.update({
        #         'class': 'form-control-user form-control'
        #     })

        self.fields['username'].widget.attrs.update({'id': 'user-name'})
        self.fields['email'].widget.attrs.update({'id': 'email'})
        self.fields['account_type'].widget.attrs.update({'id': 'account-type'})
        self.fields['user_type'].widget.attrs.update({'id': 'user-type'})
        self.fields['password1'].widget.attrs.update({'id': 'password'})
        self.fields['password2'].widget.attrs.update({'id': 'conform-password'})
        self.fields['national_id'].widget.attrs.update({'id': 'national-id'})


class LoginForm(Form):
    email = EmailField(widget=EmailInput(attrs={'id': 'email'}))
    password = CharField(widget=PasswordInput(attrs={'id': 'password'}))


class ProfileCreationForm(ModelForm):
    class Meta:
        model = Profile
        exclude = ['account']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('first_name', css_class='col-md-6 mb-0'),
                Column('last_name', css_class='col-md-6 mb-0'),
            ),
            'profile_image',
            'phone_number',
            'address',
            'city',
            'zip_code',
            Submit('submit', 'Update Profile', css_class='btn btn-primary btn-user btn-block', id="btnCreateProfile")
        )

        self.fields['first_name'].widget.attrs.update({'id': 'first-name'})
        self.fields['last_name'].widget.attrs.update({'id': 'last-name'})
        self.fields['profile_image'].widget.attrs.update({'id': 'profile-image'})
        self.fields['phone_number'].widget.attrs.update({'id': 'phone-number'})
        self.fields['address'].widget.attrs.update({'id': 'address'})
        self.fields['city'].widget.attrs.update({'id': 'city'})
        self.fields['zip_code'].widget.attrs.update({'id': 'zip-code'})
