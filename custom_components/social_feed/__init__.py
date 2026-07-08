"""The Social Feed (X & Bluesky) integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import SocialFeedCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

type SocialFeedConfigEntry = ConfigEntry[SocialFeedCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: SocialFeedConfigEntry
) -> bool:
    """Set up a feed from a config entry."""
    coordinator = SocialFeedCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: SocialFeedConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: SocialFeedConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
