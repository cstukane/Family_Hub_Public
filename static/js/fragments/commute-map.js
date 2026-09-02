// Commute Map widget with time-based rendering and live traffic routing
console.info("[CommuteMap] File parsed");

const COMMUTE_DARK_STYLE = [
    { elementType: "geometry", stylers: [{ color: "#1d2c4d" }] },
    { elementType: "labels.text.fill", stylers: [{ color: "#8ec3b9" }] },
    { elementType: "labels.text.stroke", stylers: [{ color: "#1a3646" }] },
    { featureType: "administrative.country", elementType: "geometry.stroke", stylers: [{ color: "#4b6878" }] },
    { featureType: "administrative.land_parcel", stylers: [{ visibility: "off" }] },
    { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#c4d2ff" }] },
    { featureType: "administrative.neighborhood", stylers: [{ visibility: "off" }] },
    { featureType: "poi", elementType: "labels.text.fill", stylers: [{ color: "#8ab4f8" }] },
    { featureType: "poi.park", elementType: "geometry", stylers: [{ color: "#263c3f" }] },
    { featureType: "poi.park", elementType: "labels.text.fill", stylers: [{ color: "#6b9a76" }] },
    { featureType: "road", elementType: "geometry", stylers: [{ color: "#304a7d" }] },
    { featureType: "road", elementType: "labels.icon", stylers: [{ visibility: "off" }] },
    { featureType: "road.arterial", elementType: "geometry", stylers: [{ color: "#3a4b6f" }] },
    { featureType: "road.highway", elementType: "geometry", stylers: [{ color: "#2b3f66" }] },
    { featureType: "road.highway", elementType: "geometry.stroke", stylers: [{ color: "#255763" }] },
    { featureType: "transit", elementType: "labels.text.fill", stylers: [{ color: "#98a5be" }] },
    { featureType: "water", elementType: "geometry", stylers: [{ color: "#0b1224" }] },
    { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#4e6d70" }] }
];

let googleMapsLoaderPromise = null;
let mapboxLoaderPromise = null;
let mapboxCssLoaded = false;

class CommuteMapWidget {
    constructor(rootElement) {
        console.info("[CommuteMap] Script loaded, initializing widget");
        this.root = rootElement;
        this.mapCanvas = rootElement.querySelector('[data-role="map-canvas"]');
        this.statusEl = rootElement.querySelector('[data-role="commute-status"]');
        this.directionEl = rootElement.querySelector('[data-role="commute-direction"]');
        this.geocodeCache = {};
        this.map = null;
        this.trafficLayer = null;
        this.directionsService = null;
        this.directionsRenderer = null;
        this.geocoder = null;
        this.mapboxMap = null;
        this.mapboxTrafficAdded = false;
        this.mapboxToken = null;
        this.visibilityInterval = null;
        this.refreshInterval = null;
        this.currentWindow = null;
        this.config = this.readConfig();

        this.init();
    }

    readConfig() {
        const dataset = this.root.dataset;
        return {
            enabled: dataset.enabled !== "false",
            provider: (dataset.provider || "google").toLowerCase(),
            googleApiKey: dataset.googleApiKey || "",
            mapboxToken: dataset.mapboxToken || "",
            homeAddress: (dataset.homeAddress || "").trim(),
            workAddress: (dataset.workAddress || "").trim(),
            morningStart: dataset.morningStart || "06:00",
            morningEnd: dataset.morningEnd || "09:00",
            eveningStart: dataset.eveningStart || "16:30",
            eveningEnd: dataset.eveningEnd || "18:30",
            refreshMinutes: Number(dataset.refreshMinutes) > 0 ? Number(dataset.refreshMinutes) : 2
        };
    }

    init() {
        if (!this.config.enabled) {
            this.setActiveState(false);
            this.setStatus("Commute map disabled in config.");
            console.info("[CommuteMap] Disabled via config");
            return;
        }

        this.visibilityInterval = setInterval(() => this.evaluateVisibility(), 60000);
        console.info("[CommuteMap] Initial evaluateVisibility", {
            provider: this.config.provider,
            morningStart: this.config.morningStart,
            morningEnd: this.config.morningEnd,
            eveningStart: this.config.eveningStart,
            eveningEnd: this.config.eveningEnd
        });
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

    getActiveWindow(now) {
        const dow = now.getDay(); // 0 = Sunday, 6 = Saturday
        const isWeekday = dow !== 0 && dow !== 6;
        if (!isWeekday) return null;

        const currentMinutes = now.getHours() * 60 + now.getMinutes();
        const morningStart = this.parseTimeToMinutes(this.config.morningStart) ?? 360;
        const morningEnd = this.parseTimeToMinutes(this.config.morningEnd) ?? 540;
        const eveningStart = this.parseTimeToMinutes(this.config.eveningStart) ?? 990;
        const eveningEnd = this.parseTimeToMinutes(this.config.eveningEnd) ?? 1110;

        if (currentMinutes >= morningStart && currentMinutes <= morningEnd) {
            return { key: "morning", label: "Home → Work", descriptor: "Morning commute" };
        }

        if (currentMinutes >= eveningStart && currentMinutes <= eveningEnd) {
            return { key: "evening", label: "Work → Home", descriptor: "Evening commute" };
        }

        return null;
    }

    evaluateVisibility() {
        const windowInfo = this.getActiveWindow(new Date());

        if (!windowInfo) {
            this.setActiveState(false);
            const now = new Date();
            const locale = window.getPreferredLocale ? window.getPreferredLocale() : null;
            const locales = locale ? [locale] : [];
            const timeStr = now.toLocaleTimeString(locales, { hour: "2-digit", minute: "2-digit" });
            const dayStr = now.toLocaleDateString(locales, { weekday: "long" });
            this.setStatus(`Hidden (outside weekday windows) • ${dayStr} ${timeStr}`);
            console.info("[CommuteMap] Hidden - outside configured windows", {
                now: now.toString(),
                day: now.getDay(),
                morning: { start: this.config.morningStart, end: this.config.morningEnd },
                evening: { start: this.config.eveningStart, end: this.config.eveningEnd }
            });
            this.directionEl.textContent = "Hidden until commute hours";
            this.stopRefresh();
            this.teardownMap();
            this.currentWindow = null;
            return;
        }

        this.currentWindow = windowInfo.key;
        this.setActiveState(true);
        this.directionEl.textContent = `${windowInfo.descriptor} (${windowInfo.label})`;
        this.setStatus("Loading live traffic…");
        console.info("[CommuteMap] Showing window", {
            window: windowInfo.key,
            now: new Date().toString(),
            day: new Date().getDay(),
            morning: { start: this.config.morningStart, end: this.config.morningEnd },
            evening: { start: this.config.eveningStart, end: this.config.eveningEnd }
        });
        this.renderRoute(windowInfo);
        this.startRefresh(windowInfo);
    }

    setActiveState(isActive) {
        this.root.dataset.active = isActive ? "true" : "false";
        this.root.style.display = isActive ? "" : "none";
        this.root.setAttribute("aria-hidden", isActive ? "false" : "true");
    }

    setStatus(message) {
        if (this.statusEl) {
            this.statusEl.textContent = message;
        }
    }

    async renderRoute(windowInfo) {
        if (!this.config.homeAddress || !this.config.workAddress) {
            this.setStatus("Set Home and Work addresses in config.commute to enable routing.");
            return;
        }

        try {
            if (this.config.provider === "mapbox") {
                if (!this.config.mapboxToken) {
                    throw new Error("Add a Mapbox token to config.commute.mapbox_token.");
                }
                await this.ensureMapboxMap();
                await this.drawDirectionsMapbox(windowInfo);
            } else {
                await this.ensureGoogleMap();
                await this.drawDirectionsGoogle(windowInfo);
            }
        } catch (err) {
            console.warn("Commute map failed to render route:", err);
            this.setStatus(err.message || "Unable to load commute route right now.");
        }
    }

    async ensureGoogleMap() {
        await this.loadGoogleSdk();

        if (this.map) {
            if (this.trafficLayer) this.trafficLayer.setMap(this.map);
            if (this.directionsRenderer) this.directionsRenderer.setMap(this.map);
            return;
        }

        if (!window.google || !google.maps) {
            throw new Error("Google Maps SDK failed to load.");
        }

        this.map = new google.maps.Map(this.mapCanvas, {
            center: { lat: 40.0, lng: -95.0 },
            zoom: 4,
            disableDefaultUI: true,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false,
            backgroundColor: "#0b1224",
            styles: COMMUTE_DARK_STYLE
        });

        this.trafficLayer = new google.maps.TrafficLayer();
        this.trafficLayer.setMap(this.map);

        this.directionsService = new google.maps.DirectionsService();
        this.directionsRenderer = new google.maps.DirectionsRenderer({
            suppressMarkers: false,
            preserveViewport: false,
            polylineOptions: {
                strokeColor: "#22d3ee",
                strokeOpacity: 0.9,
                strokeWeight: 6
            }
        });
        this.directionsRenderer.setMap(this.map);

        this.geocoder = new google.maps.Geocoder();
    }

    loadGoogleSdk() {
        if (window.google && window.google.maps) {
            return Promise.resolve();
        }

        if (googleMapsLoaderPromise) {
            return googleMapsLoaderPromise;
        }

        if (!this.config.googleApiKey) {
            return Promise.reject(new Error("Add a Google Maps JavaScript API key to config.commute.google_api_key."));
        }

        googleMapsLoaderPromise = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = `https://maps.googleapis.com/maps/api/js?key=${this.config.googleApiKey}&libraries=geometry&loading=async`;
            script.async = true;
            script.defer = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Failed to load Google Maps SDK."));
            document.head.appendChild(script);
        });

        return googleMapsLoaderPromise;
    }

    async ensureMapboxMap() {
        await this.loadMapboxSdk();

        if (this.mapboxMap) {
            return this.waitForMapboxLoad();
        }

        if (!window.mapboxgl) {
            throw new Error("Mapbox GL JS failed to load.");
        }

        mapboxgl.accessToken = this.config.mapboxToken;
        this.mapboxMap = new mapboxgl.Map({
            container: this.mapCanvas,
            accessToken: this.config.mapboxToken,
            style: "mapbox://styles/mapbox/dark-v11",
            center: [-95, 40],
            zoom: 3,
            attributionControl: false,
            dragRotate: false,
            touchPitch: false
        });

        this.mapboxMap.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-right");

        this.mapboxMap.on("load", () => {
            if (this.mapboxTrafficAdded) return;
            this.mapboxMap.addSource("traffic", {
                type: "vector",
                url: "mapbox://mapbox.mapbox-traffic-v1"
            });
            this.mapboxMap.addLayer({
                id: "traffic",
                type: "line",
                source: "traffic",
                "source-layer": "traffic",
                layout: { "line-cap": "round", "line-join": "round" },
                paint: {
                    "line-width": [
                        "interpolate",
                        ["linear"], ["zoom"],
                        5, 1.5,
                        10, 3,
                        14, 5,
                        18, 8
                    ],
                    "line-color": [
                        "match",
                        ["get", "congestion"],
                        "low", "#22c55e",
                        "moderate", "#fbbf24",
                        "heavy", "#f97316",
                        "severe", "#ef4444",
                        "#4b5563"
                    ],
                    "line-opacity": 0.9
                }
            });
            this.mapboxTrafficAdded = true;
        });

        return this.waitForMapboxLoad();
    }

    loadMapboxSdk() {
        if (window.mapboxgl && typeof window.mapboxgl === "object") {
            return Promise.resolve();
        }

        if (mapboxLoaderPromise) {
            return mapboxLoaderPromise;
        }

        if (!this.config.mapboxToken) {
            return Promise.reject(new Error("Add a Mapbox token to config.commute.mapbox_token."));
        }

        if (!mapboxCssLoaded) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = "https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.css";
            document.head.appendChild(link);
            mapboxCssLoaded = true;
        }

        mapboxLoaderPromise = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://api.mapbox.com/mapbox-gl-js/v2.15.0/mapbox-gl.js";
            script.async = true;
            script.defer = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error("Failed to load Mapbox GL JS."));
            document.head.appendChild(script);
        });

        return mapboxLoaderPromise;
    }

    waitForMapboxLoad() {
        if (this.mapboxMap && this.mapboxMap.isStyleLoaded()) {
            return Promise.resolve();
        }
        return new Promise((resolve) => {
            if (!this.mapboxMap) {
                resolve();
                return;
            }
            this.mapboxMap.once("load", () => resolve());
        });
    }

    async drawDirectionsGoogle(windowInfo) {
        if (!this.directionsService || !this.directionsRenderer || !this.geocoder) return;

        const originAddress = windowInfo.key === "morning" ? this.config.homeAddress : this.config.workAddress;
        const destinationAddress = windowInfo.key === "morning" ? this.config.workAddress : this.config.homeAddress;

        const [origin, destination] = await Promise.all([
            this.geocodeGoogle(originAddress),
            this.geocodeGoogle(destinationAddress)
        ]);

        const request = {
            origin,
            destination,
            travelMode: google.maps.TravelMode.DRIVING,
            drivingOptions: {
                departureTime: new Date(),
                trafficModel: google.maps.TrafficModel.BEST_GUESS
            },
            provideRouteAlternatives: false
        };

        const directions = await new Promise((resolve, reject) => {
            this.directionsService.route(request, (result, status) => {
                if (status === google.maps.DirectionsStatus.OK && result) {
                    resolve(result);
                } else {
                    reject(new Error("Could not fetch live directions for this route."));
                }
            });
        });

        this.directionsRenderer.setDirections(directions);
        this.fitToRouteGoogle(directions);

        const leg = directions.routes?.[0]?.legs?.[0];
        const eta = leg?.duration_in_traffic?.text || leg?.duration?.text;
        const distance = leg?.distance?.text;

        const statusParts = [
            windowInfo.descriptor,
            windowInfo.label,
            eta ? `ETA ${eta}` : null,
            distance ? distance : null
        ].filter(Boolean);

        this.setStatus(statusParts.join(" • "));
    }

    async drawDirectionsMapbox(windowInfo) {
        const originAddress = windowInfo.key === "morning" ? this.config.homeAddress : this.config.workAddress;
        const destinationAddress = windowInfo.key === "morning" ? this.config.workAddress : this.config.homeAddress;

        const [origin, destination] = await Promise.all([
            this.geocodeMapbox(originAddress),
            this.geocodeMapbox(destinationAddress)
        ]);

        const directionsUrl = new URL(`https://api.mapbox.com/directions/v5/mapbox/driving-traffic/${origin.lng},${origin.lat};${destination.lng},${destination.lat}`);
        directionsUrl.searchParams.set("geometries", "geojson");
        directionsUrl.searchParams.set("overview", "full");
        directionsUrl.searchParams.set("alternatives", "false");
        directionsUrl.searchParams.set("annotations", "duration,distance");
        directionsUrl.searchParams.set("access_token", this.config.mapboxToken);

        const response = await fetch(directionsUrl.toString());
        if (!response.ok) {
            throw new Error("Could not fetch live directions for this route.");
        }
        const data = await response.json();
        if (!data.routes || !data.routes[0]) {
            throw new Error("No route found between Home and Work.");
        }

        const route = data.routes[0];
        const coords = route.geometry.coordinates;
        const bounds = coords.reduce((b, coord) => b.extend(coord), new mapboxgl.LngLatBounds(coords[0], coords[0]));

        if (!this.mapboxMap.getSource("commute-route")) {
            this.mapboxMap.addSource("commute-route", {
                type: "geojson",
                data: {
                    type: "Feature",
                    geometry: {
                        type: "LineString",
                        coordinates: coords
                    }
                }
            });
            this.mapboxMap.addLayer({
                id: "commute-route-line",
                type: "line",
                source: "commute-route",
                layout: {
                    "line-cap": "round",
                    "line-join": "round"
                },
                paint: {
                    "line-width": 6,
                    "line-color": "#22d3ee",
                    "line-opacity": 0.9
                }
            });
        } else {
            const source = this.mapboxMap.getSource("commute-route");
            if (source) {
                source.setData({
                    type: "Feature",
                    geometry: {
                        type: "LineString",
                        coordinates: coords
                    }
                });
            }
        }

        this.mapboxMap.fitBounds(bounds, { padding: 40, maxZoom: 14 });

        const etaMinutes = route.duration ? Math.round(route.duration / 60) : null;
        const distanceMiles = route.distance ? (route.distance / 1609.34).toFixed(1) : null;
        const statusParts = [
            windowInfo.descriptor,
            windowInfo.label,
            etaMinutes !== null ? `ETA ~${etaMinutes} min` : null,
            distanceMiles ? `${distanceMiles} mi` : null
        ].filter(Boolean);
        this.setStatus(statusParts.join(" • "));
    }

    fitToRouteGoogle(directions) {
        const bounds = directions.routes?.[0]?.bounds;
        if (bounds && this.map) {
            this.map.fitBounds(bounds, 40);
        }
    }

    geocodeGoogle(address) {
        if (this.geocodeCache[address]) {
            return Promise.resolve(this.geocodeCache[address]);
        }

        return new Promise((resolve, reject) => {
            this.geocoder.geocode({ address }, (results, status) => {
                if (status === google.maps.GeocoderStatus.OK && results[0]) {
                    const location = results[0].geometry.location;
                    const latLng = { lat: location.lat(), lng: location.lng() };
                    this.geocodeCache[address] = latLng;
                    resolve(latLng);
                } else {
                    reject(new Error(`Unable to locate: ${address}`));
                }
            });
        });
    }

    async geocodeMapbox(address) {
        if (this.geocodeCache[address]) {
            return this.geocodeCache[address];
        }
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
        const latLng = { lat, lng };
        this.geocodeCache[address] = latLng;
        return latLng;
    }

    startRefresh(windowInfo) {
        this.stopRefresh();
        const minutes = Math.max(1, this.config.refreshMinutes);
        this.refreshInterval = setInterval(() => {
            // Only refresh if the widget is currently visible and the window hasn't changed
            if (this.root.dataset.active === "true") {
                const activeWindow = this.getActiveWindow(new Date());
                if (activeWindow && activeWindow.key === this.currentWindow) {
                    this.renderRoute(activeWindow);
                } else {
                    this.evaluateVisibility();
                }
            }
        }, minutes * 60 * 1000);
    }

    stopRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    teardownMap() {
        if (this.trafficLayer) {
            this.trafficLayer.setMap(null);
        }
        if (this.directionsRenderer) {
            this.directionsRenderer.setMap(null);
        }
        if (this.mapboxMap) {
            this.mapboxMap.remove();
        }
        this.map = null;
        this.trafficLayer = null;
        this.directionsService = null;
        this.directionsRenderer = null;
        this.geocoder = null;
        this.mapboxMap = null;
        this.mapboxTrafficAdded = false;

        if (this.mapCanvas) {
            this.mapCanvas.innerHTML = "";
        }
    }

    destroy() {
        this.stopRefresh();
        if (this.visibilityInterval) {
            clearInterval(this.visibilityInterval);
        }
        this.teardownMap();
    }
}

function bootCommuteWidget(target) {
    if (!target || !target.querySelector) return;
    const commuteEl = target.id === "commute-map-panel"
        ? target
        : target.querySelector("#commute-map-panel");

    if (!commuteEl) return;

    if (commuteEl.__commuteInstance) {
        commuteEl.__commuteInstance.destroy();
    }

    console.info("[CommuteMap] Boot widget", {
        provider: commuteEl.dataset.provider,
        morningStart: commuteEl.dataset.morningStart,
        morningEnd: commuteEl.dataset.morningEnd,
        eveningStart: commuteEl.dataset.eveningStart,
        eveningEnd: commuteEl.dataset.eveningEnd,
        enabled: commuteEl.dataset.enabled
    });

    const instance = new CommuteMapWidget(commuteEl);
    commuteEl.__commuteInstance = instance;
}

document.addEventListener("DOMContentLoaded", () => {
    console.info("[CommuteMap] DOMContentLoaded");
    bootCommuteWidget(document);
});

if (window.htmx) {
    htmx.onLoad((target) => {
        console.info("[CommuteMap] htmx onLoad");
        bootCommuteWidget(target);
    });
}

