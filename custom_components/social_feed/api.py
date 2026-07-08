"""API helpers for fetching feeds from Bluesky and X."""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

from .const import BLUESKY_API_BASE, X_API_BASE

_LOGGER = logging.getLogger(__name__)


class FeedError(Exception):
    """Generic feed error."""


class ProfileNotFound(FeedError):
    """Raised when the profile/handle cannot be found."""


class AuthFailed(FeedError):
    """Raised when authentication fails (X bearer token)."""


class RateLimited(FeedError):
    """Raised when the API rate limit is hit."""


def normalize_handle(handle: str, platform: str) -> str:
    """Clean up a user-entered handle."""
    handle = handle.strip().rstrip("/")

    if platform == "mastodon":
        # Accept @user@instance, user@instance, or https://instance/@user
        if handle.startswith(("http://", "https://")):
            rest = handle.split("://", 1)[1]
            parts = [p for p in rest.split("/") if p]
            if len(parts) >= 2:
                instance = parts[0]
                user = parts[1].lstrip("@")
                return f"{user}@{instance}"
        handle = handle.lstrip("@")
        if "@" not in handle:
            # No instance given; default to the flagship server
            handle = f"{handle}@mastodon.social"
        return handle

    handle = handle.lstrip("@")
    # Allow pasting a full profile URL
    for prefix in (
        "https://bsky.app/profile/",
        "https://x.com/",
        "https://twitter.com/",
    ):
        if handle.startswith(prefix):
            handle = handle[len(prefix):]
    handle = handle.split("/")[0].split("?")[0]
    if platform == "bluesky" and "." not in handle:
        # Bare names on Bluesky live under bsky.social
        handle = f"{handle}.bsky.social"
    return handle


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html: str) -> str:
    """Convert Mastodon's HTML status content to plain text."""
    text = html.replace("</p><p>", "\n\n").replace("<br />", "\n").replace(
        "<br>", "\n"
    )
    text = _TAG_RE.sub("", text)
    return (
        text.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
        .strip()
    )


async def fetch_mastodon_feed(
    session: aiohttp.ClientSession, handle: str, limit: int
) -> dict[str, Any]:
    """Fetch public statuses for a Mastodon account (user@instance)."""
    user, _, instance = handle.partition("@")
    base = f"https://{instance}/api/v1"

    # Step 1: resolve the account
    async with session.get(
        f"{base}/accounts/lookup", params={"acct": user}
    ) as resp:
        if resp.status == 404:
            raise ProfileNotFound(f"Mastodon account '{handle}' not found")
        if resp.status == 429:
            raise RateLimited("Mastodon rate limit reached")
        if resp.status != 200:
            raise FeedError(
                f"Mastodon instance '{instance}' returned HTTP {resp.status}"
            )
        account = await resp.json()

    # Step 2: fetch statuses
    async with session.get(
        f"{base}/accounts/{account['id']}/statuses",
        params={
            "limit": limit,
            "exclude_replies": "true",
            "exclude_reblogs": "true",
        },
    ) as resp:
        if resp.status == 429:
            raise RateLimited("Mastodon rate limit reached")
        if resp.status != 200:
            raise FeedError(
                f"Mastodon instance '{instance}' returned HTTP {resp.status}"
            )
        statuses = await resp.json()

    posts = []
    for status in statuses:
        posts.append(
            {
                "id": status.get("id"),
                "text": _strip_html(status.get("content", "")),
                "created_at": status.get("created_at"),
                "url": status.get("url"),
                "likes": status.get("favourites_count", 0),
                "reposts": status.get("reblogs_count", 0),
                "replies": status.get("replies_count", 0),
            }
        )

    return {
        "author": {
            "display_name": account.get("display_name") or account.get("username"),
            "handle": handle,
            "avatar": account.get("avatar"),
        },
        "posts": posts[:limit],
    }


