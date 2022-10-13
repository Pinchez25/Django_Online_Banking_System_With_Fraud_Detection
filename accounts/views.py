from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView

from .forms import AccountCreationForm, LoginForm, ProfileCreationForm
from .models import Profile
from .utils import login_agent


# from braces.views import SuperuserRequiredMixin


# class CreateOnlineBankAccountView2(CreateView):
#     template_name = 'accounts/create_online_bank_account.html'
#     form_class = OnlineBankAccountCreationForm
#     success_url = reverse_lazy('dashboard')
#
#     def form_valid(self, form):
#         form.instance.account = Account.objects.get(account_number=form.cleaned_data['account_number'])
#         form.save()
#         messages.success(self.request, 'Online bank account created successfully')
#         return super(CreateOnlineBankAccountView2, self).form_valid(form)
#
#     def form_invalid(self, form):
#         messages.error(self.request, 'Error creating online bank account')
#         return super(CreateOnlineBankAccountView2, self).form_invalid(form)
#
#
# class CreateOnlineBankAccountView(FormView):
#     template_name = 'accounts/create_online_bank_account.html'
#     form_class = OnlineBankAccountCreationForm
#     success_url = reverse_lazy('dashboard')
#
#     def form_valid(self, form):
#         form.save()
#         messages.success(self.request, 'Account created successfully')
#         return super().form_valid(form)
#
#     def form_invalid(self, form):
#         # messages.error(self.request, 'Account creation failed')
#         return super().form_invalid(form)


class UserRegistrationView(FormView):
    template_name = 'accounts/bank_account_creation.html'
    form_class = AccountCreationForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
            messages.success(self.request, 'Account created successfully')
        return super(UserRegistrationView, self).form_valid(form)

    def form_invalid(self, form):
        # if there are errors in the form, render the form with errors
        return render(self.request, self.template_name, {'register_form': form})

    def get_success_url(self):
        return reverse_lazy('update-profile', kwargs={'pk': self.request.user.pk})

    # def get(self, *args, **kwargs):
    #     if self.request.user.is_authenticated:
    #         return redirect('dashboard')
    #     return super(UserRegistrationView, self).get(*args, **kwargs)


def user_login(request):
    # if user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            try:
                username = get_user_model().objects.get(email=email).username
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    login_agent.get_login_agent(request)
                    messages.success(request, 'Login success')
                    return redirect(request.GET.get('next') if 'next' in request.GET else 'dashboard')
                else:
                    messages.error(request, 'Invalid email or password')

                    return redirect('login')
            except get_user_model().DoesNotExist:
                messages.error(request, "Invalid user and/or password")
                return redirect('login')

    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_user(request):
    logout(request)
    return redirect('login')


def account_locked(request):
    return render(request, 'account_locked.html')


class ProfileView(LoginRequiredMixin, DetailView):
    model = Profile
    context_object_name = 'profile'
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data()
        context['account_id'] = context['profile'].account.id

        return context


class UpdateProfile(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileCreationForm
    template_name = 'accounts/update_profile.html'

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.profile.id})

    def form_valid(self, form):
        profile_ = form.save(commit=False)
        profile_.account = self.request.user
        profile_.save()
        messages.success(self.request, 'Profile updated successfully')
        return super(UpdateProfile, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UpdateProfile, self).get_context_data()
        context['account'] = context['profile'].account

        return context
