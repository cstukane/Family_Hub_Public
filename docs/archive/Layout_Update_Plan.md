# Family Hub  Layout Update Plan

This plan organizes requested UI/UX layout changes into small, testable phases for a junior developer. Focus is on **layout & interactions**, not a backend rewrite.

---

## High-level Goals
- Clean, UI that fits as much as possible on one screen without scrolling.
- Subtle toast-style **host notifications** for system status.
- Calendar UX: **Add Event modal**, **SundaySaturday** week, **12hour time**, **event chips**, and **auto-fit height**.
- Right sidebar simplified to **three quick tools** (Notes, Shopping List, Timers) with modal UIs followed by Weather beneath.
- Weather tile redesigned to a standard app-like layout, **Fahrenheit**, **mph**, concise current + short forecast.
- Bottom toolbar icons stabilized (use placeholders where assets are missing).
- Sports ticker: placeholder + eventual ESPN-style horizontal ticker (future phase).

---

## Assumptions
- Frontend framework is web-based (HTML/CSS/JS) rendered by the Python app (e.g., Flask/FastAPI + Jinja or similar).
- Google Calendar is already authorized via `credentials.json` and a stored token.
- There is a central **Event Bus** or equivalent way to trigger UI toasts and open modals (if not, well add a small one in Phase 0).
- Screen target: Raspberry Pi display (1080p typical). We will **read viewport height** and scale sections to fit.
- Weather API already returns current, hourly, and daily data (if codes like PAR appear, well map them to readable text).

---

## Definitions
- **Host notification**: small, stackable toast that overlays above all content for ~35s, non-blocking, auto-dismiss, no persistent banner.
- **Event chip**: a rounded-rectangle container for an event: time (12hour) + title on one or two lines with a thin border.
- **Modal**: centered overlay with blurred backdrop; ESC/close button or clicking outside of modal; not full-screen; keyboard/tab-friendly.

---

## Phase 0 : Setup & Guardrails (12 commits)
[X] Add a simple **UI Event Bus** (publish/subscribe) for toasts & modals.  
[X] Add a **global CSS scale system** using CSS variables (e.g., `--vh`, `--header-h`, `--footer-h`, `--sidebar-w`).  
[X] On load & on resize, compute `--vh` = `window.innerHeight * 0.01` to allow responsive calculations.  
[X] Create reusable components: `Toast`, `Modal`, `IconButton`, `Chip`, `SectionHeader`.  
[X] Add a lightweight **icon placeholder** system: if an SVG is missing, render a generic box with the label.  
**DoD:** Components render in a story/sandbox page; resizing updates `--vh`; no layout shift warnings.

---

## Phase 1 : Host Notifications (Status Bars & Toasts) - COMPLETED
**User stories**
- As a user, I want non-intrusive status toasts when:
  - [x] System is **running normally / degraded / error**
  - [x] **Weather** data updated (show timestamp + source)
  - [x] **Calendar** auth/connection success/failure

**Tasks**
[x] Convert existing status bars into **toast notifications** that **overlay** above all content and **auto-dismiss in ~5s**.
[x] Support **stacking**; newest appears on top; max 3 visible; queue the rest.
[x] Provide `toast.success/info/warn/error` helpers.
[x] Include timestamp in weather updated toast (e.g., Updated 10:42 AM).

**DoD**
- [x] Triggering a test event shows a toast that fades out by 5s and never persists.
- [x] Keyboard focus is unaffected; screen readers announce toasts politely.

**Implementation Summary**
Phase 1 has been successfully implemented with:
- Conversion of existing status bar implementation to toast notifications
- New API endpoints: `/api/status/weather-toast`, `/api/status/calendar-toast`, and `/api/status/system`
- HTMX integration to trigger toast notifications from API responses
- Enhanced base template with proper event handling for toast notifications
- System now shows non-intrusive, auto-dismissing toast notifications instead of persistent status bars
- Toasts stack appropriately and include proper timestamp information for weather updates

---

## Phase 2 : Calendar: Add Event **Modal** + Header Placement 
**User stories**
- A small **Add Event** button appears **left of** Week of [date range] in the calendar header.
- Clicking it opens a **modal form** with **all Google Calendar fields the backend supports**.

**Tasks**
[x] Remove the always-visible big form; replace with **Add Event** `IconButton` in header. Move 'Add Event' Icon button and 'Week of X-Y' to right align, keep 'This Week' left aligned.
[x] Move 'Prev Week' and 'Next Week' buttons up to header bar beside 'This Week' label (left align). Change from text descriptions to "<" visible in the button for 'Prev Week' and ">" visible in the button for 'Next Week'
[x] New **Add Event Modal** with fields: Title, Start, End, Allday, Location, Description, Calendar, Guests (emails), Reminders, Visibility, Color.  
[x] Validate required fields; default duration 60m when Start chosen.  
[x] On submit: call existing createevent backend; show success/error toast; close modal on success.  
[x] Add "More options" link if advanced fields are hidden in compact view.

