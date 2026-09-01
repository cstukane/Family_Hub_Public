# Improvements.md — Family Hub (Raspberry Pi + TV)

## Purpose
This document is a prioritized, implementation-ready improvements backlog for the Family Hub UI. It is written to be handed to:
- a junior developer, or
- an agentic coding AI

The goal is **glanceable first**, **usable from 8–10 feet**, and **stable on a Raspberry Pi**.

---

## Target environment
- Hardware: Raspberry Pi (TV output)
- Input: wireless mouse + keyboard (not touch, not D-pad remote)
- Display context: kitchen TV (“walk-by” usage + occasional sit-and-control)
- Invariants:
  - **Sports ticker stays visible** at all times
  - **Calendar is the primary tile**
  - **Dock can auto-hide**
  - **Spotify must support Spotify Connect** (show/control playback even if audio is on a speaker or other device)

---

## UX principles (non-negotiable)
1. **10-foot readability**
   - Text must be readable at 8–10 ft without squinting.
   - Interactive items must be easy to click at distance (bigger hitboxes, generous padding).
2. **Glanceable first**
   - In 3 seconds, user should get: time/date, next relevant calendar info, weather gist, sports.
3. **Intentional empty states**
   - When there’s “nothing happening,” the UI should look calm and complete—not blank or broken.
4. **Resilient to missing data**
   - If APIs fail (weather/Spotify/calendar), show last known state + “Last updated …” instead of empty panels.
5. **Performance-aware**
   - Avoid heavy effects that stutter on Pi (excessive blur, large continuous animations, expensive reflows).

---

## Visual system requirements
### Typography
- Use responsive scaling where possible (avoid hard-coded “one size fits all”).
- Recommended approach: `clamp(min, preferred, max)` for TV readability.
- Target minimums (at typical viewing distance):
  - Primary clock: very large, bold
  - Calendar event titles: noticeably larger than current
  - Weather details (“feels like”, wind): not tiny/low-contrast

### Icons
- **No mixing emojis with SVG icons.**
- System icons (Notes/Shopping/Timers/Settings/Status/etc.) must come from **one** icon set.
- App/brand icons (Spotify/YouTube/Roku/Pluto, etc.) should use official/clean SVGs.

### Contrast
- Increase contrast on small secondary text (“No events”, small weather labels).
- Avoid gray-on-gray for anything “glanceable.”

---

## Backlog format
Each item includes:
- **Problem**
- **What to build**
- **Interaction details** (mouse/keyboard)
- **Acceptance criteria** (testable)
- **Notes / edge cases**

---

# P0 — Must-do (highest ROI)

## P0-01 — Spotify widget redesign (snapped, clean idle state, device-aware)
**Problem:** Current player looks floating/unfinished; needs to support controlling Spotify Connect devices (speaker/phone) without being visually ugly.

**What to build:**
Replace floating widget with a **snapped mini-player** that has two states:

1) **Collapsed (idle / not playing):**
   - Compact bar/card with:
     - “Not playing” (or last track)
     - a clear **Connect / Open Spotify** CTA if not authenticated
     - current device label if available (or “No device”)
   - Should look intentional, not “empty.”

2) **Expanded (active playback):**
   - Shows:
     - track title/artist
     - play/pause, next/prev
     - scrubber (optional but nice)
     - **device picker** (must-have for your use case)
     - volume (optional)

**Placement:**
- Centered below the calendar and/or integrated into the Center Zone area.
- Must not look like it was dropped randomly.

**Interaction details:**
- Click on collapsed state expands.
- Esc collapses (optional).
- Mouse hover can reveal secondary controls.

**Acceptance criteria:**
- If Spotify is playing on another device, this UI reflects it.
- Switching output device is achievable in ≤2 clicks from expanded view.
- Idle state looks clean and designed.

**Notes / edge cases:**
- If Spotify auth expires or API fails: show a clean disconnected state + retry.
- Avoid frequent polling that burdens the Pi; use reasonable intervals.

---

# P1 — Nice-to-haves

## P1-01 — Lcal news
**What to build:**
- Optional tile that can be disabled.
- If API/auth is complicated, skip until later.

**Acceptance criteria:**
- Failure to load does not break the home screen.

---

# Explicitly out of scope (do not build)
- Who’s Home / presence tracking
- Ring/Blink package/door alerts (until a clean integration path exists)
- Commute timers that require continuous location sharing

---

# QA checklist (quick)
- From 8–10 ft: read time/date, temp, event titles
- Dock hides and returns reliably; ticker never hides
- Spotify shows current device and can switch device
- Calendar handles busy days without overlapping text
- No “empty” modules look broken; fallback states look intentional
- Unplug network: UI degrades gracefully (last known state + timestamps)
