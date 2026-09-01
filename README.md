# Family Hub

A glanceable family command center for a kitchen TV, and the front door to a personal homelab. Designed for always-on kiosk display on a small PC or Raspberry Pi.

The core loop: walk into the kitchen → in ~3 seconds know what's next today, the weather, commute ETA, and scores → occasionally touch the screen to add a shopping item, set a timer, play music, or open a companion app.

**This is a personal appliance, not a platform.** The product fits on one screen and one config file.

---

## Features

### Core Dashboard (always on screen)
- **Calendar-First Interface**: Week grid view with current time indicator and "Up Next" event panel. Powered by Google Calendar or ICS feeds.
- **Commute Tile**: Real-time home→work ETA with fallback timer display. The most personal feature in the app.
- **Weather**: Current conditions, hourly forecast, and daily outlook via Open-Meteo (or NWS).
- **Sports Ticker**: Live scoreboard with favorite-team filtering (Nets, Giants, Yankees, Devils). Real data from TheSportsDB or ESPN.
- **Shopping List**: Quick-add items, check off, and clear. Local and fast, with a dedicated sidebar tile.
- **Notes**: Simple local note-taking with CRUD operations via sidebar.
- **Kitchen Timers**: Countdown timers with Socket.IO real-time updates and audio alerts.

### Media & App Launcher
- **Miniplayer**: Spotify playback control (play/pause/skip/seek) with PKCE OAuth; full playlist + liked-track sync.
- **App Bar**: Quick-launch buttons for YouTube, Spotify, Disney+, HBO Max, Pluto TV, ESPN, Roku — open in iframe or new tab.
- **Homelab Companion Apps**: Launcher bar for 12 self-hosted services on ports 5001–5011 (Budget, Lifelog, Learning Scroll, Home Inventory, Package Monitor, etc.).
- **Music**: Local music library browser + Spotify integration.

### Kiosk / Glanceable Behavior
- **Always-on display** via systemd + Chromium kiosk mode
- **Touch-friendly**: Large buttons, compact density, dark/light auto-theme
- **Socket.IO** for live timer tick, "Up Next" calendar push, and sports score updates
- **APScheduler** background jobs: calendar (15 min), weather (15 min), sports (adaptive, 1–30 min), cache cleanup (24h)
- **SQLite** TTL cache for all external API data
- **Graceful failure**: tiles degrade independently; error states surface stale-data indicators

### Configuration-Driven
Nearly all layout, provider, and feature customization is through the untracked `instance/config.yaml` — no code changes needed for:
- Sidebar panels (notes, shopping, timers, weather, sports)
- App bar buttons and launcher targets
- Calendar, weather, and sports providers
- Music sources and Spotify settings
- UI theme and density

---

## Quick Start

### Prerequisites
- Python 3.11+
- Chromium browser
- make
- Git

### Development Setup
1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd kitchen-hub
   make venv
   make install
   ```

2. **Configure your services:**
   ```bash
   mkdir -p instance
   cp config.example.yaml instance/config.yaml
   cp .env.example instance/.env
   # Edit only these ignored local files
   ```

3. **Customize your layout:**
   ```bash
   # Edit instance/config.yaml to configure:
   # - Sidebar panels (notes, shopping, timers, weather, sports)
   # - App bar buttons (YouTube, Spotify, Disney+, HBO, Pluto, ESPN)
   # - Homelab companion apps (Budget, Lifelog, etc.)
   # - Calendar, weather, and sports providers
   # - Music sources and Spotify integration
   # - UI theme and density
   ```

4. **Launch:**
   ```bash
   make run
   # Open http://localhost:5000
   ```

---

## Spotify Integration (Authorization Code + PKCE)

Spotify uses the secure Authorization Code Flow with PKCE and HTTPS redirect URIs.

1. **Create a Spotify application** in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. **Enable Spotify in `instance/config.yaml`; put its client credentials and redirect URI in `instance/.env`.**
3. **Serve the Hub over HTTPS** (mkcert + nginx or similar). Spotify rejects `http://` and `localhost` aliases in production.
4. **Open the dashboard miniplayer** and click **"Connect Spotify"**. Tokens are stored in `instance/spotify_tokens.json`.
5. **Shuffle playlists** from the miniplayer dropdown after connecting.

---

## Production Deployment

### Prerequisites
- Debian/Ubuntu or Raspberry Pi OS
- Python 3.11+, make
- Chromium browser
- systemd (for autostart services)
- Git

### Deployment Steps
1. **Install system packages and clone the repository:**
   ```bash
   sudo apt update && sudo apt install python3 python3-venv chromium-browser nginx
   sudo git clone <repository-url> /opt/kitchen-hub
   cd /opt/kitchen-hub
   ```

2. **Setup environment and install dependencies:**
   ```bash
   sudo make venv && sudo make install
   ```

3. **Configure secrets and setup systemd services:**
   ```bash
   sudo mkdir -p instance
   sudo cp config.example.yaml instance/config.yaml
   sudo cp .env.example instance/.env
   sudo nano instance/config.yaml
   sudo nano instance/.env

   sudo make gen-systemd
   ```

4. **Start the services:**
   ```bash
   sudo make deploy
   ```

