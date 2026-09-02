#!/bin/bash
# start_kiosk.sh - Linux/PI launcher for Family Hub
# Run the hub UI in a single Chromium window for the home screen

# Set the URL to the hub UI
URL="http://127.0.0.1:5000"

# Find the best available Chromium/Chrome binary
if [ -x "/usr/bin/chromium-browser" ]; then
    CHROME="/usr/bin/chromium-browser"
elif [ -x "/usr/bin/chromium" ]; then
    CHROME="/usr/bin/chromium"
elif [ -x "/usr/bin/google-chrome" ]; then
    CHROME="/usr/bin/google-chrome"
else
    echo "Error: No Chromium/Chrome binary found in common locations"
    exit 1
fi

echo "Using Chrome binary: $CHROME"

# Launch Chromium in app mode with kiosk-like flags
# --app runs as a standalone window without address bar
# --disable-infobars prevents info bars from appearing
# --noerrdialogs suppresses error dialogs
# --disable-session-crashed-bubble prevents crash recovery UI
# --enable-features=VaapiVideoDecoder enables hardware video decoding (Pi-specific)
# --use-gl=egl enables GPU acceleration (Pi-specific)
echo "Starting Family Hub UI in kiosk mode..."
$CHROME \
    --app="$URL" \
    --disable-infobars \
    --noerrdialogs \
    --disable-session-crashed-bubble \
    --enable-features=VaapiVideoDecoder \
    --use-gl=egl \
    --disable-dev-shm-usage \
    --disable-extensions \
    --disable-plugins-discovery \
    --bwsi

echo "Chromium window closed or failed to start."
