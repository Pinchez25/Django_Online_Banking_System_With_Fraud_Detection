from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from bank.services.notifications import notification_snapshot


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated or not user.is_active:
            await self.close(code=4401)
            return

        self.group_name = f"notifications_{user.pk}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json(await self.get_snapshot(user.pk))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_created(self, event):
        await self.send_json(
            {
                "type": "notifications.created",
                "notification": event["notification"],
                "unread_count": event["unread_count"],
            }
        )

    async def notifications_refresh(self, event):
        await self.send_json(await self.get_snapshot(self.scope["user"].pk))

    @database_sync_to_async
    def get_snapshot(self, user_id):
        return notification_snapshot(user_id)