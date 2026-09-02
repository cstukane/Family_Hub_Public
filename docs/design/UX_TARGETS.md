# Family Hub UX Targets

This document defines how the Claude Design export should influence the real Family Hub UI.

The export is illustrative. The current app behavior remains the source of truth unless a future implementation pass intentionally changes it.

## What To Adopt

- The darker, quieter kiosk visual language from the two `Family Hub Redesign` artboards
- A tighter, more intentional shell with clear separation between main canvas, right rail, app dock, and sports strip
- A calmer sidebar hierarchy:
  - large clock/date first
  - grouped quick tools second
  - weather and miniplayer as persistent modules beneath
- The calendar treatment:
  - subtle today highlight
  - cleaner day headers
  - restrained event block fills with color-rail ownership cues
- The lower utility row as three compact glance cards:
  - Up Next
  - Shopping
  - Commute or quick timer
- Shopping header count badge and stronger scanability
- Weather styling that reads as a single concise weather appliance, not a generic widget
- App bar buttons that feel like a dock instead of loose flat buttons
- Thin-border, low-shadow surfaces throughout the dashboard

## What Not To Copy Blindly

- The `design-canvas` wrapper and any artboard controls
- Static sample content, fake schedules, fake playlists, fake weather, and fake sports strings
- The prototype’s exact pixel sizes
- The prototype’s too-small buttons and icon controls
- The prototype’s React/Babel markup structure
- The floating miniplayer pill concept unless it is validated against the real app shell and interaction model
- Any unrelated styles from `lowlight UI Review.html`, `postcards.jsx`, or `fixes.jsx`

## Current App Behavior That Must Be Preserved

- The app remains server-rendered with Flask + Jinja + HTMX and Socket.IO, not a prototype-style React screen
- Calendar remains the main functional anchor with real week/month switching, navigation, live data, and add-event behavior
- The current modal flows for notes, shopping, timers, and kitchen reference stay functional
- Shopping, notes, and timers remain real data flows, not decorative previews
- The commute tile must preserve its real dynamic fallback to quick timer when commute is unavailable or outside active windows
- The sports ticker remains data-driven and optional based on real feature flags/config
- The miniplayer must preserve real Spotify/device/source behavior and honest disconnected states
- Existing accessibility hooks, keyboard behavior, and focus treatment should not be lost during visual polish
- Last-updated and failure-state work already called for in product docs remains a core requirement

## Areas Where The Export Is Illustrative Only

- Calendar sample density and event titles
- Weather values and layout exactness
- Shopping counts and items
- App-bar icon lineup and branding mix
- Sports ticker copy and scroll cadence
- Miniplayer playlists, device names, and playback state
- Any “Home” or launcher emphasis that changes current navigation semantics

These examples are useful for hierarchy and tone, not for content or feature scope.

## Implementation Risks

- The prototype is 1920x1080-only; blindly porting it could regress phone-width or small-window behavior
- Some prototype controls are below the real app’s touch target standards
- The prototype assumes static happy-path states and under-specifies stale, loading, auth-expired, and empty conditions
- The design export uses mock structure that hides how much live functionality the real dashboard already carries
- The shopping empty state in the current app is intentionally identified as weak in product direction; a visual pass could accidentally make it prettier without making it more actionable
- The miniplayer is the highest-risk area for visual-only implementation because the real component has much more state than the prototype
- Calendar week-start and date presentation in the prototype should not override real current logic unless explicitly chosen

## Suggested First Implementation Pass

1. Introduce formal dashboard design tokens in CSS based on the extracted dark theme.
2. Restyle the shell:
   main background, sidebar surface, app bar, ticker strip, dividers, spacing, and typography.
3. Restyle the calendar chrome and day headers without changing calendar behavior.
4. Restyle the lower three cards:
   Up Next, Shopping, and Commute/Quick Timer.
5. Fix the shopping empty state so it is visible and clearly tappable.
6. Restyle the sidebar grouped tools, weather panel, and compact miniplayer shell.
7. Add honest stale/updated/error styling patterns that work across calendar, weather, commute, and ticker.

This sequence gets the real dashboard closer to the export while staying inside the existing app structure.

## Follow-Up Polish Ideas

- Expanded miniplayer browse/source treatment, but only after disconnected and live playback states are designed honestly
- Stronger launcher active state and brand/icon consistency
- Better empty-week handling in the main calendar zone for low-event days
- Refined ticker spacing, pause-on-hover behavior, and clearer score grouping
- More deliberate motion for modal entry, card refresh, and app-bar state changes
- A formal light-theme counterpart only if the team still wants theme switching after the dark-kiosk pass lands

## Recommended Compromises Where Design And Reality Differ

- Keep the real shell and partial boundaries; only adopt the artboards’ hierarchy and styling
- Keep current weather data shape and forecasting scope even if the prototype simplifies the labels
- Keep current miniplayer capabilities even if the first visual pass only surfaces a subset more cleanly
- Preserve the current kitchen reference modal behavior even though it is not represented in the export
- Preserve app launch behavior and companion-app routing even if the dock visuals become more minimal

## Human Decisions Still Needed

- Whether the bottom-right utility card should visually prioritize commute or quick timer when both are conceptually available
- Whether the sports ticker should keep the labeled “SPORTS” badge from the first prototype or use the cleaner unlabeled v2 strip
- Whether the miniplayer should stay docked in the sidebar only, or later experiment with a floating pill variant
- Whether event owner colors should be expanded into a formal family legend in the shell
- How aggressively to tighten spacing in the calendar before readability drops on the actual kitchen display

## Bottom Line

Adopt the export as a dark-theme visual target and hierarchy cleanup, not as application structure.

If a prototype choice conflicts with live data, real interaction, accessibility, or the current product direction, keep the working app behavior and style around it.
