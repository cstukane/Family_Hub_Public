# Environment Variables

Family Hub reads environment variables from the OS and from a `.env` file that sits next to
`config.yaml` (default: repo root). OS environment values take precedence over `.env`.

Use `.env.example` as a starting point.

## Required for secure deployments

- `SECRET_KEY`: Required for stable session cookies and media launcher JWT signing. If missing, a temporary key is generated on each boot.
- `ADMIN_USERNAME` / `ADMIN_PASSWORD`: Required when `security.admin_enabled` is true and no admin credentials exist in `config.yaml`. These values are used once to write hashed credentials into `config.yaml`.

## Runtime controls

- `SOCKETIO_ALLOWED_ORIGINS`: Comma-separated list of allowed origins for Socket.IO. Defaults to localhost.
- `RATELIMIT_STORAGE_URI`: Storage backend for Flask-Limiter. Defaults to `memory://`.
- `MEDIA_LAUNCHER_JWT_SECRET`: Overrides the shared secret for media launcher JWTs. Falls back to `SECRET_KEY`.
- `MEDIA_LAUNCHER_TOKEN_TTL`: TTL (seconds) for media launcher JWTs. Defaults to `300`.
- `MEDIA_LAUNCHER_ALLOW_LEGACY_AUTH`: Set to `true` to allow `X-HUB-AUTH` legacy token authentication.
- `MEDIA_HUB_AUTH_TOKEN`: Legacy shared token for the media launcher (only used if legacy auth is enabled).
- `HUB_APP_AUTH_ENABLED`: Toggle auth checks in `hub_app.py` (defaults to `true`).
- `FLASK_ENV`: Runtime label surfaced in the admin system info panel (defaults to `production`).
 - `LOG_LEVEL`: Log level for the app (default `INFO`).
 - `LOG_CONSOLE`: Enable console logging (`true`/`false`).
 - `LOG_FILE`: Path for rotating log output (default `logs/family_hub.log`).
 - `LOG_MAX_BYTES`: Max log file size before rotation (default 10 MB).
 - `LOG_BACKUP_COUNT`: Number of rotated files to keep (default 5).
 - `LOG_FORMAT`: Python logging format string.
 - `LOG_DATE_FORMAT`: Python logging date format string.

## Config overrides (environment -> config.yaml)

These environment variables override values inside `config.yaml` at load time:

- `COMMUTE_GOOGLE_API_KEY` or `GOOGLE_MAPS_API_KEY` -> `commute.google_api_key`
- `COMMUTE_MAPBOX_TOKEN` or `MAPBOX_TOKEN` -> `commute.mapbox_token`
- `SPOTIFY_CLIENT_ID` -> `music.spotify.client_id`
- `SPOTIFY_CLIENT_SECRET` -> `music.spotify.client_secret`
- `GOOGLE_CALENDAR_CLIENT_ID` or `GOOGLE_CLIENT_ID` -> `providers.calendar.google.client_id`
- `GOOGLE_CALENDAR_CLIENT_SECRET` or `GOOGLE_CLIENT_SECRET` -> `providers.calendar.google.client_secret`
  - For multi-account Google Calendar setups, prefer `providers.calendar.google_accounts[]` with per-account
    `credentials_file` and `token_file` in `config.yaml`.
- `THESPORTSDB_API_KEY` or `SPORTS_API_KEY` -> `providers.sports.api_key`
- `GOOGLE_PHOTOS_CLIENT_ID` -> `photos.google_photos.client_id`
- `GOOGLE_PHOTOS_CLIENT_SECRET` -> `photos.google_photos.client_secret`
- `GOOGLE_PHOTOS_REFRESH_TOKEN` -> `photos.google_photos.refresh_token`
- `WEBHOOK_DEFAULT_SECRET` -> default `webhooks[].secret` if not set
- `WEBHOOK_DEFAULT_AUTHORIZATION` -> default `webhooks[].headers.Authorization` if not set

## Alexa discovery

The Alexa discovery adapter reads these variables directly:

- `ALEXA_ACCESS_TOKEN`: OAuth token for Alexa devices API.
- `ALEXA_API_BASE_URL`: Defaults to `https://api.amazonalexa.com`.
- `ALEXA_DEVICES_ENDPOINT`: Defaults to `/v1/devices`.
- `ALEXA_LOG_PAYLOADS`: Set to `true` to log outgoing payloads (redacted).
