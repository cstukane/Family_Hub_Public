# UI SPEC  Kitchen Hub

## Layout
- **Primary region**: Calendar week view (default)
- **Sidebar (right)**: stacked panels `notes`, `shopping`, `weather`
- **App Bar (bottom)**: big labeled buttons with icons

## Components
- **Calendar Week Grid**
  - MonSun, 07:0022:00 visible; Now line
  - All-day row at top
  - Up Next chip shows next 12 events
- **Notes**
  - List newest first; simple textarea + Add
  - Delete inline with confirmation
- **Shopping**
  - Add item (text + qty); toggle done with strike-through
  - Show counts
- **Weather**
  - Current: temp, feels-like, icon, humidity, wind
  - Hourly strip (next 1224h), Daily (5 cards)
- **Media Pane**
  - Iframe region; loads selected app URL; fullscreen button

## Accessibility
- Min target height: 48px
- Visible focus rings; keyboard navigable
- High-contrast check

## Theming
- CSS variables for color, spacing, radius, shadows
- `prefers-color-scheme` respected if `ui.theme=auto`