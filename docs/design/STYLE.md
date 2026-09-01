# Family Hub Style Contract

This document turns the Claude Design export in [`docs/design/claude-design-family-hub`](/docs/design/claude-design-family-hub) into a buildable visual system for the real app.

It is a styling contract, not a component copy guide. The export is a visual reference only. Production structure remains the current Flask + Jinja + HTMX shell in [`templates/base.html`](/templates/base.html) and [`static/css/base.css`](/static/css/base.css).

## Sources Reviewed

- Current app shell and dashboard partials in [`templates/base.html`](/templates/base.html), [`templates/partials/calendar_week.html`](/templates/partials/calendar_week.html), [`templates/partials/calendar_upnext.html`](/templates/partials/calendar_upnext.html), [`templates/partials/shopping_tile.html`](/templates/partials/shopping_tile.html), [`templates/partials/weather_panel.html`](/templates/partials/weather_panel.html), [`templates/partials/commute_map.html`](/templates/partials/commute_map.html), and [`templates/partials/miniplayer.html`](/templates/partials/miniplayer.html)
- Current theme and component tokens in [`static/css/base.css`](/static/css/base.css)
- Product direction in [`PRODUCT_DIRECTION.md`](/PRODUCT_DIRECTION.md), [`docs/UI_SPEC.md`](/docs/UI_SPEC.md), and [`docs/Layout_Update_Plan.md`](/docs/Layout_Update_Plan.md)
- Claude Design export files:
  - [`Family Hub Redesign.html`](/docs/design/claude-design-family-hub/Family%20Hub%20Redesign.html)
  - [`Family Hub Redesign v2.html`](/docs/design/claude-design-family-hub/Family%20Hub%20Redesign%20v2.html)
  - [`design-canvas.jsx`](/docs/design/claude-design-family-hub/design-canvas.jsx)
  - [`postcards.jsx`](/docs/design/claude-design-family-hub/postcards.jsx)
  - [`fixes.jsx`](/docs/design/claude-design-family-hub/fixes.jsx)
  - [`lowlight UI Review.html`](/docs/design/claude-design-family-hub/lowlight%20UI%20Review.html)

## Overall Visual Direction

The export’s usable direction is a calm, dark, TV-first control surface:

- Near-black background with slightly lifted charcoal surfaces
- Cool cyan accent for active state, focus, progress, and badges
- Thin borders instead of heavy shadow stacks
- Large low-weight time display and compact uppercase utility labels
- Dense but readable card layout built for a 1920x1080 always-on screen
- “Quiet appliance” feel rather than consumer-app gloss

The best reference is the pair of `Family Hub Redesign` artboards. The `design-canvas` wrapper, `postcards`, `fixes`, and `lowlight` files are support material, not Family Hub UI structure.

## Core Tokens

Use these as the target dark-theme tokens for the next implementation pass.

### Surfaces

- `--fh-bg`: `#0d1117`
- `--fh-surface-1`: `#161b22`
- `--fh-surface-2`: `#21262d`
- `--fh-surface-3`: `#2d333b`
- `--fh-surface-contrast`: `#09090c`

### Text

- `--fh-text-primary`: `#e6edf3`
- `--fh-text-secondary`: `#8b949e`
- `--fh-text-muted`: `#484f58`
- `--fh-text-on-accent`: `#0d1117`

### Accent / Status

- `--fh-accent`: `#00b4d8`
- `--fh-accent-bg`: `rgba(0,180,216,0.11)`
- `--fh-accent-bg-strong`: `rgba(0,180,216,0.22)`
- `--fh-success`: `#34d399`
- `--fh-warning`: `#f97316`
- `--fh-danger`: keep existing app error red unless a calmer dashboard red is chosen in implementation

### Borders / Chrome

- `--fh-border`: `rgba(255,255,255,0.08)`
- `--fh-border-strong`: `rgba(255,255,255,0.13)` to `rgba(255,255,255,0.14)`

### Calendar Owner Colors

These are present in the prototype and fit the current family-coloring logic:

