import random

from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Account, Profile
from django.conf import settings


def generate_unique_cc_number():
    cc_number = random.randint(1000000000000000, 9999999999999999)
    if Account.objects.filter(cc_number=cc_number).exists():
        return generate_unique_cc_number()
    return cc_number


@receiver(post_save, sender=Account)
def create_account(sender, instance, created, **kwargs):
    if created:
        instance.cc_number = generate_unique_cc_number()
        instance.save()

        # create a profile for the account holder
        profile = Profile.objects.create(account=instance)
        profile.first_name = instance.username
        profile.save()

        # send a welcome email to the user
        send_mail(
            'Welcome to the Bank',
            'Thank you for opening an account with us. Your account number is ' + str(
                instance.cc_number),
            settings.EMAIL_HOST_USER,
            [instance.email],
            fail_silently=False,
        )
