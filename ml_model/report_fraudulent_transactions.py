from django.core.mail import send_mail
from django.conf import settings


def report_fraudulent_transactions(to_email, subject="Fraud Alert"):
    message = "" \
              "Dear Customer," \
              "A transaction from your account has been flagged as potentially fraudulent. " \
              "Your account has been locked at the moment" \
              "Please contact us immediately to resolve this issue." \
              "Regards," \
              "Kwetu Bank of Kenya"

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [to_email],
        fail_silently=False,
    )
