// Miniplayer fragment module - handles the miniplayer functionality on the dashboard

class MiniplayerFragment {
    constructor(rootElement) {
        this.rootElement = rootElement;
        this.currentTrack = null;
        this.isPlaying = false;
        this.progressInterval = null;
        this.currentTime = 0;
        this.duration = 0;
        this.progressSyncedAt = 0;
        this.syncedProgressSeconds = 0;
        this.isLiked = false;
        this.spotifyStatus = null;
        this.spotifyPolling = null;
        this.spotifyPlaybackPolling = null;
        this.spotifyAutoSyncEnabled = false;
        this.spotifySyncCooldownMs = 6 * 60 * 60 * 1000;
        this.spotifySyncStorageKey = 'miniplayer.spotify_sync.last_at';
        this.spotifyPlaylistsLoaded = false;
        this.spotifyPlaybackActive = false;
        this.spotifyWasConnected = false;
        this.spotifyMessageTimeout = null;
        this.spotifyPlaylistsEnabled = false;
        this.playlistsToggleBtn = null;
        this.playlistsSection = null;
        this.spotifyQueueEnabled = false;
        this.queueToggleBtn = null;
        this.queuePanel = null;
        this.queueListEl = null;
        this.queueEmptyEl = null;
        this.spotifyQueueItems = [];
        this.queueDragIndex = -1;
        this.outsideClickHandler = null;
        this.visualizerEl = null;
        this.visualizerBars = [];
        this.visualizerTrackLabel = null;
        this.visualizerAnimationFrame = null;
        this.visualizerCollapseTimeout = null;
        this.sourceButtons = [];
        this.sourcePanels = [];
        this.activeSidebarSource = 'spotify';
        this.deviceList = [];
        this.activeDeviceId = null;
        this.selectedSpotifyPlaylistId = '';
        this.providersMetadata = [];
        this.activeProviderId = null;
        this.userExpanded = false;
        this.escapeHandler = null;
        this.beforeSwapHandler = null;
        this.seekDebounceTimer = null;
        this.spotifyCountdownInterval = null;
        this.visibilityChangeHandler = null;

        this.init();
    }

    init() {
        this.removeLegacyVisualizer();
        this.configureSpotifySyncPolicy();

        // Set up event listeners for controls
        this.setupEventListeners();
        this.setupVisualizer();

        // Load initial state if there's a current track
        Promise.allSettled([
            this.loadCurrentTrack(),
            this.loadSpotifyStatus(),
            this.loadProviderMetadata(),
        ]).finally(() => {
            this.updateChromeState();
        });

        // Register cleanup function to be called before HTMX swaps this element
        if (window.htmx) {
            if (this.beforeSwapHandler) {
                document.removeEventListener('htmx:beforeSwap', this.beforeSwapHandler);
            }
            this.beforeSwapHandler = (event) => {
                const swapTarget = event.target || (event.detail && event.detail.target);
                if (swapTarget === this.rootElement || this.rootElement.contains(swapTarget)) {
                    this.destroy();
                }
            };
            document.addEventListener('htmx:beforeSwap', this.beforeSwapHandler);
        }

        // Listen for music events from the main music player or other sources
        this.setupSocketListeners();
    }

    removeLegacyVisualizer() {
        const legacyVisualizer = document.getElementById('now-playing-visualizer');
        if (legacyVisualizer) {
            legacyVisualizer.remove();
        }
    }

