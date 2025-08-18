"""
Conflict resolution service for synchronization conflicts in DevPocket API.
"""

from datetime import datetime
from typing import Any

from app.core.logging import logger


class ConflictResolver:
    """Service for resolving synchronization conflicts between devices."""

    def __init__(self) -> None:
        self.supported_strategies = {
            "last_write_wins",
            "merge",
            "user_choice",
            "local_wins",
            "remote_wins",
        }

    async def resolve(
        self,
        local_data: dict[str, Any],
        remote_data: dict[str, Any],
        strategy: str = "last_write_wins",
        user_preference: str | None = None,
        merge_rules: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Resolve conflict between local and remote data using specified strategy.

        Args:
            local_data: The local version of the data
            remote_data: The remote version of the data
            strategy: Resolution strategy to use
            user_preference: For user_choice strategy ("local" or "remote")
            merge_rules: Custom merge rules for complex merge strategies

        Returns:
            The resolved data
        """
        try:
            if strategy not in self.supported_strategies:
                logger.warning(
                    f"Unsupported strategy '{strategy}', using 'last_write_wins'"
                )
                strategy = "last_write_wins"

            if strategy == "last_write_wins":
                return await self._resolve_last_write_wins(local_data, remote_data)
            elif strategy == "merge":
                return await self._resolve_merge(local_data, remote_data, merge_rules)
            elif strategy == "user_choice":
                return await self._resolve_user_choice(
                    local_data, remote_data, user_preference
                )
            elif strategy == "local_wins":
                return local_data
            elif strategy == "remote_wins":
                return remote_data
            else:
                # Fallback to last_write_wins
                return await self._resolve_last_write_wins(local_data, remote_data)

        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")
            # Fallback to local data on error
            return local_data

    async def _resolve_last_write_wins(
        self, local_data: dict[str, Any], remote_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Resolve conflict using last-write-wins strategy."""
        try:
            local_timestamp = self._extract_timestamp(local_data)
            remote_timestamp = self._extract_timestamp(remote_data)

            if remote_timestamp > local_timestamp:
                return remote_data
            else:
                return local_data

        except Exception as e:
            logger.error(f"Error in last_write_wins resolution: {e}")
            return local_data

    async def _resolve_merge(
        self,
        local_data: dict[str, Any],
        remote_data: dict[str, Any],
        merge_rules: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> dict[str, Any]:
        """Resolve conflict using merge strategy."""
        try:
            # Start with local data as base
            merged = local_data.copy()

            # Apply different merge strategies based on data type
            if isinstance(local_data.get("commands"), list) and isinstance(
                remote_data.get("commands"), list
            ):
                # For command lists, merge and deduplicate
                local_commands = set(local_data.get("commands", []))
                remote_commands = set(remote_data.get("commands", []))
                merged["commands"] = list(local_commands.union(remote_commands))

            elif isinstance(local_data.get("ssh_profiles"), list) and isinstance(
                remote_data.get("ssh_profiles"), list
            ):
                # For SSH profiles, merge by name and use latest timestamp
                merged["ssh_profiles"] = await self._merge_ssh_profiles(
                    local_data.get("ssh_profiles", []),
                    remote_data.get("ssh_profiles", []),
                )

            elif isinstance(local_data.get("settings"), dict) and isinstance(
                remote_data.get("settings"), dict
            ):
                # For settings, merge with remote taking precedence for conflicts
                merged_settings = local_data.get("settings", {}).copy()
                merged_settings.update(remote_data.get("settings", {}))
                merged["settings"] = merged_settings

            else:
                # For simple data, remote takes precedence for changed fields
                for key, value in remote_data.items():
                    if key in local_data and local_data[key] != value:
                        # Use remote value for conflicts
                        merged[key] = value
                    elif key not in local_data:
                        # Add new fields from remote
                        merged[key] = value

            # Update timestamp to reflect the merge
            merged["timestamp"] = datetime.now().isoformat()
            merged["merge_timestamp"] = datetime.now().isoformat()

            return merged

        except Exception as e:
            logger.error(f"Error in merge resolution: {e}")
            return local_data

    async def _resolve_user_choice(
        self,
        local_data: dict[str, Any],
        remote_data: dict[str, Any],
        user_preference: str | None,
    ) -> dict[str, Any]:
        """Resolve conflict based on user's choice."""
        try:
            if user_preference == "remote":
                return remote_data
            elif user_preference == "local":
                return local_data
            else:
                # Default to local if no preference specified
                logger.warning("No user preference specified, defaulting to local")
                return local_data

        except Exception as e:
            logger.error(f"Error in user_choice resolution: {e}")
            return local_data

    async def _merge_ssh_profiles(
        self, local_profiles: list[dict], remote_profiles: list[dict]
    ) -> list[dict]:
        """Merge SSH profiles by name, using latest timestamp for conflicts."""
        try:
            merged_profiles = {}

            # Process local profiles
            for profile in local_profiles:
                name = profile.get("name", "")
                if name:
                    merged_profiles[name] = profile

            # Process remote profiles, overriding if newer
            for profile in remote_profiles:
                name = profile.get("name", "")
                if name:
                    if name in merged_profiles:
                        local_timestamp = self._extract_timestamp(merged_profiles[name])
                        remote_timestamp = self._extract_timestamp(profile)
                        if remote_timestamp > local_timestamp:
                            merged_profiles[name] = profile
                    else:
                        merged_profiles[name] = profile

            return list(merged_profiles.values())

        except Exception as e:
            logger.error(f"Error merging SSH profiles: {e}")
            return local_profiles

    def _extract_timestamp(self, data: dict[str, Any]) -> datetime:
        """Extract timestamp from data, with fallbacks."""
        try:
            # Try different timestamp fields
            timestamp_fields = [
                "timestamp",
                "modified_at",
                "updated_at",
                "last_modified_at",
                "created_at",
            ]

            for field in timestamp_fields:
                if field in data and data[field]:
                    timestamp_str = data[field]
                    if isinstance(timestamp_str, str):
                        # Try to parse ISO format
                        try:
                            # Handle both Z and +00:00 timezone formats
                            if timestamp_str.endswith("Z"):
                                timestamp_str = timestamp_str[:-1] + "+00:00"
                            return datetime.fromisoformat(timestamp_str)
                        except ValueError:
                            continue

            # Fallback to epoch start if no valid timestamp found
            return datetime.min

        except Exception as e:
            logger.error(f"Error extracting timestamp: {e}")
            return datetime.min

    async def detect_conflicts(
        self, local_data: dict[str, Any], remote_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Detect and categorize conflicts between local and remote data."""
        try:
            conflicts: dict[str, Any] = {
                "has_conflicts": False,
                "conflict_type": None,
                "conflicting_fields": [],
                "resolution_suggestions": [],
            }

            # Check for version conflicts
            local_version = local_data.get("version", 1)
            remote_version = remote_data.get("version", 1)

            if local_version != remote_version:
                conflicts["has_conflicts"] = True
                conflicts["conflict_type"] = "version_mismatch"
                conflicts["conflicting_fields"].append("version")

            # Check for data field conflicts
            for key in set(local_data.keys()).union(set(remote_data.keys())):
                if key in ["timestamp", "modified_at", "version"]:
                    continue  # Skip metadata fields

                local_value = local_data.get(key)
                remote_value = remote_data.get(key)

                if local_value != remote_value:
                    conflicts["has_conflicts"] = True
                    conflicts["conflicting_fields"].append(key)

            # Suggest resolution strategies
            if conflicts["has_conflicts"]:
                local_timestamp = self._extract_timestamp(local_data)
                remote_timestamp = self._extract_timestamp(remote_data)

                if remote_timestamp > local_timestamp:
                    conflicts["resolution_suggestions"].append("remote_wins")
                elif local_timestamp > remote_timestamp:
                    conflicts["resolution_suggestions"].append("local_wins")
                else:
                    conflicts["resolution_suggestions"].append("user_choice")

                # Always suggest merge for complex data
                if len(conflicts["conflicting_fields"]) > 1:
                    conflicts["resolution_suggestions"].append("merge")

            return conflicts

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return {"has_conflicts": False, "error": str(e)}

    async def create_conflict_report(
        self,
        local_data: dict[str, Any],
        remote_data: dict[str, Any],
        sync_key: str,
    ) -> dict[str, Any]:
        """Create a detailed conflict report for user review."""
        try:
            conflicts = await self.detect_conflicts(local_data, remote_data)

            report = {
                "sync_key": sync_key,
                "conflict_id": f"conflict_{sync_key}_{datetime.now().isoformat()}",
                "detected_at": datetime.now().isoformat(),
                "local_data": local_data,
                "remote_data": remote_data,
                "conflicts": conflicts,
                "recommended_strategy": "last_write_wins",
            }

            # Determine recommended strategy
            if conflicts.get("resolution_suggestions"):
                report["recommended_strategy"] = conflicts["resolution_suggestions"][0]

            return report

        except Exception as e:
            logger.error(f"Error creating conflict report: {e}")
            return {"error": str(e)}

    async def resolve_conflict_automatically(
        self, conflict_report: dict[str, Any]
    ) -> dict[str, Any]:
        """Automatically resolve a conflict using the recommended strategy."""
        try:
            local_data = conflict_report["local_data"]
            remote_data = conflict_report["remote_data"]
            strategy = conflict_report.get("recommended_strategy", "last_write_wins")

            resolved_data = await self.resolve(local_data, remote_data, strategy)

            return {
                "conflict_id": conflict_report["conflict_id"],
                "resolved_at": datetime.now().isoformat(),
                "strategy_used": strategy,
                "resolved_data": resolved_data,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error auto-resolving conflict: {e}")
            return {"success": False, "error": str(e)}
