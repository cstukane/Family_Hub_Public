# GOAL & SCOPE  Kitchen Hub

## Goal
A self-contained, always-on **Kitchen Hub** that runs on a small PC or Raspberry Pi, launching in a kiosk browser and offering:
- Calendar-first dashboard (week grid + Up Next)
- Notes & Shopping list (local, fast, reliable)
- Weather (current/hourly/daily)
- Media launcher (YouTube/Pluto/Spotify) in an iframe/tab
- Config-driven layout
- Solid 24/7 reliability and graceful failure modes

## Out of Scope (MVP)
- Full smart-home control (optional later via Home Assistant adapter)
- Advanced voice (local wake word + transcription)  optional
- Multi-user auth & profiles  optional
- External task sync (Todoist/Google Tasks)  optional
- Complex SPA framework

## Non-Functional Requirements
- Robust on reboot/power loss (systemd + kiosk autostart)
- Clear error surfacing and last-updated stamps
- Caching to limit API calls
- LAN-first privacy; no cloud dependency for core features