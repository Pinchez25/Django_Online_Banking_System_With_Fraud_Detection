from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import NextOfKin


class NextOfKinModelTests(TestCase):
    def setUp(self):
        self.account = get_user_model().objects.create_user(
            username="kin-customer",
            email="kin-customer@example.com",
            password="correct-password",
            national_id=91234567,
        )

    def test_profile_can_have_multiple_next_of_kin(self):
        first = NextOfKin.objects.create(
            profile=self.account.profile,
            full_name="Wanjiku Mwangi",
            relationship="parent",
            phone_number="+254700000001",
        )
        second = NextOfKin.objects.create(
            profile=self.account.profile,
            full_name="Kamau Mwangi",
            relationship="sibling",
            phone_number="+254700000002",
        )

        self.assertQuerySetEqual(
            self.account.profile.next_of_kin.all(),
            [first, second],
        )

    def test_account_and_profile_names_stay_in_sync(self):
        self.account.first_name = "Amina"
        self.account.last_name = "Njeri"
        self.account.save()

        self.account.profile.refresh_from_db()
        self.assertEqual(self.account.profile.first_name, "Amina")
        self.assertEqual(self.account.profile.last_name, "Njeri")

    def test_deactivation_retains_account_profile_and_next_of_kin(self):
        kin = NextOfKin.objects.create(
            profile=self.account.profile,
            full_name="Wanjiku Mwangi",
            relationship="parent",
            phone_number="+254700000001",
        )

        self.account.deactivate()
        self.account.refresh_from_db()

        self.assertFalse(self.account.is_active)
        self.assertIsNotNone(self.account.deactivated_at)
        self.assertTrue(self.account.profile.next_of_kin.filter(pk=kin.pk).exists())
