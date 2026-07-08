# Social Feed for Home Assistant

A custom integration that pulls the latest posts from Bluesky, Mastodon, and X profiles into Home Assistant sensors. Fully configured through the UI — no YAML.

## Features

- UI config flow with a platform dropdown (Bluesky / Mastodon / X)
- Just enter the profile handle, e.g. `@profile handle` (full profile URLs also work)
- Multiple feeds: add the integration once per profile you want to follow
- One sensor per feed
- Options flow to change the polling interval and how many posts to keep
- Profile avatar shown as the entity picture

## Platform notes

| | Bluesky | Mastodon | X (Twitter) |
|---|---|---|---|
| Auth needed | None (public API) | None (public API) | API Bearer Token from [developer.x.com](https://developer.x.com) |
| Handle format | `@profile handle` | `@user@fosstodon.org` | `@profile handle` |
| Default poll interval | 5 min | 5 min | 60 min |

**X:** X has no free read tier anymore.

**Mastodon:** a small number of locked-down Mastodon instances require authentication for all API access. Profiles on those instances will fail validation with a "Could not connect" error during setup.

## Installation

**HACS**
1. HACS
2. Three dots at the top right
3. Custom repositories
4. Repository - https://github.com/peggleg/social-feed > Type - Integration > Add
5. Search for "Social Feed" > Install & Restart Home Assistant
6. Install & Restart Home Assistant

**Manual Installation**
1. Copy the `custom_components/social_feed` folder into your Home Assistant `config/custom_components/` directory, so you end up with `config/custom_components/social_feed/`.
2. Restart Home Assistant.

## Add feeds
1. Go to **Settings → Devices & Services → Add Integration** and search for **Social Feed**.
2. Pick a platform from the dropdown, enter the handle (and bearer token for X), and submit.
3. Repeat step 1&2 for each additional profile you want to follow.

## Sensor attributes

Each feed creates one sensor, e.g. `sensor.profile.handle_io_bluesky`:

```yaml
platform: Bluesky
handle: profile.handle.io
display_name: Display Name
latest_post_id: 3k7a...
latest_post_url: https://bsky.app/profile/profile_handle/post/3k7a...
latest_post_time: 2026-07-08T10:15:00+00:00
post_count: 5
posts:
  - id: ...
    text: ...
    created_at: ...
    url: ...
    likes: 42
    reposts: 7
    replies: 3
```

## Example Lovelace card (Markdown)

```yaml
type: markdown
content: >
  {% set s = 'sensor.profile.handle_io_bluesky' %}
  {% set post = state_attr(s, 'posts')[0] %}
  ## {{ state_attr(s, 'display_name') }} — {{ state_attr(s, 'platform') }}

  {{ post.text }}

  {{ as_timestamp(post.created_at) | timestamp_custom('%d %b %H:%M') }}
```
