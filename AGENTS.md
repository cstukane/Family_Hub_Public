# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Commands

```bash
# Environment setup
make venv        # Create .venv with Python 3.11+
make install     # Install dependencies from requirements.txt

# Run dev server (http://localhost:5000)
make run         # Activates .venv and starts Flask on 0.0.0.0:5000

# Testing
pytest                                        # Run all tests
pytest tests/test_calendar_google.py -v      # Run a single test file

# Linting & formatting (dev extras required: pip install -e ".[dev]")
ruff check .     # Lint (line length 120, Python 3.8 target)
black .          # Format
bandit -r hub/   # Security scan
```

Health check: `curl http://localhost:5000/health`

## Architecture

**Family Hub** is a kiosk-mode family dashboard (Flask + HTMX + Socket.IO) designed for always-on display on small PCs or Raspberry Pi.

### Entry Points
- `app.py` — Flask app factory, Jinja2 filters, SocketIO/Limiter/Talisman setup
- `hub_app.py` — Alternative entry point
- `hub/` — Core application package

### Request Lifecycle / Data Flow
```
APScheduler (hub/scheduler.py)
  → Adapter (hub/adapters/)          # fetch from external provider
  → Cache (hub/cache.py)             # SQLite with TTL
  → Service (hub/services/)          # business logic
  → Route (hub/routes/)              # JSON or Jinja partial
  → HTMX / Socket.IO → Browser
```

### Package Layout

| Directory | Purpose |
|-----------|---------|
| `hub/adapters/` | Swappable provider integrations (calendar_google, calendar_ics, weather_openmeteo, sports_espn, sports_thesportsdb, etc.) |
| `hub/services/` | Business logic per domain (calendar, weather, sports, music, photos, timers, notes, shopping, chores, iot, etc.) |
| `hub/routes/` | Flask blueprints — `api.py` (main REST/HTMX), `api_media_admin.py`, `api_weather.py`, `api_admin.py`, `api_webhooks.py`, `api_plugins.py`, `main.py` |
| `hub/integrations/` | OAuth flows (Spotify PKCE) |
| `hub/utils/` | Auth helpers, decorators, HTTP utils, logging config |
| `hub/models.py` | Shared dataclasses (CalendarEvent, Timer, Weather, etc.) |
| `hub/config.py` | Pydantic v2 config schema — validates `config.yaml` on startup |
| `hub/cache.py` | SQLite-backed TTL cache used by all adapters |
| `hub/scheduler.py` | APScheduler jobs: calendar (15 min), weather (15 min), sports (adaptive 1–30 min), cache cleanup (24h) |
| `hub/sockets.py` | Socket.IO event handlers for real-time timers and "Up Next" |
| `templates/` | Jinja2 templates; `base.html` is the main layout; `partials/` contains HTMX fragments |
| `static/` | CSS, JS (HTMX + Socket.IO handlers), SVG icons |
| `tests/` | Pytest test suite (~30+ files); `conftest.py` sets up fixtures |
| `docs/` | Architecture, config schema, API contracts, env vars, deployment guides |
| `instance/` | Runtime data: SQLite DB, OAuth tokens, credentials (gitignored) |

### Configuration System
All runtime customization is in `config.yaml` (validated by `hub/config.py` using Pydantic v2). Secrets go in `.env` (or `instance/secrets.env` for production). The config covers:
- `layout` / `ui` — dashboard views, theme, sidebar widgets
- `providers` — which adapter to use per domain (e.g. `calendar.kind: google|ics`)
- `features` — feature flags (voice, kiosk, auth, plugins, sports_ticker)
- `apps` / `local_apps` — media launcher shortcuts
- `security` — rate limits, CSP, SSL, session timeout

### Adapter Pattern
Each provider domain has independent, swappable adapters. To add a new weather provider, create `hub/adapters/weather_newprovider.py` matching the existing interface, then select it via `providers.weather.kind` in `config.yaml`. The service layer calls the configured adapter; adapters write to the shared SQLite cache.

### Real-time Layer
Socket.IO (`hub/sockets.py`) drives timer countdowns, "Up Next" calendar updates, and sports score pushes without client polling. `hub/routes/api.py` also serves HTMX partials for full-page-reload-free UI updates.

### Key Large Files
- `hub/routes/api.py` (51 KB) — primary REST + HTMX endpoints
- `hub/routes/api_media_admin.py` (89 KB) — media/launcher API with JWT auth
- `hub/services/sports_ticker_service.py` (52 KB) — live sports tracking logic
- `hub/services/music.py` (32 KB) — Spotify + local library
- `templates/base.html` (85 KB) — full dashboard layout

### Testing
Tests live in `tests/` (integration/unit) and `hub/tests/` (unit). Pytest is configured in `pyproject.toml` with cache disabled (`-p no:cacheprovider`). Most service tests mock adapter calls; `conftest.py` provides a Flask test client.

### Deployment
`systemd/` contains service templates for the Flask app and Chromium kiosk browser. `make deploy` generates and installs them. Production secrets go in `instance/secrets.env`.