- `--fh-event-work`: `#00b4d8`
- `--fh-event-family`: `#f97316`
- `--fh-event-personal`: `#a78bfa`
- `--fh-event-kids`: `#34d399`
- `--fh-event-home`: `#8b949e`
- `--fh-event-social`: `#f43f5e`

### Brand / External App Colors

Only use these where tied to real service branding in launcher/miniplayer surfaces:

- Spotify: `#1DB954`
- YouTube: `#FF0000`
- ESPN: `#CC0000`
- Disney+: `#0E3BC4`
- Roku: `#662D91`
- Pluto: `#0B4FFF`

## Typography

### Font Family

- Primary UI font: `Inter`
- Fallback stack: `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

Do not import `Poppins` from the unrelated `lowlight` artifacts for Family Hub.

### Type Rules

- Large display values use light weight: `300`
- Section titles and important values use `600`
- Utility labels use `700`, uppercase, with wide tracking
- General body and metadata live in the `11px` to `14px` range on desktop kiosk layouts

### Practical Scale

- Clock: `52px` to `54px`
- Main numeric weather: `52px`
- Calendar title/date range: `17px`
- Card body titles: `13px`
- Card metadata: `11px` to `12px`
- Utility labels: `10px` to `11px`, uppercase, `0.08em` to `0.1em` letter spacing

## Spacing Scale

The export repeatedly uses a tight kiosk spacing rhythm:

- `4px`
- `8px`
- `10px`
- `12px`
- `14px`
- `16px`
- `18px`
- `20px`
- `24px`

Recommended implementation token set:

- `--fh-space-1`: `4px`
- `--fh-space-2`: `8px`
- `--fh-space-3`: `12px`
- `--fh-space-4`: `16px`
- `--fh-space-5`: `20px`
- `--fh-space-6`: `24px`

Use tighter interior padding than the current UI where it improves glanceability, but do not reduce touchable controls below accessible minimums.

## Border Radius

The prototype uses a consistent rounded language:

- App shell/cards: `12px`
- Smaller inner cards and chips: `8px`
- Tiny inner bars: `2px` to `5px`
- Utility/action pills: `20px`
- Fully pill/circular badges and icon buttons: `999px` / `50%`

Recommended mapping:

- `--fh-radius-card`: `12px`
- `--fh-radius-control`: `8px`
- `--fh-radius-pill`: `999px`
- `--fh-radius-chip`: `8px`

## Shadow / Elevation

The prototype relies on borders first and shadow second.

- Default cards: minimal or no visible shadow
- Floating/overlay surfaces only: soft deep shadow
- Miniplayer pill concept: strong blur + soft shadow, but only if actually floating

Recommended rule:

- Standard dashboard cards: thin border, no heavy shadow
- Elevated modal/floating surfaces: one soft shadow layer only
- Do not mix multiple glossy shadow treatments across the shell

## App Shell

### Main Layout

- Preserve the current three-zone shell:
  - main calendar/content area
  - right sidebar
  - fixed bottom app bar
  - bottom sports ticker when enabled

- Visual target:
  - main background `#0d1117`
  - sidebar as a slightly lifted surface with left divider
  - bottom navigation as a stable dark dock, not a bright toolbar

### Header / Topbar

- Keep calendar controls compact and horizontally grouped
- Date range/title should read as calm and secondary to the content, not like a page title banner
- Today/view controls should use accent-outline or accent-tint treatment, not solid bright buttons by default

### Sidebar

- Right rail should feel like a composed utility stack
- Clock/date stay at the top with a subtle progress bar
- Quick tools should live in one unified grouped tile with separators
- Weather and miniplayer should read as separate but visually aligned modules beneath

## Calendar Layout Treatment

- Calendar remains the primary surface
- Use dark grid with subtle hour rules and a lightly tinted “today” column
- Day headers use small uppercase weekday plus circular day-number emphasis
- Event blocks/chips use owner-color left rails and low-chroma tinted fills
- “Now” line stays bright accent cyan with dot marker
- All-day row should be compact and secondary

