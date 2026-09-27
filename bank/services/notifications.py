import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from bank.models import Notification

logger = logging.getLogger(__name__)


def create_alert(*, recipient, title, body, level=Notification.Level.INFO):
    return Notification.objects.create(
        recipient=recipient,
        kind=Notification.Kind.ALERT,
        level=level,
        title=title,
        body=body,
    )


def serialize_notification(notification):
    return {
        "id": str(notification.pk),
        "kind": notification.kind,
        "level": notification.level,
        "sender_name": notification.sender_name,
        "title": notification.title,
        "body": notification.body,
        "created_at": notification.created_at.isoformat(),
    }


def notification_snapshot(user_id):
    notifications = Notification.objects.filter(
        recipient_id=user_id,
        read_at__isnull=True,
    )
    items = {kind: [] for kind in Notification.Kind.values}
    counts = {}
    for kind in Notification.Kind.values:
        counts[kind] = notifications.filter(kind=kind).count()
        items[kind] = [
            serialize_notification(notification)
            for notification in notifications.filter(kind=kind)[:5]
        ]
    return {"type": "notifications.snapshot", "counts": counts, "items": items}


def publish_notification(notification):
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        unread_count = Notification.objects.filter(
            recipient_id=notification.recipient_id,
            kind=notification.kind,
            read_at__isnull=True,
        ).count()
        async_to_sync(channel_layer.group_send)(
            f"notifications_{notification.recipient_id}",
            {
                "type": "notification.created",
                "notification": serialize_notification(notification),
                "unread_count": unread_count,
            },
        )
    except Exception:
        logger.exception("Unable to publish notification %s over WebSocket", notification.pk)


def publish_notification_snapshot(user_id):
    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        async_to_sync(channel_layer.group_send)(
            f"notifications_{user_id}",
            {"type": "notifications.refresh"},
        )
    except Exception:
        logger.exception("Unable to refresh notifications for account %s", user_id)