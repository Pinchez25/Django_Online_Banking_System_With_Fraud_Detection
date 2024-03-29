# Generated by Django 4.1.1 on 2022-11-22 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bank", "0003_alter_transaction_date"),
    ]

    operations = [
        migrations.CreateModel(
            name="TransactionLogs",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sender",
                    models.CharField(
                        blank=True, max_length=16, null=True, verbose_name="Sender"
                    ),
                ),
                (
                    "receiver",
                    models.CharField(
                        blank=True, max_length=16, null=True, verbose_name="Receiver"
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="Amount"
                    ),
                ),
                (
                    "cc_number",
                    models.CharField(
                        blank=True,
                        max_length=16,
                        null=True,
                        verbose_name="Credit Card Number",
                    ),
                ),
                ("date", models.DateTimeField(verbose_name="Date")),
                ("is_fraud", models.IntegerField(default=0, verbose_name="Fraud")),
            ],
        ),
    ]
