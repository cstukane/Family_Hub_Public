# ATTIC REACHABILITY AUDIT

**Date**: 2026-06-14
**Purpose**: Determine which experimental/frozen/attic subsystems are reachable from the active product, so a future cleanup pass can safely decide what to delete, freeze, or leave alone.
**Method**: Grep-based import/reference scan of all non-test project files (`.py`, `.html`, `.js`, `.css`, `.yaml`), excluding `.venv`, `__pycache__`, and test files (unless counting tests separately).

> ⚠️ **Status after 2026-06-14/15 cleanup passes:** News, Edge, Self-healing, and Metrics/Prometheus have been deleted. This audit now covers the remaining 8 attic subsystems.

---

## Summary Table

| Subsystem | Routes | Templates | Scheduler | Config | Tests | Dashboard visible? | Startup impact if deleted |
|-----------|--------|-----------|-----------|--------|-------|---------------------|---------------------------|
| ~~**edge**~~ | ✅ REMOVED | | | | | | |
| ~~**news**~~ | ✅ REMOVED | | | | | | |
| **iot / HA** | 3 | 0 | No | Yes | 2 files | ❌ No | Medium — imported in `api.py`, may break at import time |
| **chore** | 2 | 3 | No | Yes (disabled) | 0 files | ⚠️ Templates exist but `enabled: false` | Medium — partials and config chunk |
| **voice** | 2 | 2 | No | Yes (disabled) | 7 files | ⚠️ JS ships, but `features.voice: false` | Medium — config flag + JS + test conftest |
| **webhook** | 3 | 1 | ✅ Yes | Yes | 1 file | ⚠️ Admin panel only | High — scheduler job + dedicated route file |
| **plugins** | 3 | 3 | No | Yes | 1 file | ⚠️ Admin panel only | High — 4 plugin modules + migrations + route file |
| ~~**self_heal**~~ | ✅ REMOVED 2026-06-15 | | | | | | |
| **backup** | 3 | 6 | No | No | 3 files | ⚠️ Admin panel only | Medium — admin route + 6 template files |
| **update** | 3 | 0 | ✅ Yes | No | 3 files | ❌ No (admin+) | Medium — scheduler job + admin route |
| ~~**metrics**~~ | ✅ REMOVED 2026-06-15 | | | | | | |
| **weather_alert** | 3 | 1 | ✅ Yes | Yes | 3 files | ⚠️ Webhook admin panel | Medium — scheduler job + depends on webhooks |

---

## Detailed Findings

### 1. ~~Edge Computing (`hub/services/edge.py`)~~ ✅ **REMOVED 2026-06-14**
~~- **Main files**: `hub/services/edge.py` (15 KB)~~
~~- **Imports**: `hub/services/__init__.py` (lazy import only — `_LAZY_ATTRS`), referenced in `app.py` and `hub/config.py` but both are false positives (the word "edge" appears in unrelated contexts like "knowledge" or "hedge").~~
~~- **Active routes**: **None**. No route file imports or references this service.~~
~~- **Config**: Not configured anywhere.~~
~~- **Dashboard surface**: **None**. No templates reference it.~~
~~- **Tests**: `tests/test_edge_computing.py` (6 tests), `tests/test_service_gating.py` (mentions edge in optional service list).~~
~~- **Startup impact if deleted**: **Minimal**. Only loaded via lazy `__getattr__` in `hub/services/__init__.py`. Removing the lazy entries + the file + the test file is safe.~~
~~- **Recommendation**: ✅ **Safe deletion candidate.** Speculative code with zero reachability from the product.~~

---

