## Phase 0  Safety + Snapshot

* [ ] **Make a copy** of `miniplayer.html` (e.g., `miniplayer_backup.html`) so you can diff or roll back.
* [ ] **Open the original** `miniplayer.html` side-by-side with the backup in your editor.

---

## Phase 1  Restructure the HTML

### 1.1 Keep the top row as-is

* [ ] In `.miniplayer-content`, **leave** the existing `div.miniplayer-main-row` alone:

  * Album art container
  * Track title + artist text

That already matches what you want visually, so no structural change is needed there.

---

### 1.2 Insert a progress row (middle)

Right after `</div><!-- .miniplayer-main-row -->`, add:

```html
<div class="miniplayer-progress-row">
    <span id="miniplayer-current-time" class="miniplayer-time">0:00</span>
    <input
        type="range"
        id="miniplayer-seek"
        class="miniplayer-seek"
        min="0"
        max="100"
        value="0"
        step="1"
        aria-label="Seek through track"
    >
    <span id="miniplayer-duration" class="miniplayer-time">0:00</span>
</div>
```

Checklist:

* [ ] Add this block directly after `.miniplayer-main-row`.
* [ ] Confirm IDs: `miniplayer-current-time`, `miniplayer-seek`, `miniplayer-duration`.

(These can stay dumb for now; theyll just sit there until you wire them.)

---

### 1.3 Replace the old controls block with a new bottom row

Right now you have a standalone:

```html
<div class="miniplayer-controls">
    <!-- prev / play / pause / next / like -->
</div>
```

Youre going to **wrap and rearrange** that into a new bottom row with five zones:

1. **Far left**  service indicator
2. **Second left**  cast icon
3. **Center**  prev / play-pause / next
4. **Second right**  playlists icon
5. **Far right**  queue icon

Do this:

* [ ] Remove the old top-level `div.miniplayer-controls` (but **keep the buttons**).
* [ ] In its place, insert:

```html
<div class="miniplayer-bottom-row">
    <!-- Far left + second left -->
    <div class="miniplayer-left-rail">
        <!-- Service indicator (far left) -->
        <div id="miniplayer-service-tray"
             class="miniplayer-service-tray"
             aria-label="Current media source">
            <!-- For now, just a single placeholder button -->
            <button class="service-icon is-active" data-service="spotify" title="Spotify">
                SP
            </button>
        </div>

        <!-- Cast icon (second left) -->
        <button id="miniplayer-cast-btn"
                class="miniplayer-icon-btn"
                title="Cast to device"
                aria-label="Cast to device">
            
        </button>
    </div>

    <!-- Center: transport controls -->
    <div class="miniplayer-center-rail">
        <div class="miniplayer-controls">
            <button id="miniplayer-prev-btn" class="miniplayer-btn" title="Previous Track" aria-label="Previous Track">
                
            </button>
            <button id="miniplayer-play-btn" class="miniplayer-btn" title="Play" aria-label="Play">
                
            </button>
            <button id="miniplayer-pause-btn" class="miniplayer-btn" style="display: none;" title="Pause" aria-label="Pause">
                
            </button>
            <button id="miniplayer-next-btn" class="miniplayer-btn" title="Next Track" aria-label="Next Track">
                
            </button>
        </div>
    </div>

    <!-- Second right + far right -->
    <div class="miniplayer-right-rail">
        <!-- Playlists icon (second right) -->
        <button id="miniplayer-playlists-toggle-btn"
                class="miniplayer-icon-btn"
                title="Show playlists"
                aria-label="Show playlists">
            
        </button>

        <!-- Queue icon (far right) -->
        <button id="miniplayer-queue-btn"
                class="miniplayer-icon-btn"
                title="Show queue"
                aria-label="Show queue">
            
        </button>
    </div>
</div>
```

Checklist:

* [ ] Ensure `prev / play / pause / next` keep their **existing IDs** so any current JS keeps working.
* [ ] New IDs introduced: `miniplayer-service-tray`, `miniplayer-cast-btn`, `miniplayer-playlists-toggle-btn`, `miniplayer-queue-btn`.
* [ ] The like button can be re-added into the center rail if you still want it; otherwise leave it out for now.

---

### 1.4 Keep Spotify playlists + auth where they are (for now)

For this pass:

* [ ] Leave `#spotify-playlists-section` and `#miniplayer-spotify-auth` **in the DOM**, below the new bottom row.
* [ ] Remove any inline `style="display: none;"` from `#spotify-playlists-section`; visibility will be handled via CSS/class in a later phase.

---

## Phase 2  Basic layout CSS (rows & rails)

In your stylesheet (or a `<style>` block) add/adjust rules to get the macOS-style layout.

