# CONFIG SCHEMA — Kitchen Hub (`config.yaml`)

## YAML Schema (informal)
```yaml
layout:
  main_view: <string>                 # e.g., week_calendar
  sidebar: [<panel>...]               # names: notes, shopping, weather

apps:
  - id: <slug>
    label: <string>
    icon: <filename.svg>
    action: switch_view|open_iframe|open_tab|run_command
    target?: <view>
    url?: <string>

providers:
  calendar:
    kind: ics|google
    ics_url?: <url>
    google?: { client_id: "", client_secret: "", calendar_ids: [..] }
    google_accounts?:
      - name: <string>                # e.g., primary, spouse
        credentials_file: <path>      # OAuth client JSON path
        token_file: <path>            # per-account token JSON path
        calendar_ids: [..]            # defaults to ["primary"]
        client_id?: <string>          # optional if using credentials_file
        client_secret?: <string>
  weather:
    kind: open_meteo|nws
    location: 
      name?: <string>       # Optional: location name, zip code, or address (e.g., "New York, NY", "10001")
      lat: <float>         # Latitude (required for fallback if name geocoding fails)
      lon: <float>         # Longitude (required for fallback if name geocoding fails)

features:
  voice: <bool>
  kiosk: <bool>
  auth: <bool>

ui:
  theme: auto|light|dark
  density: compact|comfortable
```

## Validation
- Implement with pydantic models.
- Refuse boot if required keys are missing; show exact path of error.