### 2. ~~News (`hub/services/news_service.py`)~~ ✅ **REMOVED 2026-06-14**
~~- **Main files**: `hub/services/news_service.py` (301 lines), `config.yaml` (`news:` section)~~
~~- **Imports**: Only `hub/services/__init__.py` (direct import of `NewsItem`, `NewsService`, `news_service`).~~
~~- **Active routes**: **None**. No route file imports or references this service.~~
~~- **Scheduler**: **No news scheduler job.** Confirmed by reading `hub/scheduler.py` — only calendar, weather, sports, metrics, self_healing, update, weather_alerts, webhooks, casting.~~
~~- **Config**: `news.enabled: true` in `config.yaml` with 5 RSS sources — but **nothing reads this config** because no route or scheduler calls the news service.~~
~~- **Dashboard surface**: **None**. Zero references in templates. A text search for "news" across all `.html` files returned zero results.~~
~~- **Tests**: **Zero test files reference it.**~~
~~- **Startup impact if deleted**: **Minimal**. Only imported in `hub/services/__init__.py`. Removing the 3 import lines + the service file + the config section + the `__all__` entries is safe.~~
~~- **Recommendation**: ✅ **Safe deletion candidate.** This is the clearest case of dead code: config exists, service exists, but nothing calls it.~~

---

### 3. IoT / Home Assistant (`hub/services/iot_service.py`, `hub/adapters/homeassistant.py`)
- **Main files**: `hub/services/iot_service.py`, `hub/adapters/homeassistant.py`, IoT adapters for Alexa/Google Home/Roku
- **Imports**: 
  - `hub/services/__init__.py` (lazy import of `iot_service`, `IoTDevice`, `IoTService`)
  - `hub/routes/api.py` (imports `initialize_ha_adapter` from `hub.adapters.homeassistant`)
  - `hub/routes/api_media_admin.py` (references IoT)
  - `hub/routes/main.py` (references IoT)
  - `hub/config.py` (config schema includes IoT section)
  - `hub/adapters/__init__.py`
- **Active routes in dashboard**: The import in `hub/routes/api.py` is real — `initialize_ha_adapter` is called. However, this is for Home Assistant entities, which are not surfaced in the main dashboard UI (sidebar, tiles, etc.).
- **Config**: `iot.enabled: true` in `config.yaml` with Alexa/Google Home device types.
- **Dashboard surface**: **None visible in the redesigned dashboard.**
- **Tests**: `tests/test_homeassistant.py` (8 tests), `tests/test_api_routes.py` (HA API route tests)
- **Startup impact if deleted**: **Medium**. The import in `hub/routes/api.py` means removing it requires route cleanup. The `initialize_ha_adapter` call might fail gracefully already, but removing it would require a small route edit.
- **Recommendation**: ⚠️ **Needs human decision.** The HA adapter is imported in the primary API route file and has active API endpoints. However, it's not visible on the dashboard. Two options: (a) leave frozen but strip from README features (already done), or (b) remove the HA route endpoints and the service/adapter files after confirming nothing in the dashboard calls those endpoints.

---

### 4. Chore Management (`hub/services/chore_service.py`)
- **Main files**: `hub/services/chore_service.py`, `templates/partials/chore_modal.html`, `templates/partials/chore_panel.html`, `static/js/fragments/chore.js`
- **Imports**: `hub/services/__init__.py`, `hub/routes/api_media_admin.py`, `hub/routes/main.py`, `hub/migrations/chores.py`
- **Active routes**: References in `api_media_admin.py` and `main.py` (likely route registration for chore endpoints).
- **Templates**: 3 template files (`chore_modal.html`, `chore_panel.html`, and `base.html` references them). JS fragment exists.
- **Config**: `chores.enabled: false` in `config.yaml`. **The feature is explicitly disabled.**
- **Dashboard surface**: **Not visible** — disabled by config flag. Templates exist but are gated behind `enabled: false`.
- **Tests**: **Zero test files reference chore functionality.**
- **Startup impact if deleted**: **Medium**. Route files reference it, and `base.html` likely has a conditional include. Migration script references it. Removing it requires coordinated cleanup across ~7 files.
- **Recommendation**: ⚠️ **Needs human decision.** Disabled by config, not tested, not visible. Either the family wants it (then enable it and add proper tile support) or it should be removed. **Lean: deletion candidate if family confirms they won't use it.**

---

