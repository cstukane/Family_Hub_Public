#!/bin/bash
# Script to generate nginx configuration from template
DOMAIN=${1:-localhost}

sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled

# Copy the template and substitute variables
sudo cp /opt/family-hub/ops/nginx/family-hub.conf.tmpl /tmp/family-hub.conf

# Replace template variables
sudo sed -i "s/{{SERVER_NAME}}/$DOMAIN/g" /tmp/family-hub.conf
sudo sed -i "s|{{SSL_CERT_PATH}}|/etc/letsencrypt/live/$DOMAIN/fullchain.pem|g" /tmp/family-hub.conf
sudo sed -i "s|{{SSL_KEY_PATH}}|/etc/letsencrypt/live/$DOMAIN/privkey.pem|g" /tmp/family-hub.conf

# Move to sites-available and enable
sudo mv /tmp/family-hub.conf /etc/nginx/sites-available/family-hub.conf
sudo ln -sf /etc/nginx/sites-available/family-hub.conf /etc/nginx/sites-enabled/family-hub.conf

# Test nginx configuration
sudo nginx -t && echo "Nginx configuration test passed"

# Restart nginx to apply changes
sudo systemctl restart nginx

echo "Nginx configuration updated for domain: $DOMAIN"