    setupEventListeners() {
        // Play/Pause button
        const playBtn = this.rootElement.querySelector('#miniplayer-play-btn');
        const pauseBtn = this.rootElement.querySelector('#miniplayer-pause-btn');

        if (playBtn) {
            playBtn.addEventListener('click', () => this.play());
        }

        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.pause());
        }

        // Next button
        const nextBtn = this.rootElement.querySelector('#miniplayer-next-btn');
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextTrack());
        }

        // Previous button
        const prevBtn = this.rootElement.querySelector('#miniplayer-prev-btn');
        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.prevTrack());
        }

        // Like button
        const likeBtn = this.rootElement.querySelector('#miniplayer-like-btn');
        if (likeBtn) {
            likeBtn.addEventListener('click', () => this.toggleLike());
        }

        // Progress bar
        const seekInput = this.rootElement.querySelector('#miniplayer-seek');
        if (seekInput) {
            seekInput.addEventListener('input', (e) => {
                const newTime = this.duration ? (e.target.value / 100) * this.duration : 0;
                this.currentTime = newTime;
                this.updateProgressDisplay();
                this.queueSeekCommit(newTime);
            });
            seekInput.addEventListener('change', (e) => {
                const newTime = this.duration ? (e.target.value / 100) * this.duration : 0;
                if (this.seekDebounceTimer) {
                    clearTimeout(this.seekDebounceTimer);
                    this.seekDebounceTimer = null;
                }
                this.seekTo(newTime);
            });
        }

        const expandBtn = this.rootElement.querySelector('#miniplayer-expand-btn');
        if (expandBtn) {
            expandBtn.addEventListener('click', () => {
                this.setUserExpanded(!this.userExpanded);
            });
        }

        const deviceSelect = this.rootElement.querySelector('#miniplayer-device-select');
        if (deviceSelect) {
            deviceSelect.addEventListener('change', (event) => {
                const deviceId = event.target.value;
                if (deviceId) {
                    this.transferSpotifyPlayback(deviceId);
                }
            });
        }

        const deviceRefreshBtn = this.rootElement.querySelector('#miniplayer-device-refresh');
        if (deviceRefreshBtn) {
            deviceRefreshBtn.addEventListener('click', () => {
                this.loadSpotifyDevices();
            });
        }

        this.setupSpotifyAuthControls();
        this.setupMiniplayerChrome();
        this.setupSourceSelector();

        if (this.escapeHandler) {
            document.removeEventListener('keydown', this.escapeHandler);
        }
        this.escapeHandler = (event) => {
            if (event.key === 'Escape') {
                this.setUserExpanded(false);
            }
        };
        document.addEventListener('keydown', this.escapeHandler);

        if (this.visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
        }
        this.visibilityChangeHandler = () => {
            if (!document.hidden && this.isSpotifyConnected()) {
                this.loadSpotifyPlayback();
            }
        };
        document.addEventListener('visibilitychange', this.visibilityChangeHandler);
    }

    setupSpotifyAuthControls() {
        const connectBtn = this.rootElement.querySelector('#spotify-connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.startSpotifyAuthorization());
        }

        const disconnectBtn = this.rootElement.querySelector('#spotify-disconnect-btn');
        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => this.disconnectSpotify());
        }

        const shuffleBtn = this.rootElement.querySelector('#spotify-shuffle-btn');
        if (shuffleBtn) {
            shuffleBtn.addEventListener('click', () => this.shuffleSelectedPlaylist());
        }
    }

    setupMiniplayerChrome() {
        this.playlistsSection = this.rootElement.querySelector('#spotify-playlists-section');
        this.queuePanel = this.rootElement.querySelector('#spotify-queue-panel');
        this.queueListEl = this.rootElement.querySelector('#spotify-queue-list');
        this.queueEmptyEl = this.rootElement.querySelector('#spotify-queue-empty');

        if (this.playlistsSection) {
            this.playlistsSection.classList.add('is-disabled');
        }
        if (this.queueToggleBtn) {
            this.queueToggleBtn.disabled = true;
            this.queueToggleBtn.classList.remove('active');
        }
        if (this.queuePanel) {
            this.queuePanel.classList.add('is-disabled');
            this.queuePanel.classList.remove('is-open');
        }

        if (this.outsideClickHandler) {
            document.removeEventListener('mousedown', this.outsideClickHandler);
            document.removeEventListener('touchstart', this.outsideClickHandler);
        }

        this.outsideClickHandler = (event) => {
            const queueOpen = this.queuePanel && this.queuePanel.classList.contains('is-open');
            if (!queueOpen) {
                return;
            }

            if (queueOpen) {
                const clickedInsideQueue = this.queuePanel.contains(event.target);
                const clickedQueueToggle = this.queueToggleBtn && this.queueToggleBtn.contains(event.target);
                if (!clickedInsideQueue && !clickedQueueToggle) {
                    this.queuePanel.classList.remove('is-open');
                    if (this.queueToggleBtn) {
                        this.queueToggleBtn.classList.remove('active');
                    }
                }
            }
        };

        document.addEventListener('mousedown', this.outsideClickHandler);
        document.addEventListener('touchstart', this.outsideClickHandler);

        const castBtn = this.rootElement.querySelector('#miniplayer-cast-btn');
        if (castBtn) {
            castBtn.addEventListener('click', () => {
                if (window.loadAndShowModal) {
                    loadAndShowModal('/partials/casting');
                } else {
                    console.warn('Casting modal helper is not available.');
                }
            });
        }

        const queueBtn = this.rootElement.querySelector('#miniplayer-queue-btn');
        if (queueBtn) {
            queueBtn.addEventListener('click', () => {
                if (queueBtn.disabled || !this.spotifyQueueEnabled) {
                    return;
                }
                if (!this.queuePanel) {
                    return;
                }
                const isOpen = this.queuePanel.classList.toggle('is-open');
                queueBtn.classList.toggle('active', isOpen);
                if (isOpen) {
                    this.loadSpotifyQueue();
                }
            });
        }

        if (this.queueToggleBtn) {
            this.queueToggleBtn.disabled = true;
            this.queueToggleBtn.classList.remove('active');
        }

        this.updateSourcePanels();
    }

    setupSourceSelector() {
        this.sourceButtons = Array.from(this.rootElement.querySelectorAll('.miniplayer-source-pill'));
        this.sourcePanels = Array.from(this.rootElement.querySelectorAll('[data-source-panel]'));

        if (!this.sourceButtons.length) {
            return;
        }

        const activeButton = this.sourceButtons.find((button) => button.classList.contains('is-active'));
        this.activeSidebarSource = activeButton ? activeButton.dataset.source || 'spotify' : 'spotify';

        this.sourceButtons.forEach((button) => {
            button.addEventListener('click', () => {
                this.activeSidebarSource = button.dataset.source || 'spotify';
                this.updateSourcePanels();
            });
        });

        this.updateSourcePanels();
    }

    updateSourcePanels() {
        if (this.sourceButtons.length) {
            this.sourceButtons.forEach((button) => {
                const isActive = (button.dataset.source || '') === this.activeSidebarSource;
                button.classList.toggle('is-active', isActive);
                button.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });
        }

        if (this.sourcePanels.length) {
            this.sourcePanels.forEach((panel) => {
                const isActive = panel.dataset.sourcePanel === this.activeSidebarSource;
                panel.hidden = !isActive;
            });
        }
    }

    setupVisualizer() {
        this.visualizerEl = document.getElementById('now-playing-visualizer');
        this.visualizerBars = this.visualizerEl ? Array.from(this.visualizerEl.querySelectorAll('.visualizer-bar')) : [];
        this.visualizerTrackLabel = document.getElementById('now-playing-visualizer-track');

        if (this.visualizerEl) {
            this.visualizerEl.dataset.active = 'false';
            this.visualizerEl.setAttribute('aria-hidden', 'true');
            this.visualizerEl.style.display = 'none';
        }
    }

    updateVisualizerTrackLabel(track) {
        if (!this.visualizerTrackLabel) {
            return;
        }

        const resolvedTrack = track || this.currentTrack;
        const title = resolvedTrack && resolvedTrack.title ? resolvedTrack.title : 'Waiting for playback';
        const artist = resolvedTrack && resolvedTrack.artist ? resolvedTrack.artist : '';

        this.visualizerTrackLabel.textContent = artist ? `${title} - ${artist}` : title;
    }

    startVisualizerAnimation() {
        if (!this.visualizerEl) {
            return;
        }

        this.clearVisualizerHideTimer();

        this.visualizerEl.style.display = 'flex';
        this.visualizerEl.dataset.active = 'true';
        this.visualizerEl.setAttribute('aria-hidden', 'false');

        if (this.visualizerAnimationFrame) {
            return;
        }

        const animate = () => {
            if (!this.visualizerEl || this.visualizerEl.dataset.active !== 'true') {
                this.visualizerAnimationFrame = null;
                return;
            }

            this.visualizerBars.forEach((bar, index) => {
                const base = 10 + ((index % 6) * 2);
                const variance = Math.random() * 70;
                const height = Math.min(100, base + variance);
                bar.style.height = `${height}%`;
            });

            this.visualizerAnimationFrame = requestAnimationFrame(animate);
        };

        this.visualizerAnimationFrame = requestAnimationFrame(animate);
    }

    stopVisualizerAnimation() {
        if (this.visualizerAnimationFrame) {
            cancelAnimationFrame(this.visualizerAnimationFrame);
            this.visualizerAnimationFrame = null;
        }

        this.visualizerBars.forEach((bar) => {
            bar.style.height = '10%';
        });
    }

    clearVisualizerHideTimer() {
        if (this.visualizerCollapseTimeout) {
            clearTimeout(this.visualizerCollapseTimeout);
            this.visualizerCollapseTimeout = null;
        }
    }

    hideVisualizer(immediate = false) {
        if (!this.visualizerEl) {
            return;
        }

        this.clearVisualizerHideTimer();
        this.visualizerEl.dataset.active = 'false';
        this.visualizerEl.setAttribute('aria-hidden', 'true');
        this.stopVisualizerAnimation();

        const collapse = () => {
            this.visualizerEl.style.display = 'none';
            this.visualizerCollapseTimeout = null;
        };

        if (immediate) {
            collapse();
            return;
        }

        // Short delay so CSS transitions finish before the element is removed.
        this.visualizerCollapseTimeout = setTimeout(collapse, 500);
    }

    updateVisualizerVisibility() {
        const hasTrack = Boolean(this.currentTrack);
        const spotifyExternallyStopped = this.isSpotifyConnected() && this.spotifyPlaybackActive === false && !this.isPlaying;

        if (this.isPlaying && hasTrack) {
            this.updateVisualizerTrackLabel();
            this.startVisualizerAnimation();
            return;
        }

        // Stop animation immediately when playback is not active.
        if (!hasTrack || spotifyExternallyStopped) {
            this.hideVisualizer(true);
            return;
        }

        // Paused: hide now and keep a timer so it remains collapsed if paused for 3+ minutes.
        this.hideVisualizer(false);
    }

    async loadSpotifyStatus(silent = false) {
        const authSection = this.rootElement.querySelector('#miniplayer-spotify-auth');
        if (!authSection) {
            return;
        }

        try {
            const cacheBust = Date.now();
            const response = await fetch(`/api/music/spotify/status?ts=${cacheBust}`, {
                cache: 'no-store',
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.spotifyStatus = data;
            this.updateSpotifyAuthUI(data);

            if (data.connected) {
                if (this.spotifyPolling) {
                    clearInterval(this.spotifyPolling);
                    this.spotifyPolling = null;
                }
                this.maybeSyncSpotifyLibrary();
            }
        } catch (error) {
            if (!silent) {
                console.warn('Unable to load Spotify status:', error);
            }
        }
    }

    configureSpotifySyncPolicy() {
        try {
            const appConfig = window.APP_CONFIG || {};
            const musicConfig = appConfig.music || {};
            const spotifyConfig = musicConfig.spotify || {};

            this.spotifyAutoSyncEnabled = Boolean(spotifyConfig.enable_library_sync);

            const configuredCooldownMinutes = Number(spotifyConfig.sync_cooldown_minutes);
            if (Number.isFinite(configuredCooldownMinutes) && configuredCooldownMinutes > 0) {
                this.spotifySyncCooldownMs = Math.floor(configuredCooldownMinutes * 60 * 1000);
            }
        } catch (error) {
            this.spotifyAutoSyncEnabled = false;
        }
    }

    getSpotifyLastSyncAt() {
        try {
            const raw = window.localStorage.getItem(this.spotifySyncStorageKey);
            if (!raw) {
                return 0;
            }
            const parsed = Number(raw);
            return Number.isFinite(parsed) ? parsed : 0;
        } catch (error) {
            return 0;
        }
    }

    setSpotifyLastSyncAt(timestamp) {
        try {
            window.localStorage.setItem(this.spotifySyncStorageKey, String(timestamp));
        } catch (error) {
            // Ignore storage write errors in private mode or restricted environments.
        }
    }

    maybeSyncSpotifyLibrary() {
        if (!this.spotifyAutoSyncEnabled) {
            return;
        }

        if (this.spotifyPlaybackPolling) {
            return;
        }

        const now = Date.now();
        const lastSyncAt = this.getSpotifyLastSyncAt();
        if (lastSyncAt && now - lastSyncAt < this.spotifySyncCooldownMs) {
            return;
        }

        this.syncSpotifyLibrary();
    }

    updateSpotifyAuthUI(status) {
        const authSection = this.rootElement.querySelector('#miniplayer-spotify-auth');
        const messageEl = this.rootElement.querySelector('#spotify-auth-message');
        const connectBtn = this.rootElement.querySelector('#spotify-connect-btn');
        const disconnectBtn = this.rootElement.querySelector('#spotify-disconnect-btn');
        if (!authSection || !messageEl || !connectBtn) {
            return;
        }

        if (!status || !status.enabled) {
            authSection.style.display = status && !status.enabled ? 'flex' : 'none';
            messageEl.textContent = status && status.message ? status.message : 'Spotify integration disabled.';
            connectBtn.style.display = 'none';
            if (disconnectBtn) {
                disconnectBtn.style.display = 'none';
            }
            this.showSpotifyPlaylists(false);
            this.showSpotifyQueue(false);
            this.stopSpotifyPlaybackPolling();
            this.updateDeviceInfo(null);
            authSection.classList.remove('is-connected');
            return;
        }

        authSection.style.display = 'flex';
        const configured = status.configured;

        connectBtn.disabled = false;
        connectBtn.title = configured ? 'Connect Spotify' : 'Update config to enable Spotify';
        if (!configured) {
            connectBtn.setAttribute('aria-disabled', 'true');
        } else {
            connectBtn.removeAttribute('aria-disabled');
        }

        if (configured && !status.connected) {
            connectBtn.style.display = 'inline-flex';
            if (disconnectBtn) {
                disconnectBtn.style.display = 'none';
            }
        } else if (status.connected) {
            connectBtn.style.display = 'none';
            if (disconnectBtn) {
                disconnectBtn.style.display = 'inline-flex';
            }
        } else {
            connectBtn.style.display = 'inline-flex';
            if (disconnectBtn) {
                disconnectBtn.style.display = 'none';
            }
        }

        if (disconnectBtn) {
            disconnectBtn.disabled = !status.connected;
        }
        authSection.classList.toggle('is-connected', Boolean(status.connected));

        if (!configured) {
            this.showSpotifyMessage(status.message || 'Add your Spotify client ID, client secret, and redirect URI.', { sticky: true });
        } else if (status.connected) {
            if (!this.spotifyWasConnected) {
                if (window.toast && typeof window.toast.success === 'function') {
                    window.toast.success('Spotify connected. Use controls or shuffle a playlist.');
                }
                this.showSpotifyMessage('', { immediate: true });
            } else {
                this.showSpotifyMessage('', { immediate: true });
            }
            this.spotifyWasConnected = true;
        } else {
            this.showSpotifyMessage(status.message || 'Connect Spotify to sync your library.', { sticky: true });
            this.spotifyWasConnected = false;
        }

        if (status.connected) {
            this.showSpotifyPlaylists(true);
            this.showSpotifyQueue(true);
            if (!this.spotifyPlaylistsLoaded) {
                this.fetchSpotifyPlaylists();
            }
            this.beginSpotifyPlaybackPolling();
            this.loadSpotifyPlayback();
            this.loadSpotifyDevices();
        } else {
            this.showSpotifyPlaylists(false);
            this.showSpotifyQueue(false);
            this.stopSpotifyPlaybackPolling();
            this.spotifyPlaylistsLoaded = false;
            this.spotifyPlaybackActive = false;
            this.updateDeviceInfo(null);
        }
    }

    showSpotifyPlaylists(show) {
        this.spotifyPlaylistsEnabled = Boolean(show);

        if (this.playlistsSection) {
            if (!this.spotifyPlaylistsEnabled) {
                this.playlistsSection.classList.add('is-disabled');
            } else {
                this.playlistsSection.classList.remove('is-disabled');
            }
        }

        this.updateSourcePanels();
    }

    showSpotifyQueue(show) {
        this.spotifyQueueEnabled = Boolean(show);

        if (this.queueToggleBtn) {
            this.queueToggleBtn.disabled = !this.spotifyQueueEnabled;
            if (!this.spotifyQueueEnabled) {
                this.queueToggleBtn.classList.remove('active');
            }
        }

        if (this.queuePanel) {
            if (!this.spotifyQueueEnabled) {
                this.queuePanel.classList.remove('is-open');
                this.queuePanel.classList.add('is-disabled');
                this.populateSpotifyQueue([]);
            } else {
                this.queuePanel.classList.remove('is-disabled');
            }
        }
    }

    async fetchSpotifyPlaylists(limit = 10) {
        if (!this.isSpotifyConnected()) {
            return;
        }

        try {
            const params = new URLSearchParams({
                limit: String(limit),
                order: 'recent',
            });
            const response = await fetch(`/api/music/spotify/playlists?${params.toString()}`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load Spotify playlists.');
            }
            this.populateSpotifyPlaylists(data.items || []);
            this.spotifyPlaylistsLoaded = true;
        } catch (error) {
            console.warn('Unable to fetch Spotify playlists:', error);
            this.handleSpotifyError(error.message, { suppressWhilePlaying: true });
        }
    }

    populateSpotifyPlaylists(items) {
        const list = this.rootElement.querySelector('#spotify-playlist-list');
        const emptyState = this.rootElement.querySelector('#spotify-playlist-empty');
        if (!list) {
            return;
        }

        list.innerHTML = '';
        const validItems = (items || []).filter((playlist) => playlist && playlist.id);

        if (!validItems.length) {
            this.selectedSpotifyPlaylistId = '';
            if (emptyState) {
                emptyState.hidden = false;
            }
            return;
        }

        if (emptyState) {
            emptyState.hidden = true;
        }

        if (!validItems.some((playlist) => playlist.id === this.selectedSpotifyPlaylistId)) {
            this.selectedSpotifyPlaylistId = validItems[0].id;
        }

        validItems.forEach((playlist) => {
            const row = document.createElement('button');
            row.type = 'button';
            row.className = 'spotify-playlist-item';
            row.setAttribute('role', 'listitem');
            row.dataset.playlistId = playlist.id;
            row.dataset.playlistName = playlist.name || 'Playlist';
            row.setAttribute('aria-pressed', playlist.id === this.selectedSpotifyPlaylistId ? 'true' : 'false');

            if (playlist.id === this.selectedSpotifyPlaylistId) {
                row.classList.add('is-active');
            }

            const title = document.createElement('span');
            title.className = 'spotify-playlist-item-title';
            title.textContent = playlist.name || 'Playlist';

            const meta = document.createElement('span');
            meta.className = 'spotify-playlist-item-meta';
            const hasTrackCount = playlist.track_count !== undefined && playlist.track_count !== null;
            const metaParts = [];
            if (hasTrackCount) {
                metaParts.push(`${playlist.track_count} songs`);
            }
            if (playlist.owner) {
                metaParts.push(playlist.owner);
            }
            if (playlist.last_played_at) {
                const playedDate = new Date(playlist.last_played_at);
                if (!Number.isNaN(playedDate.getTime())) {
                    metaParts.push(`Last played ${playedDate.toLocaleDateString()}`);
                    row.title = `Last played ${playedDate.toLocaleString()}`;
                }
            }
            meta.textContent = metaParts.join(' • ') || 'Spotify playlist';

            row.addEventListener('click', async () => {
                this.selectedSpotifyPlaylistId = playlist.id;
                this.populateSpotifyPlaylists(validItems);

                try {
                    await this.callSpotifyCommand(`/api/music/providers/spotify/playlists/${playlist.id}/play`, { shuffle: false });
                    this.showSpotifyMessage(`Queued ${playlist.name || 'playlist'} on Spotify.`, { duration: 5000 });
                    this.beginSpotifyPlaybackPolling();
                    this.loadSpotifyPlayback();
                } catch (error) {
                    console.error('Failed to start playlist:', error);
                    this.handleSpotifyError(error.message || 'Unable to start playlist.');
                }
            });

            row.appendChild(title);
            row.appendChild(meta);

            if (playlist.image_url) {
                const art = document.createElement('img');
                art.className = 'spotify-playlist-item-art';
                art.src = playlist.image_url;
                art.alt = '';
                art.loading = 'lazy';
                row.prepend(art);
            }

            list.appendChild(row);
        });
    }

    async shuffleSelectedPlaylist() {
        if (!this.isSpotifyConnected()) {
            this.showSpotifyMessage('Connect Spotify first.', { duration: 5000 });
            return;
        }

        if (!this.selectedSpotifyPlaylistId) {
            this.showSpotifyMessage('Select a playlist to shuffle.', { duration: 5000 });
            return;
        }

        try {
            await this.callSpotifyCommand(`/api/music/spotify/playlists/${this.selectedSpotifyPlaylistId}/shuffle`, { shuffle: true });
            this.showSpotifyMessage('Playlist queued on Spotify.', { duration: 5000 });
            this.beginSpotifyPlaybackPolling();
            this.loadSpotifyPlayback();
        } catch (error) {
            console.error('Failed to shuffle playlist:', error);
            this.handleSpotifyError(error.message || 'Unable to shuffle playlist.');
        }
    }

    isSpotifyConnected() {
        return Boolean(this.spotifyStatus && this.spotifyStatus.connected);
    }

    async loadProviderMetadata() {
        try {
            const response = await fetch('/api/music/providers', {
                cache: 'no-store',
            });
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            this.providersMetadata = Array.isArray(data.providers) ? data.providers : [];
            this.activeProviderId = typeof data.active_provider === 'string' ? data.active_provider : null;
            const activeProvider = this.providersMetadata.find((provider) => provider.id === this.activeProviderId) || null;
            this.updateServiceTray(activeProvider);
        } catch (error) {
            console.warn('Unable to load music provider metadata:', error);
        }
    }

    updateServiceTray(activeProvider) {
        const tray = this.rootElement.querySelector('#miniplayer-service-tray');
        if (!tray) {
            return;
        }

        let activeIcon = tray.querySelector('.service-icon');
        if (!activeIcon) {
            activeIcon = document.createElement('button');
            activeIcon.className = 'service-icon is-active';
            activeIcon.type = 'button';
            tray.appendChild(activeIcon);
        }

        const providerId = (activeProvider && activeProvider.id) || 'spotify';
        const providerLabel = (activeProvider && activeProvider.label) || 'Spotify';
        const abbreviation = providerLabel
            .split(/\s+/)
            .map((part) => part[0] || '')
            .join('')
            .slice(0, 2)
            .toUpperCase() || 'SP';

        activeIcon.dataset.service = providerId;
        activeIcon.title = providerLabel;
        activeIcon.textContent = abbreviation;
    }

    beginSpotifyPlaybackPolling() {
        if (this.spotifyPlaybackPolling) {
            return;
        }

        this.spotifyPlaybackPolling = setInterval(() => {
            if (document.hidden) {
                return;
            }
            if (this.isSpotifyConnected()) {
                this.loadSpotifyPlayback();
            }
        }, 10000);
    }

    stopSpotifyPlaybackPolling() {
        if (this.spotifyPlaybackPolling) {
            clearInterval(this.spotifyPlaybackPolling);
            this.spotifyPlaybackPolling = null;
        }
    }

    async loadSpotifyPlayback() {
        if (!this.isSpotifyConnected()) {
            return;
        }

        try {
            const response = await fetch('/api/music/spotify/playback');
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to fetch playback.');
            }

            if (data && data.device) {
                this.updateDeviceInfo(data.device);
            }

            if (data && data.track) {
                const track = {
                    ...data.track,
                    id: data.track.spotify_id || data.track.uri || data.track.title,
                    source: 'spotify'
                };

                const trackChanged = !this.isSameTrack(track);
                if (trackChanged) {
                    this.updateTrack(track);
                } else {
                    this.currentTrack = {
                        ...this.currentTrack,
                        ...track,
                    };
                    this.duration = track.duration || this.duration;
                }
                this.isPlaying = !!data.is_playing;
                this.spotifyPlaybackActive = true;
                this.syncedProgressSeconds = Math.floor((data.progress_ms || 0) / 1000);
                this.currentTime = this.syncedProgressSeconds;
                this.progressSyncedAt = Date.now();
                this.duration = track.duration || this.duration;
                this.updatePlayState();
                this.updateProgressDisplay();
                this.showSpotifyMessage('', { immediate: true });
                if (this.isPlaying) {
                    this.startProgressSimulation();
                } else {
                    this.stopProgressSimulation();
                }
            } else {
                this.spotifyPlaybackActive = false;
                this.stopProgressSimulation();
                this.updateVisualizerVisibility();
                this.updateChromeState();
            }
        } catch (error) {
            console.warn('Unable to load Spotify playback info:', error);
            this.handleSpotifyError(error.message, { suppressWhilePlaying: true });
        }
    }

    async loadSpotifyQueue() {
        if (!this.isSpotifyConnected()) {
            this.populateSpotifyQueue([]);
            return;
        }

        try {
            const cacheBust = Date.now();
            const response = await fetch(`/api/music/spotify/queue?ts=${cacheBust}`, {
                cache: 'no-store',
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load Spotify queue.');
            }
            this.populateSpotifyQueue(data.queue || []);
        } catch (error) {
            console.warn('Unable to load Spotify queue:', error);
            this.handleSpotifyError(error.message, { suppressWhilePlaying: true });
        }
    }

    populateSpotifyQueue(items) {
        if (!this.queueListEl || !this.queueEmptyEl) {
            return;
        }

        this.queueListEl.innerHTML = '';
        const tracks = Array.isArray(items) ? items.filter(Boolean).slice(0, 10) : [];
        this.spotifyQueueItems = tracks;

        if (!tracks.length) {
            this.queueEmptyEl.style.display = 'block';
            return;
        }

        this.queueEmptyEl.style.display = 'none';
        tracks.forEach((track, index) => {
            const li = document.createElement('li');
            li.className = 'queue-item';
            li.draggable = true;
            li.dataset.index = String(index);

            const title = document.createElement('div');
            title.className = 'queue-track-title';
            title.textContent = track.title || 'Unknown Track';

            const artist = document.createElement('div');
            artist.className = 'queue-track-artist';
            artist.textContent = track.artist || 'Unknown Artist';

            li.addEventListener('click', (event) => {
                event.preventDefault();
                event.stopPropagation();
                this.playSpotifyQueueItem(track);
            });

            li.addEventListener('dragstart', (event) => {
                this.queueDragIndex = index;
                li.classList.add('is-dragging');
                if (event.dataTransfer) {
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', String(index));
                }
            });

            li.addEventListener('dragend', () => {
                li.classList.remove('is-dragging');
                this.queueDragIndex = -1;
            });

            li.addEventListener('dragover', (event) => {
                event.preventDefault();
                if (event.dataTransfer) {
                    event.dataTransfer.dropEffect = 'move';
                }
            });

            li.addEventListener('drop', (event) => {
                event.preventDefault();
                const fromIndexRaw = event.dataTransfer ? event.dataTransfer.getData('text/plain') : '';
                const fromIndex = Number.parseInt(fromIndexRaw, 10);
                const toIndex = index;
                if (Number.isInteger(fromIndex)) {
                    this.reorderSpotifyQueueLocally(fromIndex, toIndex);
                }
            });

            li.appendChild(title);
            li.appendChild(artist);
            this.queueListEl.appendChild(li);
        });
    }

    async playSpotifyQueueItem(track) {
        const uri = track && track.uri ? String(track.uri) : '';
        if (!uri) {
            this.showSpotifyMessage('Track cannot be played from queue.', { duration: 4000 });
            return;
        }

        try {
            await this.callSpotifyCommand('/api/music/spotify/queue/play', { uri });
            this.showSpotifyMessage('Playing selected track.', { duration: 3500 });
            this.beginSpotifyPlaybackPolling();
            this.loadSpotifyPlayback();
            this.loadSpotifyQueue();
        } catch (error) {
            console.warn('Unable to play selected queue item:', error);
            this.handleSpotifyError(error.message || 'Unable to play queue item.');
        }
    }

    async reorderSpotifyQueueLocally(fromIndex, toIndex) {
        if (!Array.isArray(this.spotifyQueueItems) || this.spotifyQueueItems.length < 2) {
            return;
        }
        if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0) {
            return;
        }
        if (fromIndex >= this.spotifyQueueItems.length || toIndex >= this.spotifyQueueItems.length) {
            return;
        }

        const reordered = [...this.spotifyQueueItems];
        const [moved] = reordered.splice(fromIndex, 1);
        reordered.splice(toIndex, 0, moved);

        this.populateSpotifyQueue(reordered);

        const uris = reordered
            .map((item) => (item && item.uri ? String(item.uri).trim() : ''))
            .filter(Boolean);

        if (!uris.length) {
            this.showSpotifyMessage('Queue items are missing Spotify URIs.', { duration: 5000 });
            return;
        }

        try {
            const result = await this.callSpotifyCommand('/api/music/spotify/queue/reorder', { uris });
            const count = typeof result.enqueued_count === 'number' ? result.enqueued_count : uris.length;
            this.showSpotifyMessage(
                `Queue order updated (${count} items appended on Spotify).`,
                { duration: 5000 }
            );
        } catch (error) {
            console.warn('Unable to reorder Spotify queue:', error);
            this.handleSpotifyError(error.message || 'Unable to reorder Spotify queue.');
        }
    }

    async callSpotifyCommand(endpoint, payload) {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: payload ? JSON.stringify(payload) : undefined
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.error || 'Spotify command failed.');
        }
        return data;
    }

    showSpotifyMessage(message, options = {}) {
        const { sticky = false, duration = 6000, immediate = false } = options;
        const messageEl = this.rootElement.querySelector('#spotify-auth-message');
        if (!messageEl) {
            return;
        }

        if (this.spotifyMessageTimeout) {
            clearTimeout(this.spotifyMessageTimeout);
            this.spotifyMessageTimeout = null;
        }
        if (this.spotifyCountdownInterval) {
            clearInterval(this.spotifyCountdownInterval);
            this.spotifyCountdownInterval = null;
        }

        if (!message) {
            messageEl.textContent = '';
            messageEl.classList.remove('visible');
            return;
        }

        messageEl.textContent = message;
        messageEl.classList.add('visible');

        const retryMatch = message.match(/^(.*?Try again in )(\d+)s\.?$/i);
        if (retryMatch) {
            const prefix = retryMatch[1];
            let remaining = Math.max(0, parseInt(retryMatch[2], 10) || 0);
            messageEl.textContent = `${prefix}${remaining}s.`;
            this.spotifyCountdownInterval = setInterval(() => {
                remaining -= 1;
                if (remaining <= 0) {
                    if (this.spotifyCountdownInterval) {
                        clearInterval(this.spotifyCountdownInterval);
                        this.spotifyCountdownInterval = null;
                    }
                    messageEl.textContent = `${prefix}0s.`;
                    return;
                }
                messageEl.textContent = `${prefix}${remaining}s.`;
            }, 1000);
        }

        if (!sticky) {
            this.spotifyMessageTimeout = setTimeout(() => {
                messageEl.textContent = '';
                messageEl.classList.remove('visible');
            }, duration);
        }
    }

    handleSpotifyError(message, options = {}) {
        if (!message) {
            return;
        }

        const { suppressWhilePlaying = false } = options;
        const isTransientAvailabilityError = /temporarily unavailable|rate limit|try again in \d+s/i.test(message);
        if (suppressWhilePlaying && (this.spotifyPlaybackActive || this.currentTrack || this.isPlaying)) {
            return;
        }
        if (isTransientAvailabilityError && this.isSpotifyConnected() && (this.spotifyPlaybackActive || this.currentTrack || this.isPlaying)) {
            return;
        }

        let finalMessage = message;
        if (/permission|scope/i.test(finalMessage)) {
            finalMessage += ' Ensure your Spotify app has user-read-playback-state and user-modify-playback-state scopes, then reconnect.';
        }
        const hasRetryWindow = /Try again in \d+s/i.test(finalMessage);
        this.showSpotifyMessage(finalMessage, hasRetryWindow ? { sticky: true } : {});
    }

    async startSpotifyAuthorization() {
        if (this.spotifyStatus && !this.spotifyStatus.configured) {
            this.showSpotifyMessage('Spotify credentials are missing or incomplete. Update .env or config.yaml with client ID, secret, and redirect URI.', { duration: 6000 });
            return;
        }

        try {
            this.showSpotifyMessage('Opening Spotify authorization…', { sticky: true });
            const response = await fetch('/api/music/spotify/authorize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to initiate Spotify authorization.');
            }

            const width = 520;
            const height = 720;
            const left = window.screenX + Math.max(0, (window.outerWidth - width) / 2);
            const top = window.screenY + Math.max(0, (window.outerHeight - height) / 2);
            const popup = window.open(
                data.authorization_url,
                'spotify-oauth',
                `width=${width},height=${height},left=${left},top=${top}`
            );
            if (!popup) {
                window.location.href = data.authorization_url;
            }

            this.beginSpotifyStatusPolling();
        } catch (error) {
            console.error('Failed to start Spotify authorization:', error);
            this.handleSpotifyError(error.message || 'Unable to start Spotify authorization.');
        }
    }

    beginSpotifyStatusPolling() {
        if (this.spotifyPolling) {
            clearInterval(this.spotifyPolling);
        }

        const maxAttempts = 24; // Poll for up to 2 minutes
        let attempts = 0;
        this.spotifyPolling = setInterval(() => {
            attempts += 1;
            this.loadSpotifyStatus(true);

            if (attempts >= maxAttempts) {
                clearInterval(this.spotifyPolling);
                this.spotifyPolling = null;
                this.showSpotifyMessage('Spotify authorization timed out. Try again.');
            }
        }, 5000);
    }

    async disconnectSpotify() {
        try {
            const response = await fetch('/api/music/spotify/logout', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Failed to disconnect Spotify.');
            }

            await this.loadSpotifyStatus();
            this.stopSpotifyPlaybackPolling();
            this.showSpotifyPlaylists(false);
            this.showSpotifyQueue(false);
            this.spotifyPlaylistsLoaded = false;
            this.spotifyPlaybackActive = false;
        } catch (error) {
            console.error('Error disconnecting Spotify:', error);
            this.handleSpotifyError('Unable to disconnect Spotify. Check logs for details.');
        }
    }

    async syncSpotifyLibrary() {
        if (!this.spotifyAutoSyncEnabled) {
            return;
        }

        if (this.spotifyPlaybackPolling) {
            return;
        }

        const now = Date.now();
        const lastSyncAt = this.getSpotifyLastSyncAt();
        if (lastSyncAt && now - lastSyncAt < this.spotifySyncCooldownMs) {
            return;
        }

        this.setSpotifyLastSyncAt(now);

        try {
            const response = await fetch('/api/music/sync', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                console.warn('Spotify sync request failed:', await response.text());
            }
        } catch (error) {
            console.warn('Unable to trigger Spotify sync:', error);
        }
    }

    setupSocketListeners() {
        // If socket.io is available, listen for music updates
        if (window.socket) {
            // Listen for track change events
            window.socket.on('track_changed', (data) => {
                this.updateTrack(data.track);
            });

            // Listen for play state updates
            window.socket.on('play_state_changed', (data) => {
                if (data.is_playing) {
                    this.play();
                } else {
                    this.pause();
                }
            });

            // Listen for progress updates
            window.socket.on('progress_updated', (data) => {
                this.updateProgress(data.current_time, data.duration);
            });
        }
    }

    async loadCurrentTrack() {
        try {
            const response = await fetch('/api/music/current');
            if (response.ok) {
                const data = await response.json();
                if (data.track) {
                    this.updateTrack(data.track);
                    this.isPlaying = data.is_playing || false;
                    this.updatePlayState();
                } else {
                    this.updateChromeState();
                }
            }
        } catch (error) {
            console.error('Error loading current track:', error);
        }
    }

    async loadSpotifyDevices() {
        if (!this.isSpotifyConnected()) {
            return;
        }

        try {
            const response = await fetch('/api/music/spotify/devices');
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to load devices.');
            }
            const devices = Array.isArray(data.devices) ? data.devices : [];
            this.deviceList = devices;
            const activeId = data.active_device_id || null;
            this.populateDeviceSelect(devices, activeId);
            if (activeId) {
                const activeDevice = devices.find((device) => device.id === activeId);
                if (activeDevice) {
                    this.updateDeviceInfo(activeDevice);
                }
            }
        } catch (error) {
            console.warn('Unable to load Spotify devices:', error);
            this.handleSpotifyError(error.message, { suppressWhilePlaying: true });
        }
    }

    populateDeviceSelect(devices, activeId) {
        const select = this.rootElement.querySelector('#miniplayer-device-select');
        if (!select) {
            return;
        }
        select.innerHTML = '';

        if (!devices.length) {
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = 'No devices found';
            select.appendChild(emptyOption);
            select.disabled = true;
            return;
        }

        const placeholder = document.createElement('option');
        placeholder.value = '';
        placeholder.textContent = 'Select device';
        select.appendChild(placeholder);

        devices.forEach((device) => {
            if (!device || !device.id) {
                return;
            }
            const option = document.createElement('option');
            option.value = device.id;
            option.textContent = device.name || device.type || 'Spotify device';
            if (device.id === activeId || device.is_active) {
                option.selected = true;
            }
            select.appendChild(option);
        });

        select.disabled = false;
    }

    async transferSpotifyPlayback(deviceId) {
        if (!deviceId || !this.isSpotifyConnected()) {
            return;
        }

        try {
            await this.callSpotifyCommand('/api/music/spotify/transfer', {
                device_id: deviceId
            });
            await this.loadSpotifyPlayback();
            await this.loadSpotifyDevices();
            this.setUserExpanded(true);
        } catch (error) {
            console.warn('Unable to transfer playback:', error);
            this.handleSpotifyError(error.message || 'Unable to switch devices.');
        }
    }

    async play() {
        if (this.isSpotifyConnected()) {
            try {
                await this.callSpotifyCommand('/api/music/spotify/play');
                this.isPlaying = true;
                this.updatePlayState();
                this.startProgressSimulation();
                this.loadSpotifyPlayback();
                this.notifyMusicPlayer('play', this.currentTrack);
            } catch (error) {
                console.error('Spotify play failed:', error);
                this.handleSpotifyError(error.message || 'Unable to control Spotify playback.');
            }
            return;
        }

        try {
            const response = await fetch('/api/music/play', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.isPlaying = true;
                this.updatePlayState();

                // Start progress simulation if we have duration
                if (this.currentTrack && this.currentTrack.duration) {
                    this.startProgressSimulation();
                }

                // Update main music player to reflect the change
                this.notifyMusicPlayer('play', data.track || this.currentTrack);
            }
        } catch (error) {
            console.error('Error playing track:', error);
        }
    }

    async pause() {
        if (this.isSpotifyConnected()) {
            try {
                await this.callSpotifyCommand('/api/music/spotify/pause');
                this.isPlaying = false;
                this.updatePlayState();
                this.stopProgressSimulation();
                this.loadSpotifyPlayback();
                this.notifyMusicPlayer('pause');
            } catch (error) {
                console.error('Spotify pause failed:', error);
                this.handleSpotifyError(error.message || 'Unable to pause Spotify.');
            }
            return;
        }

        try {
            const response = await fetch('/api/music/pause', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.isPlaying = false;
                this.updatePlayState();
                this.stopProgressSimulation();

                // Update main music player to reflect the change
                this.notifyMusicPlayer('pause');
            }
        } catch (error) {
            console.error('Error pausing track:', error);
        }
    }

    async nextTrack() {
        if (this.isSpotifyConnected()) {
            try {
                await this.callSpotifyCommand('/api/music/spotify/next');
                await this.loadSpotifyPlayback();
                this.notifyMusicPlayer('next', this.currentTrack);
            } catch (error) {
                console.error('Spotify next track failed:', error);
            }
            return;
        }

        try {
            const response = await fetch('/api/music/next', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.track) {
                    this.updateTrack(data.track);
                    this.isPlaying = true;
                    this.updatePlayState();

                    // Start progress simulation if we have duration
                    if (this.currentTrack && this.currentTrack.duration) {
                        this.startProgressSimulation();
                    }

                    // Update main music player to reflect the change
                    this.notifyMusicPlayer('next', data.track);
                }
            }
        } catch (error) {
            console.error('Error going to next track:', error);
        }
    }

    async prevTrack() {
        if (this.isSpotifyConnected()) {
            try {
                await this.callSpotifyCommand('/api/music/spotify/previous');
                await this.loadSpotifyPlayback();
                this.notifyMusicPlayer('prev', this.currentTrack);
            } catch (error) {
                console.error('Spotify previous track failed:', error);
            }
            return;
        }

        try {
            const response = await fetch('/api/music/previous', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.track) {
                    this.updateTrack(data.track);
                    this.isPlaying = true;
                    this.updatePlayState();

                    // Start progress simulation if we have duration
                    if (this.currentTrack && this.currentTrack.duration) {
                        this.startProgressSimulation();
                    }

                    // Update main music player to reflect the change
                    this.notifyMusicPlayer('prev', data.track);
                }
            }
        } catch (error) {
            console.error('Error going to previous track:', error);
        }
    }

    // Method to notify the main music player of changes
    notifyMusicPlayer(action, track = null) {
        // Find the main music player and update it
        const musicPlayerElement = document.querySelector('.music-player-container');
        if (musicPlayerElement && musicPlayerElement.__musicPlayerFragment) {
            switch (action) {
                case 'play':
                    musicPlayerElement.__musicPlayerFragment.play();
                    break;
                case 'pause':
                    musicPlayerElement.__musicPlayerFragment.pause();
                    break;
                case 'next':
                    // Update the track in the main player
                    const trackId = track ? this.findTrackIdByTitleAndArtist(track.title, track.artist) : null;
                    if (trackId) {
                        musicPlayerElement.__musicPlayerFragment.playTrack(trackId);
                    }
                    break;
                case 'prev':
                    // Update the track in the main player
                    const prevTrackId = track ? this.findTrackIdByTitleAndArtist(track.title, track.artist) : null;
                    if (prevTrackId) {
                        musicPlayerElement.__musicPlayerFragment.playTrack(prevTrackId);
                    }
                    break;
            }
        }
    }

    findTrackIdByTitleAndArtist(title, artist) {
        // Look for a track in the music player fragment's track list
        const musicPlayerElement = document.querySelector('.music-player-container');
        if (musicPlayerElement && musicPlayerElement.__musicPlayerFragment) {
            const track = musicPlayerElement.__musicPlayerFragment.tracks.find(
                t => t.title === title && t.artist === artist
            );
            return track ? track.id : null;
        }
        return null;
    }

    async toggleLike() {
        if (!this.currentTrack) return;

        try {
            const response = await fetch(`/api/music/tracks/${this.currentTrack.id}/like`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    like: !this.isLiked
                })
            });

            if (response.ok) {
                this.isLiked = !this.isLiked;
                this.updateLikeButton();
            }
        } catch (error) {
            console.error('Error toggling like:', error);
        }
    }

    async seekTo(time) {
        if (!this.currentTrack && !this.isSpotifyConnected()) return;

        if (this.isSpotifyConnected()) {
            try {
                await this.callSpotifyCommand('/api/music/spotify/seek', {
                    position_ms: Math.max(0, Math.floor(time * 1000))
                });
                this.currentTime = time;
                this.syncedProgressSeconds = time;
                this.progressSyncedAt = Date.now();
                this.updateProgressDisplay();
            } catch (error) {
                console.error('Spotify seek failed:', error);
            }
            return;
        }

        try {
            const response = await fetch('/api/music/seek', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    time: time
                })
            });

            if (response.ok) {
                this.currentTime = time;
                this.syncedProgressSeconds = time;
                this.progressSyncedAt = Date.now();
                this.updateProgressDisplay();
            }
        } catch (error) {
            console.error('Error seeking:', error);
        }
    }

    updateTrack(track) {
        const trackChanged = !this.isSameTrack(track);
        this.currentTrack = track;

        // Update track info
        const titleEl = this.rootElement.querySelector('#miniplayer-track-title');
        const artistEl = this.rootElement.querySelector('#miniplayer-track-artist');
        const albumImage = this.rootElement.querySelector('#miniplayer-album-art');
        const defaultArtEl = this.rootElement.querySelector('#miniplayer-default-art');

        if (titleEl) {
            titleEl.textContent = track.title || 'Unknown Track';
        }

        if (artistEl) {
            artistEl.textContent = track.artist || 'Unknown Artist';
        }

        if (albumImage) {
            if (track.album_art_url) {
                albumImage.src = track.album_art_url;
                albumImage.style.display = 'block';
                if (defaultArtEl) {
                    defaultArtEl.style.display = 'none';
                }
            } else {
                albumImage.style.display = 'none';
                if (defaultArtEl) {
                    defaultArtEl.style.display = 'flex';
                }
            }
        }

        // Update duration
        this.duration = track.duration || 0;

        // Reset progress on track changes only.
        if (trackChanged) {
            this.currentTime = 0;
            this.syncedProgressSeconds = 0;
        }
        this.progressSyncedAt = Date.now();
        this.updateProgressDisplay();

        this.updateVisualizerTrackLabel(track);
        this.updateVisualizerVisibility();
        this.updateChromeState();

        // Show the miniplayer if it was hidden
        this.showMiniplayer();
    }

    updatePlayState() {
        const playBtn = this.rootElement.querySelector('#miniplayer-play-btn');
        const pauseBtn = this.rootElement.querySelector('#miniplayer-pause-btn');

        if (!playBtn || !pauseBtn) return;

        if (this.isPlaying) {
            playBtn.style.display = 'none';
            pauseBtn.style.display = 'block';
        } else {
            playBtn.style.display = 'block';
            pauseBtn.style.display = 'none';
        }

        this.updateVisualizerVisibility();
        this.updateChromeState();
    }

    setUserExpanded(expanded) {
        this.userExpanded = Boolean(expanded);
        this.updateChromeState();
    }

    updateChromeState() {
        const miniplayerEl = this.rootElement;
        if (!miniplayerEl) {
            return;
        }

        const trackTitleEl = this.rootElement.querySelector('#miniplayer-track-title');
        const trackTitle = trackTitleEl ? trackTitleEl.textContent.trim() : '';
        const isPlaceholder = !this.currentTrack || trackTitle === 'No track playing' || trackTitle === '';

        const isActivePlayback = Boolean(this.isPlaying);
        const isIdle = !isActivePlayback && isPlaceholder && !this.userExpanded;

        miniplayerEl.classList.toggle('is-idle', isIdle);
        miniplayerEl.classList.toggle('no-track', isPlaceholder);

        // Keep the sidebar shell compact by default; user expansion is the only
        // signal that opens the richer controls panel.
        const shouldExpand = this.userExpanded;
        miniplayerEl.setAttribute('data-state', shouldExpand ? 'expanded' : 'collapsed');

        const expandBtn = this.rootElement.querySelector('#miniplayer-expand-btn');
        if (expandBtn) {
            expandBtn.textContent = shouldExpand ? '_' : '+';
            expandBtn.setAttribute('aria-label', shouldExpand ? 'Collapse player' : 'Expand player');
            expandBtn.setAttribute('title', shouldExpand ? 'Minimize player' : 'Expand player');
            expandBtn.setAttribute('aria-expanded', shouldExpand ? 'true' : 'false');
        }

        const statusEl = this.rootElement.querySelector('#miniplayer-playback-status');
        if (statusEl) {
            statusEl.textContent = this.isPlaying ? 'Playing' : 'Not playing';
        }

        this.updateSourcePanels();
    }

    updateDeviceInfo(device) {
        const nameEl = this.rootElement.querySelector('#miniplayer-device-name');
        if (device && device.id) {
            this.activeDeviceId = device.id;
        }
        if (!nameEl) {
            return;
        }
        if (device && device.name) {
            nameEl.textContent = device.name;
        } else {
            nameEl.textContent = 'No device';
        }
    }

    updateLikeButton() {
        const likeBtn = this.rootElement.querySelector('#miniplayer-like-btn');
        if (!likeBtn) return;

        likeBtn.innerHTML = this.isLiked
            ? '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>'
            : '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3zm-4.4 15.55-.1.1-.1-.1C7.14 14.24 4 11.39 4 8.5 4 6.5 5.5 5 7.5 5c1.54 0 3.04.99 3.57 2.36h1.87C13.46 5.99 14.96 5 16.5 5c2 0 3.5 1.5 3.5 3.5 0 2.89-3.14 5.74-7.9 10.05z"/></svg>';
        likeBtn.setAttribute('title', this.isLiked ? 'Unlike Track' : 'Like Track');
    }

    updateProgressDisplay() {
        const seekInput = this.rootElement.querySelector('#miniplayer-seek');
        const currentTimeEl = this.rootElement.querySelector('#miniplayer-current-time');
        const durationEl = this.rootElement.querySelector('#miniplayer-duration');

        const progressPercent = this.duration > 0 ? (this.currentTime / this.duration) * 100 : 0;
        const clampedPercent = Math.max(0, Math.min(100, progressPercent || 0));

        if (seekInput) {
            seekInput.value = clampedPercent;
            seekInput.style.setProperty('--seek-progress', `${clampedPercent}%`);
        }

        if (currentTimeEl) {
            currentTimeEl.textContent = this.formatTime(this.currentTime);
        }

        if (durationEl) {
            durationEl.textContent = this.formatTime(this.duration);
        }
    }

    formatTime(seconds) {
        if (!Number.isFinite(seconds) || seconds < 0) {
            return '0:00';
        }
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    }

    updateProgress(currentTime, duration) {
        this.currentTime = currentTime;
        this.syncedProgressSeconds = currentTime;
        this.progressSyncedAt = Date.now();
        this.duration = duration || this.duration;
        this.updateProgressDisplay();
    }

    startProgressSimulation() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(() => {
            if (this.isPlaying) {
                if (this.isSpotifyConnected()) {
                    const elapsedSeconds = Math.max(0, Math.floor((Date.now() - this.progressSyncedAt) / 1000));
                    const projectedTime = this.syncedProgressSeconds + elapsedSeconds;
                    this.currentTime = Math.min(this.duration || projectedTime, projectedTime);
                } else {
                    this.currentTime = Math.min(this.duration || this.currentTime + 1, this.currentTime + 1);
                }

                // If we've reached the end, go to next track
                if (this.duration > 0 && this.currentTime >= this.duration) {
                    this.currentTime = 0;
                    this.nextTrack();
                } else {
                    this.updateProgressDisplay();
                }
            }
        }, 1000);
    }

    stopProgressSimulation() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    isSameTrack(track) {
        if (!this.currentTrack || !track) {
            return false;
        }
        const currentId = this.currentTrack.id || this.currentTrack.uri || this.currentTrack.title;
        const nextId = track.id || track.uri || track.title;
        return Boolean(currentId && nextId && currentId === nextId);
    }

    showMiniplayer() {
        const miniplayerEl = this.rootElement;
        if (miniplayerEl) {
            miniplayerEl.style.display = 'block';
        }
    }

    queueSeekCommit(time) {
        if (this.seekDebounceTimer) {
            clearTimeout(this.seekDebounceTimer);
        }
        this.seekDebounceTimer = setTimeout(() => {
            this.seekDebounceTimer = null;
            this.seekTo(time);
        }, 180);
    }

    hideMiniplayer() {
        const miniplayerEl = this.rootElement;
        if (miniplayerEl) {
            miniplayerEl.style.display = 'none';
        }
    }

    destroy() {
        // Clean up any intervals
        this.stopProgressSimulation();
        if (this.spotifyPolling) {
            clearInterval(this.spotifyPolling);
            this.spotifyPolling = null;
        }
        if (this.spotifyPlaybackPolling) {
            clearInterval(this.spotifyPlaybackPolling);
            this.spotifyPlaybackPolling = null;
        }
        if (this.outsideClickHandler) {
            document.removeEventListener('mousedown', this.outsideClickHandler);
            document.removeEventListener('touchstart', this.outsideClickHandler);
            this.outsideClickHandler = null;
        }
        if (this.escapeHandler) {
            document.removeEventListener('keydown', this.escapeHandler);
            this.escapeHandler = null;
        }
        if (this.visibilityChangeHandler) {
            document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
            this.visibilityChangeHandler = null;
        }
        if (this.beforeSwapHandler) {
            document.removeEventListener('htmx:beforeSwap', this.beforeSwapHandler);
            this.beforeSwapHandler = null;
        }
        if (this.seekDebounceTimer) {
            clearTimeout(this.seekDebounceTimer);
            this.seekDebounceTimer = null;
        }
        if (this.spotifyCountdownInterval) {
            clearInterval(this.spotifyCountdownInterval);
            this.spotifyCountdownInterval = null;
        }
        this.stopVisualizerAnimation();
        this.clearVisualizerHideTimer();
        this.playlistsToggleBtn = null;
        this.playlistsSection = null;
        this.queueToggleBtn = null;
        this.queuePanel = null;
        this.queueListEl = null;
        this.queueEmptyEl = null;
        this.spotifyQueueItems = [];
        this.queueDragIndex = -1;

        // Remove socket listeners if they exist
        if (window.socket) {
            window.socket.off('track_changed');
            window.socket.off('play_state_changed');
            window.socket.off('progress_updated');
        }
    }
}

