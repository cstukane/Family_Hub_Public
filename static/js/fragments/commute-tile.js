// Commute tile widget (Mapbox) for live traffic and ETA
console.info("[CommuteTile] File parsed");

class CommuteTile {
    constructor(rootElement) {
        this.root = rootElement;
        this.etaEl = rootElement.querySelector('[data-role="commute-eta"]');
        this.deltaEl = rootElement.querySelector('[data-role="commute-delta"]');
        this.statusEl = rootElement.querySelector('[data-role="commute-status"]');
        this.windowEl = rootElement.querySelector('[data-role="commute-window"]');
        this.incidentEl = rootElement.querySelector('[data-role="commute-incident"]');
        this.progressEl = rootElement.querySelector('[data-role="commute-progress-fill"]');
        this.footerEl = rootElement.querySelector('[data-role="commute-updated"]');
        this.refreshInterval = null;
        this.visibilityInterval = null;
        this.currentWindow = null;
        this.cache = null;
        this.statusState = { current: null, pending: null, pendingCount: 0 };
        this.geocodeCache = {};
        this.config = this.readConfig();

        this.init();
    }

    readConfig() {
        const dataset = this.root.dataset;
        return {
            enabled: dataset.enabled !== "false",
            morningStart: dataset.morningStart || "06:00",
            morningEnd: dataset.morningEnd || "09:00",
            eveningStart: dataset.eveningStart || "16:30",
            eveningEnd: dataset.eveningEnd || "18:30",
            refreshMinutes: Number(dataset.refreshMinutes) > 0 ? Number(dataset.refreshMinutes) : 5,
            alwaysVisible: dataset.alwaysVisible === "true"
        };
    }

    init() {
        if (!this.config.enabled) {
            this.setActiveState(false);
            this.setFooter("Commute tile disabled in config.");
            return;
        }

        this.visibilityInterval = setInterval(() => this.evaluateVisibility(), 60000);
        this.evaluateVisibility();

        if (window.htmx) {
            htmx.on("htmx:beforeSwap", (event) => {
                if (event.target === this.root || this.root.contains(event.target)) {
                    this.destroy();
                }
            });
        }

    }

    parseTimeToMinutes(value) {
        if (!value) return null;
        const [hours, minutes] = value.split(":").map(Number);
        if (Number.isNaN(hours) || Number.isNaN(minutes)) return null;
        return hours * 60 + minutes;
    }

    getScheduledWindow(now) {
        const dow = now.getDay();
        const isWeekday = dow !== 0 && dow !== 6;
        if (!isWeekday) return null;

        const currentMinutes = now.getHours() * 60 + now.getMinutes();
        const morningStart = this.parseTimeToMinutes(this.config.morningStart) ?? 360;
        const morningEnd = this.parseTimeToMinutes(this.config.morningEnd) ?? 540;
        const eveningStart = this.parseTimeToMinutes(this.config.eveningStart) ?? 990;
        const eveningEnd = this.parseTimeToMinutes(this.config.eveningEnd) ?? 1110;

        if (currentMinutes >= morningStart && currentMinutes <= morningEnd) {
            return { key: "morning", label: "Home -> Work", descriptor: "Morning commute" };
        }

        if (currentMinutes >= eveningStart && currentMinutes <= eveningEnd) {
            return { key: "evening", label: "Work -> Home", descriptor: "Evening commute" };
        }

        return null;
    }

    getDefaultWindow() {
        return { key: "morning", label: "Home -> Work", descriptor: "Commute" };
    }

    getActiveWindow(now) {
        const scheduled = this.getScheduledWindow(now);
        if (scheduled) return scheduled;
        if (this.config.alwaysVisible) {
            return this.currentWindow || this.getDefaultWindow();
        }
        return null;
    }

    evaluateVisibility() {
        const windowInfo = this.getActiveWindow(new Date());

        if (!windowInfo) {
            this.setActiveState(false);
            this.setFooter("Hidden outside commute windows.");
            this.stopRefresh();
            return;
        }

        this.setActiveState(true);
        this.currentWindow = windowInfo;
        if (this.windowEl) {
            this.windowEl.textContent = windowInfo.label;
        }
        this.fetchCommute(windowInfo);
        this.startRefresh(windowInfo);
    }

