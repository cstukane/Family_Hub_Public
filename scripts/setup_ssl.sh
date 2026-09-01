#!/bin/bash
# Script to set up Let's Encrypt SSL certificates for Kitchen Hub
# Usage: sudo ./setup_ssl.sh yourdomain.com

set -e

DOMAIN=${1:-yourdomain.com}
EMAIL=${2:-admin@yourdomain.com}
WEBROOT_PATH="/var/www/certbot"

echo "Setting up SSL certificate for domain: $DOMAIN"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
    echo "This script should NOT be run as root. It will use sudo where needed."
    exit 1
fi

# Install certbot if not already installed
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    sudo apt update
    sudo apt install -y certbot
fi

# Create webroot directory if it doesn't exist
sudo mkdir -p $WEBROOT_PATH

# Obtain the certificate using webroot method
echo "Obtaining SSL certificate from Let's Encrypt..."
sudo certbot certonly --webroot --webroot-path $WEBROOT_PATH --domain $DOMAIN --email $EMAIL --agree-tos --non-interactive

echo "SSL certificate setup complete!"
echo "Certificate location: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
echo "Private key location: /etc/letsencrypt/live/$DOMAIN/privkey.pem"

echo ""
echo "To renew certificates automatically, add this to your crontab:"
echo "0 12 * * * /usr/bin/certbot renew --quiet"