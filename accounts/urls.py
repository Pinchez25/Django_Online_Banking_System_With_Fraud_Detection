from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.AccountRegisterView.as_view(), name="register"),
    path("login/", views.AccountLoginView.as_view(), name="login"),
    path("logout/", views.AccountLogoutView.as_view(), name="logout"),
    path("profile/", views.AccountProfileDetailView.as_view(), name="profile-detail"),
    path("profile/edit/", views.ProfileUpdateView.as_view(), name="profile-update"),
    path("account/edit/", views.AccountUpdateView.as_view(), name="account-update"),
    path("account/deactivate/", views.AccountDeactivateView.as_view(), name="account-deactivate"),
    path("password/change/", views.AccountPasswordChangeView.as_view(), name="password-change"),
    path(
        "password/change/done/",
        views.AccountPasswordChangeDoneView.as_view(),
        name="password-change-done",
    ),
    path("password/reset/", views.AccountPasswordResetView.as_view(), name="password-reset"),
    path(
        "password/reset/done/",
        views.AccountPasswordResetDoneView.as_view(),
        name="password-reset-done",
    ),
    path(
        "password/reset/confirm/<uidb64>/<token>/",
        views.AccountPasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password/reset/complete/",
        views.AccountPasswordResetCompleteView.as_view(),
        name="password-reset-complete",
    ),
]
