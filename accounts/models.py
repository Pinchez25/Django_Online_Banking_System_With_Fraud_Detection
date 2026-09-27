import uuid

from creditcards.models import CardNumberField
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

USER_TYPES = (
    ("individual", "Individual"),
    ("business", "Business"),
    ("joint", "Joint"),
    ("power of attorney", "Power of Attorney"),
)

ACCOUNT_TYPES = (
    ("checking", "Checking"),
    ("savings", "Savings"),
    ("certificate of deposit", "Certificate of Deposit"),
    ("money market", "Money Market"),
)


class Account(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account_type = models.CharField(
        _("Type of Account"),
        max_length=50,
        choices=ACCOUNT_TYPES,
        default="savings",
    )
    cc_number = CardNumberField(
        _("Credit Card"),
        help_text=_("Customer credit card number"),
        null=True,
        blank=True,
    )
    user_type = models.CharField(
        _("User Type"),
        max_length=50,
        choices=USER_TYPES,
        default="individual",
        null=True,
        blank=True,
    )
    email = models.EmailField(_("Email"), unique=True)
    national_id = models.IntegerField(
        _("National ID"),
        unique=True,
        null=True,
        blank=True,
        validators=[MaxValueValidator(99999999, message="Invalid National ID")],
    )
    bank_balances = models.DecimalField(
        _("Balance"),
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    is_blocked = models.BooleanField(_("Blocked"), default=False)
    deactivated_at = models.DateTimeField(null=True, blank=True, editable=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = "auth_user"
        constraints = [
            models.CheckConstraint(
                name="account_bank_balances_non_negative",
                condition=models.Q(bank_balances__gte=0),
            ),
        ]

    def __str__(self):
        return self.username

    def can_approve_transactions(self):
        return (
            self.is_active
            and not self.is_blocked
            and (self.is_staff or self.has_perm("bank.approve_transaction"))
        )

    def deactivate(self):
        self.is_active = False
        self.deactivated_at = self.deactivated_at or timezone.now()
        self.save(update_fields=["is_active", "deactivated_at"])


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = models.CharField(_("First Name"), max_length=50, blank=True, default="")
    last_name = models.CharField(_("Last Name"), max_length=50, blank=True, default="")
    profile_image = models.ImageField(
        _("Image"),
        null=True,
        blank=True,
        upload_to="profile_images",
        default="default.png",
    )
    phone_number = models.CharField(_("Phone Number"), max_length=50, null=True, blank=True)
    address = models.CharField(_("Address"), max_length=50, null=True, blank=True)
    city = models.CharField(_("City"), max_length=50, null=True, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=50, null=True, blank=True)
    created = models.DateTimeField(_("Created"), auto_now_add=True)
    updated = models.DateTimeField(_("Updated"), auto_now=True)

    def __str__(self):
        return self.account.username

    def get_profile_image(self):
        return self.profile_image.url if self.profile_image else None

    class Meta:
        db_table = "profile"
        ordering = ["-created"]


class NextOfKin(models.Model):
    RELATIONSHIP_CHOICES = (
        ("parent", _("Parent")),
        ("spouse", _("Spouse")),
        ("child", _("Child")),
        ("sibling", _("Sibling")),
        ("other", _("Other")),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="next_of_kin")
    full_name = models.CharField(_("Full Name"), max_length=100)
    relationship = models.CharField(_("Relationship"), max_length=20, choices=RELATIONSHIP_CHOICES)
    phone_number = models.CharField(_("Phone Number"), max_length=50)
    email = models.EmailField(_("Email"), blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created", "id"]

    def __str__(self):
        return f"{self.full_name} ({self.get_relationship_display()})"
