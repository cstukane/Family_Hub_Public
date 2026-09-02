/**
 * Media launcher bridge for the app bar.
 * Intercepts media app buttons (open_iframe) and calls the local media_launcher
 * service to spawn a child Chromium window instead of embedding in the main UI.
 */
(function () {
    // Always use the same-origin Flask proxy to avoid CORS issues with the local launcher service.
    const MEDIA_ENDPOINT = '/api/media/open';
    const ALLOWED_DOMAINS = (Array.isArray(window.MEDIA_WHITELIST) ? window.MEDIA_WHITELIST : [])
        .map((d) => String(d || '').toLowerCase())
        .filter(Boolean);

    function isAllowed(url) {
        try {
            const parsed = new URL(url);
            if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
                return false;
            }
            const host = (parsed.hostname || '').toLowerCase();
            return ALLOWED_DOMAINS.some((domain) => host === domain || host.endsWith(`.${domain}`));
        } catch (err) {
            console.warn('Invalid media URL provided:', err);
            return false;
        }
    }

    async function openMediaChild(url, opts = {}) {
        if (!url) {
            const message = 'Missing media URL.';
            window.toast ? toast.error(message) : alert(message);
            throw new Error(message);
        }
        if (!isAllowed(url)) {
            const message = 'Media host not allowed by whitelist.';
            window.toast ? toast.error(message) : alert(message);
            throw new Error(message);
        }

        const payload = {
            url: url.trim(),
            controller: opts.controller !== false // default true
        };

        if (opts.position) {
            payload.position = opts.position;
        }
        if (opts.size) {
            payload.size = opts.size;
        }

        const response = await fetch(MEDIA_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.ok === false) {
            const errMsg = data.err || `Failed to open media (HTTP ${response.status})`;
            throw new Error(errMsg);
        }
        return data;
    }

    function handleMediaButtonClick(event) {
        const button = event.target.closest('[data-media-launch="child"]');
        if (!button) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        const url = button.getAttribute('data-app-url') || '';
        const appId = button.getAttribute('data-app-id') || '';
        const appLabel = button.getAttribute('aria-label') || 'Media';

        openMediaChild(url, { controller: false })
            .then((data) => {
                const msg = data && data.pid ? `Opening ${appLabel} (PID ${data.pid})` : `Opening ${appLabel}`;
                if (window.toast) {
                    toast.success(msg);
                }
            })
            .catch((error) => {
                console.error('Media launcher failed, falling back to iframe:', error);
                const fallbackMsg = 'Media launcher unreachable. Loading in the app instead.';
                if (window.toast) {
                    toast.error(fallbackMsg);
                } else {
                    alert(fallbackMsg);
                }

                // Fallback: load via API launch endpoint (iframe flow)
                if (appId) {
                    fetch('/api/launch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ app_id: appId })
                    })
                        .then((resp) => resp.text())
                        .then((html) => {
                            const target = document.querySelector('#main-content');
                            if (target) {
                                target.innerHTML = html;
                            }
                        })
                        .catch((fallbackErr) => {
                            console.error('Fallback to iframe failed:', fallbackErr);
                        });
                }
            });
    }

    document.addEventListener('click', handleMediaButtonClick);

    // Expose helper for other scripts if needed
    window.openMediaChild = openMediaChild;
})();