### 2.1 Overall column layout

* [ ] Ensure `.miniplayer-content` is column-oriented:

```css
.miniplayer-content {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}
```

---

### 2.2 Top row (already close)

* [ ] If not already, make `.miniplayer-main-row` flex:

```css
.miniplayer-main-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
```

---

### 2.3 Progress row

* [ ] Add:

```css
.miniplayer-progress-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.8rem;
    opacity: 0.9;
}

.miniplayer-seek {
    flex: 1;
}

.miniplayer-time {
    min-width: 2.5rem;
    text-align: center;
}
```

This gives you a thin bar with time labels on each side, like the screenshots.

---

### 2.4 Bottom row + rails

* [ ] Add:

```css
.miniplayer-bottom-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.miniplayer-left-rail,
.miniplayer-center-rail,
.miniplayer-right-rail {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
```

* [ ] Ensure the controls stay tight in the center:

```css
.miniplayer-center-rail .miniplayer-controls {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}
```

---

### 2.5 Service tray + icon buttons

* [ ] Style the service indicator and generic small icon buttons:

```css
.miniplayer-service-tray {
    display: flex;
    align-items: center;
    gap: 0.25rem;
}

.service-icon {
    border: none;
    border-radius: 4px;
    padding: 0.15rem 0.35rem;
    font-size: 0.65rem;
    opacity: 0.6;
    cursor: default;
}

.service-icon.is-active {
    opacity: 1;
    font-weight: 600;
}

.miniplayer-icon-btn {
    border: none;
    background: transparent;
    padding: 0.2rem;
    cursor: pointer;
    font-size: 0.9rem;
}
```

* [ ] Confirm that all five bottom items appear in a straight line in the order you want:

  * Service  Cast  [controls centered]  Playlists  Queue.

---

## Phase 3  Playlists dropdown as a popover

This phase is just UI; no Spotify calls yet, just showing/hiding the panel.

### 3.1 Position the playlists panel

* [ ] Add CSS to anchor `#spotify-playlists-section` to the right-rail:

```css
.miniplayer-right-rail {
    position: relative;
}

#spotify-playlists-section {
    position: absolute;
    bottom: 120%;      /* appear above the icons */
    right: 0;
    min-width: 220px;
    padding: 0.5rem;
    border-radius: 8px;
    background: rgba(20, 20, 20, 0.95);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
    display: none;
    z-index: 20;
}

#spotify-playlists-section.is-open {
    display: block;
}
```

### 3.2 Add minimal JS toggle

* [ ] In your JS file where you handle the miniplayer, add:

```js
const playlistsToggleBtn = document.getElementById('miniplayer-playlists-toggle-btn');
const playlistsSection   = document.getElementById('spotify-playlists-section');

if (playlistsToggleBtn && playlistsSection) {
    playlistsToggleBtn.addEventListener('click', () => {
        playlistsSection.classList.toggle('is-open');
    });
}
```

* [ ] Confirm clicking the playlists icon shows/hides the dropdown panel.

(Youre not changing how the `<select>` or Shuffle Play work; this is strictly visibility.)

---

## Phase 4  New button stubs (no backend yet)

This is just to make sure nothing explodes when you click the new icons.

* [ ] In your JS, after the playlists toggle, add:

```js
const castBtn   = document.getElementById('miniplayer-cast-btn');
const queueBtn  = document.getElementById('miniplayer-queue-btn');

if (castBtn) {
    castBtn.addEventListener('click', () => {
        console.log('[Miniplayer] Cast button clicked');
        // Later: hook into your existing "open cast devices" UI
    });
}

if (queueBtn) {
    queueBtn.addEventListener('click', () => {
        console.log('[Miniplayer] Queue button clicked');
        // Later: open a queue panel or call Spotify queue API
    });
}
```

* [ ] Click each of:

  * Service indicator (no JS; just visual for now).
  * Cast icon.
  * Playlists icon.
  * Queue icon.

and verify:

* Nothing throws errors in the console.
* Playlists popover opens/closes.
* Cast/Queue log messages appear.

---

## Phase 5  Optional integration wiring (later)

When youre ready to go beyond UI:

* [ ] **Service indicator**: update `miniplayer-service-tray` dynamically from your now playing source (Spotify / Amazon / etc.), toggling `.is-active` and/or showing only one button.
* [ ] **Cast icon**: call your existing device-discovery / casting UI from the cast button handler.
* [ ] **Queue icon**: either open a queue overlay and populate it from Spotifys queue endpoint, or show a Not available message if the API doesnt give you what you want.
* [ ] **Progress bar**: wire `miniplayer-current-time`, `miniplayer-duration`, and `miniplayer-seek` to your playback state and seek function.