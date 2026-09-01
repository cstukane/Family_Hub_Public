# Security and Privacy

Family Hub is designed for LAN-first use. If you expose it outside the LAN, treat it like a
full web app and harden the deployment.

## Baseline expectations

- Keep the hub on a private network. Do not bind it directly to the public internet.
- Use a reverse proxy (nginx, Traefik) with TLS if you need remote access.
- Prefer VPN access (Tailscale, WireGuard) instead of opening ports.

## Required production settings

- `SECRET_KEY` must be set in `instance/.env` for stable sessions and JWT signing.
- `security.ssl_enabled` should be `true` when running behind HTTPS.
- `security.secure_headers` should remain `true`.
- `security.rate_limit_enabled` should remain `true`.
- If admin is enabled (`security.admin_enabled: true`), set `ADMIN_USERNAME` and
  `ADMIN_PASSWORD` in the environment before the first boot. The app hashes and stores their hash in the local deployment database/configuration.

## Access controls

- **Admin endpoints**: Primarily gated by IP whitelist.
  - Enable with `security.ip_whitelist_enabled: true`.
  - Populate `security.ip_whitelist` with allowed client IPs.
- **Session cookies**: Honoring `security.session_timeout` with secure cookie flags.
- **Socket.IO**: Use `SOCKETIO_ALLOWED_ORIGINS` or `security.socketio_allowed_origins` to
  restrict browser origins.

## Media launcher service

- Runs locally on `127.0.0.1:7666`.
- Uses JWT auth by default (`Authorization: Bearer <token>`).
- Legacy header auth can be enabled with `MEDIA_LAUNCHER_ALLOW_LEGACY_AUTH=true` and
  `MEDIA_HUB_AUTH_TOKEN`, but this is not recommended for production.
- Allowed media domains are controlled by `config/media_whitelist.json`.

## Configuration hygiene

- Copy `config.example.yaml` to ignored `instance/config.yaml`; never commit household settings.
- Put secrets in ignored `instance/.env`; use the documented environment overrides.
- Rotate tokens periodically (Spotify refresh tokens, Google credentials, webhook secrets).
- Restrict file permissions on `instance/.env` in production (example: `chmod 600`).

## Monitoring

- Check `/health` for application status and version info.
- Prefer system-level monitoring (systemd, journalctl) for runtime health.
- Removed metrics/status subsystems stay removed; use the lightweight health endpoint.
- Prefer centralized log collection when running long-lived deployments.
