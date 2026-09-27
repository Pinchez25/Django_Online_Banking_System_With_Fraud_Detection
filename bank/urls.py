from django.urls import path
from .views import (
    HomeView,
    DepositMoneyView,
    NotificationCenterView,
    SendMoneyView,
    WithdrawMoneyView,
    mark_all_notifications_read,
    mark_notification_read,
    settings_view,
)

app_name = "bank"
urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('deposit/', DepositMoneyView.as_view(), name="deposit-money"),
    path('withdraw/', WithdrawMoneyView.as_view(), name="withdraw-money"),
    path('send/', SendMoneyView.as_view(), name='send-money'),
    # path('transaction-history/', TransactionHistoryView.as_view(), name="history")
    path("settings/", settings_view, name="settings"),
    path("notifications/", NotificationCenterView.as_view(), name="notification-center"),
    path("notifications/read-all/", mark_all_notifications_read, name="notifications-read-all"),
    path("notifications/<int:pk>/read/", mark_notification_read, name="notification-read"),
]
