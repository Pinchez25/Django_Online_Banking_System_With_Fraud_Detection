import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Account, Profile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Account, dispatch_uid="accounts_create_profile")
def create_profile(sender, instance, created, **kwargs):
    """Provision a Profile for each Account, and keep the user/profile names synced."""
    profile, provisioned = Profile.objects.get_or_create(
        account=instance,
        defaults={"first_name": instance.first_name, "last_name": instance.last_name},
    )

    if provisioned:
        logger.info("Profile provisioned for account: %s", instance.pk)

    if profile.first_name != instance.first_name or profile.last_name != instance.last_name:
        profile.first_name = instance.first_name
        profile.last_name = instance.last_name
        profile.save(update_fields=["first_name", "last_name"])
        logger.info("Profile identity synced for account: %s", instance.pk)
