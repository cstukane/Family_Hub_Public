# IMPLEMENTATION_PHASES — Family Hub

*Generated 2026-07-02 from the current repo review, the 2026-07-02 product review, prior product-direction docs, and the current repo roadmap/config state.*

Family Hub is a local-first, always-on kitchen TV dashboard and homelab launcher. Its product loop is intentionally small:

1. Walk into the kitchen.
2. In a few seconds, know what is next today, weather, commute status, and relevant sports/scores.
3. Occasionally touch the screen to add a shopping item, set a timer, control music, or open a sibling/homelab app.

This file is the implementation roadmap. It supersedes expansionist roadmap items that would turn Family Hub into Command Center, a smart-home control surface, a plugin platform, or a full family operating system.

## Source Anchors

Use these files as the primary source of truth before implementing phases:

- `README.md` — current product framing and feature summary.
- `PRODUCT_DIRECTION.md` — product identity, convergence guidance, and attic warnings.
- `docs/PRODUCT_REVIEW.md` — Fable product/architecture review and roadmap sharpening.
- `docs/design/STYLE.md` — dark, calm, TV-first visual contract.
- `docs/design/UX_TARGETS.md` — how the Claude Design export should influence real UI.
- `docs/ATTIC_REACHABILITY_AUDIT.md` — attic subsystem reachability and deletion/freeze notes.
- `docs/API_CONTRACTS.md` — route and endpoint reference.
- `docs/DEPLOYMENT.md` — systemd/kiosk deployment guidance.
- `config.example.yaml` — safe tracked defaults; ignored `instance/config.yaml` is the live deployment config.
- `.env.example`, ignored `instance/.env`, and deployment scripts — the documented secrets model.
- `app.py`, `hub/config.py`, `hub/scheduler.py`, `hub/routes/main.py`, `hub/routes/api.py`.
- `templates/base.html`, `templates/partials/*`, `static/css/base.css`, `static/js/fragments/*`.
- Core service/cache files for calendar, weather, commute, sports ticker, shopping, timers, media launcher, and Spotify/miniplayer.

## Agent Operating Rules

- Before implementing a phase, inspect the current repo state. Do not assume this file is perfectly current.
- Keep Family Hub appliance-shaped. Prefer convergence, trust, privacy, and reliability over feature growth.
- Do not add new panels, providers, smart-home controls, voice, profiles, plugins, auth, or Command Center-style workflows unless a phase explicitly calls for it.
- If inspection suggests a phase should be narrowed, delayed, split, merged, renamed, or materially changed, stop and explain the proposed change before editing.
- Do not perform destructive git history rewrites, secret scrubs, or force pushes without explicit owner approval.
- Do not repeat or print sensitive real config values in logs, docs, commits, examples, tests, or review notes.
- Prefer tests around behavior and rendered state over broad refactors.
- Use the existing Flask + Jinja + HTMX + Socket.IO + APScheduler + SQLite shape. Do not introduce a frontend framework.
- For normal validation, run `pytest --ignore=tests/e2e`. Use e2e/kiosk/manual checks only when the phase touches layout, browser behavior, or deployment.

---

## Phase 1 - Product Identity and Redesign Baseline

**Status:** Completed / Preserve

### Goal

Preserve the work already done to make Family Hub a coherent appliance: honest README, deleted attic subsystems, committed TV-first redesign, and a clear product direction.

### Deliverables

- Keep the README framing centered on the kitchen TV dashboard and homelab launcher.
- Preserve the committed dashboard shape:
  - main calendar canvas,
  - bottom Up Next / Shopping / Commute-or-Timer tiles,
  - right rail with clock, quick tools, weather, and miniplayer,
  - bottom app dock and sports ticker.
- Preserve the June cleanup stance:
  - news, edge, self-heal, and metrics/Prometheus remain removed.
  - `/health` remains the lightweight status endpoint.
  - systemd restart + cache-on-disk remain the resilience strategy.
- Protect the current shopping tile improvements:
  - tile is tappable,
  - empty state is visible,
  - `+ Add item` affordance remains clear.
- Protect miniplayer disconnected/no-track polish from regressions.

