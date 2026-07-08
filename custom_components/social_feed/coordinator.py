"""DataUpdateCoordinator for the Social Feed integration."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    AuthFailed,
    FeedError,
    RateLimited,
    fetch_bluesky_feed,
    fetch_mastodon_feed,
    fetch_x_feed,
)
from .const import (
    CONF_BEARER_TOKEN,
    CONF_FEED_PLATFORM,
    CONF_HANDLE,
    CONF_MAX_POSTS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MAX_POSTS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORM_MASTODON,
    PLATFORM_X,
)

_LOGGER = logging.getLogger(__name__)


class SocialFeedCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches one profile's feed on a schedule."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.feed_platform: str = entry.data[CONF_FEED_PLATFORM]
        self.handle: str = entry.data[CONF_HANDLE]

        interval = entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL[self.feed_platform]
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{self.feed_platform}_{self.handle}",
            update_interval=timedelta(minutes=interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        max_posts = self.entry.options.get(CONF_MAX_POSTS, DEFAULT_MAX_POSTS)

        try:
            if self.feed_platform == PLATFORM_X:
                return await fetch_x_feed(
                    session,
                    self.handle,
                    self.entry.data[CONF_BEARER_TOKEN],
                    max_posts,
                )
            if self.feed_platform == PLATFORM_MASTODON:
                return await fetch_mastodon_feed(
                    session, self.handle, max_posts
                )
            return await fetch_bluesky_feed(session, self.handle, max_posts)
        except AuthFailed as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RateLimited as err:
            # Keep the last known data; just log and retry next cycle.
            raise UpdateFailed(f"Rate limited: {err}") from err
        except FeedError as err:
            raise UpdateFailed(str(err)) from err