Month/week toggle and navigation can borrow the prototype’s capsule/button treatment, but week/month behavior and real event interactions must stay intact.

## Cards, Lists, and Widgets

- Standard card background: `--fh-surface-1`
- Interior nested cards: `--fh-surface-2`
- Borders are subtle and always present
- Card headers should use small uppercase utility labels instead of large chrome-heavy bars
- List rows should favor simple line items with small badges or left-edge markers over boxed rows unless interaction requires it

### Up Next

- Vertical event list with left color bar
- Time on the left, title as primary content
- “Now” row may use accent emphasis
- Secondary date badge only when needed, such as “Tomorrow”

### Shopping

- Compact preview list
- Count badge in header
- Empty state must still be visible and tappable; do not fade the whole card away

### Commute / Timer

- Lower-right utility card can visually match the prototype’s simple stats card
- Progress bar and status pill treatment are valid
- Preserve the current real commute-or-quick-timer fallback behavior

## Ticker / Status Strip

- Sports ticker should sit in a dark strip below the app bar
- Background target: `#09090c`
- Content should scroll on a single line with muted text
- Accent label block is optional; v2 omits it
- Avoid overly bright separators or oversized league glyphs

Toast/system status should not copy the sports strip styling. Keep those distinct.

## Family / Home / Kitchen Module Treatment

- Family-owned data should be color-coded through event owner/category accents, not by changing full-card backgrounds
- Home/kitchen utility modules should feel practical and information-dense
- Kitchen reference, timers, shopping, and commute should visually belong to the same system as weather and miniplayer
- Avoid decorative illustration-heavy treatments from unrelated export files

## Buttons and Controls

- Default controls: dark surface, subtle border, text in secondary color
- Active controls: accent-tinted background and accent border/text
- Icon buttons may be circular or pill-like, but should be visually quiet
- Launcher buttons can keep brand-color icons while the surrounding shell stays neutral

Important accessibility correction:

- The prototype uses some `28px` to `36px` controls that are too small for the real touch-friendly kiosk
- Production controls should keep at least `44px` touch targets, with `48px` preferred for primary tap areas

## Empty, Loading, and Error States

- Empty states should remain visible, intentional, and actionable
- Loading states should use reserved space and calm placeholder treatment rather than flash/reflow
- Error and stale states should be explicit but non-alarming
- “Quiet honesty” is the target:
  - clear status label
  - last updated timestamp where relevant
  - next action if available, such as reconnecting Spotify or calendar auth

Do not replace live content modules with static “coming soon” shells unless the current app already behaves that way.

## Responsive Behavior

The export is 1920x1080-first. The real app must also support smaller browser widths and touch devices.

- Preserve the one-screen kiosk composition at 1080p first
- On narrower widths:
  - bottom card row should wrap or stack cleanly
  - sidebar content may compress before becoming unreadable
  - app bar labels may shrink but must stay legible
- Avoid copying fixed-pixel export measurements blindly
- Respect the current app’s dynamic height calculations for the calendar and fixed footer/ticker relationship

## Accessibility Notes

- Maintain strong contrast between `#0d1117` / `#161b22` surfaces and `#e6edf3` text
- Secondary text in `#8b949e` is acceptable for metadata, but avoid using `#484f58` for primary readable copy
- Accent cyan on dark is suitable for focus and active state, but verify contrast for smaller text
- Keep visible focus rings in the real app even if the prototype omits them
- Preserve keyboard access and modal semantics from the current implementation
- Maintain `44px` to `48px` touch targets even when the visual shape looks compact
- Do not rely on color alone for meaning in event ownership or status states

## Explicit Non-Production Elements

The following are not production structure and should not be copied as-is:

- `design-canvas.jsx` framing, focus mode, artboard controls, and sidecar state file
- static mock data, fake scores, fake playlists, and fake family content in the redesign HTML
- unrelated `lowlight`, `fixes`, and `postcards` visual experiments
- exact DOM hierarchy from the artboards

The production contract is the design language, not the prototype markup.
