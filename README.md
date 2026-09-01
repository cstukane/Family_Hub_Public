# Family Hub

A glanceable family command center for a kitchen TV or desktop display. Designed for always-on kiosk mode on a Windows PC, with secondary support for Raspberry Pi and Linux.

The core loop: walk into the room → in ~3 seconds know what's next today, the weather, and scores → occasionally touch the screen to add a shopping item, set a timer, or open a useful web destination.

**This is a personal appliance, not a platform.** The product fits on one screen and one config file.

## Features

### Core Dashboard (always on screen)
- **Calendar-First Interface**: Week grid view with current time indicator and "Up Next" event panel. Powered by Google Calendar or ICS feeds.
- **Weather**: Current conditions, hourly forecast, and daily outlook via Open-Meteo.
- **Sports Ticker**: Live scoreboard with configurable league filtering. Real data from ESPN or TheSportsDB.
- **Shopping List**: Quick-add items, check off, and clear. Local and fast, with a dedicated sidebar tile.
- **Notes**: Simple local note-taking with CRUD operations via sidebar.
- **Kitchen Timers**: Countdown timers with Socket.IO real-time updates and audio alerts.

### Media & App Launcher
- **App Bar**: Quick-launch buttons for YouTube, ESPN, Disney+, HBO Max, Pluto TV, Roku — open in iframe or new tab.

### Kiosk / Glanceable Behavior
- **Always-on display** via systemd + Chromium kiosk mode (Linux) or manual Chrome app mode (Windows)
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
- UI theme and density

## Quick Start

### Prerequisites
- Windows 10 or 11 (primary), or Linux / Raspberry Pi (secondary)
- Python 3.11+
- Chromium browser (optional, for kiosk mode)
- make
- Git

### Development Setup (Windows — primary host)
1. **Clone and setup environment:**
    ```cmd
    git clone <repository-url>
    cd family-hub
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    ```

2. **Configure your services:**
    ```cmd
    mkdir instance 2>nul
    copy config.example.yaml instance\config.yaml
    copy .env.example instance\.env
    rem Edit only these ignored local files
    ```

3. **Launch:**
    ```cmd
    make run
    rem Open http://localhost:5000
    ```

### Development Setup (Linux / Raspberry Pi — secondary)
```bash
git clone <repository-url> family-hub
cd family-hub
make venv
make install
mkdir -p instance
cp config.example.yaml instance/config.yaml
cp .env.example instance/.env
make run
```

## Google Calendar Setup

Google Calendar uses OAuth for authorization.

1. **Create a Google application** in the [Google Cloud Console](https://console.cloud.google.com/).
2. **Enable Google Calendar in `instance/config.yaml`; put its client credentials and redirect URI in `instance/.env`.**
3. **Open the dashboard and click "Connect Google Calendar".** Tokens are stored in `instance/token.json`.
4. **Authorize Family Hub** when prompted by Google.

## Production Deployment

### Windows (primary)

The normal Windows experience is a self-hosted local web app. No installer exists yet; run from source during Phase 1.

1. **Setup environment:**
    ```cmd
    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    mkdir instance 2>nul
    copy config.example.yaml instance\config.yaml
    copy .env.example instance\.env
    ```

2. **Launch:**
    ```cmd
    make run
    ```

3. **Kiosk mode:** Open http://localhost:5000 in Chrome and use Chrome's app mode for a dedicated window.

### Linux / Raspberry Pi (secondary / self-hosted)

#### Prerequisites
- Debian/Ubuntu or Raspberry Pi OS
- Python 3.11+, make
- Chromium browser
- systemd (for autostart services)
- Git

#### Deployment Steps
1. **Install system packages and clone the repository:**
    ```bash
    sudo apt update && sudo apt install python3 python3-venv chromium-browser nginx
    sudo git clone <repository-url> /opt/family-hub
    cd /opt/family-hub
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

#### Health Check
- `GET /health` — application status, version info, and platform details

#### Managing Services
```bash
sudo systemctl status family-hub@$USER.service
sudo systemctl status family-hub-kiosk@$USER.service
sudo journalctl -u family-hub@$USER.service -f
```

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
  - id: sports
    label: Sports
    action: switch_view
    target: sports

providers:
  calendar:
    kind: "google"  # "google" | "ics"
    google:
      calendar_ids: ["primary"]  # OAuth credentials belong in instance/.env
  weather:
    kind: "open_meteo"  # "open_meteo" | "nws"
    location:
      name: Your City
      lat: 0.0
      lon: 0.0
  sports:
    kind: "thesportsdb"  # "thesportsdb" | "espn"
    favorite_teams: []

commute:
  enabled: false
  home_address: ""
  work_address: ""

features:
  voice: false      # Experimental — disabled by default
  kiosk: true       # Enable kiosk mode
  auth: false       # Optional local auth for edit actions
```

See [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) for the current configuration and privacy model.

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

## Documentation

- [**System Architecture**](docs/SYSTEM_ARCHITECTURE.md) — Technical design overview
- [**Configuration**](docs/CONFIGURATION.md) — Current config, secrets, and browser boundary
- [**API Reference**](docs/API_CONTRACTS.md) — REST/HTMX endpoints and media launcher API
- [**Deployment Guide**](docs/DEPLOYMENT.md) — Production deployment instructions
- [**Implementation Phases**](docs/IMPLEMENTATION_PHASES.md) — Public Edition roadmap

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

## Hardware Recommendations

- Windows 10/11 PC (primary host; any desktop or laptop capable of running Chrome)
- Raspberry Pi 4+ with 4GB RAM (recommended for secondary Linux/Pi deployment)
- Small form-factor PC (Intel NUC, etc.) for secondary Linux deployment
- Any Linux device with Chromium support
- Touchscreen monitor for optimal user experience

## Contributing

This project follows a **configuration-over-code** philosophy: customize ignored `instance/config.yaml` without modifying source code.

1. See [Implementation Phases](docs/IMPLEMENTATION_PHASES.md) for current priorities
2. See [Development Guide](docs/DEV_GUIDE.md) for setup and workflow
3. Submit issues for bugs or enhancement requests
4. PRs welcome for adapters, UI improvements, and documentation
