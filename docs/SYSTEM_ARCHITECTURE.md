# SYSTEM ARCHITECTURE — Family Hub

This document focuses on components and data flow.

## Components
- **Flask App**: routes for views and HTMX partials
- **Services Layer**: calendar, weather, notes, shopping, timers, sports ticker, commute, reference/conversion
- **Adapters**: swappable provider modules (ICS/Google, Open-Meteo/NWS, TheSportsDB/ESPN, etc.)
- **SQLite**: persistence for local data + TTL caches
- **APScheduler**: background refresh jobs (calendar 15 min, weather 15 min, sports adaptive 1–30 min, cache cleanup 24h)
- **Socket.IO**: real-time timer countdowns, "Up Next" pushes, sports score updates
- **Kiosk Shell**: Chromium fullscreen via systemd or manual app mode

## Data Flow (example: Weather)
1. Scheduler triggers `weather.refresh()` every 15 minutes.
2. Adapter fetches data; result cached in `cache` with TTL.
3. UI pulls `/partials/weather`; service returns cached data or triggers fetch on stale.
4. Errors are recorded and shown in `alerts_banner.html`.

## Error Handling
- Service functions must return `(data, error)` or raise typed exceptions caught by routes.
- Banner consolidates current provider errors with timestamps.

## Observability
- Log to STDOUT with timestamps and phases.
- Health endpoint at `/health` with application status and version info.