# Manual Smoke Tests - Family Hub Media Child Windows

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

## Manual Test Steps

### 1. Test Hub UI Server
1. Start the hub app server:
   ```bash
   python hub_app.py
   ```

2. Open browser and navigate to `http://127.0.0.1:5000`
3. Verify the main hub UI loads correctly
4. Verify static assets (CSS, JS) load correctly
5. Verify the `/media_control` endpoint loads the controller UI

### 2. Test Static Files Serving
1. Navigate to `http://127.0.0.1:5000/css/main.css` - should load CSS
2. Navigate to `http://127.0.0.1:5000/js/media-client.js` - should load JS
3. Navigate to `http://127.0.0.1:5000/images/` - if images exist, should serve them

### 3. Test Media Control Overlay
1. Navigate to `http://127.0.0.1:5000/media_control`
2. Verify the controller overlay UI loads
3. Verify the "Home" button is visible
4. Verify the styling applies correctly

### 4. Windows Development Flow
1. Make sure `hub_app.py` is running on port 5000
2. Launch using Windows script:
   ```bash
   scripts\start_chrome_win.bat
   ```
3. Verify Chrome opens in app mode with the hub UI

### 5. Linux/PI Development Flow
1. Make sure `hub_app.py` is running on port 5000
2. Launch using Linux script:
   ```bash
   ./scripts/start_kiosk.sh
   ```
3. Verify Chromium opens in app mode with the hub UI

## Expected Results
- Hub UI should load at `http://127.0.0.1:5000`
- All static assets should load without 404 errors
- Media control overlay should be available at `/media_control`
- Both Windows and Linux launch scripts should properly open the hub UI in app mode

## Troubleshooting
- If the server fails to start, check that port 5000 is available
- If static files don't load, verify the `hub_ui` directory structure
- If Chrome doesn't launch, verify Chrome/Chromium is installed and accessible

## Windows-Specific Acceptance Checklist (Phase 6)

1. **Run dev startup script**
   - Execute `scripts\dev_run.bat`
   - Verify it checks for and activates virtual environment
   - Verify it starts both `hub_app.py` and `media_launcher.py` services
   - Verify it launches the UI in Chrome via `start_chrome_win.bat`

2. **Test media spawning**
   - Click YouTube icon in the UI
   - Verify a separate Chrome window opens with YouTube
   - Verify the original hub UI window remains active

3. **Test controller overlay**
   - Verify a small floating controller window appears (with "Home" button)
   - Click the controller's "Home" button
   - Verify the media window closes but the main hub UI remains

4. **Test keyboard shortcuts**
   - With media window open, press `Ctrl+Shift+X` in main UI
   - Verify the media window closes
   - Try double-pressing `Esc` quickly (within 400ms)
   - Verify media window closes on double-Esc

5. **Verify process cleanup**
   - Close the main UI window
   - Verify that any spawned media processes are cleaned up properly
   - Check Windows Task Manager to ensure no orphaned Chrome processes remain

## Test Completion
If all steps pass, Phase 6 implementation is successfully complete.