### 5. Voice Commands (`hub/services/voice.py`, `hub/services/local_voice.py`)
- **Main files**: `hub/services/voice.py`, `hub/services/local_voice.py`, `static/js/voice.js`
- **Imports**: `hub/services/__init__.py`, `hub/routes/api.py`, `hub/routes/main.py`, `hub/config.py`
- **Active routes**: `hub/routes/api.py` imports `voice` from services (line 14).
- **Templates**: `templates/base.html` (voice JS include), `templates/admin/config.html` (voice toggle in admin).
- **Config**: `features.voice: false` in `config.yaml`. **Disabled.**
- **Dashboard behavior**: `voice.js` ships and logs "not enabled" on every page load. No voice functionality is active when disabled.
- **Tests**: 7 test files (`test_voice.py`, `test_voice_commands.py`, `conftest.py`, `e2e/conftest.py`, `test_config.py`, `test_photos_music.py`, `test_service_gating.py`).
- **Startup impact if deleted**: **Medium**. Imported in `api.py` and `conftest.py`. The route import likely just makes voice commands available but they're gated by the config flag. Removing it requires route + conftest cleanup.
- **Recommendation**: ⚠️ **Needs human decision.** Disabled by default, ships unused JS on every page, has a large test footprint. Two options: (a) keep as-is (frozen attic), or (b) remove voice service + JS + tests but preserve the config flag as a no-op. **Lean: keep frozen until a future cleanup pass is ready to touch `api.py` and `conftest.py`.**

---

### 6. Webhooks (`hub/services/webhook.py`)
- **Main files**: `hub/services/webhook.py` (20 KB), `hub/routes/api_webhooks.py`, `templates/partials/webhook_management.html`, `hub/migrations/webhooks.py`
- **Imports**: `hub/services/__init__.py`, `hub/services/weather_alert.py` (weather alerts trigger webhooks), `hub/routes/api_media_admin.py`, `hub/routes/main.py`, `hub/utils/http.py`
- **Active routes**: **Yes** — `hub/routes/api_webhooks.py` is a dedicated route file (exists in `hub/routes/__init__.py` as a blueprint). `api_media_admin.py` and `main.py` also reference webhooks.
- **Scheduler**: ✅ **Active scheduler job** — `check_webhook_statuses` runs every 15 minutes.
- **Templates**: `templates/partials/webhook_management.html` (admin UI).
- **Config**: `webhooks:` section in `config.yaml` with a "Weather Alerts" example.
- **Dashboard surface**: **Admin panel only** — not on the main kiosk dashboard.
- **Tests**: `tests/test_webhooks.py` (6 tests).
- **Startup impact if deleted**: **High**. Has a scheduler job, dedicated route file, migrations, and is imported by the weather_alert service. Removing it would require coordinated cleanup across scheduler, routes, and weather_alert.
- **Recommendation**: ⚠️ **Needs human decision.** This is the most deeply wired attic subsystem. It's a webhook platform for one house, as PRODUCT_DIRECTION.md notes. Two options: (a) freeze it and stop maintaining tests/config, or (b) remove it entirely including the scheduler job, route file, and `weather_alert.py` dependency. **Lean: demote to "freeze" — too many dependencies to remove safely in a single pass.**

---

