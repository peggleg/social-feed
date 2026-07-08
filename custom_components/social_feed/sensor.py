"""Sensor platform for the Social Feed integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import SocialFeedConfigEntry
from .const import DOMAIN, PLATFORM_NAMES
from .coordinator import SocialFeedCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SocialFeedConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the feed sensor for a config entry."""
    async_add_entities([SocialFeedSensor(entry.runtime_data, entry)])


class SocialFeedSensor(CoordinatorEntity[SocialFeedCoordinator], SensorEntity):
    """State = text of the newest post. Full feed lives in attributes."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_icon = "mdi:message-text"

    def __init__(
        self, coordinator: SocialFeedCoordinator, entry: SocialFeedConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id
        platform_name = PLATFORM_NAMES[coordinator.feed_platform]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"{coordinator.handle} ({platform_name})",
            manufacturer=platform_name,
            model="Social Feed",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self) -> str | None:
        """Text of the latest post, truncated to HA's 255-char state limit."""
        posts = self.coordinator.data.get("posts", [])
        if not posts:
            return None
        text = posts[0].get("text", "") or ""
        return text[:252] + "..." if len(text) > 255 else text

    @property
    def entity_picture(self) -> str | None:
        return self.coordinator.data.get("author", {}).get("avatar")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        posts = data.get("posts", [])
        author = data.get("author", {})

        latest: dict[str, Any] = posts[0] if posts else {}
        latest_dt: datetime | None = None
        if latest.get("created_at"):
            latest_dt = dt_util.parse_datetime(latest["created_at"])

        return {
            "platform": PLATFORM_NAMES[self.coordinator.feed_platform],
            "handle": self.coordinator.handle,
            "display_name": author.get("display_name"),
            "latest_post_id": latest.get("id"),
            "latest_post_url": latest.get("url"),
            "latest_post_time": latest_dt,
            "post_count": len(posts),
            "posts": posts,
        }
