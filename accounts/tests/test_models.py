# from ..models import Profile, Account
# from django.test import TestCase
# from model_bakery import baker
#
#
# class TestModels(TestCase):
#     def setUp(self) -> None:
#         # remember to take care of unique constraints
#         # to avoid the UNIQUE constraint failed: accounts_profile.account_id error, let's do the following
#         self.account = Account.objects.create(
#             account_type="Savings",
#             username="test",
#             email="test@yahoo.com",
#             cc_number="1234567890123456",
#             national_id="22333456",
#             bank_balances=1000,
#             is_blocked=False,
#
#         )
#         self.profile = baker.make(Profile, account=self.account,_quantity=1)
#
#     def test_account_model(self):
#         self.assertEqual(self.account.__str__(), self.account.username)
#
#     def tearDown(self) -> None:
#         del self.account
#         del self.profile
#
#     def test_profile_model(self):
#         self.assertEqual(self.profile.__str__(), self.profile.account.username)
