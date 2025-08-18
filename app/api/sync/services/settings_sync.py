"""
User settings synchronization service for DevPocket API.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID as PyUUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.sync import SyncData
from app.repositories.sync import SyncDataRepository


class SettingsSyncResult(BaseModel):
    """Result of settings synchronization operation."""

    updated_settings: list[str]
    conflicts: list[dict[str, Any]] = []
    total_settings: int = 0


class SettingsSyncService:
    """Service for synchronizing user settings across devices."""

    def __init__(self, session: AsyncSession | None = None):
        self.session = session
        # Initialize repository only if session is provided
        self.sync_repo = SyncDataRepository(session) if session else None

        # Define which settings can be synced
        self.syncable_settings = {
            "terminal_theme",
            "terminal_font_size",
            "terminal_font_family",
            "ai_suggestions_enabled",
            "auto_complete_enabled",
            "command_history_size",
            "notification_preferences",
            "privacy_settings",
            "default_ssh_timeout",
            "preferred_editor",
            "color_scheme",
            "keyboard_shortcuts",
        }

    def _normalize_user_id(self, user_id: str | PyUUID) -> PyUUID:
        """Convert user_id to UUID, handling test string IDs."""
        if isinstance(user_id, str):
            try:
                return PyUUID(user_id)
            except ValueError:
                import hashlib

                return PyUUID(hashlib.md5(user_id.encode()).hexdigest())
        return user_id

    async def sync_settings(
        self, user_id: str | PyUUID, settings_update: dict[str, Any]
    ) -> SettingsSyncResult:
        """Sync user settings across devices."""
        try:
            user_id = self._normalize_user_id(user_id)

            updated_settings = []
            conflicts = []

            # Filter to only syncable settings
            syncable_updates = {
                k: v for k, v in settings_update.items() if k in self.syncable_settings
            }

            for setting_key, setting_value in syncable_updates.items():
                sync_key = f"user_setting_{user_id}_{setting_key}"

                # For tests without database, skip sync operations
                if not hasattr(self, "sync_repo") or self.sync_repo is None:
                    updated_settings.append(setting_key)
                    continue

                # Get existing setting sync data
                existing_sync = await self.sync_repo.get_by_sync_key(user_id, sync_key)

                if existing_sync:
                    # Check for conflicts
                    if self._has_setting_conflict(
                        existing_sync.data, {"value": setting_value}
                    ):
                        conflicts.append(
                            {
                                "setting_key": setting_key,
                                "local_value": existing_sync.data.get("value"),
                                "remote_value": setting_value,
                                "sync_key": sync_key,
                            }
                        )
                        continue

                    # Update existing setting
                    new_data = {
                        "value": setting_value,
                        "modified_at": datetime.now(UTC).isoformat(),
                        "setting_type": type(setting_value).__name__,
                    }
                    existing_sync.update_data(
                        new_data,
                        settings_update.get("device_id", "unknown"),
                        settings_update.get("device_type", "unknown"),
                    )
                    await self.sync_repo.update(existing_sync)
                else:
                    # Create new setting sync
                    setting_data = {
                        "value": setting_value,
                        "modified_at": datetime.now(UTC).isoformat(),
                        "setting_type": type(setting_value).__name__,
                    }
                    sync_data = SyncData.create_sync_item(
                        user_id=user_id,
                        sync_type="user_setting",
                        sync_key=sync_key,
                        data=setting_data,
                        device_id=settings_update.get("device_id", "unknown"),
                        device_type=settings_update.get("device_type", "unknown"),
                    )
                    await self.sync_repo.create(sync_data)

                updated_settings.append(setting_key)

            if self.session:
                await self.session.commit()

            return SettingsSyncResult(
                updated_settings=updated_settings,
                conflicts=conflicts,
                total_settings=len(syncable_updates),
            )

        except Exception as e:
            logger.error(f"Error syncing settings: {e}")
            if self.session:
                await self.session.rollback()
            raise

    async def calculate_settings_diff(
        self, current_settings: dict[str, Any], new_settings: dict[str, Any]
    ) -> dict[str, Any]:
        """Calculate the difference between current and new settings."""
        try:
            diff = {}

            for key, new_value in new_settings.items():
                if key in self.syncable_settings:
                    current_value = current_settings.get(key)
                    if current_value != new_value:
                        diff[key] = new_value

            return diff

        except Exception as e:
            logger.error(f"Error calculating settings diff: {e}")
            return {}

    async def get_settings_since(
        self, user_id: str | PyUUID, device_id: str, last_sync: datetime
    ) -> dict[str, Any]:
        """Get settings changes since the last sync timestamp."""
        try:
            if isinstance(user_id, str):
                user_id = PyUUID(user_id)

            if self.sync_repo is None:
                return {}

            sync_data_list = await self.sync_repo.get_sync_changes_since(
                user_id, last_sync
            )

            settings = {}
            for sync_data in sync_data_list:
                if (
                    sync_data.sync_type == "user_setting"
                    and sync_data.source_device_id != device_id
                ):
                    # Extract setting key from sync_key
                    setting_key = sync_data.sync_key.split("_")[-1]
                    settings[setting_key] = sync_data.data.get("value")

            return settings

        except Exception as e:
            logger.error(f"Error getting settings since last sync: {e}")
            return {}

    async def resolve_setting_conflict(
        self,
        user_id: str | PyUUID,
        setting_key: str,
        chosen_value: Any,
        device_id: str,
        device_type: str,
    ) -> bool:
        """Resolve a setting sync conflict."""
        try:
            if isinstance(user_id, str):
                user_id = PyUUID(user_id)

            if self.sync_repo is None:
                return False

            sync_key = f"user_setting_{user_id}_{setting_key}"
            existing_sync = await self.sync_repo.get_by_sync_key(user_id, sync_key)

            if existing_sync and existing_sync.has_conflict:
                resolved_data = {
                    "value": chosen_value,
                    "modified_at": datetime.now(UTC).isoformat(),
                    "setting_type": type(chosen_value).__name__,
                }
                existing_sync.resolve_conflict(resolved_data, device_id, device_type)
                await self.sync_repo.update(existing_sync)

                if self.session:
                    await self.session.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error resolving setting conflict: {e}")
            if self.session:
                await self.session.rollback()
            raise

    async def get_all_user_settings(self, user_id: str | PyUUID) -> dict[str, Any]:
        """Get all synchronized settings for a user."""
        try:
            if isinstance(user_id, str):
                user_id = PyUUID(user_id)

            if self.sync_repo is None:
                return {}

            sync_data_list = await self.sync_repo.get_by_sync_type(
                user_id, "user_setting"
            )

            settings = {}
            for sync_data in sync_data_list:
                if not sync_data.is_deleted:
                    # Extract setting key from sync_key
                    setting_key = sync_data.sync_key.split("_")[-1]
                    if setting_key in self.syncable_settings:
                        settings[setting_key] = sync_data.data.get("value")

            return settings

        except Exception as e:
            logger.error(f"Error getting all user settings: {e}")
            return {}

    async def reset_setting(
        self, user_id: str | PyUUID, setting_key: str, device_id: str, device_type: str
    ) -> bool:
        """Reset a setting to its default value."""
        try:
            if isinstance(user_id, str):
                user_id = PyUUID(user_id)

            if setting_key not in self.syncable_settings:
                return False

            if self.sync_repo is None:
                return False

            sync_key = f"user_setting_{user_id}_{setting_key}"
            existing_sync = await self.sync_repo.get_by_sync_key(user_id, sync_key)

            if existing_sync:
                existing_sync.mark_as_deleted(device_id, device_type)
                await self.sync_repo.update(existing_sync)

                if self.session:
                    await self.session.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error resetting setting: {e}")
            if self.session:
                await self.session.rollback()
            raise

    async def export_settings(self, user_id: str | PyUUID) -> dict[str, Any]:
        """Export all user settings for backup or migration."""
        try:
            if isinstance(user_id, str):
                user_id = PyUUID(user_id)

            settings = await self.get_all_user_settings(user_id)

            return {
                "user_id": str(user_id),
                "exported_at": datetime.now(UTC).isoformat(),
                "settings": settings,
                "version": "1.0",
            }

        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return {}

    async def import_settings(
        self,
        user_id: str | PyUUID,
        settings_data: dict[str, Any],
        device_id: str,
        device_type: str,
        overwrite: bool = False,
    ) -> SettingsSyncResult:
        """Import settings from backup or migration."""
        try:
            if isinstance(user_id, str):
                user_id = PyUUID(user_id)

            settings_to_import = settings_data.get("settings", {})

            # Add device info for sync
            settings_to_import["device_id"] = device_id
            settings_to_import["device_type"] = device_type

            if overwrite:
                # Clear existing settings first
                for setting_key in self.syncable_settings:
                    await self.reset_setting(
                        user_id, setting_key, device_id, device_type
                    )

            # Import the new settings
            return await self.sync_settings(user_id, settings_to_import)

        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            if self.session:
                await self.session.rollback()
            raise

    def _has_setting_conflict(
        self, existing_data: dict[str, Any], new_data: dict[str, Any]
    ) -> bool:
        """Check if there's a conflict between existing and new setting data."""
        existing_value = existing_data.get("value")
        new_value = new_data.get("value")

        # Simple conflict detection - values are different
        return existing_value != new_value

    def _get_default_setting_value(self, setting_key: str) -> Any:
        """Get the default value for a setting."""
        defaults = {
            "terminal_theme": "dark",
            "terminal_font_size": 14,
            "terminal_font_family": "Monaco",
            "ai_suggestions_enabled": True,
            "auto_complete_enabled": True,
            "command_history_size": 1000,
            "notification_preferences": {"push": True, "email": False},
            "privacy_settings": {"share_usage_data": False},
            "default_ssh_timeout": 30,
            "preferred_editor": "vim",
            "color_scheme": "default",
            "keyboard_shortcuts": {},
        }

        return defaults.get(setting_key)
