# API Reference

Base URLs:

- Hub app (default): `http://<host>:5000`
- Media launcher service: dormant in Public V1 (was `http://127.0.0.1:7666`)

Common behavior:

- JSON requests use `Content-Type: application/json`.
- Many endpoints are rate limited. Exceeded limits return `429`.
- Admin endpoints are primarily gated by IP whitelist (`security.ip_whitelist_enabled`).
- Some endpoints return HTML fragments when `HX-Request: true` is present.

## Views (HTML)

- `GET /` main dashboard
- `GET /view/<name>` switch central view (calendar, sports)
- `GET /view/cooking` cooking mode
- `GET /settings` settings page
- ~~`GET /status`~~ Removed 2026-06-14 (deleted with metrics subsystem)
- `GET /admin` admin landing page
- `GET /admin/login` admin login
- `GET /admin/config` admin config UI
- `GET /admin/backup` admin backup UI
- `GET /admin/diagnostics` admin diagnostics UI
- `GET /admin/system` admin system UI
- `GET /admin/updates` admin updates UI
- `GET /integrations/spotify/callback` Spotify OAuth callback (if enabled)

## Partials (HTMX HTML)

- `GET /partials/calendar/week`
- `GET /partials/calendar/upnext`
- `GET /partials/calendar/add-event-modal`
- `GET /partials/notes`
- `GET /partials/notes-modal`
- `GET /partials/shopping`
- `GET /partials/shopping-modal`
- `GET /partials/timers`
- `GET /partials/timers-modal`
- `GET /partials/weather`
- `GET /partials/media`
- `GET /partials/alerts`
- `GET /partials/commute-map`
- `GET /partials/miniplayer`
- `GET /partials/casting`
- `GET /partials/sports/manage-teams`
- `GET /partials/sports/horizontal-ticker`

## Health and metrics

- `GET /health` JSON health info (lightweight — app version, platform, timestamp)
- ~~`GET /metrics`~~ Removed 2026-06-14 (deleted with metrics/Prometheus subsystem)
- ~~`GET /status`~~ Removed 2026-06-14 (deleted with metrics subsystem)
- `GET /admin/performance-metrics` JSON memory/photo/ticker size info (separate from removed metrics)

## Notes

- `GET /api/notes`
- `POST /api/notes` `{ "text": "..." }`
- `GET /api/notes/<id>`
- `GET /api/notes/<id>/edit` HTML edit fragment
- `PUT /api/notes/<id>` `{ "text": "..." }`
- `DELETE /api/notes/<id>`

## Shopping

- `GET /api/shopping`
- `POST /api/shopping` `{ "text": "...", "qty": "1" }`
- `GET /api/shopping/<id>`
- `GET /api/shopping/<id>/edit` HTML edit fragment
- `PUT /api/shopping/<id>` `{ "text": "...", "done": false, "qty": "1" }`
- `PATCH /api/shopping/<id>` partial update
- `POST /api/shopping/<id>/toggle`
- `DELETE /api/shopping/<id>`
- `DELETE /api/shopping` clear all (admin rate limit)
- `POST /api/shopping/clear-all` clear all (HTMX-friendly)

## Timers

- `GET /api/timers`
- `POST /api/timers` `{ "label": "...", "seconds": 90 }`
- `GET /api/timers/<id>`
- `PUT /api/timers/<id>` update timer
- `DELETE /api/timers/<id>`

## Calendar

- `POST /api/calendar/local` create event
  - `{ "title": "...", "starts_at": "...", "ends_at": "...", "location": "...", "description": "...", "all_day": false }`
- `POST /api/calendar/google` create Google event (requires provider config)
- `GET /api/oauth/google` start Google OAuth
- `GET /api/oauth/google/callback` finish OAuth

## Media launcher (dormant in Public V1)

The child-window media launcher service is disabled by default. When enabled, endpoints require `Authorization: Bearer <jwt>` unless legacy auth is enabled.

- `POST /api/media/open` proxy to launcher service
- `POST /api/media/close` proxy to launcher service
- `POST /api/launch` launch an app by config ID (iframe fallback)

