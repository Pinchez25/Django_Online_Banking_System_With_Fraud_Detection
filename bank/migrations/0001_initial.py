# Generated by Django 4.1.1 on 2022-09-12 16:13

import bank.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaction",
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
                    "transaction_id",
                    models.CharField(
                        default=bank.models.generate_unique_id,
                        max_length=16,
                        unique=True,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("D", "Deposit"),
                            ("W", "Withdrawal"),
                            ("T", "Transfer"),
                        ],
                        max_length=1,
                        verbose_name="Type of Transaction",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2, max_digits=12, verbose_name="Amount"
                    ),
                ),
                ("date", models.DateField(auto_now=True)),
                (
                    "customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="accounts.customer",
                    ),
                ),
            ],
        ),
    ]