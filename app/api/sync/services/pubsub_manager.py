"""
Redis pub/sub manager for real-time synchronization notifications.
"""

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID as PyUUID

import redis.asyncio as aioredis

from app.core.logging import logger


class PubSubManager:
    """Manager for Redis pub/sub operations for real-time sync notifications."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.redis_client = redis_client
        self._subscribers: dict[str, Callable] = {}

    async def subscribe_user_sync(
        self, user_id: str | PyUUID, callback: Callable[[dict], None] | None = None
    ) -> None:
        """Subscribe to sync notifications for a specific user."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}"

            if self.redis_client:
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe(channel)

                if callback:
                    self._subscribers[channel] = callback

                logger.info(f"Subscribed to sync channel: {channel}")

        except Exception as e:
            logger.error(f"Error subscribing to user sync: {e}")
            raise

    async def unsubscribe_user_sync(self, user_id: str | PyUUID) -> None:
        """Unsubscribe from sync notifications for a specific user."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}"

            if self.redis_client:
                pubsub = self.redis_client.pubsub()
                await pubsub.unsubscribe(channel)

                if channel in self._subscribers:
                    del self._subscribers[channel]

                logger.info(f"Unsubscribed from sync channel: {channel}")

        except Exception as e:
            logger.error(f"Error unsubscribing from user sync: {e}")
            raise

    async def publish_sync_update(
        self, user_id: str | PyUUID, sync_data: dict[str, Any]
    ) -> bool:
        """Publish a sync update notification to all user's devices."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}"
            message = {
                "type": "sync_update",
                "user_id": user_id,
                "sync_data": sync_data,
                "timestamp": sync_data.get("timestamp", ""),
                "device_id": sync_data.get("device_id", ""),
            }

            if self.redis_client:
                await self.redis_client.publish(channel, json.dumps(message))
                logger.debug(f"Published sync update to channel: {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error publishing sync update: {e}")
            raise

    async def publish_conflict_notification(
        self,
        user_id: str | PyUUID,
        conflict_data: dict[str, Any],
        sync_key: str,
    ) -> bool:
        """Publish a conflict notification to user's devices."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}"
            message = {
                "type": "sync_conflict",
                "user_id": user_id,
                "sync_key": sync_key,
                "conflict_data": conflict_data,
                "timestamp": conflict_data.get("timestamp", ""),
            }

            if self.redis_client:
                await self.redis_client.publish(channel, json.dumps(message))
                logger.debug(f"Published conflict notification to channel: {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error publishing conflict notification: {e}")
            raise

    async def publish_device_status(
        self, user_id: str | PyUUID, device_id: str, status: str
    ) -> bool:
        """Publish device online/offline status to other devices."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}"
            message = {
                "type": "device_status",
                "user_id": user_id,
                "device_id": device_id,
                "status": status,  # "online", "offline"
                "timestamp": str(datetime.now().isoformat()),
            }

            if self.redis_client:
                await self.redis_client.publish(channel, json.dumps(message))
                logger.debug(f"Published device status to channel: {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error publishing device status: {e}")
            raise

    async def subscribe_device_channel(
        self,
        user_id: str | PyUUID,
        device_id: str,
        callback: Callable[[dict], None] | None = None,
    ) -> None:
        """Subscribe to device-specific sync notifications."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}:device:{device_id}"

            if self.redis_client:
                pubsub = self.redis_client.pubsub()
                await pubsub.subscribe(channel)

                if callback:
                    self._subscribers[channel] = callback

                logger.info(f"Subscribed to device channel: {channel}")

        except Exception as e:
            logger.error(f"Error subscribing to device channel: {e}")
            raise

    async def publish_to_device(
        self, user_id: str | PyUUID, device_id: str, message_data: dict[str, Any]
    ) -> bool:
        """Publish a message to a specific device."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            channel = f"sync:user:{user_id}:device:{device_id}"
            message = {
                "type": "device_message",
                "user_id": user_id,
                "device_id": device_id,
                "data": message_data,
                "timestamp": str(datetime.now().isoformat()),
            }

            if self.redis_client:
                await self.redis_client.publish(channel, json.dumps(message))
                logger.debug(f"Published message to device channel: {channel}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error publishing to device: {e}")
            raise

    async def listen_for_messages(self) -> None:
        """Listen for incoming pub/sub messages and route to callbacks."""
        if not self.redis_client:
            return

        try:
            pubsub = self.redis_client.pubsub()

            async for message in pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])

                    if channel in self._subscribers:
                        callback = self._subscribers[channel]
                        try:
                            await callback(data) if callable(callback) else None
                        except Exception as e:
                            logger.error(f"Error in message callback: {e}")

        except Exception as e:
            logger.error(f"Error listening for messages: {e}")
            raise

    async def get_active_devices(self, user_id: str | PyUUID) -> list[str]:
        """Get list of active devices for a user based on recent activity."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            # Use Redis to track active devices (simple implementation)
            if self.redis_client:
                devices = await self.redis_client.smembers(f"active_devices:{user_id}")
                return list(devices) if devices else []

            return []

        except Exception as e:
            logger.error(f"Error getting active devices: {e}")
            return []

    async def register_device_activity(
        self, user_id: str | PyUUID, device_id: str, ttl: int = 3600
    ) -> None:
        """Register device activity with TTL for auto-cleanup."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            active_devices_key = f"active_devices:{user_id}"

            if self.redis_client:
                await self.redis_client.sadd(active_devices_key, device_id)
                await self.redis_client.expire(active_devices_key, ttl)

        except Exception as e:
            logger.error(f"Error registering device activity: {e}")

    async def cleanup_inactive_devices(self, user_id: str | PyUUID) -> None:
        """Clean up inactive devices from the active list."""
        try:
            if isinstance(user_id, PyUUID):
                user_id = str(user_id)

            if self.redis_client:
                # Redis TTL will handle automatic cleanup
                # This method can be extended for more complex cleanup logic
                pass

        except Exception as e:
            logger.error(f"Error cleaning up inactive devices: {e}")
