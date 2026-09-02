// Sports ticker fragment module - handles sports ticker functionality with proper cleanup

class SportsTickerFragment {
    constructor(rootElement) {
        this.rootElement = rootElement;
        this.tickerInitialised = false;
        this.observer = null;
        this.observerTimeout = null;
        this.init();
    }

    init() {
        this.initialise();
        
        // Register cleanup function to be called before HTMX swaps this element
        if (window.htmx) {
            htmx.on('htmx:beforeSwap', (event) => {
                if (event.target === this.rootElement || this.rootElement.contains(event.target)) {
                    this.destroy();
                }
            });
        }
    }

    initialise() {
        const tickerRoot = this.getTickerRoot();
        if (!tickerRoot || tickerRoot.dataset.tickerInitialised === 'true') {
            return;
        }
        tickerRoot.dataset.tickerInitialised = 'true';
        this.tickerInitialised = true;

        const tickerContainer = tickerRoot.querySelector('.ticker-container');
        const tickerContent = tickerRoot.querySelector('.ticker-content');

        if (tickerContent) {
            const pauseTicker = () => {
                tickerContent.style.animationPlayState = 'paused';
            };
            const resumeTicker = () => {
                tickerContent.style.animationPlayState = 'running';
            };

            // Store event handlers to remove later
            this.pauseTicker = pauseTicker;
            this.resumeTicker = resumeTicker;

            tickerRoot.addEventListener('mouseenter', pauseTicker);
            tickerRoot.addEventListener('mouseleave', resumeTicker);
            tickerRoot.addEventListener('focusin', pauseTicker);
            tickerRoot.addEventListener('focusout', resumeTicker);
        }

        this.applyTickerMetrics();

        // Check if clickable games feature is enabled in config
        // Note: In a real implementation, config would be passed in or available globally
        const clickableConfig = window.currentConfig?.features?.sports_ticker_clickable || false;

        // If clickable feature is disabled, remove cursor pointer styling and onclick handlers
        if (!clickableConfig) {
            const tickerItems = tickerRoot.querySelectorAll('.ticker-item[onclick]');
            tickerItems.forEach(item => {
                item.style.cursor = 'default';
                item.onclick = null;
            });
        } else {
            // Add keyboard accessibility for the clickable ticker items
            const tickerItems = tickerRoot.querySelectorAll('.ticker-item[onclick]');
            tickerItems.forEach(item => {
                item.setAttribute('tabindex', '0');
                item.setAttribute('role', 'button');
                item.setAttribute('aria-label', 'Click to open game details in new tab');

                const handleTickerKeydown = (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        this.click();
                    }
                };
                
                // Store the handler to remove later
                item.handleTickerKeydown = handleTickerKeydown;
                
                item.addEventListener('keydown', handleTickerKeydown);
            });
        }

        // Set up MutationObserver
        if (typeof MutationObserver !== 'undefined' && tickerContent) {
            // Use a timeout-based observer as an alternative to ensure content changes are captured
            this.observerTimeout = null;
            this.observer = new MutationObserver(() => {
                if (this.observerTimeout) {
                    clearTimeout(this.observerTimeout);
                }
                this.observerTimeout = setTimeout(() => {
                    this.applyTickerMetrics();
                }, 100);
            });
            this.observer.observe(tickerContent, { childList: true, subtree: true });
        }
    }

    applyTickerMetrics() {
        const tickerRoot = this.getTickerRoot();
        if (!tickerRoot) return;
        
        const tickerContainer = tickerRoot.querySelector('.ticker-container');
        const tickerContent = tickerRoot.querySelector('.ticker-content');

        if (!tickerContainer || !tickerContent) {
            return;
        }

        // Use setTimeout to ensure DOM is fully rendered before measuring
        setTimeout(() => {
            const containerWidth = tickerContainer.clientWidth;
            if (containerWidth === 0) {
                // Retry after a short delay if container width is 0
                setTimeout(() => this.applyTickerMetrics(), 100);
                return;
            }

            // Calculate the actual total width of all content including gaps
            let totalWidth = 0;
            const children = tickerContent.children;
            for (let i = 0; i < children.length; i++) {
                // Add the width of each child plus the gap
                totalWidth += children[i].offsetWidth;
                if (i < children.length - 1) {
                    // Add gap between items (default is 12px from CSS)
                    totalWidth += 12;
                }
            }

            if (totalWidth === 0) {
                tickerContent.classList.add('ticker-static');
                tickerContent.style.removeProperty('--ticker-distance');
                tickerContent.style.removeProperty('--ticker-duration');
                tickerContent.style.animation = 'none';
                return;
            }

            // Travel distance must exactly equal one set's width for a seamless loop snap-back
            const numCopies = parseInt(tickerContent.dataset?.tickerCopies || '2');
            const travelDistance = totalWidth / numCopies;
            if (travelDistance <= 0) {
                tickerContent.classList.add('ticker-static');
                tickerContent.style.animation = 'none';
                return;
            }
            const PX_PER_SECOND = 60; // Pixels per second - adjust for desired speed
            const MIN_DURATION = 20; // Minimum duration in seconds
            const MAX_DURATION = 60; // Maximum duration in seconds
            
            const duration = Math.min(MAX_DURATION, Math.max(MIN_DURATION, travelDistance / PX_PER_SECOND));

            tickerContent.style.setProperty('--ticker-distance', `${travelDistance}px`);
            tickerContent.style.setProperty('--ticker-duration', `${duration.toFixed(2)}s`);
            tickerContent.classList.remove('ticker-static');
            tickerContent.style.animation = `ticker-scroll ${duration.toFixed(2)}s linear infinite`;
            tickerContent.style.animationPlayState = 'running';
        }, 50); // Small delay to ensure DOM is rendered
    }

    destroy() {
        // Clear observer
        if (this.observer) {
            this.observer.disconnect();
            this.observer = null;
        }
        
        if (this.observerTimeout) {
            clearTimeout(this.observerTimeout);
            this.observerTimeout = null;
        }

        // Remove event listeners
        const tickerRoot = this.getTickerRoot();
        if (tickerRoot) {
            const tickerContent = tickerRoot.querySelector('.ticker-content');
            
            if (tickerContent && this.pauseTicker && this.resumeTicker) {
                tickerRoot.removeEventListener('mouseenter', this.pauseTicker);
                tickerRoot.removeEventListener('mouseleave', this.resumeTicker);
                tickerRoot.removeEventListener('focusin', this.pauseTicker);
                tickerRoot.removeEventListener('focusout', this.resumeTicker);
            }

            // Remove keyboard accessibility handlers
            const tickerItems = tickerRoot.querySelectorAll('.ticker-item[onclick]');
            tickerItems.forEach(item => {
                if (item.handleTickerKeydown) {
                    item.removeEventListener('keydown', item.handleTickerKeydown);
                }
            });
        }
        
        // Remove the initialization flag
        if (tickerRoot) {
            tickerRoot.dataset.tickerInitialised = 'false';
        }
    }

    getTickerRoot() {
        // Accept either the ticker element itself or a container that holds it
        if (this.rootElement && this.rootElement.id === 'sports-horizontal-ticker') {
            return this.rootElement;
        }
        if (this.rootElement && this.rootElement.querySelector) {
            return this.rootElement.querySelector('#sports-horizontal-ticker');
        }
        return null;
    }
}

