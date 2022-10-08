from django.urls import path
from .views import HomeView, DepositMoneyView, WithdrawMoneyView, SendMoneyView

urlpatterns = [
    path('', HomeView.as_view(), name='dashboard'),
    path('deposit/', DepositMoneyView.as_view(), name="deposit-money"),
    path('withdraw/', WithdrawMoneyView.as_view(), name="withdraw-money"),
    path('send/', SendMoneyView.as_view(), name='send-money'),
]