### Non-Goals

- Do not rebuild the UI from the Claude Design export.
- Do not introduce React or another SPA framework.
- Do not add new dashboard cards.
- Do not resurrect removed subsystems.
- Do not treat this completed phase as an excuse to freeze all future UI polish.

### Acceptance Criteria

- README and `PRODUCT_DIRECTION.md` still describe the same product.
- Home dashboard renders the core one-screen experience.
- Shopping tile empty state remains actionable.
- Removed systems are not reintroduced.
- Existing tests still pass with `pytest --ignore=tests/e2e`.

---

## Phase 2 - Privacy and Config Hygiene

**Status:** Completed 2026-08-12

### Goal

Remove private, deploy-specific, and location-specific values from tracked canonical files, and make it clear where real local configuration belongs.

This phase comes first because privacy/config leaks get worse over time, especially if the repo is ever made public, cloned to additional machines, mirrored, or shared with coding agents.

### Deliverables

- Create or update `config.example.yaml` with placeholder-safe values for:
  - home/work addresses,
  - LAN IPs,
  - Tailscale hostnames,
  - SSL certificate paths,
  - map/Spotify/Google credentials,
  - webhook URLs/secrets,
  - local app ports and labels where appropriate.
- Move real deploy-specific config out of tracked source:
  - preferred locations: `.env`, `instance/secrets.env`, `instance/config.yaml`, or a documented local override path.
  - update `.gitignore` so real config files are not re-added.
- Scrub README examples so they do not contain real addresses, hostnames, local IPs, or private deployment details.
- Update `docs/DEPLOYMENT.md` and `.env.example` so a junior dev knows how to configure a local copy without copying private values.
- Ensure app boot still works from a safe example configuration or clearly documented local config path.
- Add or update tests for public config exposure:
  - public/browser config should not expose raw home/work street addresses.
  - public/browser config should not expose secret tokens.
  - only intentionally public map/client values may be exposed, and only if documented.
- Add an explicit note: git history rewrite is a separate manual decision, not part of this phase unless the owner approves it.

### Non-Goals

- Do not rewrite git history without explicit approval.
- Do not remove commute functionality.
- Do not break local kiosk deployment.
- Do not invent a full multi-environment config framework.
- Do not add auth as a privacy substitute.

### Acceptance Criteria

- No tracked README/config/example file contains real private location or network details.
- `config.example.yaml` is safe to commit and share.
- Real local config is documented and ignored by git.
- The app can run with safe defaults or clear local setup instructions.
- Tests or targeted checks confirm public config does not leak raw private fields.
- If history rewrite is needed, it is documented as a separate owner-approved operation.

---

## Phase 3 - Core Tile Trust: Freshness, Staleness, and Failure States

**Status:** Planned / Start After Phase 2

### Goal

Make the wall trustworthy. Every core resting tile should quietly communicate whether its data is fresh, stale, failed, or needs reconnect.

The target is not a noisy monitoring dashboard. The target is quiet honesty.

### Deliverables

Apply one consistent freshness/failure pattern to these surfaces:

- Weather tile and weather modal.
- Calendar week grid.
- Up Next tile.
- Commute tile, preserving existing update/stale behavior.
- Sports ticker.
- Center zone or any fallback/preview module already showing last-updated state.

Implementation should include:

- reusable helper/context shape for:
  - `last_updated`,
  - freshness age,
  - stale threshold,
  - error state,
  - auth/reconnect state where relevant.
- visual treatment in the design language from `docs/design/STYLE.md`:
  - subtle updated badge,
  - amber stale state,
  - quiet failed state,
  - non-alarming reconnect action where useful.
- Google Calendar token-expiry UX:
  - clear message such as calendar cannot sync,
  - tap/click path to reconnect when feasible,
  - no silent blank calendar.
- tests for rendered states where possible.
- one manual browser smoke check at 1920x1080 or the nearest available viewport.

### Non-Goals

- Do not build a full metrics dashboard.
- Do not add Prometheus, `/metrics`, or a new observability stack.
- Do not add a new status page unless explicitly needed.
- Do not spam toasts for normal stale states.
- Do not create a generalized failure-state framework larger than the app needs.

