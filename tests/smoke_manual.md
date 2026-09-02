# Manual Smoke Tests - Family Hub

## Pre-requisites
- Python 3.11+ installed
- Chrome or Chromium browser installed
- Virtual environment with dependencies installed

## Test Setup
1. Create and activate virtual environment:
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On Linux/Mac:
    source venv/bin/activate
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3. Copy configuration:
    ```bash
    mkdir -p instance
    copy config.example.yaml instance\config.yaml
    copy .env.example instance\.env
    ```

## Manual Test Steps

### 1. Test App Startup
1. Start the Family Hub server:
    ```bash
    python app.py
    # or
    make run
    ```

2. Open browser and navigate to `http://localhost:5000`
3. Verify the dashboard loads correctly
4. Verify static assets (CSS, JS) load without 404 errors
5. Verify `/health` returns `{"status": "ok"}`

### 2. Test Core Dashboard
1. Verify calendar widget renders
2. Verify weather widget renders (or shows disabled state if no API key)
3. Verify sports ticker renders (or shows disabled state if no API key)
4. Verify shopping list widget renders
5. Verify notes widget renders
6. Verify timers widget renders

### 3. Test Public App Launcher
1. Click a public launcher button (e.g., YouTube, ESPN)
2. Verify it opens in a new tab or iframe as configured
3. Verify no private/homelab launcher entries appear

## Expected Results
- App starts on port 5000
- `/health` returns `{"status": "ok", "service": "family-hub"}`
- Dashboard renders all enabled widgets
- Public launcher destinations work
- No references to private companion apps or localhost media services appear in the UI

## Troubleshooting
- If the server fails to start, check that port 5000 is available
- If static assets don't load, verify the `static/` directory structure
- If Chrome doesn't launch, verify Chrome/Chromium is installed and accessible

## Test Completion
If all steps pass, the basic Family Hub dashboard is working.
