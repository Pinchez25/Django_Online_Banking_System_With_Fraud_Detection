from .forms import AccountRegistrationForm


# from .models import Account


def authentication_forms(request):
    return {
        'register_form': AccountRegistrationForm(),
    }