### Acceptance Criteria

- Weather, calendar/week, Up Next, commute, sports ticker, and center/fallback surfaces show an honest freshness/failure state.
- If provider data is stale, the UI says so without breaking the glanceable layout.
- If Google Calendar auth fails or expires, the UI shows an understandable reconnect/sync-failed state.
- Existing successful data paths still render normally.
- Tests cover at least fresh, stale, provider-error, and auth-error paths for core surfaces where practical.
- `pytest --ignore=tests/e2e` passes.

---

## Phase 4 - Runtime Attic Shutdown

**Status:** Completed 2026-08-12 (runtime gating; attic deletion remains deferred)

### Goal

Make "frozen" mean off at runtime, not merely labeled as frozen in docs.

Family Hub can carry some dormant code for now, but the appliance should not run background jobs, network discovery, webhook checks, plugin loading, or smart-home scans for features that are not part of the active dashboard.

### Deliverables

- Review `config.example.yaml`, `hub/config.py`, `app.py`, and `hub/scheduler.py`.
- Flip dormant/attic defaults off unless the owner confirms active use:
  - IoT / Home Assistant,
  - casting discovery,
  - webhooks,
  - plugins,
  - voice,
  - update checks,
  - weather-alert webhook paths,
  - chores if still unused,
  - photos/ambient if not intentionally used.
- Stop registering scheduler jobs for dormant systems unless explicitly enabled.
- Stop loading unused browser scripts where feature flags are false, especially voice-related JS.
- Keep core jobs:
  - calendar refresh,
  - weather refresh,
  - sports ticker refresh,
  - cache cleanup.
- Add tests around scheduler job registration for enabled/disabled configs.
- Update config docs to distinguish:
  - core,
  - optional but currently supported,
  - attic/frozen,
  - removed.

### Non-Goals

- Do not delete large subsystems yet unless removal is trivial and already proven safe.
- Do not refactor `hub/routes/api.py` or `api_media_admin.py` just because they are large.
- Do not remove `/health`.
- Do not remove weather/calendar/sports cache priming.
- Do not add replacement monitoring.

### Acceptance Criteria

- A default/safe config starts only core background jobs.
- Attic jobs do not run unless explicitly enabled.
- Disabled voice does not load noisy/unneeded active browser behavior.
- Tests prove scheduler job registration follows config.
- The app still boots and the main dashboard still works.

---

## Phase 5 - Roadmap and Narrative Cleanup

**Status:** Planned / Protective Steering Work

### Goal

Make the repo tell one coherent story so future humans and coding agents do not follow stale expansionist plans.

This phase should rewrite or replace `docs/ROADMAP.md`, which currently contradicts the newer product direction by listing profiles/presence, voice wake word, and automatic update scheduling as future work.

### Deliverables

- Rewrite `docs/ROADMAP.md` so it aligns with this phases file and `PRODUCT_DIRECTION.md`.
- Add a clear note that this file, `PRODUCT_DIRECTION.md`, and the latest product review supersede older expansionist plans.
- Archive or delete stale planning files that are no longer steering documents, such as:
  - old kitchen hub plan docs,
  - obsolete rebrand notes,
  - stale port references if superseded,
  - dead frontend docs,
  - any doc still promising removed systems.
- Keep useful historical docs only if they are clearly marked as archive/history.
- Clarify naming:
  - Product name: Family Hub.
  - Historical/internal package or service names may still use Kitchen Hub / `kitchen_hub` / `kitchen-hub`.
  - Do not rename packages/services in this phase unless trivial.
- Update `docs/API_CONTRACTS.md` if routes are no longer real or intentionally frozen.

### Non-Goals

- Do not perform broad code deletion in the docs cleanup phase unless it is a verified dead artifact.
- Do not rename the Python package.
- Do not create a sprawling new roadmap.
- Do not keep two competing steering docs.

### Acceptance Criteria

