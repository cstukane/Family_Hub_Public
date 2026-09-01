# RUNBOOK  Family Hub (Ops)

## Service Management
```
# Start/Stop/Restart
sudo systemctl start|stop|restart family-hub@<user>.service
sudo systemctl start|stop|restart family-hub-kiosk@<user>.service
sudo systemctl start|stop|restart nginx-family-hub@<user>.service  # For SSL/HTTPS setup

# Check status
sudo systemctl status family-hub@<user>.service
sudo systemctl status family-hub-kiosk@<user>.service
sudo systemctl status nginx-family-hub@<user>.service

# Check both services at once
sudo systemctl status 'family-hub*@<user>.service'
```

## Logs
```
# Application logs
sudo journalctl -u family-hub@<user> -f

# File logs (if LOG_FILE is enabled)
tail -f /opt/family-hub/logs/family_hub.log

# Kiosk browser logs
sudo journalctl -u family-hub-kiosk@<user> -f

# Nginx logs (for SSL/HTTPS)
sudo journalctl -u nginx -f
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Both services
sudo journalctl -fu 'family-hub*@<user>.service'
```

## Health Check

<!-- AUTO-GENERATED from hub/routes/ -->
| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | None | App status, timestamp, version, platform |
| `GET /api/status/summary` | None | Sidebar counts + weather/calendar/system status messages in one call |
| ~~`GET /api/admin/health-check`~~ | (removed 2026-06-14) | Deleted with self-healing subsystem |
| ~~`GET /status`~~ | (removed 2026-06-14) | Deleted with metrics subsystem |

Examples:
```bash
curl http://localhost:5000/health
curl http://localhost:5000/api/status/summary
make deploy-test  # runs health check as part of deployment verification
```
<!-- END AUTO-GENERATED -->

## Security Management
### Rate Limiting
- Check current rate limits in application logs
- Default: 60 requests per minute for general endpoints
- Admin: 10 requests per minute for sensitive endpoints
- To adjust limits, modify `security.default_rate_limit` and `security.admin_rate_limit` in `instance/config.yaml`

### IP Whitelist Management
- To add/remove IPs from whitelist, update `security.ip_whitelist` in `instance/config.yaml`
- Restart service after changes: `sudo systemctl restart family-hub@<user>.service`
- IPs are checked for admin endpoints

### SSL Certificate Management
- Certificates location: `/etc/letsencrypt/live/yourdomain.com/`
- Fullchain: `/etc/letsencrypt/live/yourdomain.com/fullchain.pem`
- Private key: `/etc/letsencrypt/live/yourdomain.com/privkey.pem`
- Auto-renewal: Add to crontab: `0 12 * * * /usr/bin/certbot renew --quiet`

## Secrets Management
- Location: `/opt/family-hub/instance/.env`
- Contains: API keys, OAuth tokens, database credentials
- Permissions: `600` (readable only by service user)
- Rotation: update `/opt/family-hub/instance/.env` and restart services

## Backups
- Admin API (recommended):
  - List: `GET /api/admin/backup`
  - Create: `POST /api/admin/backup` (optional body `{ "name": "custom.tar.gz" }`)
  - Restore: `POST /api/admin/restore/<backup_name>`
  - Download: `GET /api/admin/backup/<backup_name>/download`
- CLI database backup: `flask backup-db` (creates a timestamped SQLite backup)
- Manual backup: `cp /opt/family-hub/instance/family_hub.db /backup/location/`
- Backups stored in: `/opt/family-hub/instance/backups/`

## Logging Configuration
- Configure via `instance/.env`:
  - `LOG_LEVEL`, `LOG_CONSOLE`, `LOG_FILE`
  - `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT` for rotation
  - `LOG_FORMAT`, `LOG_DATE_FORMAT` for output formatting
- Default log file: `logs/family_hub.log`

## Monitoring and Alerting

> ⚠️ **Note (2026-06-14):** `/metrics` (Prometheus) and `/status` were removed along with the metrics subsystem. The `/health` endpoint remains for lightweight status checks. System-level monitoring (systemd, journalctl) is preferred for a single-deployment kiosk.

## Common Issues
- **Blank weather**: check network connectivity; see banner timestamp; tail app logs: `journalctl -u family-hub@<user> -f`
- **Calendar missing**: ICS URL changed; update `instance/config.yaml` and restart the app service
- **Kiosk not launching**: verify DISPLAY environment, user permissions in kiosk unit; check Chromium path
- **Display not available**: ensure X11 session is running: `echo $DISPLAY`
- **Services not starting**: check `instance/.env` permissions and content, verify all required environment variables are present
- **SSL/HTTPS not working**: verify nginx configuration with `sudo nginx -t`, check certificate paths in `/etc/nginx/sites-enabled/family-hub.conf`
- **Rate limit exceeded**: Check application logs for rate limit messages. Increase limits in config if legitimate.
- **Access denied (IP whitelist)**: Verify client IP is in `instance/config.yaml` under `security.ip_whitelist`, restart service after changes.

## Sports Ticker Management
### Troubleshooting Repeated 429s (Rate Limits)
- Check application logs for repeated HTTP 429 responses: `journalctl -u family-hub@<user> -f | grep -i "429"`
- If repeatedly seeing rate limits, consider reducing polling frequency by adjusting the ticker intervals in `instance/config.yaml`
- Verify the configured polling cadence defaults: `idle`, `active`, and `post_final` settings
- Temporarily disable the ticker using the admin toggle in Settings if needed for troubleshooting: `curl -X PUT -H "Content-Type: application/json" -d '{"enabled": false}' http://localhost:5000/api/admin/sports-ticker/enabled`

### Forcing Sports Ticker Refresh
- To manually refresh the sports ticker data: `curl -X POST http://localhost:5000/api/admin/sports-ticker/refresh`
- Check the status of the ticker by visiting `/api/sports/ticker` in your browser or using curl
- Verify the last updated time and freshness of data in logs: `journalctl -u family-hub@<user> -f | grep -i "sports_ticker"`

### Interpreting `meta` Flags in Sports Ticker Data
When examining the ticker data, pay attention to these `meta` fields:
- `stale`: When `true`, indicates data is older than the configured threshold (typically 2-3 minutes for live games, 5 minutes for others)
- `cache_age_seconds`: Shows how long ago the data was cached; useful for diagnosing freshness issues
- `fetch_error_reason`: Contains the last error that occurred during data retrieval
- `consecutive_empty_count`: Number of consecutive times the ticker returned empty; if >3, ticker may auto-hide
- `should_hide`: When `true`, indicates ticker should be hidden due to multiple consecutive empty responses
- `favorites`: List of teams being tracked for priority display
- `source`: Which data source provided the information (`espn-scoreboard-v1`)

### Checking Sports Ticker Metrics
- The ticker tracks several performance metrics including:
  - Fetch latency (time to retrieve data from ESPN)
  - Cache hit/miss rates
  - Write duration (time to save to cache file)
- Monitor these metrics through logs or by accessing the metrics endpoint at `/metrics`
- Look for patterns of failed fetches or high latency that might indicate network or API issues

## Deployment
- Deploy: `sudo make deploy` (generates systemd files, enables and starts services)
- Update: intentionally manual (`git pull`, tests, then service restart); automatic checks are dormant by default
- Rollback: Use admin interface or API to rollback to previous version with backup restoration