## Weather and status

- `GET /api/status/weather`
- `GET /api/status/weather-toast`
- `GET /api/status/calendar`
- `GET /api/status/calendar-toast`
- `GET /api/status/system`
- `GET /api/weather-alerts`
- `GET /api/weather-alerts/history`
- `POST /api/weather-alerts/check`
- `GET /api/weather-alerts/severity`

## Sports

- `GET /api/sports`
- `GET /api/sports/ticker`
- `POST /api/sports/refresh`
- `POST /api/sports/ticker/refresh`
- `GET /api/sports/last-updated`
- `GET /api/sports/favorite_teams`
- `POST /api/sports/favorite_teams` replace favorites
- `POST /api/sports/favorite_teams/add` add favorites
- `GET /api/admin/sports-ticker/enabled` (IP whitelist)
- `PUT /api/admin/sports-ticker/enabled` (IP whitelist)
- `GET /api/admin/sports-ticker/mock-mode` (IP whitelist)
- `PUT /api/admin/sports-ticker/mock-mode` (IP whitelist)
- `POST /api/admin/sports-ticker/refresh` (IP whitelist)

## Voice

- `POST /api/voice/recognize` `{ "text": "..." }`
- `GET /api/voice/commands`
- `GET /api/voice/status`

## Config

- `GET /api/config` returns sanitized config for UI

## Home Assistant

- `GET /api/ha/entities`
- `GET /api/ha/entities/<entity_id>`
- `POST /api/ha/services/<domain>/<service>` body contains service payload

## Admin (IP whitelist recommended)

- `POST /api/admin/login` `{ "username": "...", "password": "..." }`
- `POST /api/admin/logout`
- `GET /api/admin/config`
- `PUT /api/admin/config`
- `GET /api/admin/system`
- `GET /api/admin/diagnostics`
- ~~`GET /api/admin/health-check`~~ Removed 2026-06-14 (deleted with self-healing subsystem)
- ~~`POST /api/admin/heal`~~ Removed 2026-06-14 (deleted with self-healing subsystem)
- `GET /api/admin/backup`
- `POST /api/admin/backup`
- `GET /api/admin/backup/<backup_name>`
- `DELETE /api/admin/backup/<backup_name>`
- `POST /api/admin/restore/<backup_name>`
- `GET /api/admin/backup/<backup_name>/download`
- `POST /api/admin/clear-cache`
- `POST /api/admin/restart-app`
- `GET /api/admin/updates/check`
- `POST /api/admin/updates`
- `GET /api/admin/updates/history`
- `POST /api/admin/updates/rollback`

## Webhooks

- `GET /api/webhooks`
- `POST /api/webhooks`
- `GET /api/webhooks/<id>`
- `PUT /api/webhooks/<id>`
- `DELETE /api/webhooks/<id>`
- `POST /api/webhooks/<id>/test`
- `POST /api/webhooks/<id>/trigger`
- `POST /api/webhooks/trigger-all`
- `GET /api/webhooks/<id>/logs`
- `GET /api/webhooks/logs`

## Plugins

- `GET /api/plugins`
- `POST /api/plugins` install by URL or repo
- `GET /api/plugins/<name>`
- `DELETE /api/plugins/<name>`
- `POST /api/plugins/<name>/enable`
- `POST /api/plugins/<name>/disable`
- `POST /api/plugins/<name>/reload`
- `GET /api/plugins/marketplace`
- `GET /api/plugins/marketplace/search`
- `GET /api/plugins/check-updates`
- `POST /api/plugins/<name>/update`

## IoT

- `GET /api/iot/devices`
- `POST /api/iot/devices`
- `GET /api/iot/devices/<id>`
- `PUT /api/iot/devices/<id>`
- `DELETE /api/iot/devices/<id>`
- `POST /api/iot/devices/discover`
- `POST /api/iot/devices/<id>/command`
  - `/api/iot/devices/discover` accepts `{ "async": true }` (default) to queue discovery and return `202`.