- `docs/ROADMAP.md` no longer lists profiles/presence, voice wake word, automatic updates, or other rejected expansion items as committed future work.
- Future direction points to appliance trust, privacy, staleness, launcher reliability, runtime slimming, and optional ambient/dead-zone work.
- Archived docs are clearly marked or moved.
- README, Product Direction, Product Review, and Roadmap no longer contradict each other.
- A coding agent reading only README + Roadmap + Product Direction would understand the intended product.

---

## Phase 6 - Launcher Reliability and Sibling App Health

**Status:** Future / After Phases 2-5

### Goal

Make the homelab launcher trustworthy. Family Hub's app dock is the front door to sibling apps, so dead ports and broken buttons are trust failures on the hub even if the sibling app is the cause.

### Deliverables

- Define a minimal launcher health contract for local apps:
  - configured URL,
  - optional health endpoint,
  - last checked time,
  - reachable/unreachable/unknown status.
- Add tiny health dots or dimming to launcher entries:
  - no big status page,
  - no noisy alerts,
  - no polling storm.
- Check local app health at a safe cadence.
- Keep open-tab/open-child behavior unchanged.
- Add fallback copy for unreachable apps:
  - "App unavailable"
  - optional "last reachable" timestamp.
- Document expected sibling app port/health behavior.
- Add tests for:
  - reachable local app,
  - unreachable local app,
  - disabled health checks,
  - rendering of health dots/states.

### Non-Goals

- Do not absorb sibling app functionality into Family Hub.
- Do not build a full homelab monitoring dashboard.
- Do not add authentication or reverse-proxy orchestration.
- Do not implement automatic restarts of sibling apps.
- Do not make the launcher depend on all sibling apps being online to render.

### Acceptance Criteria

- Launcher buttons remain usable and glanceable.
- Dead/unreachable local apps are visibly but quietly indicated.
- No local app failure breaks the hub dashboard.
- Health checks are bounded, cached, and configurable.
- Tests pass.

---

## Phase 7 - Single Hub Self-Status Glyph

**Status:** Future / Optional but Recommended After Phase 3 or 6

### Goal

Give the owner one tiny appliance-grade status signal without resurrecting the deleted metrics system.

### Deliverables

- Add a small status glyph in a low-priority location, such as a corner of the shell or settings entry point.
- Status should summarize only:
  - core scheduler job freshness,
  - provider failures,
  - stale core data,
  - maybe launcher health if Phase 6 is complete.
- States should be simple:
  - OK,
  - attention,
  - failed/needs action.
- Tap/click reveals one-line reasons, not a metrics dashboard.
- Include a route/service helper that gathers the minimal status.
- Add tests for status aggregation.

### Non-Goals

- Do not re-add `/metrics`, Prometheus, self-healing, or a diagnostics dashboard.
- Do not expose internal logs to the family-facing screen.
- Do not make this a notification center.
- Do not add external alerting.

### Acceptance Criteria

- Owner can tell at a glance whether the wall is healthy.
- Family-facing experience remains calm and uncluttered.
- The glyph does not distract from calendar/weather/commute/sports.
- Status calculation is cheap and resilient.
- Tests pass.

---

## Phase 8 - Ambient / Dead-Zone Resting-State Experiment

**Status:** Future / Do Not Start Until Privacy, Trust, Runtime Slimming, and Roadmap Cleanup Are Done

### Goal

Improve the screen's resting state when the calendar week is sparse, without turning Family Hub into a photo frame or new app surface.

The product direction warns that the week grid may optimize for the 5% planning moment rather than the 95% ambient glance moment. This phase tests whether the main canvas should breathe differently when little is scheduled.

### Deliverables

- Define a narrow experiment:
  - when week grid has low event density,
  - show larger Today / Up Next / clock / weather context,
  - optionally use an existing local photo/ambient backdrop if already configured.
- Reuse existing ambient/photos code only if it is already safe and not a scope explosion.
- Preserve the normal week calendar as the default functional anchor.
- Add a config flag for the experiment.
- Keep the bottom tiles, right rail, app dock, and sports ticker stable.
- Add browser/manual validation at 1920x1080.
- Add basic tests for feature gating and template selection.

### Non-Goals

