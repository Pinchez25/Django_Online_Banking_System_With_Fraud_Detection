from ..models import TransactionLogs


def create_transaction_logs(sender, receiver, amount, cc_number,rec_cc_number, created, is_fraud):
    TransactionLogs.objects.create(sender=sender, receiver=receiver, amount=amount,
                                   cc_number=cc_number,rec_cc_number=rec_cc_number, date=created, is_fraud=is_fraud)