**DoD**
- [x] Form never appears inline; modal is the only entry point; event creation works and toasts confirm outcome.

**Implementation Summary**
Phase 2 has been successfully implemented with:
- Calendar header restructured with "This Week" label and navigation controls (Prev <, Today, Next >) left-aligned, and date range/Add Event button right-aligned
- Navigation controls moved from bottom to header with < and > symbols instead of text descriptions
- Enhanced Add Event modal with all required Google Calendar fields: Title, Start, End (with default 60-minute duration), All-day, Location, Description, Calendar selection, Guests, Reminders, Visibility, and Color
- Advanced fields hidden behind "More options..." toggle for cleaner interface
- Form validation with required field indicators and default duration logic
- Success and error toast notifications on form submission
- Proper HTMX integration with calendar refresh on successful event creation
- Updated CSS to support the new header layout with proper alignment

---

## Phase 3 : Calendar: Week Range & Time Format  COMPLETED
**Scope**
- Change **week layout** to **Sunday  Saturday**.  
- Switch to **12hour time** with lowercase `a.m./p.m.` (or `AM/PM` if design prefers).

**Tasks**
[x] Update calendar **week start** to Sunday (ensure navigation & range labels match).  
[x] Change time rendering to **12hour** everywhere (grid labels, event chips, tooltips).  
[x] Implement a single **formatTime(dt, tz, format="12h")** util to avoid regressions.  
[x] Unit tests snapshot a sample week before/after.

**DoD**
- [x] Header reads Week of Sun [mm/dd]Sat [mm/dd]; no 24hour remnants.  
- [x] Example: 7:00 p.m. not 19:00.

**Implementation Summary**
Phase 3 has been successfully implemented with:
- Custom Jinja filters `time_12hour` and `datetime_12hour` in app.py for 12-hour time formatting with lowercase a.m./p.m. notation
- Updated calendar_week.html template to use 12-hour time format for event displays
- Updated calendar_upnext.html template to use 12-hour time format with date
- Week layout maintained as Sunday-Saturday as it was already implemented in the existing code
- All time displays in calendar now use the requested 12-hour format with lowercase a.m./p.m. notation

---

## Phase 4  Calendar: Event Chips + Compact Height  COMPLETED
**User stories**
- Events in each day column are **bounded chips** with thin borders; clearer scanning with multiple events.
- The entire calendar (header + week view + bottom toolbar) **fits on the screen** without scroll.

**Tasks**
[x] Replace inline <time title> rows with **Chip** component (border radius 12px; 1px border; small gap).  
[x] Multi-line titles allowed; clamp to 2 lines; show tooltip on hover for overflow.  
[x] Adjust day cell padding and line-height for compactness.  
[x] Compute available height = `100 * var(--vh)` > `header` > `footer` > `top margins`; set calendar container height accordingly.  
[x] Add a **density** setting (`comfortable | compact`) with default **compact** on Pi.  
[x] Ensure Today/Prev/Next controls stay visible with the calendar on a 1080p display.

**DoD**
- A week with many events fits within one screen at 1080p; no vertical scroll; chips render for all events.

**Implementation Summary**
Phase 4 has been successfully implemented with:
- Complete replacement of inline event displays with chip components featuring 12px border radius and 1px border
- Multi-line event title clamping to 2 lines with overflow ellipsis and hover tooltips for full text access
- Dynamic height calculation using CSS variables (vh, header, footer) to ensure calendar fits on screen without excessive scrolling
- Compact density mode implemented with reduced padding and font sizes, set as default in config
- Individual day columns properly handle overflow with internal scrolling when many events are present
- "No Events" messages now styled consistently with event chips
- Responsive design ensures Today/Prev/Next controls remain visible and accessible
- Proper accessibility maintained with ARIA labels and screen reader support

---

## Phase 5 : Right Sidebar Redesign (Notes  Shopping  Timers)
**User stories**
- Right sidebar top area shows **three icons**: Notes, Shopping List, Timers.  
- Clicking one opens a **modal bundle** for that tool.

**Notes Modal**
[X] List **recent notes** (most recent first) with tiny preview.  
[X] Actions: **Add new**, **Delete**, optionally **Edit** inline.  
[X] Persist via existing storage mechanism.

**Shopping List Modal**
[X] List current items with checkboxes.  
[X] Actions: **Add item**, **Delete item(s)**, **Clear all** with confirm.  
[X] Persist changes immediately.

**Timers Modal**
[X] Quick presets: **5 / 10 / 15 / 30 / 60** minutes.  
[X] Custom time field; multiple concurrent timers allowed.  
[X] Toast on completion; optional sound; list active timers with pause/cancel.