window.SportsTickerFragment = SportsTickerFragment;

// Use htmx onLoad to initialize the sports ticker fragment when it's loaded
if (window.htmx) {
    htmx.onLoad((target) => {
        // Check if this target contains sports ticker functionality
        if (target.querySelector) {
            let tickerElement = null;

            // Look for the actual ticker element to initialize the fragment on
            if (target.classList.contains('sports-horizontal-ticker')) {
                // If target is the ticker itself
                tickerElement = target;
            } else if (target.id === 'sports-horizontal-ticker') {
                // If target has the ticker ID
                tickerElement = target;
            } else if (target.querySelector('.sports-horizontal-ticker')) {
                // If target contains the ticker
                tickerElement = target.querySelector('.sports-horizontal-ticker');
            } else if (target.classList.contains('sports-horizontal-ticker-container')) {
                // If target is the container and contains the ticker
                tickerElement = target.querySelector('.sports-horizontal-ticker');
            }

            if (tickerElement) {
                // Create a new instance, making sure to destroy any previous instance on the ticker element
                const existingFragment = tickerElement.__sportsTickerFragment;
                if (existingFragment) {
                    existingFragment.destroy();
                }

                const sportsTickerFragment = new SportsTickerFragment(tickerElement);
                tickerElement.__sportsTickerFragment = sportsTickerFragment;
            }
        }
    });
}

// Add fallback initialization for cases where HTMX events don't fire
function initializeSportsTickerFallback() {
    try {
        const tickerElement = document.getElementById('sports-horizontal-ticker');
        if (tickerElement && !tickerElement.__sportsTickerFragment) {
            console.log('Initializing SportsTickerFragment via fallback');
            const sportsTickerFragment = new SportsTickerFragment(tickerElement);
            tickerElement.__sportsTickerFragment = sportsTickerFragment;
        }
    } catch (error) {
        console.error('Error in sports ticker fallback initialization:', error);
    }
}

// Try to initialize on DOMContentLoaded as fallback
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure HTMX has had a chance to process
    setTimeout(initializeSportsTickerFallback, 500);
});

// Also try after a longer delay in case of slow loading
setTimeout(initializeSportsTickerFallback, 2000);

// Add MutationObserver to catch dynamically added tickers
function setupTickerMutationObserver() {
    try {
        const observer = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.id === 'sports-horizontal-ticker' && !node.__sportsTickerFragment) {
                            console.log('Found dynamically added ticker, initializing');
                            const sportsTickerFragment = new SportsTickerFragment(node);
                            node.__sportsTickerFragment = sportsTickerFragment;
                        } else if (node.querySelector) {
                            const ticker = node.querySelector('#sports-horizontal-ticker');
                            if (ticker && !ticker.__sportsTickerFragment) {
                                console.log('Found ticker in added content, initializing');
                                const sportsTickerFragment = new SportsTickerFragment(ticker);
                                ticker.__sportsTickerFragment = sportsTickerFragment;
                            }
                        }
                    }
                }
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        return observer;
    } catch (error) {
        console.error('Error setting up ticker mutation observer:', error);
        return null;
    }
}

// Set up mutation observer if available
if (typeof MutationObserver !== 'undefined') {
    const tickerObserver = setupTickerMutationObserver();
    if (tickerObserver) {
        window.sportsTickerMutationObserver = tickerObserver;
    }
}