    setActiveState(isActive) {
        this.root.dataset.active = isActive ? "true" : "false";
        this.root.style.display = isActive ? "" : "none";
        this.root.setAttribute("aria-hidden", isActive ? "false" : "true");
    }

    setFooter(message) {
        if (this.footerEl) {
            this.footerEl.textContent = message;
        }
    }

    setEta(value) {
        if (this.etaEl) {
            this.etaEl.textContent = value;
        }
    }

    setDelta(value) {
        if (this.deltaEl) {
            this.deltaEl.textContent = value;
        }
    }

    setStatus(key, label) {
        if (this.statusEl) {
            this.statusEl.dataset.status = key;
            this.statusEl.textContent = label;
        }
        if (this.progressEl) {
            this.progressEl.dataset.status = key;
        }
    }

    applyStatus(key, label) {
        if (!this.statusState.current || key === this.statusState.current) {
            this.statusState.current = key;
            this.statusState.pending = null;
            this.statusState.pendingCount = 0;
            this.setStatus(key, label);
            return;
        }

        if (this.statusState.pending !== key) {
            this.statusState.pending = key;
            this.statusState.pendingCount = 1;
            return;
        }

        this.statusState.pendingCount += 1;
        if (this.statusState.pendingCount < 2) {
            return;
        }

        this.statusState.current = key;
        this.statusState.pending = null;
        this.statusState.pendingCount = 0;
        this.setStatus(key, label);
    }

    showIncident(text) {
        if (!this.incidentEl) return;
        if (!text) {
            this.incidentEl.hidden = true;
            this.incidentEl.textContent = "";
            return;
        }
        this.incidentEl.hidden = false;
        this.incidentEl.textContent = text;
    }

    cacheGeocode(address, coords) {
        this.geocodeCache[address] = coords;
        try {
            localStorage.setItem(`commute_geocode_${address}`, JSON.stringify(coords));
        } catch (err) {
            // Ignore storage errors
        }
    }

    readGeocodeCache(address) {
        if (this.geocodeCache[address]) {
            return this.geocodeCache[address];
        }
        try {
            const stored = localStorage.getItem(`commute_geocode_${address}`);
            if (stored) {
                const parsed = JSON.parse(stored);
                if (parsed && typeof parsed.lat === "number" && typeof parsed.lng === "number") {
                    this.geocodeCache[address] = parsed;
                    return parsed;
                }
            }
        } catch (err) {
            // Ignore storage errors
        }
        return null;
    }

    async geocodeMapbox(address) {
        const cached = this.readGeocodeCache(address);
        if (cached) return cached;

        const url = new URL(`https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(address)}.json`);
        url.searchParams.set("limit", "1");
        url.searchParams.set("access_token", this.config.mapboxToken);

        const response = await fetch(url.toString());
        if (!response.ok) {
            throw new Error(`Unable to geocode: ${address}`);
        }
        const data = await response.json();
        const feature = data.features && data.features[0];
        if (!feature || !feature.center) {
            throw new Error(`Unable to locate: ${address}`);
        }
        const [lng, lat] = feature.center;
        const coords = { lat, lng };
        this.cacheGeocode(address, coords);
        return coords;
    }

    classifyStatus(deltaMinutes) {
        if (deltaMinutes === null || typeof deltaMinutes !== "number") {
            return { key: "unknown", label: "Live" };
        }
        if (deltaMinutes <= -2) {
            return { key: "light", label: "Light" };
        }
        if (deltaMinutes <= 2) {
            return { key: "normal", label: "Normal" };
        }
        if (deltaMinutes <= 10) {
            return { key: "heavy", label: "Heavy" };
        }
        return { key: "severe", label: "Severe" };
    }

