# from django.db.models.signals import post_save
# from django.dispatch import receiver
# from .models import TransactionLogs, Transaction
#
#
# @receiver(post_save, sender=Transaction)
# def create_transaction_logs(sender, instance, created, **kwargs):
#     if created:
#         TransactionLogs.objects.create(sender=instance.account, receiver=instance.account, amount=instance.amount,
#                                        date=instance.date)