### 7. Plugins System (`hub/services/plugins.py`, `hub/plugins/`)
- **Main files**: `hub/services/plugins.py`, `hub/plugins/base.py`, `hub/plugins/manager.py`, `hub/plugins/marketplace.py`, `hub/plugins/sandbox.py`, `hub/routes/api_plugins.py`, `hub/migrations/plugins.py`
- **Imports**: `hub/services/__init__.py` (lazy imports for 12 plugin functions), `app.py` (registers plugin blueprint), `hub/routes/main.py`, `hub/routes/api_media_admin.py`, `hub/services/media_launcher.py`
- **Active routes**: **Yes** — `hub/routes/api_plugins.py` is a dedicated route file, registered as a blueprint in `app.py`.
- **Templates**: `templates/admin/plugins.html`, `templates/admin/admin.html`, `templates/admin/system.html` (admin panel only).
- **Config**: `features.plugins: true` in `config.yaml` schema (not present in the live config but validated).
- **Dashboard surface**: **Admin panel only.**
- **Tests**: `tests/test_plugins.py` (12 tests).
- **Startup impact if deleted**: **High**. Registered as a Flask blueprint in `app.py`, has 4 plugin modules, migrations, and is referenced in `media_launcher.py`. Requires coordinated removal from `app.py`, routes, services init, and migrations.
- **Recommendation**: ⚠️ **Needs human decision.** No evidence of a real plugin. PRODUCT_DIRECTION.md says "freeze." The blueprint registration in `app.py` makes it one of the more invasive removals. **Lean: freeze (do not delete yet) — too entangled for a safe cleanup pass.**

---

### 8. Self-Healing (`hub/services/self_heal.py`)
- **Main files**: `hub/services/self_heal.py`
- **Imports**: `hub/services/__init__.py`, `hub/scheduler.py` (scheduler job), `hub/routes/api_admin.py`
- **Active routes**: Admin route only (`api_admin.py`).
- **Scheduler**: ✅ **Active scheduler job** — `run_periodic_self_healing` runs every 30 minutes.
- **Dashboard surface**: **None** (admin panel only).
- **Tests**: `tests/services/test_self_heal.py` (8 tests), `tests/routes/test_admin_api.py` (admin healing endpoint).
- **Startup impact if deleted**: **Medium**. Has a scheduler job. Removing it requires deleting the scheduler job + admin route reference + service file + tests.
- **Recommendation**: ✅ **Safe deletion candidate** (with small coordinated edits). PRODUCT_DIRECTION.md notes: "A `/health` endpoint and a systemd restart policy cover 95% of this." The scheduler job can be removed, the admin route reference cleaned up, and the service file deleted. This is self-contained and doesn't affect the dashboard.

---

### 9. Backup (`hub/services/backup.py`)
- **Main files**: `hub/services/backup.py`
- **Imports**: `hub/services/__init__.py`, `hub/services/admin.py`, `hub/services/update.py`, `hub/services/sports_ticker_service.py`, `hub/db.py`, `hub/utils/logging_config.py`
- **Active routes**: `hub/routes/api_admin.py`, `hub/routes/api_media_admin.py`, `hub/routes/main.py` (admin routes only).
- **Templates**: 6 admin templates reference backup functionality (`admin/backup.html`, `admin/admin.html`, `admin/config.html`, `admin/diagnostics.html`, `admin/system.html`, `admin/updates.html`).
- **Scheduler**: **No scheduler job.**
- **Dashboard surface**: **Admin panel only.**
- **Tests**: `tests/services/test_backup.py` (4 tests), `tests/routes/test_admin_api.py`, `tests/test_updates.py`.
- **Startup impact if deleted**: **Medium**. No scheduler job, but imported by `admin.py`, `update.py`, and `sports_ticker_service.py` (likely for backup-before-update patterns). 6 admin templates reference it.
- **Recommendation**: ⚠️ **Needs human decision.** PRODUCT_DIRECTION.md: "Reasonable instincts, enterprise execution." The backup-before-update integration with `sports_ticker_service.py` is unexpected and suggests the sports ticker service may call backup functions. **Lean: freeze — investigate the sports_ticker dependency before attempting deletion.**

---