- Do not build a full photo management system.
- Do not add Google Photos sync.
- Do not make ambient mode the default without owner approval.
- Do not remove week/month/workweek calendar behavior.
- Do not add new content modules.

### Acceptance Criteria

- Sparse-calendar mode improves glanceability without reducing trust.
- Calendar remains accessible and unchanged when active/planning mode is needed.
- Experiment can be disabled by config.
- No new provider dependency is introduced.
- Existing tests pass and manual kiosk check looks stable.

---

## Phase 9 - Touch Usage Validation and Interaction Polish

**Status:** Conditional / Start Only After Real Usage Is Observed

### Goal

Polish touch interactions only where real household usage proves they matter.

A key open assumption is whether anyone besides the builder actually touches the screen. If not, Family Hub should bias even harder toward glanceable display and defer touch-heavy polish.

### Deliverables

- Observe or log, lightly and privately, whether the following are used:
  - shopping modal,
  - timers,
  - notes,
  - weather modal,
  - app launcher,
  - miniplayer.
- Based on observed use, polish only the top touch paths.
- Candidate polish if justified:
  - shopping add/check/clear flow,
  - timer presets and cancel flow,
  - modal close/focus behavior,
  - app launcher fallback behavior,
  - miniplayer connect/disconnected state.
- Preserve minimum touch target standards from `docs/design/STYLE.md`.
- Add targeted tests where behavior changes.

### Non-Goals

- Do not add analytics services.
- Do not track personal behavior externally.
- Do not polish every modal because it exists.
- Do not add new touch-heavy features.
- Do not prioritize touch polish over stale/failure trust work.

### Acceptance Criteria

- Phase begins with a written note stating whether the screen is actually used for touch.
- Only observed/high-value touch paths are changed.
- No new large surface area is added.
- Accessibility and focus behavior do not regress.
- Tests pass.

---

## Phase 10 - Weather, Calendar, Commute, and Sports Resting-State Refinement

**Status:** Future / Carefully Bounded

### Goal

Refine the core visible information surfaces after freshness/failure states are complete, focusing on the resting dashboard rather than deeper drill-ins.

### Deliverables

Potential refinements, chosen only if justified:

- Weather:
  - improve concise current/hourly/daily readability,
  - keep modal useful but avoid more drill-in layers.
- Calendar/Up Next:
  - better empty-day or low-event presentation,
  - preserve week/month/workweek and add-event behavior.
- Commute:
  - preserve commute-or-quick-timer fallback,
  - avoid exposing raw private addresses client-side.
- Sports ticker:
  - tune spacing, grouping, cadence, and favorite-team emphasis,
  - preserve optional/configured nature.

### Non-Goals

- Do not add new weather providers unless an existing provider is unreliable.
- Do not expand the weather modal into a weather app.
- Do not add sports pages beyond existing surfaces unless a separate phase approves it.
- Do not make commute a navigation app.
- Do not add Command Center-style recommendations here.

### Acceptance Criteria

- The dashboard is easier to read from the kitchen display.
- Existing interactions continue to work.
- Core surfaces retain freshness/failure badges.
- No new dependency or provider is added without a documented reason.
- Tests and manual display check pass.

---

## Phase 11 - Settings and Admin Surface Slimming

**Status:** Future / After Runtime Attic Shutdown

### Goal

Make settings/admin reflect the real appliance rather than every historical subsystem.

The current settings/admin surface is large for a one-admin household appliance. It should be honest, not expansive.

### Deliverables

- Review `templates/partials/settings_view.html`, admin templates, `api_admin`, and `api_media_admin` surfaces.
- Hide or remove settings for disabled/frozen systems unless explicitly needed.
- Group settings into:
  - Core dashboard,
  - Providers,
  - Launcher,
  - Kiosk/deployment,
  - Experimental/attic.
- Do not add "Settings Phase 1/2" polish from the stale roadmap unless re-justified.
- Make stale/error/provider reconnect states visible where settings are the right repair surface.
- Stop adding new routes to the largest route files unless the phase explicitly calls for it.
- Document any route/file split recommendation without necessarily doing it.

### Non-Goals

