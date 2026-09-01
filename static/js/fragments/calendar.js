// System clock module - keeps the header time/date updated.

class SystemClock {
    constructor() {
        this.interval = null;
        this.timeout = null;
        this.update();
        this.schedule();
    }

    formatTime(now) {
        const locale = window.getPreferredLocale ? window.getPreferredLocale() : null;
        const locales = locale ? [locale] : [];
        return now.toLocaleTimeString(locales, { hour: '2-digit', minute: '2-digit' });
    }

    formatDate(now) {
        const locale = window.getPreferredLocale ? window.getPreferredLocale() : null;
        const locales = locale ? [locale] : [];
        return now.toLocaleDateString(locales, { weekday: 'short', month: 'short', day: 'numeric' });
    }

    update() {
        const now = new Date();
        const timeEl = document.getElementById('system-time');
        const dateEl = document.getElementById('system-date');
        if (timeEl) {
            const timeString = this.formatTime(now);
            timeEl.textContent = timeString;
            timeEl.setAttribute('aria-label', `Current time: ${timeString}`);
        }
        if (dateEl) {
            const dateString = this.formatDate(now);
            dateEl.textContent = dateString;
            dateEl.setAttribute('aria-label', `Current date: ${dateString}`);
        }

        // Day progress bar — fraction of day elapsed
        const progressEl = document.getElementById('day-progress-fill');
        if (progressEl) {
            const secondsElapsed = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
            const pct = (secondsElapsed / 86400) * 100;
            progressEl.style.width = pct.toFixed(2) + '%';
        }
    }

    schedule() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
        }

        const now = new Date();
        const msUntilNextMinute = 60000 - (now.getSeconds() * 1000 + now.getMilliseconds());
        this.timeout = setTimeout(() => {
            this.update();
            this.interval = setInterval(() => this.update(), 60000);
        }, msUntilNextMinute);
    }

    destroy() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
        if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
        }
    }
}

function ensureSystemClock() {
    if (!window.__systemClock) {
        window.__systemClock = new SystemClock();
    } else {
        window.__systemClock.update();
    }
}

document.addEventListener('DOMContentLoaded', ensureSystemClock);

if (window.htmx) {
    htmx.onLoad(() => {
        ensureSystemClock();
    });
}
