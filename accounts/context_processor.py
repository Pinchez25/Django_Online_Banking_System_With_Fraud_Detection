from .forms import AccountCreationForm


# from .models import Account


def authentication_forms(request):
    return {
        'register_form': AccountCreationForm(),
    }