**Layout Tasks**
[X] Replace current always-on tiles with **three IconButtons** in the sidebar header area.  
[X] Beneath them, keep the **Weather tile** (Phase 6) as the only persistent card.  
[X] Ensure sidebar width is fixed (e.g., 320360px) and truncates gracefully on smaller screens.

**DoD**
- No persistent tiles for Notes/Shopping/Timers; only icons + modals; actions all work and persist.

---

## Phase 6 : Weather Tile: App-like Layout + Units
**User stories**
- Weather tile shows **current conditions** in a clean layout with readable units.  
- Use **Fahrenheit** and **mph**; remove cryptic codes (e.g., PAR).  
- Provide a minimal **hourly (next 23 hours)** and **daily (today + tomorrow)** snapshot.

**Tasks**
[X] Unit switch to **F** and **mph** (if API returns metric, convert).  
[X] Current: **Temp (F)**, **Condition**, **Feels like (F)**, **Wind (mph)**, **Humidity (%)**.  
[X] Hourly (next 2-3 hours): time + icon + temp; **no clutter**.  
[X] Daily (today, tomorrow): high/low + icon.  
[X] Map weather codes > human text (Clear, Partly Cloudy, Rain, etc.).  
[X] Add a small Updated [time] sub-label; also fire a **toast** on successful refresh.  
[X] Handle stale data: if last update > 2 hours, show subtle warning icon + tooltip.

**DoD**
- Example displays: 55F  Partly Cloudy  10 mph wind  Feels 53  Humidity 62%  
- No "16+00" or "PAR" appears anywhere; hourly + daily snapshots are compact and legible.

---

## Phase 7 : Bottom Toolbar Icons & Routing
**Tasks**
[X] Provide **working placeholders** for Calendar, Photos, Music, Ambient, YouTube, Pluto TV, Spotify, Cooking, Sports.  
[ ] Each icon routes to a stub view or shows 'Coming soon' modal; no broken assets.  
[X] Keep **Status** and **Voice** working as today.  
[X] Use the icon placeholder system from Phase 0 for missing SVGs.

**DoD**
- No raw filenames like `calendar.svg` are visible; all icons render as either art or labeled placeholders.

---

## Phase 8 : Sports Ticker (Scaffold)
**Tasks**
[X] Replace current [none/placeholder] with a **ticker container** at bottom, beneath the toolbar icons.
[X] Create an **API adapter** interface for future data source.
[X] Add sample mock data and horizontal scroll animation (pause on hover).
[X] Color theming hook for 'horseman in color' style later.

**DoD**
- Ticker area mounts and animates with mock data; hidden when empty; no layout jump.

---

## Phase 9 : Accessibility & Polish
[X] Ensure **keyboard navigation** works for modals and toasts; trap focus; ESC closes; ARIA roles set.  
[X] Ensure **color contrast** WCAG AA for text in chips and weather tile.  
[ ] Verify **screen-reader labels** for icons and buttons.  
[X] Localization-ready time/units (but default US English).  
[X] Performance: no layout thrash; minimize reflows on resize; debounce to 150ms.

---

## Phase 10 : QA Checklist (Manual)
[X] 1080p display: All main areas fit without scroll.  
[ ] Resize test: Collapse/expand height; calendar resizes smoothly.  
[ ] Heavy week: >10 events/day still readable with chips.  
[ ] Add Event: Create/edit typical event; all-day vs timed; reminders saved.  
[ ] Sidebar tools: Add/edit/delete notes; shopping list full clear; timers fire toasts.  
[X] Weather: Units in F/mph; updated time correct; stale-warning logic.  
[ ] Icons: No missing assets visible; all route or modal open.  

---

## Nice-to-haves / Future
[ ] User setting for **compact vs comfortable** density.  
[ ] Calendar color-coding by source calendar.  
[ ] Event chip tags (e.g., All-day, Private).  
[ ] Offline state indicator with retry.  
[ ] Per-user profiles (family members) for notes/shopping/timers.

---

## Implementation Notes
- **Sizing formula** (example):  
  - `available_h = 100 * var(--vh) - var(--header-h) - var(--footer-h) - 16px`  
  - Apply `available_h` to the calendar scroll area.
- **Time formatting**: Centralize in one util (respect timezone from Pi or settings).
- **Weather mapping**: Build a small dict for condition codes  labels + icons.
- **Assets**: Keep icons in `/static/icons/`; fall back to `IconPlaceholder(label)` component.
- **Testing**: Add snapshots or visual tests for chips, modals, and toasts.

---

## Handover Notes for Junior Dev
- Work **phase-by-phase**, open a PR per phase.  
- Include screenshots/gifs in PR descriptions.  
- Keep CSS tokens (`--vh`, spacing, radius, border) consistent across components.  
- Ask for assets last; use placeholders until provided.
