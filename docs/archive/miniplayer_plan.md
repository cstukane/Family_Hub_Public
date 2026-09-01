# Audio Miniplayer Review and Implementation Plan

## Purpose
This document is a handoff plan for fixing and hardening the audio miniplayer while preserving all existing functionality and user-facing behavior.

Primary goals:
- Resolve High and Medium priority issues first.
- Keep current Spotify and local playback actions intact.
- Improve code maintainability and performance.
- Prepare the miniplayer for additional providers: Radio Browser, SomaFM, Podcast Index.

---

## Scope and Constraints
- In scope:
  - `templates/partials/miniplayer.html`
  - `static/js/fragments/miniplayer.js`
  - `static/css/base.css`
  - `hub/routes/api_media_admin.py`
  - `hub/services/music_providers/providers/*`
- Out of scope:
  - Redesigning unrelated dashboard modules.
  - Removing existing endpoints or changing API contracts used by current UI.
- Non-negotiable:
  - Preserve all current controls/actions (play, pause, next, previous, seek, Spotify auth, playlists, queue, device transfer, cast modal action).

---

## Current Architecture (Quick Context)
- Miniplayer HTML is served via partial:
  - `hub/routes/main.py:315-321` (`/partials/miniplayer`)
  - inserted in dashboard by `templates/base.html:192`
- Miniplayer behavior:
  - `static/js/fragments/miniplayer.js` (`MiniplayerFragment` class)
  - initialized via DOM/HTMX hooks near `miniplayer.js:1525+`
- Styling:
  - `static/css/base.css` miniplayer block starts near `base.css:3557`
- Music provider backend:
  - Generic provider endpoints and aliases in `hub/routes/api_media_admin.py:1838-2177`
  - provider interface and registry in:
    - `hub/services/music_providers/providers/base.py`
    - `hub/services/music_providers/providers/spotify_provider.py`
    - `hub/services/music_providers/providers/registry.py`

---

## Findings Summary

### High Priority
1. **State updates target wrong DOM node**
   - File: `static/js/fragments/miniplayer.js`
   - Lines: `1355`, `1474`, `1481`
   - Problem:
     - Code does `this.rootElement.querySelector('#miniplayer')`.
     - `this.rootElement` is already `#miniplayer`.
     - Query returns `null`, so state/class/display updates silently do nothing.
   - Impact:
     - `is-idle` state may not toggle reliably.
     - `data-state` expanded/collapsed logic can fail.
     - `showMiniplayer()`/`hideMiniplayer()` can no-op.

2. **Launch default state is collapsed and hides too much**
   - Files:
     - `static/js/fragments/miniplayer.js:46`
     - `static/css/base.css:3805-3811`
   - Problem:
     - Init sets `data-state="collapsed"` before contextual state is resolved.
     - Collapsed CSS hides progress, controls, playlist panel, queue panel, device picker, album art, and Spotify auth section.
   - Impact:
     - Default launch state can appear overly empty or inconsistent with the intended idle UX.
     - Connect CTA visibility can be suppressed depending on CSS state.

### Medium Priority
3. **Potential HTMX event listener accumulation**
   - File: `static/js/fragments/miniplayer.js:54-58`
   - Problem:
     - `htmx.on('htmx:beforeSwap', ...)` is registered during init.
     - Handler is not removed in `destroy()`.
   - Impact:
     - Possible duplicate callbacks and avoidable memory/event overhead after repeated swaps.

4. **Seek operation can spam backend on drag**
   - File: `static/js/fragments/miniplayer.js:99-101`
   - Problem:
     - Seek API call is made on every `input` event.
   - Impact:
     - Excess requests during slider drag.
     - Potential lag and unnecessary load, especially on low-power hardware.

---

## Lower Priority Cleanup (Do After High/Medium)
1. **Dead like-button wiring**
   - JS references `#miniplayer-like-btn` at `miniplayer.js:91` and `1401`.
   - Element does not exist in `templates/partials/miniplayer.html`.
   - Action:
     - Either remove dead JS paths or add the button back intentionally.
   - Status: Deferred (kept as-is to avoid changing latent like/favorite behavior until product decision).

