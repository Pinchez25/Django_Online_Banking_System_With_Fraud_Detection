from .forms import AccountCreationForm


def authentication_forms(request):
    return {
        'register_form': AccountCreationForm(),
    }