async def fetch_bluesky_feed(
    session: aiohttp.ClientSession, handle: str, limit: int
) -> dict[str, Any]:
    """Fetch the author feed for a Bluesky handle. No auth required."""
    url = f"{BLUESKY_API_BASE}/app.bsky.feed.getAuthorFeed"
    params = {"actor": handle, "limit": limit, "filter": "posts_no_replies"}

    async with session.get(url, params=params) as resp:
        if resp.status == 400:
            raise ProfileNotFound(f"Bluesky profile '{handle}' not found")
        if resp.status == 429:
            raise RateLimited("Bluesky rate limit reached")
        if resp.status != 200:
            raise FeedError(f"Bluesky API returned HTTP {resp.status}")
        data = await resp.json()

    posts = []
    author_info: dict[str, Any] = {}
    for item in data.get("feed", []):
        post = item.get("post", {})
        record = post.get("record", {})
        author = post.get("author", {})
        # Skip reposts of other people's content
        if author.get("handle", "").lower() != handle.lower():
            continue
        if not author_info:
            author_info = {
                "display_name": author.get("displayName"),
                "handle": author.get("handle"),
                "avatar": author.get("avatar"),
            }
        uri = post.get("uri", "")
        post_id = uri.rsplit("/", 1)[-1] if uri else ""
        posts.append(
            {
                "id": post_id,
                "text": record.get("text", ""),
                "created_at": record.get("createdAt"),
                "url": f"https://bsky.app/profile/{handle}/post/{post_id}",
                "likes": post.get("likeCount", 0),
                "reposts": post.get("repostCount", 0),
                "replies": post.get("replyCount", 0),
            }
        )

    return {"author": author_info, "posts": posts[:limit]}


async def fetch_x_feed(
    session: aiohttp.ClientSession, handle: str, bearer_token: str, limit: int
) -> dict[str, Any]:
    """Fetch recent posts for an X username using API v2."""
    headers = {"Authorization": f"Bearer {bearer_token}"}

    # Step 1: resolve username -> user id
    user_url = f"{X_API_BASE}/users/by/username/{handle}"
    async with session.get(
        user_url,
        headers=headers,
        params={"user.fields": "name,username,profile_image_url"},
    ) as resp:
        if resp.status in (401, 403):
            raise AuthFailed("X API rejected the bearer token")
        if resp.status == 429:
            raise RateLimited("X API rate limit reached")
        if resp.status != 200:
            raise FeedError(f"X API returned HTTP {resp.status}")
        user_data = await resp.json()

    if "data" not in user_data:
        raise ProfileNotFound(f"X profile '{handle}' not found")

    user = user_data["data"]
    user_id = user["id"]

    # Step 2: fetch tweets
    tweets_url = f"{X_API_BASE}/users/{user_id}/tweets"
    params = {
        "max_results": max(5, min(limit, 100)),
        "exclude": "retweets,replies",
        "tweet.fields": "created_at,public_metrics",
    }
    async with session.get(tweets_url, headers=headers, params=params) as resp:
        if resp.status in (401, 403):
            raise AuthFailed("X API rejected the bearer token")
        if resp.status == 429:
            raise RateLimited("X API rate limit reached")
        if resp.status != 200:
            raise FeedError(f"X API returned HTTP {resp.status}")
        tweet_data = await resp.json()

    posts = []
    for tweet in tweet_data.get("data", []):
        metrics = tweet.get("public_metrics", {})
        posts.append(
            {
                "id": tweet["id"],
                "text": tweet.get("text", ""),
                "created_at": tweet.get("created_at"),
                "url": f"https://x.com/{handle}/status/{tweet['id']}",
                "likes": metrics.get("like_count", 0),
                "reposts": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
            }
        )

    return {
        "author": {
            "display_name": user.get("name"),
            "handle": user.get("username"),
            "avatar": user.get("profile_image_url"),
        },
        "posts": posts[:limit],
    }