2. **CSS cleanup opportunities**
   - Duplicate `is-idle` declarations around `base.css:3833-3849`.
   - `border-radius: var(--radius-sm);` at `base.css:3911` may rely on undefined variable.
   - Action:
     - Consolidate duplicate blocks.
     - Replace with known variable or define `--radius-sm`.
   - Status: Complete (`--radius-sm` added; duplicate idle declarations removed).

---

## Implementation Plan (High + Medium First)

### Phase 1: Fix DOM root targeting bug (High)
Files:
- `static/js/fragments/miniplayer.js`

Actions:
1. In `updateChromeState()`, replace:
   - `const miniplayerEl = this.rootElement.querySelector('#miniplayer');`
   with:
   - `const miniplayerEl = this.rootElement;`
2. In `showMiniplayer()` and `hideMiniplayer()`, use `this.rootElement` directly.
3. Keep all existing behavior (class toggles, aria labels, status text) unchanged.

Acceptance criteria:
- `is-idle` class toggles correctly.
- `data-state` updates between `expanded` and `collapsed`.
- Expand button label and aria-label update correctly.

---

### Phase 2: Correct default launch state behavior (High)
Files:
- `static/js/fragments/miniplayer.js`
- `static/css/base.css`

Actions:
1. Avoid hard-forcing collapsed state too early at init (`miniplayer.js:46`).
2. Ensure startup flow runs state resolution after:
   - `loadCurrentTrack()`
   - `loadSpotifyStatus()`
3. Preserve current intent:
   - Idle state should look intentional and compact.
   - If disconnected, connect messaging/CTA remains discoverable.
4. Do not remove existing state model (`is-idle`, `data-state`), only fix ordering and visibility interactions.

Acceptance criteria:
- On app launch with no track:
  - Title shows “No track playing”.
  - Playback status is “Not playing”.
  - Device state is visible or gracefully represented.
  - Auth/connect path remains available (not accidentally hidden).
- On active playback:
  - Player becomes expanded and shows controls/progress as expected.

---

### Phase 3: Prevent HTMX handler accumulation (Medium)
File:
- `static/js/fragments/miniplayer.js`

Actions:
1. Store a stable reference to the before-swap handler on the instance.
2. Register once per instance during init.
3. Remove the exact same handler in `destroy()`.

Acceptance criteria:
- Repeated HTMX swaps do not multiply callbacks.
- `destroy()` performs full cleanup symmetry for listeners and intervals.

---

### Phase 4: Reduce seek request pressure (Medium)
File:
- `static/js/fragments/miniplayer.js`

Actions:
1. Preserve visual slider responsiveness on `input`.
2. Move network seek commit to either:
   - `change` event, or
   - debounced `input` (recommended window: 150-250ms).
3. Keep provider behavior unchanged:
   - Spotify seek via `/api/music/spotify/seek`
   - Local seek via `/api/music/seek`

Acceptance criteria:
- Dragging seek does not produce request floods.
- Final seek position is accurate.
- Play/pause/next/prev interactions remain unchanged.

---

## Detailed Developer Notes (Behavior Preservation)

### Miniplayer to main music player sync
- Methods around `miniplayer.js:1183+` call `musicPlayerElement.__musicPlayerFragment`.
- Keep this coupling intact unless replacing both sides together.
- If refactoring, maintain action mapping:
  - `play` -> play
  - `pause` -> pause
  - `next/prev` -> attempt track alignment via title/artist lookup

### Spotify-specific flows currently in miniplayer
- Status/auth:
  - `/api/music/spotify/status`
  - `/api/music/spotify/authorize`
  - `/api/music/spotify/logout`
- Playback:
  - `/api/music/spotify/playback`
  - `/api/music/spotify/play|pause|next|previous|seek`
