#!/bin/bash

# Script to generate and install systemd service files for Family Hub
# Usage: sudo ./gen_systemd.sh [username]
# Default username is 'pi' if not specified

set -e

USERNAME=${1:-pi}
INSTALL_DIR="/opt/family-hub"
SERVICE_NAME="family-hub"
KIOSK_SERVICE_NAME="family-hub-kiosk"

echo "Generating systemd service files for user: $USERNAME"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "This script should NOT be run as root. It will use sudo where needed."
    exit 1
fi

# Check if the family-hub directory exists
if [[ ! -d "$INSTALL_DIR" ]]; then
    echo "Error: $INSTALL_DIR does not exist. Please install Family Hub first."
    exit 1
fi

# Create service files from templates
echo "Creating service files from templates..."

# Generate the app service file
sed "s/%i/$USERNAME/g" "$INSTALL_DIR/ops/systemd/family-hub.service.tmpl" > "/tmp/family-hub.service"
sudo cp "/tmp/family-hub.service" "/etc/systemd/system/family-hub@$USERNAME.service"
rm "/tmp/family-hub.service"

# Generate the kiosk service file
sed "s/%i/$USERNAME/g" "$INSTALL_DIR/ops/systemd/family-hub-kiosk.service.tmpl" > "/tmp/family-hub-kiosk.service"
sudo cp "/tmp/family-hub-kiosk.service" "/etc/systemd/system/family-hub-kiosk@$USERNAME.service"
rm "/tmp/family-hub-kiosk.service"

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Service files created successfully!"
echo ""
echo "To enable and start the services, run:"
echo "  sudo systemctl enable family-hub@$USERNAME.service"
echo "  sudo systemctl enable family-hub-kiosk@$USERNAME.service"
echo "  sudo systemctl start family-hub@$USERNAME.service"
echo "  sudo systemctl start family-hub-kiosk@$USERNAME.service"
echo ""
echo "To check status:"
echo "  sudo systemctl status family-hub@$USERNAME.service"
echo "  sudo systemctl status family-hub-kiosk@$USERNAME.service"