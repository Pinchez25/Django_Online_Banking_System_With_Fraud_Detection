import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, Profile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Account, dispatch_uid="accounts_create_profile")
def create_profile(sender, instance, created, **kwargs):
    """Provisions a Profile the moment a new Account is created.

    Runs for every Account creation path — the accounts view, the admin,
    createsuperuser, the shell — not just the one form this app ships.
    get_or_create rather than create as a defensive no-op if a Profile
    somehow already exists (e.g. a fixture load), rather than raising.
    """
    if created:
        _, provisioned = Profile.objects.get_or_create(
            account=instance,
            defaults={"first_name": instance.first_name, "last_name": instance.last_name},
        )
        if provisioned:
            logger.info("Profile provisioned for account: %s", instance.pk)
