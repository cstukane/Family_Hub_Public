// Photos slideshow fragment module - handles photo slideshow functionality with proper cleanup

class PhotosSlideshowFragment {
    constructor(rootElement) {
        this.rootElement = rootElement;
        this.photos = [];
        this.currentPhotoIndex = 0;
        this.slideshowInterval = 5000; // 5 seconds
        this.slideshowTimer = null;
        this.isPlaying = false;
        this.init();
    }

    init() {
        this.loadPhotos();
        
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

    loadPhotos() {
        fetch('/api/photos?limit=50')
            .then(response => response.json())
            .then(photos => {
                this.photos = photos;

                if (this.photos.length > 0) {
                    this.showPhoto(this.currentPhotoIndex);
                }
            })
            .catch(error => {
                console.error('Error loading photos:', error);
            });
    }

    showPhoto(index) {
        if (this.photos.length === 0) return;

        // Adjust index if out of bounds
        if (index >= this.photos.length) {
            this.currentPhotoIndex = 0;
        } else if (index < 0) {
            this.currentPhotoIndex = this.photos.length - 1;
        } else {
            this.currentPhotoIndex = index;
        }

        const photo = this.photos[this.currentPhotoIndex];
        const img = this.rootElement.querySelector('#slideshow-image');

        // Update image source with the photo
        if (photo.source === 'local') {
            img.src = `/static/photos/${photo.filename}`;
        } else if (photo.album_art_url) {
            img.src = photo.album_art_url;
        } else {
            // Fallback: create a placeholder image based on filename
            img.src = `/static/photos/${photo.filename}`;
        }

        // Update photo info
        const titleElement = this.rootElement.querySelector('#photo-title');
        const descriptionElement = this.rootElement.querySelector('#photo-description');
        const dateElement = this.rootElement.querySelector('#photo-date');
        
        if (titleElement) titleElement.textContent = photo.title || 'Untitled';
        if (descriptionElement) descriptionElement.textContent = photo.description || 'No description';
        if (dateElement && photo.date_taken) {
            const date = new Date(photo.date_taken);
            const locale = window.getPreferredLocale ? window.getPreferredLocale() : undefined;
            dateElement.textContent = date.toLocaleDateString(locale);
        }

        // Show the image and info
        if (img) img.style.display = 'block';
        const infoElement = this.rootElement.querySelector('#photo-info');
        if (infoElement) infoElement.style.display = 'block';
    }

    nextPhoto() {
        this.currentPhotoIndex++;
        if (this.currentPhotoIndex >= this.photos.length) {
            this.currentPhotoIndex = 0; // Loop back to start
        }
        this.showPhoto(this.currentPhotoIndex);
    }

    prevPhoto() {
        this.currentPhotoIndex--;
        if (this.currentPhotoIndex < 0) {
            this.currentPhotoIndex = this.photos.length - 1; // Loop to end
        }
        this.showPhoto(this.currentPhotoIndex);
    }

    startSlideshow() {
        if (this.isPlaying) return;

        this.isPlaying = true;
        const playBtn = this.rootElement.querySelector('#slideshow-play-btn');
        const pauseBtn = this.rootElement.querySelector('#slideshow-pause-btn');
        if (playBtn) playBtn.style.display = 'none';
        if (pauseBtn) pauseBtn.style.display = 'inline-block';

        this.slideshowTimer = setInterval(() => {
            this.nextPhoto();
        }, this.slideshowInterval);
    }

    pauseSlideshow() {
        if (!this.isPlaying) return;

        this.isPlaying = false;
        const playBtn = this.rootElement.querySelector('#slideshow-play-btn');
        const pauseBtn = this.rootElement.querySelector('#slideshow-pause-btn');
        if (playBtn) playBtn.style.display = 'inline-block';
        if (pauseBtn) pauseBtn.style.display = 'none';

        if (this.slideshowTimer) {
            clearInterval(this.slideshowTimer);
            this.slideshowTimer = null;
        }
    }

    updateInterval() {
        const intervalInput = this.rootElement.querySelector('#slideshow-interval');
        if (!intervalInput) return;
        
        const newInterval = intervalInput.value * 1000;
        this.slideshowInterval = newInterval;

        // If slideshow is playing, restart with new interval
        if (this.isPlaying) {
            this.pauseSlideshow();
            this.startSlideshow();
        }
    }

    setupEventListeners() {
        const nextBtn = this.rootElement.querySelector('#slideshow-next-btn');
        const prevBtn = this.rootElement.querySelector('#slideshow-prev-btn');
        const playBtn = this.rootElement.querySelector('#slideshow-play-btn');
        const pauseBtn = this.rootElement.querySelector('#slideshow-pause-btn');
        const updateBtn = this.rootElement.querySelector('#update-interval-btn');

        if (nextBtn) nextBtn.addEventListener('click', () => this.nextPhoto());
        if (prevBtn) prevBtn.addEventListener('click', () => this.prevPhoto());
        if (playBtn) playBtn.addEventListener('click', () => this.startSlideshow());
        if (pauseBtn) pauseBtn.addEventListener('click', () => this.pauseSlideshow());
        if (updateBtn) updateBtn.addEventListener('click', () => this.updateInterval());

        // Keyboard navigation - add to document so it works even when not directly focused
        this.handleKeyDown = (event) => {
            if (event.key === 'ArrowRight') {
                this.nextPhoto();
            } else if (event.key === 'ArrowLeft') {
                this.prevPhoto();
            } else if (event.key === ' ') { // Space bar
                event.preventDefault(); // Prevent page scroll
                if (this.isPlaying) {
                    this.pauseSlideshow();
                } else {
                    this.startSlideshow();
                }
            }
        };

        document.addEventListener('keydown', this.handleKeyDown);
    }

    destroy() {
        // Clear the slideshow interval
        if (this.slideshowTimer) {
            clearInterval(this.slideshowTimer);
            this.slideshowTimer = null;
        }
        
        // Remove keyboard event listener
        document.removeEventListener('keydown', this.handleKeyDown);
        
        this.isPlaying = false;
    }
}

// Use htmx onLoad to initialize the photos slideshow fragment when it's loaded
if (window.htmx) {
    htmx.onLoad((target) => {
        // Check if this target contains photos slideshow functionality
        if (target.querySelector && 
            (target.classList.contains('panel') && target.classList.contains('photo-slideshow-container')) ||
            target.id === 'photo-slideshow-container' || 
            target.querySelector('.photo-slideshow-container') ||
            target.querySelector('#slideshow-image')) {
            
            // Create a new instance, making sure to destroy any previous instance
            const existingFragment = target.__photosSlideshowFragment;
            if (existingFragment) {
                existingFragment.destroy();
            }
            
            const photosSlideshowFragment = new PhotosSlideshowFragment(target);
            target.__photosSlideshowFragment = photosSlideshowFragment;
        }
    });
}
