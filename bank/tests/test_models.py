from ..models import Transaction
from django.test import TestCase
from model_bakery import baker


class TestTransactionModel(TestCase):
    def setUp(self):
        self.transaction = baker.make(Transaction)

    def test_transaction_model(self):
        self.assertEqual(self.transaction.__str__(), self.transaction.transaction_id)

