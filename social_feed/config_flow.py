"""Config flow for the Social Feed integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    AuthFailed,
    FeedError,
    ProfileNotFound,
    RateLimited,
    fetch_bluesky_feed,
    fetch_mastodon_feed,
    fetch_x_feed,
    normalize_handle,
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
    PLATFORM_BLUESKY,
    PLATFORM_MASTODON,
    PLATFORM_NAMES,
    PLATFORM_X,
)

_LOGGER = logging.getLogger(__name__)


class SocialFeedConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow. Each entry is one feed; add the

    integration multiple times to follow multiple profiles."""

    VERSION = 1

    def __init__(self) -> None:
        self._platform: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: pick the platform from a dropdown."""
        if user_input is not None:
            self._platform = user_input[CONF_FEED_PLATFORM]
            if self._platform == PLATFORM_X:
                return await self.async_step_x()
            if self._platform == PLATFORM_MASTODON:
                return await self.async_step_mastodon()
            return await self.async_step_bluesky()

        schema = vol.Schema(
            {
                vol.Required(CONF_FEED_PLATFORM): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            SelectOptionDict(
                                value=PLATFORM_BLUESKY, label="Bluesky"
                            ),
                            SelectOptionDict(
                                value=PLATFORM_MASTODON, label="Mastodon"
                            ),
                            SelectOptionDict(
                                value=PLATFORM_X, label="X (Twitter)"
                            ),
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_bluesky(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 (Bluesky): just ask for the profile handle."""
        errors: dict[str, str] = {}

        if user_input is not None:
            handle = normalize_handle(user_input[CONF_HANDLE], PLATFORM_BLUESKY)
            await self.async_set_unique_id(f"{PLATFORM_BLUESKY}_{handle.lower()}")
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                result = await fetch_bluesky_feed(session, handle, 1)
            except ProfileNotFound:
                errors["base"] = "profile_not_found"
            except RateLimited:
                errors["base"] = "rate_limited"
            except FeedError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Bluesky handle")
                errors["base"] = "unknown"
            else:
                name = result["author"].get("display_name") or handle
                return self.async_create_entry(
                    title=f"{name} ({PLATFORM_NAMES[PLATFORM_BLUESKY]})",
                    data={
                        CONF_FEED_PLATFORM: PLATFORM_BLUESKY,
                        CONF_HANDLE: handle,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HANDLE): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                )
            }
        )
        return self.async_show_form(
            step_id="bluesky", data_schema=schema, errors=errors
        )

    async def async_step_mastodon(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 (Mastodon): ask for the handle (user@instance)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            handle = normalize_handle(
                user_input[CONF_HANDLE], PLATFORM_MASTODON
            )
            await self.async_set_unique_id(
                f"{PLATFORM_MASTODON}_{handle.lower()}"
            )
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                result = await fetch_mastodon_feed(session, handle, 1)
            except ProfileNotFound:
                errors["base"] = "profile_not_found"
            except RateLimited:
                errors["base"] = "rate_limited"
            except FeedError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating Mastodon handle")
                errors["base"] = "unknown"
            else:
                name = result["author"].get("display_name") or handle
                return self.async_create_entry(
                    title=f"{name} ({PLATFORM_NAMES[PLATFORM_MASTODON]})",
                    data={
                        CONF_FEED_PLATFORM: PLATFORM_MASTODON,
                        CONF_HANDLE: handle,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HANDLE): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                )
            }
        )
        return self.async_show_form(
            step_id="mastodon", data_schema=schema, errors=errors
        )

    async def async_step_x(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2 (X): ask for the handle and an API bearer token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            handle = normalize_handle(user_input[CONF_HANDLE], PLATFORM_X)
            token = user_input[CONF_BEARER_TOKEN].strip()
            await self.async_set_unique_id(f"{PLATFORM_X}_{handle.lower()}")
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            try:
                result = await fetch_x_feed(session, handle, token, 5)
            except ProfileNotFound:
                errors["base"] = "profile_not_found"
            except AuthFailed:
                errors["base"] = "invalid_auth"
            except RateLimited:
                errors["base"] = "rate_limited"
            except FeedError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating X handle")
                errors["base"] = "unknown"
            else:
                name = result["author"].get("display_name") or handle
                return self.async_create_entry(
                    title=f"{name} ({PLATFORM_NAMES[PLATFORM_X]})",
                    data={
                        CONF_FEED_PLATFORM: PLATFORM_X,
                        CONF_HANDLE: handle,
                        CONF_BEARER_TOKEN: token,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HANDLE): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.TEXT)
                ),
                vol.Required(CONF_BEARER_TOKEN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="x", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Expose an options flow for polling interval and post count."""
        return SocialFeedOptionsFlow()


class SocialFeedOptionsFlow(OptionsFlow):
    """Options: update interval and number of posts to keep."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        platform = self.config_entry.data[CONF_FEED_PLATFORM]
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL[platform]
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=1440,
                        step=1,
                        unit_of_measurement="min",
                        mode=NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    CONF_MAX_POSTS,
                    default=self.config_entry.options.get(
                        CONF_MAX_POSTS, DEFAULT_MAX_POSTS
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=20, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
