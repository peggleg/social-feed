"""Constants for the Social Feed integration."""

DOMAIN = "social_feed"

CONF_FEED_PLATFORM = "feed_platform"
CONF_HANDLE = "handle"
CONF_BEARER_TOKEN = "bearer_token"
CONF_MAX_POSTS = "max_posts"
CONF_UPDATE_INTERVAL = "update_interval"

PLATFORM_BLUESKY = "bluesky"
PLATFORM_X = "x"
PLATFORM_MASTODON = "mastodon"

PLATFORM_NAMES = {
    PLATFORM_BLUESKY: "Bluesky",
    PLATFORM_X: "X (Twitter)",
    PLATFORM_MASTODON: "Mastodon",
}

DEFAULT_MAX_POSTS = 5

# Bluesky and Mastodon public APIs are free and generous. X has no free
# read tier at all (pay-per-use as of Feb 2026), so poll it far less
# often by default to keep the cost down.
DEFAULT_UPDATE_INTERVAL = {
    PLATFORM_BLUESKY: 5,  # minutes
    PLATFORM_X: 60,  # minutes
    PLATFORM_MASTODON: 5,  # minutes
}

BLUESKY_API_BASE = "https://public.api.bsky.app/xrpc"
X_API_BASE = "https://api.x.com/2"