### Health Check
- `GET /health` — application status, version info, and platform details

### Managing Services
```bash
sudo systemctl status kitchen-hub@$USER.service
sudo systemctl status kitchen-hub-kiosk@$USER.service
sudo journalctl -u kitchen-hub@$USER.service -f
```

---

## Configuration

The application is configured via ignored `instance/config.yaml`, copied from `config.example.yaml`. Key sections:

```yaml
layout:
  main_view: week_calendar
  sidebar: [notes, shopping, timers, weather, sports]

apps:  # App bar buttons (dock)
  - id: home
    label: Home
    action: switch_view
    target: week_calendar
  - id: youtube
    label: YouTube
    action: open_iframe
    url: "https://www.youtube.com/"
  - id: spotify
    label: Spotify
    action: open_tab
    url: "https://open.spotify.com/"
  - id: sports
    label: Sports
    action: switch_view
    target: sports

local_apps:  # Homelab companion apps
  - id: budget
    label: Budget
    action: open_tab
    url: "http://127.0.0.1:5009"

providers:
  calendar:
    kind: "google"  # "google" | "ics"
    google:
      calendar_ids: ["primary"]  # OAuth credentials belong in instance/.env
  weather:
    kind: "open_meteo"  # "open_meteo" | "nws"
    location:
      name: "Your City"
      lat: 0.0
      lon: 0.0
  sports:
    kind: "thesportsdb"  # "thesportsdb" | "espn"
    favorite_teams: ["brooklyn nets", "new york giants", "new york yankees", "new jersey devils"]

commute:
  enabled: true
  home_address: "123 Example Street, Your Town"
  work_address: "456 Example Avenue, Nearby City"

features:
  voice: false      # Experimental — disabled by default
  kiosk: true       # Enable kiosk mode
  auth: false       # Optional local auth for edit actions

music:
  enabled: true
  spotify:
    enabled: true
    client_id: ""
    client_secret: ""
```

See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for the current configuration and privacy model.

---

## Architecture

### Stack
- **Backend**: Flask with HTMX for server-rendered partials
- **Real-time**: Socket.IO for live updates (timers, Up Next, sports)
- **Database**: SQLite with SQLAlchemy ORM for local data persistence
- **Scheduling**: APScheduler for background data refresh (calendar, weather, sports)
- **Caching**: SQLite-backed TTL cache (adapter → cache → service → route)
- **Adapters**: Swappable provider modules (ICS/Google for calendar, Open-Meteo/NWS for weather, TheSportsDB/ESPN for sports)
- **Deployment**: systemd services for kiosk + app

### Data Flow
```
APScheduler → Adapter (fetch from external provider)
  → Cache (SQLite with TTL)
  → Service (business logic)
  → Route (JSON or Jinja partial)
  → HTMX / Socket.IO → Browser
```

---

## Documentation

- [**System Architecture**](docs/SYSTEM_ARCHITECTURE.md) — Technical design overview
- [**Configuration**](docs/CONFIGURATION.md) — Current config, secrets, and browser boundary
- [**API Reference**](docs/API_CONTRACTS.md) — REST/HTMX endpoints and media launcher API
- [**Deployment Guide**](docs/DEPLOYMENT.md) — Production deployment instructions
- [**Development Guide**](docs/DEV_GUIDE.md) — Contributing and development workflow

### Experimental / Attic Subsystems
These exist in the codebase but are **not part of the active dashboard experience**:
- **Voice commands** — `voice.js` ships but is disabled by default (`features.voice: false`)
- **IoT / Home Assistant** — Smart home adapter exists; not surfaced in the redesigned UI
- **Google Photos sync** — Local photos only; Google Photos disabled in config
- **Cooking Mode / Ambient / Photos views** — Partial implementations, not primary surfaces
- **Casting** — Chromecast device discovery code present; not surfaced in dashboard
- **Chore management** — Disabled in config (`chores.enabled: false`)
- **Plugins system** — Plugin infrastructure exists; no real plugins
- **Webhooks** — Webhook management UI and service exist; not part of the glanceable loop
- **Self-healing / backup / update** — Self-healing was removed 2026-06-15; backup/update remain frozen. A kiosk updates via `git pull` + restart.
- ~~**Metrics / Prometheus / /status**~~ — Removed 2026-06-15. `/health` endpoint remains for lightweight status checks.
- ~~**News**~~ — Removed 2026-06-15 (dead code with zero reachability).
- ~~**Edge computing**~~ — Removed 2026-06-15 (speculative code with zero reachability).

These subsystems are **frozen** — no new investment, no README billing, first against the wall when they cause friction.

---

## Hardware Recommendations
- Raspberry Pi 4+ with 4GB RAM (recommended for all features)
- Small form-factor PC (Intel NUC, etc.) for enhanced performance
- Any Linux device with Chromium support
- Touchscreen monitor for optimal user experience

---

## Contributing

This project follows a **configuration-over-code** philosophy: customize ignored `instance/config.yaml` without modifying source code.

1. Check [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md) for current priorities
2. See [Development Guide](docs/DEV_GUIDE.md) for setup and workflow
3. Submit issues for bugs or enhancement requests
4. PRs welcome for adapters, UI improvements, and documentation