    formatTime(ts) {
        const locale = window.getPreferredLocale ? window.getPreferredLocale() : null;
        const locales = locale ? [locale] : [];
        return ts.toLocaleTimeString(locales, { hour: "numeric", minute: "2-digit" });
    }

    async fetchCommute(windowInfo) {
        try {
            const response = await fetch(`/api/commute?window=${encodeURIComponent(windowInfo.key)}`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || "Commute request failed.");

            const etaMinutes = data.eta_minutes;
            const typicalMinutes = data.typical_minutes;
            const deltaMinutes = (etaMinutes !== null && typicalMinutes !== null) ? etaMinutes - typicalMinutes : null;
            const statusInfo = this.classifyStatus(deltaMinutes);
            this.applyStatus(statusInfo.key, statusInfo.label);
            this.setDelta(deltaMinutes === null ? "Typical time unavailable" : (deltaMinutes <= 0 ? "Normal ETA" : `+${deltaMinutes} min vs typical`));
            this.setEta(etaMinutes !== null ? `${etaMinutes}` : "--");
            this.showIncident(data.has_incident ? "Incident reported" : "");
            const updatedAt = this.formatTime(new Date(data.updated_at));
            this.setFooter(`Updated ${updatedAt}`);
            this.cache = { etaMinutes, typicalMinutes, deltaMinutes, statusInfo, incidentText: data.has_incident ? "Incident reported" : "", updatedAt };
        } catch (err) {
            console.warn("[CommuteTile] Failed to refresh commute", err);
            if (this.cache) {
                this.setEta(this.cache.etaMinutes !== null ? `${this.cache.etaMinutes}` : "--");
                this.setDelta(this.cache.deltaMinutes === null ? "Typical time unavailable" : (this.cache.deltaMinutes <= 0 ? "Normal ETA" : `+${this.cache.deltaMinutes} min vs typical`));
                this.applyStatus(this.cache.statusInfo.key, this.cache.statusInfo.label);
                this.showIncident(this.cache.incidentText);
                this.setFooter(`Updated ${this.cache.updatedAt} (stale)`);
            } else {
                this.setDelta("Traffic unavailable.");
                this.applyStatus("offline", "Offline");
                this.setFooter("Unable to load commute data.");
            }
        }
    }

    getIncidentBadge(route) {
        const incidents = route.incidents || [];
        if (Array.isArray(incidents) && incidents.length > 0) {
            return "Incident reported";
        }

        const legs = route.legs || [];
        for (const leg of legs) {
            if (leg.incidents && leg.incidents.length > 0) {
                return "Incident reported";
            }
            const closure = leg.annotation && leg.annotation.closure;
            if (Array.isArray(closure) && closure.some(value => Number(value) > 0)) {
                return "Closure reported";
            }
        }

        return "";
    }

    startRefresh(windowInfo) {
        this.stopRefresh();
        const minutes = Math.max(1, this.config.refreshMinutes);
        this.refreshInterval = setInterval(() => {
            const activeWindow = this.getActiveWindow(new Date());
            if (!activeWindow) {
                this.evaluateVisibility();
                return;
            }
            if (windowInfo.key !== activeWindow.key) {
                this.evaluateVisibility();
                return;
            }
            this.fetchCommute(activeWindow);
        }, minutes * 60 * 1000);
    }

    stopRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    destroy() {
        this.stopRefresh();
        if (this.visibilityInterval) {
            clearInterval(this.visibilityInterval);
            this.visibilityInterval = null;
        }
    }
}

function bootCommuteTile(target) {
    if (!target || !target.querySelector) return;
    const commuteEl = target.id === "commute-tile"
        ? target
        : target.querySelector("#commute-tile");

    if (!commuteEl) return;

    if (commuteEl.__commuteInstance) {
        commuteEl.__commuteInstance.destroy();
    }

    const instance = new CommuteTile(commuteEl);
    commuteEl.__commuteInstance = instance;
}

document.addEventListener("DOMContentLoaded", () => {
    bootCommuteTile(document);
});

document.addEventListener("htmx:load", (event) => {
    bootCommuteTile(event.target);
});
