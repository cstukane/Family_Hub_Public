# Configuration

Family Hub separates non-secret appliance settings from credentials, and keeps both deployment-specific files untracked.

## Canonical locations

1. Copy the safe tracked template to the instance directory:
   ```bash
   mkdir -p instance
   cp config.example.yaml instance/config.yaml
   cp .env.example instance/.env
   chmod 600 instance/config.yaml instance/.env
   ```
2. Put layout, provider selection, favorite teams, weather coordinates, commute addresses, launcher URLs, LAN origins, and certificate paths in `instance/config.yaml`.
3. Put secrets and credentials in `instance/.env`. The loader reads the `.env` beside the selected YAML without overriding variables already supplied by the service environment.
4. Start normally. The application selects `instance/config.yaml` when present and otherwise uses the safe `config.example.yaml`. Set `FAMILY_HUB_CONFIG=/absolute/path/config.yaml` to select another file explicitly.

Never commit `instance/config.yaml`, `instance/.env`, root `config.yaml`, or `instance/secrets.env`; all are ignored. The example is intentionally bootable but has household providers and optional network features disabled.

## Environment overrides

`.env.example` lists supported secret overrides, including calendar and Spotify OAuth credentials, sports keys, commute provider credentials, Socket.IO origins, and the media-launcher signing key. Deployment-specific non-secrets remain in the local YAML so there is one understandable appliance configuration.

## Runtime surface

- **Core:** calendar refresh, weather refresh, optional sports ticker refresh, cache cleanup, timers/Socket.IO, launcher, and configured music/miniplayer.
- **Optional supported:** Spotify, local photos, chores, and sports ticker; each performs work only when enabled/configured.
- **Dormant by default:** casting discovery, IoT integrations, plugins, voice browser code, webhooks, weather-alert dispatch, update checks, photo sync, and music sync. These require explicit flags; some are retained as attic code and may be deleted later.

## Browser boundary

The rendered public configuration contains presentation values only. Commute addresses and map credentials remain on the Flask server. The browser requests calculated ETA data from `/api/commute`; the server calls the configured provider and returns only duration, traffic/incident state, and update time.
