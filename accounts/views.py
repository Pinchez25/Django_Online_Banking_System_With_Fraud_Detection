import sweetify as sw
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView
from sweetify.views import SweetifySuccessMixin

from .forms import AccountCreationForm, LoginForm, ProfileCreationForm
from .models import Profile


class UserRegistrationView(FormView):
    template_name = 'accounts/register.html'
    form_class = AccountCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
            sw.success(self.request, 'Account created successfully', timer=3000, timerProgressBar=True)
            # messages.success(self.request, 'Account created successfully')
        return super(UserRegistrationView, self).form_valid(form)

    def form_invalid(self, form):
        # if there are errors in the form, render the form with errors
        return render(self.request, self.template_name, {'register_form': form})

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('dashboard')
        return super(UserRegistrationView, self).get(*args, **kwargs)


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            username = get_user_model().objects.get(email=email).username
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Login successfully')
                return redirect(request.GET.get('next') if 'next' in request.GET else 'dashboard')
            else:
                messages.error(request, 'Invalid email or password')
                return redirect('login')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_user(request):
    logout(request)
    return redirect('login')


class ProfileView(LoginRequiredMixin, DetailView):
    model = Profile
    context_object_name = 'profile'
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super(ProfileView, self).get_context_data()
        context['account_id'] = context['profile'].account.id

        return context


class UpdateProfile(LoginRequiredMixin, SweetifySuccessMixin, UpdateView):
    model = Profile
    form_class = ProfileCreationForm
    success_message = 'Profile updated successfully'
    template_name = 'accounts/update_profile.html'

    def get_success_url(self):
        return reverse_lazy('profile', kwargs={'pk': self.request.user.profile.id})

    def form_valid(self, form):
        profile_ = form.save(commit=False)
        profile_.account = self.request.user
        profile_.save()
        return super(UpdateProfile, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UpdateProfile, self).get_context_data()
        context['account'] = context['profile'].account

        return context
