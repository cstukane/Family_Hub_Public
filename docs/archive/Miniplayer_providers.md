# Miniplayer Provider Rollout

Guiding principles:
- Keep Spotify as the default provider; every new provider plugs into the shared `MusicProvider` interface.
- Expose provider capabilities (`playback`, `queue`, `favorites`, `seek`) so the existing miniplayer chrome only shows controls that make sense.
- Use the service tray badge + modal to let the user switch providers without reloading the dashboard.

---

## Radio Browser (FM / iHeart-style)

- [ ] **Phase 1  Provider plumbing**
  - [ ] Extend `config.music.providers` with an entry for `radio_browser`, storing API base URL and default ZIP/city presets.
  - [ ] Implement a `RadioBrowserProvider` class (HTTP client + provider interface) that can search by `country/state/city` and retrieve stream URLs + metadata.
  - [ ] Persist user favorites (stations + ZIP) alongside playlists so the UI can surface them.

- [ ] **Phase 2  API + backend endpoints**
  - [ ] Add `/api/music/providers/radio_browser/stations`, `/favorites`, `/presets`, and `/play` routes that funnel through the provider registry.
  - [ ] Wire the global active provider setter so selecting Radio Browser swaps the playback controller to this provider.

- [ ] **Phase 3  Miniplayer integration**
  - [ ] Populate the service tray modal with Radio Browser, showing connection status (always Ready) and list of saved stations.
  - [ ] Map existing controls:
    - Play/Pause  start/stop the selected stream.
    - Skip/Back  cycle through saved stations.
    - Seek slider  open Change ZIP/City modal (optional).
    - Playlist dropdown  favorites list.
    - Queue panel  other saved cities/stations.
  - [ ] Display current station metadata (station name, bit rate, genre) in the track area.

---

## SomaFM (Curated ambient/genre streams)

- [ ] **Phase 1  Static catalog**
  - [ ] Import SomaFMs JSON channel feed during build/startup and cache station metadata (name, description, now-playing endpoint, stream URLs).
  - [ ] Add a `somafm` provider entry in config, allowing you to hide/show specific channels.

- [ ] **Phase 2  Provider implementation**
  - [ ] Implement `SomaFmProvider` with methods to list channels, fetch now-playing text, and return the stream URL for playback.
  - [ ] Add lightweight caching for now-playing lookups to avoid hammering their API (e.g., 30s TTL).

- [ ] **Phase 3  Miniplayer wiring**
  - [ ] When user selects SomaFM, populate the playlist dropdown with channels grouped by vibe (Jazz, Ambient, Electronic, etc.).
  - [ ] Keep Play/Pause + Skip/Back as start this channel / go to next channel in favorites.
  - [ ] Repurpose the queue panel to show the current channel description + upcoming tracks (if available from now-playing feed).
  - [ ] Update the album-art slot with SomaFMs channel art.

---

## Podcast Index (Podcasts + episodes)

- [ ] **Phase 1  Provider + storage**
  - [ ] Create a `PodcastIndexProvider` that handles search (by keyword/feed ID) and fetches episode metadata via their API.
  - [ ] Add tables for `podcast_subscriptions` and cached `podcast_episodes` (title, media URL, duration, published_at, artwork).

- [ ] **Phase 2  API surface**
  - [ ] Add `/api/music/providers/podcast_index/search`, `/subscriptions`, `/episodes`, `/play` endpoints.
  - [ ] Support optional API key/secret in config (Podcast Index offers improved rate limits when authenticated).

- [ ] **Phase 3  Miniplayer UX**
  - [ ] Playlist dropdown lists subscribed podcasts; selecting one loads recent episodes into the queue panel.
  - [ ] Queue entries become tap-to-play episode rows; include duration + publish date.
  - [ ] Hook Skip/Back to 15s seek; expose 15s buttons near the transport or overload existing skip buttons when Podcast Index is active.
  - [ ] Display episode artwork + title/host in the main track area.
  - [ ] (Optional future) Add playback enhancements like Smart Speed or bass boost once basic streaming works.

---

## Shared tasks

- [ ] Implement a provider registry + capability map so the miniplayer knows which controls to enable for each provider.
- [ ] Add `active_provider` storage (per session and persisted) plus `/api/music/providers` endpoint for status + capabilities.
- [ ] Update `static/js/fragments/miniplayer.js` to fetch providers, highlight the active one, and route actions through a generic `callProviderCommand`.
- [ ] Add tests for each provider module + API contract to ensure the miniplayer can switch providers without page reloads.