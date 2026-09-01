// media-client.js
/**
 * Media Client for Family Hub
 * Handles communication with the media_launcher service
 */

// List of allowed domains for media playback
const ALLOWED_DOMAINS = [
    '127.0.0.1',
    'localhost',
    'youtube.com', 'youtu.be',
    'twitch.tv',
    'pluto.tv',
    'roku.com', 'roku.tv',
    'vimeo.com',
    'dailymotion.com',
    'tubitv.com',
    'spotify.com',
    'disneyplus.com',
    'max.com',
    'espn.com',
    'photos.google.com',
    'google.com',
    'therokuchannel.roku.com'
];

function getMediaLauncherAuthHeaders() {
    const token = window.MEDIA_LAUNCHER_TOKEN;
    if (token && token !== "__MEDIA_LAUNCHER_TOKEN__") {
        return { 'Authorization': `Bearer ${token}` };
    }
    if (window.MEDIA_HUB_AUTH_TOKEN) {
        return { 'X-HUB-AUTH': window.MEDIA_HUB_AUTH_TOKEN };
    }
    return {};
}

/**
 * Opens a media URL in a separate child window via the media launcher service
 * @param {string} url - The media URL to open
 * @param {Object} opts - Optional parameters like position and size
 * @returns {Promise} - A promise that resolves when the request is complete
 */
async function openMedia(url, opts = {}) {
    // Local whitelist check
    try {
        const u = new URL(url);
        if (!ALLOWED_DOMAINS.some(d => u.hostname === d || u.hostname.endsWith(`.${d}`))) {
            alert('Media host not allowed');
            return Promise.reject(new Error('Domain not allowed'));
        }
    } catch (e) {
        alert('Invalid URL');
        return Promise.reject(new Error('Invalid URL'));
    }

    // Try to call the local launcher service
    try {
        const response = await fetch('http://127.0.0.1:7666/v1/open_media', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getMediaLauncherAuthHeaders()
            },
            body: JSON.stringify({
                url,
                position: opts.position, // [x, y] coordinates
                size: opts.size          // [width, height]
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.err || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Media window opened successfully:', data);
        return data;
    } catch (err) {
        console.error('Failed to open media:', err);
        // Show user-facing alert
        alert('Could not open media player. Is the media launcher running?\n\n' +
              'Please ensure media_launcher.py is running on port 7666.');
        
        // Dev-only fallback: load in an iframe for quick testing (uncomment for development)
        // const iframe = document.getElementById('dev-frame');
        // if (iframe) {
        //     iframe.src = url;
        //     iframe.style.display = 'block';
        // }
        
        return Promise.reject(err);
    }
}

/**
 * Closes the current media window via the media launcher service
 * @returns {Promise} - A promise that resolves when the request is complete
 */
async function closeMedia() {
    try {
        const response = await fetch('http://127.0.0.1:7666/v1/close_media', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getMediaLauncherAuthHeaders()
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.err || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Media window closed successfully:', data);
        return data;
    } catch (err) {
        console.warn('closeMedia failed:', err);
        return Promise.reject(err);
    }
}

/**
 * Opens a media URL with controller overlay option
 * @param {string} url - The media URL to open
 * @param {Object} opts - Optional parameters
 * @returns {Promise} - A promise that resolves when the request is complete
 */
async function openMediaWithController(url, opts = {}) {
    // Add controller option to request for media_launcher to spawn a controller window
    opts.controller = true;
    return openMedia(url, opts);
}

/**
 * Toggles fullscreen state of the media window
 * Note: This is currently a placeholder - actual fullscreen would require changes to media_launcher
 */
function toggleMediaFullscreen() {
    console.log('Fullscreen toggle requested');
    // In a real implementation, this would communicate with media_launcher to toggle fullscreen
    // For now, just log the request
}

// Variables for double-Esc detection
let lastEscPress = 0;

/**
 * Checks the status of the media window
 * @returns {Promise} - A promise that resolves with the status information
 */
async function checkMediaStatus() {
    try {
        const response = await fetch('http://127.0.0.1:7666/v1/media_status', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...getMediaLauncherAuthHeaders()
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.err || `HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (err) {
        console.warn('checkMediaStatus failed:', err);
        return Promise.reject(err);
    }
}

/**
 * Handles keyboard shortcuts for media windows
 * @param {Event} event - The keyboard event
 */
function handleMediaKeyboardShortcuts(event) {
    // Toggle fullscreen with F11 key
    if (event.key === 'F11') {
        event.preventDefault();
        toggleMediaFullscreen();
    }
    
    // Close with Ctrl+Shift+X (specifically requested in requirements)
    if (event.ctrlKey && event.shiftKey && event.key === 'X') {
        event.preventDefault();
        closeMedia();
        console.log('Media window closed via keyboard shortcut');
    }
    
    // Optional double-Esc detection (within 400ms) to close media
    if (event.key === 'Escape') {
        const now = Date.now();
        if (now - lastEscPress < 400) { // Double press within 400ms
            closeMedia();
            console.log('Media window closed via double-Esc');
            lastEscPress = 0; // Reset to prevent triple+ detection
        } else {
            lastEscPress = now; // Record first press
        }
    }
}

// Add keyboard event listener when the script loads
document.addEventListener('keydown', handleMediaKeyboardShortcuts);

// Export functions for use in other modules (if using modules)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { 
        openMedia, 
        closeMedia, 
        openMediaWithController, 
        ALLOWED_DOMAINS, 
        handleMediaKeyboardShortcuts, 
        toggleMediaFullscreen, 
        checkMediaStatus 
    };
}