- Queue/playlist/device:
  - `/api/music/spotify/queue`
  - `/api/music/spotify/playlists`
  - `/api/music/spotify/transfer`
  - `/api/music/spotify/devices`

Do not break these endpoints while cleaning code.

---

## Future Audio Integrations Plan

Target providers:
- Radio Browser
- SomaFM
- Podcast Index

Reference:
- `docs/Miniplayer_providers.md`

### Backend extension pattern
1. Implement provider classes under:
   - `hub/services/music_providers/providers/`
2. Inherit `MusicProvider` and define:
   - `id`, `label`, `kind`, `capabilities`, `get_status()`
   - optional methods only when supported:
     - `resume_playback`, `pause_playback`, `next_track`, `previous_track`, `seek`
     - `get_current_playback`, `get_queue`, `get_playlists`, `shuffle_playlist`
3. Register in `registry.py` (`_build_providers()`).
4. Ensure availability in generic routes:
   - `/api/music/providers`
   - `/api/music/providers/active`
   - `/api/music/providers/<provider_id>/*`

### Frontend miniplayer generalization pattern
Current issue:
- JS is largely Spotify-hardcoded.

Required path:
1. On init, fetch `/api/music/providers` and active provider.
2. Render provider indicator(s) in service tray from provider metadata.
3. Route playback calls through generic endpoints:
   - `/api/music/providers/<provider_id>/play`
   - `/pause`, `/next`, `/previous`, `/seek`
   - `/playback`, `/queue`, `/playlists`
4. Use capability flags (`base.py`) to enable/disable controls:
   - Example:
     - no `seek` capability -> disable/hide seek slider
     - no `queue` -> disable queue button
5. Preserve Spotify aliases for backward compatibility until migration is complete.

### Provider-specific UX mapping suggestions
- Radio Browser:
  - Playlist dropdown -> saved stations
  - Next/Previous -> station cycling
  - Track text -> station metadata
- SomaFM:
  - Playlist dropdown -> channels
  - Queue panel -> channel details/now playing if available
- Podcast Index:
  - Playlist dropdown -> subscribed podcasts
  - Queue panel -> episodes
  - Optional remap next/prev to seek-forward/seek-back for podcasts

---

## Testing Plan

### Manual QA matrix
1. Launch app, no media selected.
2. Spotify disabled in config.
3. Spotify enabled but disconnected.
4. Spotify connected with active playback on external device.
5. Seek dragging during active playback.
6. HTMX refresh/reload cycles for miniplayer partial.

### Verify each scenario
- UI state:
  - idle/collapsed/expanded transitions
  - auth CTA visibility
  - status/device labels
- Controls:
  - play/pause/next/previous/seek
  - playlists popover
  - queue popover
  - device transfer
  - cast button modal invocation
- Stability:
  - no duplicate event behavior after repeated swaps
  - no console errors
  - no request flood from seek

---

## Suggested Work Order
1. High #1: root targeting bug fix.
   - Status: Complete.
2. High #2: startup/default state and visibility correction.
   - Status: Complete.
3. Medium #3: listener lifecycle cleanup.
   - Status: Complete.
4. Medium #4: seek request throttling/debouncing.
   - Status: Complete.
5. Low cleanup: dead like-path and CSS dedupe.
6. Provider-generalization prep PR (no behavior changes yet).
   - Status: Complete (service tray now loads active provider metadata from `/api/music/providers`; Spotify action paths unchanged).
7. Provider additions (Radio Browser, SomaFM, Podcast Index) in separate feature PRs.
   - Status: Started (backend skeleton providers added and registry wiring completed, disabled by default).

---

## Deliverables Checklist
- [ ] Miniplayer state logic fixed without regressions.
- [ ] Launch default state visually intentional and usable.
- [ ] Event listeners cleaned with proper teardown.
- [ ] Seek interaction optimized.
- [ ] Existing Spotify and local actions preserved.
- [ ] Provider-agnostic frontend plan documented in code comments or follow-up issue.
- [ ] Future provider integration tasks tracked and scoped.
