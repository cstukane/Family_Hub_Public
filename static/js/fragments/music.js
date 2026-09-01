// Music player fragment module - handles music player functionality with proper cleanup

class MusicPlayerFragment {
    constructor(rootElement) {
        this.rootElement = rootElement;
        this.tracks = [];
        this.currentQueue = [];
        this.currentTrackIndex = 0;
        this.isPlaying = false;
        this.audioElement = null;
        this.progressInterval = null;
        this.init();
    }

    init() {
        this.loadRecentTracks();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Register cleanup function to be called before HTMX swaps this element
        if (window.htmx) {
            htmx.on('htmx:beforeSwap', (event) => {
                if (event.target === this.rootElement || this.rootElement.contains(event.target)) {
                    this.destroy();
                }
            });
        }
    }

    loadRecentTracks() {
        fetch('/api/music/tracks?limit=5')
            .then(response => response.json())
            .then(tracks => {
                this.tracks = tracks;

                // Update recent tracks display
                const container = this.rootElement.querySelector('#recent-tracks-list');
                if (!container) return;

                container.innerHTML = '';

                this.tracks.forEach((track, index) => {
                    const trackElement = document.createElement('div');
                    trackElement.className = 'recent-track-item';
                    trackElement.innerHTML = `
                        <div class="track-info">
                            <span class="track-title">${track.title}</span> -
                            <span class="track-artist">${track.artist}</span>
                        </div>
                        <button class="btn btn-sm add-to-queue-btn"
                                onclick="addToQueue(${track.id})"
                                aria-label="Add ${track.title} to queue">
                            Queue
                        </button>
                    `;
                    container.appendChild(trackElement);
                });
            })
            .catch(error => {
                console.error('Error loading recent tracks:', error);
            });
    }

    playTrack(trackId) {
        const track = this.tracks.find(t => t.id == trackId);
        if (!track) return;

        // Update display with track info
        const titleElement = this.rootElement.querySelector('#current-track-title');
        const artistElement = this.rootElement.querySelector('#current-track-artist');
        const albumElement = this.rootElement.querySelector('#current-track-album');
        
        if (titleElement) titleElement.textContent = track.title;
        if (artistElement) artistElement.textContent = track.artist;
        if (albumElement) albumElement.textContent = track.album;

        const albumArtElement = this.rootElement.querySelector('#album-art');
        if (albumArtElement && track.album_art_url) {
            albumArtElement.src = track.album_art_url;
            albumArtElement.style.display = 'block';
        } else if (albumArtElement) {
            albumArtElement.style.display = 'none';
        }

        // In a real implementation, we would actually play the audio file
        // For now, we'll just simulate the playback
        this.simulatePlayback(track);
    }

    simulatePlayback(track) {
        this.isPlaying = true;
        
        const playBtn = this.rootElement.querySelector('#play-btn');
        const pauseBtn = this.rootElement.querySelector('#pause-btn');
        if (playBtn) playBtn.style.display = 'none';
        if (pauseBtn) pauseBtn.style.display = 'inline-block';

        // Update display with track duration
        const duration = track.duration || 180; // Default to 3 minutes
        const durationElement = this.rootElement.querySelector('#track-duration');
        if (durationElement) durationElement.textContent = this.formatTime(duration);

        // Simulate progress
        let currentTime = 0;
        const progressElement = this.rootElement.querySelector('#progress-bar');
        const currentTimeElement = this.rootElement.querySelector('#current-time');
        
        // Clear any existing interval to prevent duplicates
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }

