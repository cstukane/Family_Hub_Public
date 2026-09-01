# ROADMAP  Kitchen Hub

## Near-Term
- Sports ticker score polish (live in-game score push cadence tuning)

## Mid-Term
- Profiles & presence strip
- Summary card for currently selected favorite teams (Settings Phase 4)
- Settings Phase 1: loading spinners, progress bars for cache operations, tooltips
- Settings Phase 2: richer error recovery messages, persistent status feedback

## Long-Term
- Local voice: wake word + STT (Porcupine + Whisper/Vosk)
- Automatic update scheduling integration with APScheduler

## Completed
- WebSocket push for Up Next + timers (hub/sockets.py)
- Sports ticker with team filters (hub/services/sports_ticker_service.py)
- Settings Phase 3: ARIA labels, keyboard shortcuts, skip links, keyboard navigation
- Optional adapter fallback NameError fix (hub/adapters/__init__.py, hub/services/casting.py)
- Python 3.11 baseline alignment (pyproject.toml)
- Media launcher consolidated to hub/services/media_launcher.py
