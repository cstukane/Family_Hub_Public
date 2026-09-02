# Test Corrections

This document maps the currently observed failing tests to the most likely correction. It separates real product defects from stale assertions and local environment issues.

## Scope

- Source run reviewed: local `python -m pytest -q` after the Playwright collection fix.
- Result reviewed: `13 failed, 315 passed, 15 errors`.
- Already addressed separately: optional Playwright collection is now gated so CI running only `.[dev]` does not fail during test discovery.

## Corrections

| Failing test(s) | Type | Current issue | Recommended correction | Primary files |
| --- | --- | --- | --- | --- |
| `tests/routes/test_casting_api.py::TestCastingAPIRoutes::test_get_device_status` | Test is stale | The endpoint can legitimately return `404` when casting is enabled but no adapter exists for the requested device. The test only allows `200` or `400`. | Update the assertion to allow `404`, or patch `hub.services.casting.casting_manager.get_adapter_for_device` and assert the exact intended branch. | `tests/routes/test_casting_api.py`, `hub/routes/api_media_admin.py` |
| `tests/test_keyboard_shortcuts.py::test_media_launcher_status_endpoint_exists` | Test is stale | The canonical route lives in `hub/services/media_launcher.py`, but the test reads the thin shim at repo root `media_launcher.py`. | Point the file-content assertion at `hub/services/media_launcher.py`, or replace the file-content check with an app/route-level test against `/v1/media_status`. | `tests/test_keyboard_shortcuts.py`, `hub/services/media_launcher.py`, `media_launcher.py` |
| ~~`tests/test_metrics.py::test_metrics_service`~~ | ✅ OBSOLETE | Test file deleted 2026-06-15 (metrics subsystem removed). | N/A | N/A |
| ~~`tests/test_metrics_enhanced.py::test_log_metrics_to_db_with_new_metrics`~~ | ✅ OBSOLETE | Test file deleted 2026-06-15 (metrics subsystem removed). | N/A | N/A |
| ~~`tests/test_metrics_enhanced.py::test_get_status_page_data_with_new_metrics`~~ | ✅ OBSOLETE | Test file deleted 2026-06-15 (metrics subsystem removed). | N/A | N/A |
| `tests/test_plugins.py::TestPluginManager::test_discover_plugins` | Local environment issue | Failure is `PermissionError` creating temp directories under `<system-temp>\\...`. This is not caused by plugin manager logic. | Harden the test to use a writable repo-local temp path or pytest `tmp_path` configured under the workspace. On this machine, avoid the default global temp directory. | `tests/test_plugins.py` |
| `tests/test_plugins.py::TestPluginManager::test_load_plugin` | Local environment issue | Same `PermissionError` as above while creating plugin fixture directories. | Same fix: use a writable workspace temp directory instead of the default global temp location. | `tests/test_plugins.py` |
| `tests/test_scheduler.py::test_create_scheduler` | Test is stale | `create_scheduler(app)` intentionally does not start the scheduler when `TESTING` is true. The test unconditionally calls `scheduler.shutdown()`, which raises `SchedulerNotRunningError`. | Change teardown to `if scheduler.running: scheduler.shutdown()` or explicitly start the scheduler in the test before shutting it down. | `tests/test_scheduler.py`, `hub/scheduler.py` |
| `tests/test_sports_ticker_service.py::TestSportsTickerService::test_fetch_sports_data_with_resilience` | Test is stale vs current behavior | The service now post-processes ESPN results through `_ensure_future_events_for_favorites()` and `_filter_final_events_by_retention()`. A final game dated `2024-01-15` is filtered out as old, so the returned event list is empty. | Update the fixture date to a current date relative to test execution, or patch the retention/filter helpers so the test only validates response normalization. | `tests/test_sports_ticker_service.py`, `hub/services/sports_ticker_service.py` |
| `tests/test_updates.py::test_get_update_history` | Test patch target is wrong | The test patches `hub.db.get_db`, but `hub/services/update.py` imported `get_db` directly. The real `get_db()` runs without app context and raises. | Patch `hub.services.update.get_db` instead. Optionally wrap the call in `app.app_context()` if the service is expected to run in Flask context. | `tests/test_updates.py`, `hub/services/update.py` |
| `tests/test_updates.py::test_rollback_update` | Test patch target is wrong | Same direct-import issue as above: patching `hub.db.get_db` does not affect `hub.services.update.get_db`. | Patch `hub.services.update.get_db`. | `tests/test_updates.py`, `hub/services/update.py` |
| `tests/test_updates.py::test_schedule_update_check` | Test is stale | The implementation is explicitly a stub and returns `{"status": "not_implemented"}`. The test still expects `"success"`. | Update the test to assert the current stub contract, or implement real scheduler registration and then update both the code and test together. | `tests/test_updates.py`, `hub/services/update.py` |
| `tests/test_updates.py::test_graceful_update_shutdown` | Test patch target is wrong | Same direct-import issue as `get_update_history` and `rollback_update`. | Patch `hub.services.update.get_db`. | `tests/test_updates.py`, `hub/services/update.py` |
| `tests/test_service_gating.py::test_optional_services_disabled_do_not_start_threads` | Test teardown issue plus local temp issue | In the full suite, teardown calls `app.scheduler.shutdown()` even though the scheduler is not started in test mode. In isolated local reruns, `tmp_path` also fails due a temp-directory permission issue on this machine. | Guard teardown with `if hasattr(app, "scheduler") and app.scheduler.running:`. If the temp-dir permission issue persists locally, configure pytest temp roots inside the workspace. | `tests/test_service_gating.py`, `app.py`, `hub/scheduler.py` |
| `tests/e2e/test_dashboard.py` collection on CI without Playwright | Already fixed | CI installed only `.[dev]`, but e2e tests imported Playwright during collection. | Fixed by gating `tests/e2e` collection when `playwright` and `pytest-playwright` are not installed. | `tests/conftest.py`, `tests/e2e/test_dashboard.py` |

## Priority Order

1. Fix wrong patch targets in update and metrics tests.
2. Fix stale scheduler teardown tests for non-running schedulers.
3. Fix stale assertion tests for casting status, media launcher path, and sports ticker retention behavior.
4. Decide whether update scheduling remains a stub or becomes implemented behavior.
5. Normalize pytest temp-directory usage for local Windows runs if the `PermissionError` reproduces outside this sandbox.

## Notes

- The metrics and update failures are primarily test-isolation problems, not necessarily regressions in production behavior.
- The scheduler-related failures are caused by test assumptions that conflict with the deliberate `TESTING` behavior in `app.py` and `hub/scheduler.py`.
- The Playwright CI collection issue is the only failure in this set that directly blocked GitHub Actions collection before tests even ran.