- Do not build a full admin console.
- Do not refactor all route files in this phase.
- Do not expose attic controls prominently.
- Do not add multi-user profiles or auth.
- Do not add plugin marketplace/settings.

### Acceptance Criteria

- Settings/admin no longer imply frozen features are active product commitments.
- Core repair actions are discoverable.
- Disabled features are hidden or clearly marked.
- No major dashboard regressions.
- Tests pass.

---

## Phase 12 - Attic Code Deletion and Megafile Containment

**Status:** Future / Only After Runtime Shutdown and Narrative Cleanup

### Goal

Reduce maintenance load by deleting verified-dead remnants and preventing large route files from growing further.

This is not a refactor-for-refactor's-sake phase. It is cleanup after runtime risk has been removed.

### Deliverables

- Use `docs/ATTIC_REACHABILITY_AUDIT.md` as the starting point, then re-verify current reachability.
- Candidate deletion/removal items if still unused:
  - orphaned news adapter/aggregator remnants,
  - dead `hub_ui/` parallel frontend,
  - obsolete rebrand/port/reference files,
  - unused voice browser loading if already disabled,
  - unused webhook/casting/update/admin surfaces if runtime shutdown proved safe.
- Add a "do not add to megafiles" rule:
  - `hub/routes/api.py`,
  - `hub/routes/api_media_admin.py`,
  - giant settings template.
- If a route split is necessary, do the smallest extraction around a coherent subsystem.
- Remove tests only when the feature is truly removed.
- Keep migrations safe; avoid destructive database changes unless clearly needed.

### Non-Goals

- Do not delete disabled but intentionally retained features without owner decision.
- Do not do broad architectural rewrites.
- Do not split files merely for aesthetics.
- Do not change dashboard behavior as a side effect.
- Do not combine this with new feature work.

### Acceptance Criteria

- Verified dead artifacts are removed or archived.
- No active dashboard route/template breaks.
- Tests are updated to match intentional removals.
- Core app still boots.
- Route file growth is constrained by documented convention.

---

## Phase 13 - Chores, Voice, IoT, Plugins, and Other Conditional Decisions

**Status:** Conditional / Owner Decision Required Before Any Build

### Goal

Make explicit yes/no decisions for features that are currently fossils, temptations, or sibling-app candidates.

### Deliverables

For each item, write a decision note before coding:

- Chores:
  - either earns a real tile because the household uses it,
  - or remains disabled/deletion candidate.
- Voice:
  - default answer is no on-hub voice.
  - if ever built, prefer a separate sibling service that calls hub APIs.
- IoT/Home Assistant:
  - default answer is no on the hub.
  - if needed, prefer a sibling smart-home app or Command Center.
- Plugins:
  - default answer is no plugin ecosystem.
- Profiles/presence:
  - default answer is no until household need is proven.
- Automatic updates:
  - default answer is no; use git pull + restart.
- Backup:
  - keep only if it is actively useful for local recovery.

### Non-Goals

- Do not start implementing any of these based on old roadmap entries.
- Do not add "just in case" settings for these features.
- Do not use existing code as proof a feature should exist.
- Do not turn Family Hub into Command Center.

### Acceptance Criteria

- Each conditional subsystem has an explicit owner decision:
  - keep dormant,
  - delete,
  - sibling app,
  - future phase.
- `docs/ROADMAP.md` reflects those decisions.
- Default app behavior remains appliance-shaped.
- No conditional feature runs by default.

---

## Phase 14 - Kiosk Deployment and Appliance Hardening

**Status:** Future / After Trust and Runtime Slimming

### Goal

Make the deployed wall appliance boring to run on the target machine.

### Deliverables

- Reconcile deployment naming:
  - Family Hub product name,
  - historical Kitchen Hub service/path names if retained.
- Validate Linux/systemd deployment docs against actual scripts:
  - app service,
  - kiosk service,
  - restart behavior,
  - health check,
  - Chromium flags.
- Validate Raspberry Pi or small-PC setup assumptions.
- Ensure startup after reboot:
  - app starts,
  - browser opens,
  - cache warms,
  - dashboard shows stale/fresh states honestly.