// Resolve the #miniplayer element from a candidate root, then create or
// replace a MiniplayerFragment on it. Safe to call multiple times.
function _tryInitMiniplayer(root) {
    if (!root || !root.querySelector) return;
    const el = root.id === 'miniplayer' ? root : root.querySelector('#miniplayer');
    if (!el) return;
    if (el.__miniplayerFragment) {
        return;
    }
    el.__miniplayerFragment = new MiniplayerFragment(el);
}

// Path 1: DOMContentLoaded — catches the rare case where the partial was
// already in the DOM before this script ran (e.g. server-side render).
document.addEventListener('DOMContentLoaded', function () {
    _tryInitMiniplayer(document.body);
});

// Path 2: htmx.onLoad — works when HTMX is already defined (normal case
// after adding `defer` to this script tag, which makes it run after HTMX).
if (window.htmx) {
    htmx.onLoad(_tryInitMiniplayer);
}

// Path 3: DOM-level htmx:load listener — fires regardless of script order,
// providing a reliable fallback if htmx.onLoad was not registered in time.
document.addEventListener('htmx:load', function (event) {
    _tryInitMiniplayer(event.detail.elt);
});

// Global functions to update miniplayer from elsewhere in the app
window.updateMiniplayerTrack = function (track) {
    const miniplayerElement = document.getElementById('miniplayer');
    if (miniplayerElement && miniplayerElement.__miniplayerFragment) {
        miniplayerElement.__miniplayerFragment.updateTrack(track);
    }
};

window.updateMiniplayerPlayState = function (isPlaying) {
    const miniplayerElement = document.getElementById('miniplayer');
    if (miniplayerElement && miniplayerElement.__miniplayerFragment) {
        miniplayerElement.__miniplayerFragment.isPlaying = isPlaying;
        miniplayerElement.__miniplayerFragment.updatePlayState();
    }
};