## Casting

- `GET /api/casting/devices`
- `GET /api/casting/devices/<device_id>`
- `GET /api/casting/devices/discover`
- `POST /api/casting/devices/<device_id>/play`
- `POST /api/casting/devices/<device_id>/pause`
- `POST /api/casting/devices/<device_id>/stop`
- `PUT /api/casting/devices/<device_id>/volume`
- `GET /api/casting/devices/<device_id>/status`
- `GET /api/casting/groups`
- `POST /api/casting/groups`
- `POST /api/casting/groups/<group_id>/play`
- `GET /api/casting/queue/<device_id>`
- `POST /api/casting/queue/<device_id>/add`

## Photos

- `GET /api/photos`
- `POST /api/photos`
- `GET /api/photos/<photo_id>`
- `PUT /api/photos/<photo_id>`
- `DELETE /api/photos/<photo_id>`
- `GET /api/photos/slideshow`
- `POST /api/photos/sync`
- `GET /api/albums`
- `POST /api/albums`
- `GET /api/albums/<album_id>`
- `PUT /api/albums/<album_id>`
- `DELETE /api/albums/<album_id>`

## Music

- `GET /api/music/tracks`
- `POST /api/music/tracks`
- `GET /api/music/tracks/<track_id>`
- `PUT /api/music/tracks/<track_id>`
- `DELETE /api/music/tracks/<track_id>`
- `GET /api/music/playlists`
- `POST /api/music/playlists`
- `GET /api/music/playlists/<playlist_id>`
- `PUT /api/music/playlists/<playlist_id>`
- `DELETE /api/music/playlists/<playlist_id>`
- `GET /api/music/playlists/<playlist_id>/tracks`
- `POST /api/music/playlists/<playlist_id>/tracks`
- `DELETE /api/music/playlists/<playlist_id>/tracks/<track_id>`
- `POST /api/music/queues`
- `GET /api/music/queues/<queue_id>`
- `PUT /api/music/queues/<queue_id>`
- `POST /api/music/queues/<queue_id>/play`
- `POST /api/music/queues/<queue_id>/pause`
- `POST /api/music/queues/<queue_id>/tracks`
- `POST /api/music/sync`
- `GET /api/music/current`
- `POST /api/music/play`
- `POST /api/music/pause`
- `POST /api/music/next`
- `POST /api/music/previous`
- `POST /api/music/seek` `{ "position_ms": 12345 }`
- `POST /api/music/tracks/<track_id>/like`
- `POST /api/music/queue`

### Provider control

- `GET /api/music/providers`
- `GET /api/music/providers/active`
- `POST /api/music/providers/active`
- `GET /api/music/providers/<provider_id>/status`
- `POST /api/music/providers/<provider_id>/authorize`
- `POST /api/music/providers/<provider_id>/logout`
- `POST /api/music/providers/<provider_id>/play`
- `POST /api/music/providers/<provider_id>/pause`
- `POST /api/music/providers/<provider_id>/next`
- `POST /api/music/providers/<provider_id>/previous`
- `POST /api/music/providers/<provider_id>/seek`
- `GET /api/music/providers/<provider_id>/playback`
- `GET /api/music/providers/<provider_id>/queue`
- `GET /api/music/providers/<provider_id>/playlists`
- `POST /api/music/providers/<provider_id>/playlists/<playlist_id>/shuffle`
- `POST /api/music/providers/<provider_id>/playlists/<playlist_id>/play`

### Spotify convenience aliases

- `GET /api/music/spotify/status`
- `POST /api/music/spotify/authorize`
- `POST /api/music/spotify/logout`
- `GET /api/music/spotify/playback`
- `GET /api/music/spotify/queue`
- `POST /api/music/spotify/play`
- `POST /api/music/spotify/pause`
- `POST /api/music/spotify/next`
- `POST /api/music/spotify/previous`
- `POST /api/music/spotify/seek`
- `GET /api/music/spotify/playlists`
- `POST /api/music/spotify/playlists/<playlist_id>/shuffle`
