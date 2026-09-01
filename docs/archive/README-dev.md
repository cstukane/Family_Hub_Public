# Development and Raspberry Pi Guide

This guide covers Windows development and Raspberry Pi kiosk setup.

## Windows development

### Prereqs
- Python 3.11+
- Chrome or Chromium

### Setup
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

### Run
```cmd
make run
```

Open `http://localhost:5000` in Chrome for testing.

### Media child windows

- The media launcher listens on `http://127.0.0.1:7666`.
- The controller overlay uses `/media_control` on the hub app.

## Raspberry Pi deployment

### Prereqs
- Raspberry Pi OS with desktop
- Chromium browser
- Python 3.11+

### Setup
```bash
sudo apt update
sudo apt install -y chromium-browser python3 python3-venv
git clone <repository-url>
cd family-hub
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Run
```bash
make run
```

### Start kiosk mode
```bash
./scripts/start_kiosk.sh
```

## Media launcher security

- Uses JWTs by default (Authorization: Bearer).
- Legacy auth can be enabled with `MEDIA_LAUNCHER_ALLOW_LEGACY_AUTH`.
- Allowed domains are listed in `config/media_whitelist.json`.