- Review burn-in mitigation config and night-dim behavior:
  - keep only if it serves the actual display.
- Add a short manual deployment checklist.

### Non-Goals

- Do not build self-healing.
- Do not build automatic update scheduling.
- Do not add external monitoring.
- Do not require internet for core local functions beyond configured providers.
- Do not make deployment generic for many users.

### Acceptance Criteria

- Deployment docs match current scripts and service names.
- `/health` works after boot.
- Kiosk can recover from normal reboot/power loss.
- Core tiles render cached/stale/fresh states appropriately after startup.
- Manual checklist is short enough to actually use.

---

## Phase 15 - Long-Term Optional Appliance Improvements

**Status:** Future / Opportunistic Only

### Goal

Capture reasonable long-term improvements that fit the appliance identity, while preventing them from becoming near-term distractions.

### Candidate Deliverables

Only consider these after earlier phases are complete:

- Better app dock organization if sibling apps grow.
- Optional launcher grouping/folder refinements.
- Display-safe burn-in tweaks based on real panel behavior.
- Better offline/cached empty states.
- More deliberate motion for modal entry and refresh, as long as it stays calm.
- Light theme counterpart only if real use justifies it.
- Additional sibling-app health metadata if Phase 6 proves useful.

### Non-Goals

- No meal planning inside Family Hub.
- No package monitor tile inside Family Hub.
- No budget dashboard inside Family Hub.
- No school/lunch/news/transit modules unless they replace an existing core surface and are explicitly approved.
- No general assistant behavior.
- No multi-user operating system.
- No plugin ecosystem.

### Acceptance Criteria

- Any long-term improvement has a written reason tied to the core loop.
- No improvement adds a new permanent dashboard surface without replacing or simplifying another surface.
- The app remains glanceable on one screen.
- Family Hub remains a launcher for sibling apps, not the container for all sibling-app functionality.

---

## Phase 16 - Explicitly Deferred / Do Not Build Without New Approval

**Status:** Intentionally Deferred

### Goal

Prevent old roadmap gravity from re-opening rejected or unproven product directions.

### Deferred Items

These should not be implemented unless the owner explicitly creates a new phase and explains why the prior decision changed:

- Profiles and presence strip.
- Local wake word / always-listening voice.
- On-hub speech-to-text command handling.
- Automatic update scheduling.
- General plugin marketplace/ecosystem.
- Full smart-home control.
- General Home Assistant control panel.
- Multi-user auth/profiles for the kitchen display.
- Full metrics dashboard or Prometheus.
- Self-healing/watchdog intelligence beyond systemd restart.
- Command Center-style planning, workflows, approvals, or memory.
- Package/budget/home inventory feature absorption into the hub.
- Large frontend framework migration.
- Generic platformization for other households.

### Non-Goals

- This phase is not a backlog.
- This phase is not an invitation to implement deferred items later by default.
- This phase should shrink over time only when owner decisions are explicit.

### Acceptance Criteria

- Deferred items are absent from active roadmap phases.
- Future coding prompts do not cite stale roadmap entries as approval to build them.
- Any new approval for a deferred item includes:
  - why the old decision changed,
  - why it belongs in Family Hub instead of a sibling app or Command Center,
  - how it preserves the appliance identity.

---

## Recommended Phase Grouping for Agentic Coding

Use these as broad handoff batches:

1. **Phase 2 only:** Privacy and config hygiene. Keep isolated.
2. **Phases 3-4:** Trust states plus runtime attic shutdown, if the agent can keep changes separated and tests clear.
3. **Phase 5:** Narrative cleanup. Good for a cheaper model after Phase 2-4 are done.
4. **Phases 6-7:** Launcher health and small self-status glyph, after trust patterns exist.
5. **Phase 8:** Ambient experiment, only after the product is trustworthy and slimmed.
6. **Phases 11-12:** Settings/admin slimming and attic deletion, only after runtime shutdown proves safe.

For Fable or another high-end model, use it for product/architecture review and messy cross-cutting judgment. For implementation, use the lowest capable model that can safely inspect the repo and keep changes bounded.
