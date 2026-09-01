#!/bin/bash

# Script to generate and install systemd service files for Kitchen Hub
# Usage: sudo ./gen_systemd.sh [username]
# Default username is 'pi' if not specified

set -e

USERNAME=${1:-pi}
INSTALL_DIR="/opt/kitchen-hub"
SERVICE_NAME="kitchen-hub"
KIOSK_SERVICE_NAME="kitchen-hub-kiosk"

echo "Generating systemd service files for user: $USERNAME"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "This script should NOT be run as root. It will use sudo where needed."
    exit 1
fi

# Check if the kitchen-hub directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Error: $INSTALL_DIR does not exist. Please install Kitchen Hub first."
    exit 1
fi

# Create service files from templates
echo "Creating service files from templates..."

# Generate the app service file
sed "s/%i/$USERNAME/g" "$INSTALL_DIR/ops/systemd/kitchen-hub.service.tmpl" > "/tmp/kitchen-hub.service"
sudo cp "/tmp/kitchen-hub.service" "/etc/systemd/system/kitchen-hub@$USERNAME.service"
rm "/tmp/kitchen-hub.service"

# Generate the kiosk service file
sed "s/%i/$USERNAME/g" "$INSTALL_DIR/ops/systemd/kitchen-hub-kiosk.service.tmpl" > "/tmp/kitchen-hub-kiosk.service"
sudo cp "/tmp/kitchen-hub-kiosk.service" "/etc/systemd/system/kitchen-hub-kiosk@$USERNAME.service"
rm "/tmp/kitchen-hub-kiosk.service"

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Service files created successfully!"
echo ""
echo "To enable and start the services, run:"
echo "  sudo systemctl enable kitchen-hub@$USERNAME.service"
echo "  sudo systemctl enable kitchen-hub-kiosk@$USERNAME.service"
echo "  sudo systemctl start kitchen-hub@$USERNAME.service"
echo "  sudo systemctl start kitchen-hub-kiosk@$USERNAME.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status kitchen-hub@$USERNAME.service"
echo "  sudo systemctl status kitchen-hub-kiosk@$USERNAME.service"