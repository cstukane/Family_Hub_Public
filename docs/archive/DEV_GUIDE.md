# Development Guide

## Prereqs

- Python 3.11+
- Chromium or Chrome (required for E2E tests)

## Setup

<!-- AUTO-GENERATED from Makefile -->
```bash
make venv      # create .venv with Python 3.11+
make install   # install dependencies from requirements.txt
cp .env.example .env
```

On Windows (no `make`):
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
<!-- END AUTO-GENERATED -->

## Run

<!-- AUTO-GENERATED from Makefile -->
```bash
make run   # activates .venv and starts Flask on 0.0.0.0:5000
```

Health check: `curl http://localhost:5000/health`
<!-- END AUTO-GENERATED -->

Optional (media launcher service):
```bash
python media_launcher.py
```

## Configuration

- `config.yaml` drives layout, providers, and feature toggles.
- `.env` supplies secrets and overrides. See `docs/ENVIRONMENT_VARIABLES.md`.

## Testing

<!-- AUTO-GENERATED -->
| Command | Description |
|---------|-------------|
| `PYTHONPATH=. pytest` | Run all tests |
| `PYTHONPATH=. pytest tests/<file>.py -v` | Run a single test file |
| `PYTHONPATH=. pytest tests/e2e/ -v --browser chromium` | Run E2E tests (requires Playwright) |

**First-time E2E setup:**
```bash
pip install pytest-playwright playwright
python -m playwright install chromium
```
<!-- END AUTO-GENERATED -->

## Linting & Formatting

<!-- AUTO-GENERATED from pyproject.toml -->
```bash
ruff check .   # lint (line length 120, Python 3.8 target)
black .        # format
bandit -r hub/ # security scan
```

Install dev extras first: `pip install -e ".[dev]"`
<!-- END AUTO-GENERATED -->
