from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.test import TransactionTestCase, override_settings

from bank.consumers import NotificationConsumer
from bank.models import Notification


@override_settings(
    CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
    },
)
class NotificationConsumerTests(TransactionTestCase):
    def setUp(self):
        account_model = get_user_model()
        self.account = account_model.objects.create_user(
            username="socket-user",
            email="socket-user@example.com",
            password="password123",
            national_id=51001,
        )
        self.other_account = account_model.objects.create_user(
            username="other-socket-user",
            email="other-socket-user@example.com",
            password="password123",
            national_id=51002,
        )

    def test_notification_is_delivered_only_to_its_recipient(self):
        async_to_sync(self._assert_recipient_delivery)()

    async def _assert_recipient_delivery(self):
        recipient_socket = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
        other_socket = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
        recipient_socket.scope["user"] = self.account
        other_socket.scope["user"] = self.other_account

        try:
            recipient_connected, _ = await recipient_socket.connect()
            other_connected, _ = await other_socket.connect()
            self.assertTrue(recipient_connected)
            self.assertTrue(other_connected)
            self.assertEqual(
                (await recipient_socket.receive_json_from())["type"],
                "notifications.snapshot",
            )
            await other_socket.receive_json_from()

            await database_sync_to_async(database_create_notification)(self.account)

            event = await recipient_socket.receive_json_from(timeout=1)
            self.assertEqual(event["type"], "notifications.created")
            self.assertEqual(event["notification"]["title"], "Transfer received")
            self.assertTrue(await other_socket.receive_nothing(timeout=0.1))

            await database_sync_to_async(database_mark_notification_read)(
                event["notification"]["id"]
            )
            refreshed = await recipient_socket.receive_json_from(timeout=1)
            self.assertEqual(refreshed["type"], "notifications.snapshot")
            self.assertEqual(refreshed["counts"][Notification.Kind.ALERT], 0)
            self.assertEqual(refreshed["items"][Notification.Kind.ALERT], [])
            self.assertTrue(await other_socket.receive_nothing(timeout=0.1))
        finally:
            await recipient_socket.disconnect()
            await other_socket.disconnect()

    def test_anonymous_socket_is_rejected(self):
        async_to_sync(self._assert_anonymous_rejected)()

    async def _assert_anonymous_rejected(self):
        communicator = WebsocketCommunicator(NotificationConsumer.as_asgi(), "/ws/notifications/")
        communicator.scope["user"] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertFalse(connected)


@transaction.atomic
def database_create_notification(recipient):
    return Notification.objects.create(
        recipient=recipient,
        kind=Notification.Kind.ALERT,
        level=Notification.Level.SUCCESS,
        title="Transfer received",
        body="KES 100.00 was received.",
    )


@transaction.atomic
def database_mark_notification_read(notification_id):
    notification = Notification.objects.get(pk=notification_id)
    notification.read_at = notification.created_at
    notification.save(update_fields=["read_at"])