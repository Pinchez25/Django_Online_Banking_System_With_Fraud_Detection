from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, \
    PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import path

from .views import user_login, logout_user, UserRegistrationView, UpdateProfile, ProfileView

urlpatterns = [
    path('login/', user_login, name='login'),
    path('logout/', logout_user, name='logout'),
    path('register/', UserRegistrationView.as_view(), name='register'),
    # path('create-online-account/', CreateOnlineBankAccountView.as_view(), name="create-online-account"),

    # password change views
    path('reset_password/', PasswordResetView.as_view(template_name="accounts/forgot-password.html"),
         name='reset_password'),
    path('reset_password_sent/', PasswordResetDoneView.as_view(template_name="accounts/password_reset_sent.html"),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name="accounts/reset.html"),
         name='password_reset_confirm'),
    path('reset_password_complete/',
         PasswordResetCompleteView.as_view(template_name="accounts/reset_password_complete.html"),
         name='password_reset_complete'),

    # profile view
    path('profile/<str:pk>/', ProfileView.as_view(), name='profile'),
    path('update-profile/<str:pk>/', UpdateProfile.as_view(), name='update-profile')

]
