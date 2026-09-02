// Ambient mode module - handles ambient display functionality with proper cleanup

class AmbientMode {
    constructor() {
        this.ambientModeActive = false;
        this.ambientInterval = null;
        this.ambientPhotos = [];
        this.currentAmbientPhotoIndex = 0;
        this.dateTimeInterval = null;
        this.keyDownHandler = null;
        this.domContentLoadedHandler = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Store the handler functions so they can be removed during cleanup
        this.keyDownHandler = (event) => {
            // Check if Alt+A is pressed
            if (event.altKey && event.key === 'a') {
                event.preventDefault();
                if (this.ambientModeActive) {
                    this.exitAmbientMode();
                } else {
                    this.enterAmbientMode();
                }
            }

            // If ambient mode is active, press Escape to exit
            if (this.ambientModeActive && event.key === 'Escape') {
                this.exitAmbientMode();
            }
        };

        this.domContentLoadedHandler = () => {
            // Check if ambient mode is enabled in config and add button if so
            const config = window.currentConfig || {};
            if (config && config.photos && config.photos.enabled) {
                // Ambient mode is available
                console.log("Ambient display mode available");
            }
        };

        document.addEventListener('keydown', this.keyDownHandler);
        document.addEventListener('DOMContentLoaded', this.domContentLoadedHandler);
    }

    enterAmbientMode() {
        // Get photos for ambient display
        fetch('/api/photos?limit=20')
            .then(response => response.json())
            .then(photos => {
                this.ambientPhotos = photos;
                if (this.ambientPhotos.length > 0) {
                    // Show the ambient display
                    const ambientDisplay = document.getElementById('ambient-display');
                    if (ambientDisplay) {
                        ambientDisplay.style.display = 'block';
                    }
                    
                    document.body.style.display = 'none'; // Hide the regular interface
                    this.ambientModeActive = true;

                    // Start photo rotation
                    this.showAmbientPhoto(this.currentAmbientPhotoIndex);
                    this.ambientInterval = setInterval(() => {
                        this.currentAmbientPhotoIndex = (this.currentAmbientPhotoIndex + 1) % this.ambientPhotos.length;
                        this.showAmbientPhoto(this.currentAmbientPhotoIndex);
                    }, (window.currentConfig?.photos?.slideshow_interval || 5) * 1000); // Use config value or default to 5s

                    // Update date/time every second
                    this.dateTimeInterval = setInterval(() => {
                        this.updateAmbientDateTime();
                    }, 1000);

                    // Update weather info
                    this.updateAmbientWeather();
                }
            })
            .catch(error => {
                console.error('Error loading photos for ambient mode:', error);
            });
    }

    exitAmbientMode() {
        if (this.ambientInterval) {
            clearInterval(this.ambientInterval);
            this.ambientInterval = null;
        }
        
        if (this.dateTimeInterval) {
            clearInterval(this.dateTimeInterval);
            this.dateTimeInterval = null;
        }
        
        const ambientDisplay = document.getElementById('ambient-display');
        if (ambientDisplay) {
            ambientDisplay.style.display = 'none';
        }
        
        document.body.style.display = 'block'; // Show the regular interface again
        this.ambientModeActive = false;
    }

    showAmbientPhoto(index) {
        if (this.ambientPhotos.length === 0) return;

        const photo = this.ambientPhotos[index];
        const img = document.getElementById('ambient-photo');

        if (img) {
            // Set photo source based on source type
            if (photo.source === 'local') {
                img.src = `/static/photos/${photo.filename}`;
            } else if (photo.album_art_url) {
                img.src = photo.album_art_url;
            } else {
                // Fallback to placeholder
                img.src = `data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect width="400" height="300" fill="%23333"/><text x="200" y="150" font-family="Arial" font-size="20" fill="white" text-anchor="middle">Photo ${index + 1}</text></svg>`;
            }
        }
    }

    updateAmbientDateTime() {
        const now = new Date();
        const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit' };

        const locale = window.getPreferredLocale ? window.getPreferredLocale() : undefined;
        const dateStr = now.toLocaleDateString(locale, dateOptions);
        const timeStr = now.toLocaleTimeString(locale, timeOptions);

        const dateTimeElement = document.getElementById('ambient-date-time');
        if (dateTimeElement) {
            dateTimeElement.innerHTML =
                `<div>${dateStr}</div><div style="font-size: 3em; margin: 10px 0;">${timeStr}</div>`;
        }
    }

    updateAmbientWeather() {
        fetch('/api/weather')
            .then(response => response.json())
            .then(weatherData => {
                const current = weatherData.current;
                const weatherElement = document.getElementById('ambient-weather');
                if (weatherElement) {
                    const tempText = window.formatUnit
                        ? window.formatUnit(current.temperature, 'fahrenheit', { maxFractionDigits: 0, fallback: 'F' })
                        : `${Math.round(Number(current.temperature))}F`;
                    weatherElement.textContent = `${tempText}, ${current.condition}`;
                }
            })
            .catch(error => {
                console.error('Error loading weather for ambient mode:', error);
                const weatherElement = document.getElementById('ambient-weather');
                if (weatherElement) {
                    weatherElement.textContent = 'Weather info unavailable';
                }
            });
    }

    destroy() {
        // Clear intervals
        if (this.ambientInterval) {
            clearInterval(this.ambientInterval);
            this.ambientInterval = null;
        }
        
        if (this.dateTimeInterval) {
            clearInterval(this.dateTimeInterval);
            this.dateTimeInterval = null;
        }
        
        // Remove event listeners
        if (this.keyDownHandler) {
            document.removeEventListener('keydown', this.keyDownHandler);
        }
        
        if (this.domContentLoadedHandler) {
            document.removeEventListener('DOMContentLoaded', this.domContentLoadedHandler);
        }
        
        // Exit ambient mode if it's active
        if (this.ambientModeActive) {
            this.exitAmbientMode();
        }
    }
}

// Initialize ambient mode when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.ambientMode = new AmbientMode();
});