        this.progressInterval = setInterval(() => {
            if (!this.isPlaying) {
                clearInterval(this.progressInterval);
                return;
            }

            currentTime++;
            const progressPercent = (currentTime / duration) * 100;
            if (progressElement) progressElement.value = progressPercent;
            if (currentTimeElement) currentTimeElement.textContent = this.formatTime(currentTime);

            if (currentTime >= duration) {
                clearInterval(this.progressInterval);
                // Move to next track
                this.nextTrack();
            }
        }, 1000); // Update every second
    }

    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
    }

    play() {
        if (this.tracks.length === 0) return;

        if (this.currentTrackIndex >= this.tracks.length) {
            this.currentTrackIndex = 0;
        }

        this.playTrack(this.tracks[this.currentTrackIndex].id);
    }

    pause() {
        this.isPlaying = false;
        
        const playBtn = this.rootElement.querySelector('#play-btn');
        const pauseBtn = this.rootElement.querySelector('#pause-btn');
        if (playBtn) playBtn.style.display = 'inline-block';
        if (pauseBtn) pauseBtn.style.display = 'none';
        
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }

    nextTrack() {
        this.currentTrackIndex++;
        if (this.currentTrackIndex >= this.tracks.length) {
            this.currentTrackIndex = 0; // Loop back to start
        }
        this.playTrack(this.tracks[this.currentTrackIndex].id);
    }

    prevTrack() {
        this.currentTrackIndex--;
        if (this.currentTrackIndex < 0) {
            this.currentTrackIndex = this.tracks.length - 1; // Loop to end
        }
        this.playTrack(this.tracks[this.currentTrackIndex].id);
    }

    // Add track to queue function
    async addToQueue(trackId) {
        try {
            // First, create a queue if one doesn't exist
            let queueResponse = await fetch('/api/music/queues', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            let queue = await queueResponse.json();

            // Add the track to the queue
            const addResponse = await fetch(`/api/music/queues/${queue.id}/tracks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    track_id: trackId
                })
            });

            if (addResponse.ok) {
                alert('Track added to queue!');
            } else {
                alert('Failed to add track to queue');
            }
        } catch (error) {
            console.error('Error adding track to queue:', error);
            alert('Error adding track to queue');
        }
    }

    updateVolume() {
        const volumeSlider = this.rootElement.querySelector('#volume-slider');
        const volumeValue = this.rootElement.querySelector('#volume-value');
        if (!volumeSlider || !volumeValue) return;
        
        const volume = volumeSlider.value;
        volumeValue.textContent = volume + '%';

        // In a real implementation, we would update the actual volume
        // For now, we just update the display
    }

    setupEventListeners() {
        const playBtn = this.rootElement.querySelector('#play-btn');
        const pauseBtn = this.rootElement.querySelector('#pause-btn');
        const nextBtn = this.rootElement.querySelector('#next-track-btn');
        const prevBtn = this.rootElement.querySelector('#prev-track-btn');
        const volumeSlider = this.rootElement.querySelector('#volume-slider');

        if (playBtn) playBtn.addEventListener('click', () => this.play());
        if (pauseBtn) pauseBtn.addEventListener('click', () => this.pause());
        if (nextBtn) nextBtn.addEventListener('click', () => this.nextTrack());
        if (prevBtn) prevBtn.addEventListener('click', () => this.prevTrack());
        if (volumeSlider) volumeSlider.addEventListener('input', () => this.updateVolume());
    }

    destroy() {
        // Clear the progress interval
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
        
        // Reset playing state
        this.isPlaying = false;
    }
}

// Use htmx onLoad to initialize the music player fragment when it's loaded
if (window.htmx) {
    htmx.onLoad((target) => {
        // Check if this target contains music player functionality
        if (target.querySelector && 
            (target.classList.contains('panel') && target.classList.contains('music-player-container')) ||
            target.id === 'music-player-container' || 
            target.querySelector('.music-player-container') ||
            target.querySelector('#current-track-title')) {
            
            // Create a new instance, making sure to destroy any previous instance
            const existingFragment = target.__musicPlayerFragment;
            if (existingFragment) {
                existingFragment.destroy();
            }
            
            const musicPlayerFragment = new MusicPlayerFragment(target);
            target.__musicPlayerFragment = musicPlayerFragment;
        }
    });
}