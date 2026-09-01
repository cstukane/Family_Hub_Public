# Deployment Guide

This guide covers common deployment paths for Family Hub.

## Linux (production with systemd)

### Prereqs
- Python 3.11+
- Chromium
- nginx (optional, for HTTPS)
- systemd

### Install
```bash
sudo apt update
sudo apt install -y python3 python3-venv chromium-browser nginx
sudo git clone <repository-url> /opt/family-hub
cd /opt/family-hub
make venv
make install
```

### Configure the appliance
```bash
mkdir -p instance
cp config.example.yaml instance/config.yaml
cp .env.example instance/.env
chmod 600 instance/config.yaml instance/.env
# Edit both ignored local files, then deploy.
```

The generated systemd unit explicitly sets
`FAMILY_HUB_CONFIG=/opt/family-hub/instance/config.yaml`. Production therefore
fails clearly if the deployment config is missing instead of using the safe
example configuration.

> **Existing install migration:** copy the former root `config.yaml` to
> `/opt/family-hub/instance/config.yaml`, move secret overrides to
> `/opt/family-hub/instance/.env`, set both files to mode `600`, regenerate the
> units with `make gen-systemd`, and restart `family-hub@<user>.service`.

### Generate systemd services and deploy
```bash
make gen-systemd
make deploy
```

### Optional: HTTPS via nginx
```bash
make deploy-nginx
sudo ./scripts/setup_ssl.sh your-domain.com your-email@example.com
```

## Raspberry Pi (kiosk)

### Prereqs
- Raspberry Pi OS with desktop
- Chromium
- Python 3.11+

### Install and run
```bash
sudo apt update
sudo apt install -y chromium-browser python3 python3-venv
git clone <repository-url> family-hub
cd family-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p instance
cp config.example.yaml instance/config.yaml
cp .env.example instance/.env
make run
```

### Start kiosk
```bash
./scripts/start_kiosk.sh
```

## Windows (development/test)

### Prereqs
- Python 3.11+
- Chrome or Chromium

### Setup
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
mkdir instance 2>nul
copy config.example.yaml instance\config.yaml
copy .env.example instance\.env
```

### Run
```cmd
make run
```

Open http://localhost:5000 in Chrome for kiosk testing.

## Health and validation

- `/health` returns application status (app version, platform, timestamp).
- ~~`/metrics`~~ Removed 2026-06-14 (deleted with metrics/Prometheus subsystem).
- ~~`/status`~~ Removed 2026-06-14 (deleted with metrics subsystem).

## Service management (systemd)

```bash
sudo systemctl status family-hub@<user>.service
sudo systemctl status family-hub-kiosk@<user>.service
sudo journalctl -u family-hub@<user>.service -f
```
