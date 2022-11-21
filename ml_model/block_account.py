# function to block the logged in account
from django.contrib.auth import logout
from django.shortcuts import redirect


def block_account(request):
    account = request.user
    account.is_blocked = True
    account.save()
    logout(request)
    return redirect('account-blocked')
