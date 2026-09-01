# PRODUCT DIRECTION — Family Hub

*Written 2026-06-11, after a fresh product-direction pass: full repo read, config review, test run (337 passed), and a live render of the in-flight redesign at 1920×1080.*

This is an opinionated direction document, not a task list. Its job is to make the next few implementation passes easier and to stop future passes from chasing the wrong work.

---

## 1. What this app actually is

Strip away the README and the package layout, and the deployed product is expressed through untracked `instance/config.yaml`:

**A glanceable family command center on a 50" kitchen TV** — and the front door to a personal homelab. The live config has a real Google calendar, a real home→work commute (home → work), real favorite teams (Nets, Giants, Yankees, Devils), Spotify enabled, and an app bar that launches both streaming services and **twelve companion apps on ports 5001–5011** (Budget, Lifelog, Learning Scroll, Home Inventory, Package Monitor, etc.).

The core user loop is **glance, occasionally touch**:

1. Walk into the kitchen → in ~3 seconds know: what's next today, the weather, the commute ETA, the score.
2. Occasionally touch: add a shopping item, set a timer, play music, open YouTube/ESPN/one of the homelab apps.

That's it. That is the entire product. Everything in the repo should be judged against that loop. The rendered dashboard (calendar week grid center, Up Next / Shopping / Commute tiles, weather + miniplayer sidebar, app bar, live MLB ticker) already *is* this product, and it looks legitimately good with real data.

The emotional purpose: **the family trusts the wall**. The screen is right, current, and never wedged. A kiosk that's wrong is worse than no kiosk — nobody walks over to debug a wall.

## 2. The verdict in one paragraph

The product shape is right and the in-flight redesign (uncommitted in the working tree, all 337 tests green) is moving in exactly the right direction. The app does not need new features. It needs three things, in order: **(a) commit and finish the redesign's payoff moments, (b) make the glance trustworthy — visible staleness and graceful failure on every tile, (c) shrink the claimed surface to match the real one.** The repo currently carries roughly 2× the code its product needs, and the README describes an app that doesn't exist. The next phase is convergence, not expansion.

## 3. What's strong — leave it alone

- **The data pipeline architecture** (APScheduler → adapter → SQLite TTL cache → service → route → HTMX/Socket.IO). It's the right shape for a kiosk: cheap, resilient, debuggable. Don't replatform, don't add a frontend framework.
- **The calendar pipeline** (Google + ICS adapters, week/month views, add-event modal). This is the anchor view and it works.
- **The sports ticker** (`hub/services/sports_ticker_service.py`, 54KB). Heavily invested, live data confirmed working, recently polished across five PRs. It's done — resist further tinkering.
- **The commute tile.** This is the most *personal* feature in the app — a real differentiator over any off-the-shelf dashboard. Its quick-timer fallback behavior is thoughtful.
- **The media/app launcher.** Recently consolidated to `hub/services/media_launcher.py` with the root file as a shim. As the front door to 12 companion apps, this is strategically the most important non-dashboard surface. Keep it boring and reliable.
- **The test suite.** 337 passing tests plus e2e scaffolding is unusual discipline for a personal project. Protect it.

## 4. The payoff moments that need to become satisfying

These are the moments where the product currently under-delivers relative to how often they happen:

### a) The morning glance (highest frequency, highest value)
Up Next + commute + weather are all morning features, and they're now adjacent on screen — good. What's missing is **confidence**: none of the tiles tell you whether what you're looking at is current. The original NFRs in `docs/GOAL_AND_SCOPE.md` literally listed "clear error surfacing and last-updated stamps" — this got lost. When the Google token expires or Open-Meteo flakes at 6am, the family should see a quiet "as of 9:40 PM yesterday" badge, not silently stale data or a blank tile. **This is the single highest-leverage trust improvement in the app.**

### b) The "add milk" moment (highest-frequency *touch*)
Shopping is the family feature most likely to be used by someone other than the person who built the hub. Right now it's the weakest tile: in the live render, the empty shopping tile is nearly invisible (dark-on-dark, no affordance), and adding an item requires finding the sidebar quick-access button → modal. The tile itself should be the affordance: tappable anywhere, with a visible "+ Add item" in the empty state. Two taps and a keyboard, max.

### c) The evening dead zone
With a sparse family calendar, the week grid leaves the majority of a 50" screen empty most of the day (clearly visible in the live render: a huge black field from Tue–Sat). The week grid is a *planning* view, but the screen spends 95% of its life as an *ambient* view. Don't redesign around this yet — finish the current redesign first — but the next layout iteration should consider letting the main zone breathe differently when the week is empty (larger today-focus, photo backdrop, bigger up-next). This is the one place where the current UX points slightly in the wrong direction: it optimizes for the 5% planning moment over the 95% glance moment.

### d) The miniplayer when Spotify isn't connected
Disconnected state renders as a ghost ("No track playing" + a bare "+") and the console fills with 400s on a polling loop. Fine on the real kiosk where Spotify is connected; embarrassing on any fresh install. Show a single "Connect Spotify" state and stop polling until connected.

## 5. What is overbuilt — the attic

A large fraction of `hub/` is platform-engineering for a product that has exactly one deployment, one admin (Cole), and a LAN of trusted users. None of this needs to be deleted *this week*, but it should be explicitly demoted: no new investment, no README billing, no test expansion, and it should be first against the wall when it causes friction.

