from __future__ import annotations

from django.utils import timezone

from bank.models import Notification


def get_dashboard_data(user):
    profile = getattr(user, "profile", None)

    unread_alerts = Notification.objects.filter(
        recipient=user,
        kind=Notification.Kind.ALERT,
        read_at__isnull=True,
    )
    unread_messages = Notification.objects.filter(
        recipient=user,
        kind=Notification.Kind.MESSAGE,
        read_at__isnull=True,
    )

    transactions = (
        user.transactions.select_related("account", "recipient", "approved_by")
        .all()[:10]
    )

    return {
        "summary": {
            "total_balance": str(user.bank_balances),
            "balance_change": "0%",
            "account_number": "N/A",
            "account_type": "Personal account",
            "savings_total": "0.00",
            "savings_goal": "0 active goals",
            "loans_total": "0.00",
            "loan_due": "N/A",
            "national_id": str(user.national_id) if user.national_id is not None else "N/A",
        },
        "alerts": unread_alerts[:5],
        "alerts_unread_count": unread_alerts.count(),
        "messages_list": unread_messages[:5],
        "messages_unread_count": unread_messages.count(),
        "transactions": transactions,
        "cards": [],
        "spending": {
            "total": "0",
            "categories": [],
        },
        "beneficiaries": [],
        "profile": {
            "first_name": profile.first_name if profile else "",
            "last_name": profile.last_name if profile else "",
            "email": user.email,
        },
        "notification_settings": [
            {"label": "Transaction alerts", "hint": "Get notified for every debit or credit", "enabled": True},
            {"label": "Low balance warnings", "hint": "Alert when balance drops below KES 5,000", "enabled": True},
            {"label": "Marketing emails", "hint": "Product news, offers and surveys", "enabled": False},
            {"label": "SMS notifications", "hint": "Mirror alerts to your registered phone number", "enabled": True},
        ],
        "security": {
            "password_changed": "N/A",
            "two_factor_enabled": False,
            "biometric_enabled": False,
        },
        "preferences": {"currency": "KES", "language": "English", "statement_delivery": "Email"},
    }


def get_dashboard_context(request, **extra):
    user_data = get_dashboard_data(request.user)
    context = {
        "summary": user_data["summary"],
        "alerts": user_data["alerts"],
        "alerts_unread_count": user_data["alerts_unread_count"],
        "messages_list": user_data["messages_list"],
        "messages_unread_count": user_data["messages_unread_count"],
        "transactions": user_data["transactions"],
        "cards": user_data["cards"],
        "spending": user_data["spending"],
        "beneficiaries": user_data["beneficiaries"],
        "profile": user_data["profile"],
        "current_year": timezone.now().year,
        "today": timezone.now().strftime("%A, %d %B %Y"),
        "notification_settings": user_data["notification_settings"],
        "security": user_data["security"],
        "preferences": user_data["preferences"],
    }
    context.update(extra)
    return context