### 10. Update / Self-Update (`hub/services/update.py`)
- **Main files**: `hub/services/update.py` (16 KB)
- **Imports**: `hub/services/__init__.py`, `hub/scheduler.py`, `hub/routes/api_admin.py`, `hub/routes/api_media_admin.py`, `hub/routes/api_plugins.py`, `hub/plugins/marketplace.py`
- **Active routes**: 3 admin route files reference updates.
- **Scheduler**: ✅ **Active scheduler job** — `check_for_updates_and_notify` runs daily.
- **Dashboard surface**: **None** (admin panel only).
- **Tests**: `tests/services/test_update.py` (4 tests), `tests/test_updates.py` (10 tests), `tests/routes/test_admin_api.py`.
- **Startup impact if deleted**: **Medium**. Has a daily scheduler job. Imported by plugins marketplace. The prior audit noted it's "partially `not_implemented` by design."
- **Recommendation**: ✅ **Safe deletion candidate** (with coordinated edits). PRODUCT_DIRECTION.md: "A kiosk updates via `git pull` + systemd restart." The scheduler job can be removed, admin route references cleaned up, and the service + tests deleted. The plugins marketplace dependency is the only entanglement — remove both together or remove the marketplace reference first.

---

### 11. Metrics / Prometheus / Status (`hub/services/metrics.py`)
- **Main files**: `hub/services/metrics.py` (29 KB)
- **Imports**: `hub/services/__init__.py`, `hub/scheduler.py`, `hub/services/calendar.py`, `hub/services/sports_ticker_service.py`
- **Active routes**: **None directly.** The `/status` and `/metrics` endpoints exist as routes in some form but were not flagged by the route scan — they may be served through a different mechanism.
- **Scheduler**: ✅ **Active scheduler job** — `log_metrics` runs every 5 minutes and logs to the audit table.
- **Dashboard surface**: `/status` page exists but is not part of the main dashboard flow.
- **Tests**: `tests/test_metrics.py`, `tests/test_metrics_enhanced.py`, `tests/test_metrics_phase13.py` (3 files, ~24 tests).
- **Startup impact if deleted**: **Low/Medium**. Scheduler job runs every 5 minutes, but removing it just means fewer audit log entries. The `/health` endpoint is in `api.py`, not in metrics. The metrics service is imported by `calendar.py` and `sports_ticker_service.py` — these may be logging metrics internally.
- **Recommendation**: ✅ **Safe-ish deletion candidate** (check calendar/sports imports first). PRODUCT_DIRECTION.md: "A `/health` endpoint and a systemd restart policy cover 95% of this. Keep `/health`, demote the rest." The 5-minute metrics logging is pure overhead for a single kiosk. But the calendar and sports services importing metrics means those imports need checking before deletion.

---

### 12. Weather Alerts (`hub/services/weather_alert.py`)
- **Main files**: `hub/services/weather_alert.py`
- **Imports**: `hub/services/__init__.py`, `hub/services/webhook.py` (weather alerts trigger webhooks), `hub/scheduler.py`, `hub/routes/api_weather.py`, `hub/routes/api_webhooks.py`, `hub/routes/api_media_admin.py`, `hub/config.py`, `hub/migrations/weather.py`
- **Active routes**: 3 route files reference it.
- **Scheduler**: ✅ **Active scheduler job** — `monitor_weather_alerts` runs every 30 minutes.
- **Templates**: `templates/partials/webhook_management.html` (admin).
- **Config**: Weather alert thresholds in config schema.
- **Dashboard surface**: **Admin/notification only** — not a dashboard tile.
- **Tests**: `tests/test_weather_alerts.py` (3 tests), `tests/test_webhooks.py`, `tests/test_service_gating.py`.
- **Startup impact if deleted**: **High**. Tightly coupled to the webhook system. Its scheduler job checks weather thresholds and fires webhooks. Deleting it means either deleting webhooks too or breaking that integration.
- **Recommendation**: ⚠️ **Tied to webhook decision.** If webhooks are deleted, weather_alerts should be deleted too (they are the only consumer of the webhook trigger logic). If webhooks are frozen, weather_alerts should be frozen alongside them.

---

## Startup/Runtime Impact Summary

If you were to delete ALL 12 subsystems tomorrow, here's what would need attention:

| What would break | Severity | Fix required |
|-----------------|----------|-------------|
| `hub/services/__init__.py` | **Critical** | Remove ~80 import lines and `__all__` entries |
| `hub/scheduler.py` | **High** | Remove 5 scheduler jobs (self_heal, update, metrics, weather_alerts, webhooks) |
| `hub/routes/api.py` | **High** | Remove `voice` and `homeassistant` imports |
| `hub/routes/api_media_admin.py` | **High** | Remove references to chores, IoT, webhooks, plugins, backup, update, weather_alerts |
| `hub/routes/main.py` | **Medium** | Remove chore/IoT/webhook/plugin/voice/backup route registrations |
| `hub/routes/api_admin.py` | **Medium** | Remove self_heal, backup, update references |
| `hub/routes/api_webhooks.py` | **Low** | Delete entire file |
| `hub/routes/api_plugins.py` | **Low** | Delete entire file |
| `app.py` | **Medium** | Remove plugin blueprint registration |
| `templates/base.html` | **Medium** | Remove chore panel include, voice.js include |
| `hub/config.py` | **Medium** | Strip IoT, chore, news, webhook, weather_alert config sections |
| `config.yaml` | **Low** | Remove stale config sections |
| `conftest.py` | **Low** | Remove voice imports |
| Admin templates | **Low** | Remove backup/plugin/webhook admin pages |
| Migration files | **Low** | Remove chore/webhook/plugin/weather migrations |
| ~12 test files | **Low** | Delete or update |

---

## Recommended Cleanup Order (Safest First)

This is the recommended order for a future cleanup pass, starting with items that have the lowest risk of breaking anything:

### Tier 1: Definitely Safe — Can Delete in One Pass
1. **News** — Zero routes, zero scheduler jobs, zero templates, zero tests. Only in `__init__.py`. Delete: `news_service.py` + 3 import lines in `__init__.py` + `news:` config section.
2. **Edge** — Zero routes, zero scheduler jobs. Only lazy-loaded in `__init__.py`. Delete: `edge.py` + lazy entries in `__init__.py` + test file.

### Tier 2: Safe with Minor Coordinated Edits
3. **Self-healing** — Remove scheduler job + admin route reference + service file + tests. Self-contained.
4. **Metrics** — Remove 5-minute scheduler job + service file + tests. Check calendar/sports imports first.
5. **Update** — Remove daily scheduler job + service file + admin references + tests. Also remove from plugins marketplace.

### Tier 3: Requires Human Decision (Family Usage Call)
6. **Chores** — Disabled in config, no tests, but templates + JS + route references exist. Delete if family confirms they won't use it.
7. **Voice** — Disabled in config, JS ships on every page load, 7 test files depend on it. Delete if family confirms they won't use it, or keep frozen.

### Tier 4: Interdependent — Must Be Removed Together or Not at All
8. **Weather Alerts + Webhooks** — Tightly coupled. Weather alerts feed webhooks. If webhooks go, weather alerts go too. If webhooks stay, weather alerts stay. This pair has the deepest wiring (scheduler, dedicated route files, migrations, admin templates).
9. **IoT / Home Assistant** — Imported in primary `api.py` route. Requires route surgery to remove cleanly. Decision: does the family use any smart home features through the hub?

### Tier 5: Most Invasive — Leave for Last
10. **Plugins** — Blueprint registered in `app.py`, 4 plugin modules, marketplace, sandbox, migrations. The most invasive removal. PRODUCT_DIRECTION.md says "freeze" — this is the right call for now.

---

## Verification

- **Tests pass**: 335 passed (same as before this audit — no code was changed).
- **Audit script**: One-shot `_audit_reachability.py` was written, executed, and deleted. All data captured in this document.
- **False positives removed**: The audit script flagged some `.venv` site-packages files and false keyword matches (e.g., "edge" in "knowledge"). These were manually filtered out. The "edge" hits in `app.py`, `hub/config.py`, and `static/js/voice.js` were verified as false positives (the word "edge" appears in unrelated contexts like "knowledge" / variable names, not as an import of the edge computing service).

---

## Files Changed in This Pass

- **Created**: `docs/ATTIC_REACHABILITY_AUDIT.md` (this file)
- **No code was modified, deleted, or refactored.**