| Subsystem | Reality check |
|---|---|
| `hub/services/edge.py` (15KB) | "Edge computing service for distributed computing tasks" — in a kitchen dashboard. Pure speculation; nothing on the dashboard uses it. Delete candidate. |
| IoT layer (`iot_service.py`, alexa/google_home/roku adapters) | Enabled in config but surfaced nowhere in the redesigned UI. Aspirational. Freeze. |
| Webhooks (`webhook.py` 20KB + management UI) | A webhook *platform* for one house. Freeze. |
| `update.py` (16KB) | Self-update scheduling, partially `not_implemented` by design (per prior audit). A kiosk updates via `git pull` + systemd restart. Freeze or gut. |
| ~~`self_heal.py`~~ (removed 2026-06-15), ~~`metrics.py`~~ (removed 2026-06-15), `backup.py`, ~~`/status`~~, ~~Prometheus~~ | Self-healing and metrics subsystems were deleted in the 2026-06-15 cleanup pass. A `/health` endpoint and systemd restart policy cover the remaining needs. Backup remains frozen. |
| Plugins system | No evidence of a real plugin. Freeze. |
| Chores | Disabled in config (`enabled: false`). Either the family wants it (then it earns a tile) or it doesn't (then stop carrying it). Decide by usage, not by code. |
| **News** | The most misleading one: config exists, service exists, README and CLAUDE.md claim "news every 5 min" — but **the scheduler has no news job and the dashboard renders no news anywhere**. It's a feature that exists only in documentation. Either give it one modest line somewhere or remove the config/docs claims. |
| Voice | Disabled in config; `voice.js` still ships and logs "not enabled" on every load. Fine to keep the code, but it's attic. |
| Cooking mode / ambient / photos views | Half-real (Google Photos disabled, local path only). Ambient is actually the most promising of the three given the dead-zone problem in §4c — it may be the answer rather than a separate view. |

Two oversized files deserve mention because they distort every future maintenance pass: `hub/routes/api_media_admin.py` (93KB, plus an untracked `.bak` copy sitting next to it — delete the `.bak`) and `templates/partials/settings_view.html` (42KB). The prior audit already flagged the route-file split and deferred it; that remains the right call to defer, but **stop adding to these files.**

## 6. What should be made more trustworthy

Trust is the kiosk's whole value proposition. In priority order:

1. **Per-tile staleness** (§4a). Each HTMX partial already comes from a TTL cache that knows its fetch time — surface it. A small "updated 7:08 PM" / amber "stale" treatment on calendar, weather, commute, and ticker. This is mostly plumbing that already exists.
2. **Failure states that a non-technical family member can read.** "Calendar can't sync — tap to reconnect" beats an empty grid. The Google OAuth token expiry is the most likely real-world failure; make that one path excellent before generalizing.
3. **README honesty pass.** The README promises voice, IoT/Home Assistant, Google Photos sync, casting, news, metrics dashboards. A reader (human or model) doing future work will be misled into maintaining or extending fiction. Rewrite Features to describe the real dashboard, move the aspirational list to a clearly-labeled "experimental / unwired" section. Same for the stale plan docs in `docs/` (26 files, several superseded).
4. **Kiosk resilience checks** stay as-is: systemd restart + cache-on-disk already cover the reboot story. Don't build more self-healing.

## 7. What the next few implementation passes should be

In order, each small enough for a single focused session:

1. **Land the redesign.** The working tree holds ~2,300 lines of uncommitted redesign that renders well and passes all tests. Commit it (it's already coherent), then do a polish pass on the three weak moments: shopping tile empty state + tap-to-add, miniplayer disconnected state, and the sports ticker's empty-middle-tile contrast.
2. **Staleness + failure surfacing pass.** One pattern, applied to four tiles (calendar, weather, commute, ticker). Includes the Google-token-expired UX.
3. **Honesty pass.** README rewrite, prune/mark stale docs, resolve the news ghost (wire one line or remove claims), delete `api_media_admin.py.bak`, delete `edge.py` unless something secret depends on it (nothing in `hub/routes` imports it).
4. **Ambient/dead-zone experiment** (only after 1–3): when the visible week is nearly empty, let the main zone relax — bigger clock/up-next, optional photo backdrop. This reuses the existing ambient and photos code rather than adding anything new.

Explicitly **not** on the list: new providers, new panels, voice, IoT, plugins, multi-user auth, route-file refactors, framework changes. The homelab companion apps (ports 5001–5011) are where new *functionality* belongs; the hub's job is to launch them reliably, not to absorb them.

## 8. Notes for narrower/cheaper models working from this doc

- The product is the **kiosk dashboard**. When in doubt whether code matters, ask: "does this change what's on the 50" screen, or how much the family can trust it?" If no to both, it's attic work.
- `config.example.yaml` defines safe defaults; ignored `instance/config.yaml` is the deployment ground truth. Current docs describe the active surface, while archived plans are historical only.
- The redesign uses tiles in `templates/base.html` + partials in `templates/partials/`; styling concentrates in `static/css/base.css`. The body gets class `home-dashboard-view` on the home view.
- Run with `make run` (or the app factory + `socketio.run`); never `python app.py`. Tests: `pytest --ignore=tests/e2e` runs in ~60s.
- Don't trust `docs/ROADMAP.md`'s mid-term list ("Profiles & presence strip", settings phases) as commitments — re-justify anything there against §7 before building it.

## 9. Code changed during this pass

None. Nothing found during the read was both small and necessary enough to justify touching code mid-redesign; the working tree already carries a large uncommitted change set, and mixing direction-pass edits into it would muddy the redesign commit. Verification performed instead: full test suite (`337 passed` excluding e2e), app boots cleanly via the factory, dashboard rendered and screenshotted with live calendar/weather/commute/sports data, shopping-tile partial fetched directly to confirm its empty state renders (it does — it's a contrast/affordance problem, not a bug).

One untracked artifact was left for the owner to delete rather than removed unilaterally: `hub/routes/api_media_admin.py.bak`.
