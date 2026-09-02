// Client-side SocketIO handling for live updates
let socket = null;
let socketConnected = false;

// Function to initialize SocketIO connection
function initSocket() {
    // Check if SocketIO is available
    if (typeof io !== 'undefined') {
        // Prefer websocket transport and fall back to polling when needed.
        socket = io({
            transports: ['websocket', 'polling'],
            upgrade: true,
            rememberUpgrade: true,
            reconnection: true,
            reconnectionDelay: 3000,
            reconnectionDelayMax: 10000,
            timeout: 20000
        });
        
        // Handle connection events
        socket.on('connect', function() {
            console.log('Connected to SocketIO server');
            socketConnected = true;
            
            // Join relevant rooms
            socket.emit('join_room', {room: 'timers'});
            socket.emit('join_room', {room: 'upcoming_events'});
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from SocketIO server');
            socketConnected = false;
        });
        
        // Handle timer updates
        socket.on('timer_update', function(data) {
            updateTimersDisplay(data.timers);
        });
        
        // Handle upcoming events updates
        socket.on('upcoming_events_update', function(data) {
            updateUpcomingEventsDisplay(data.events);
        });
        
        // Handle timer creation
        socket.on('timer_created', function(data) {
            console.log('New timer created:', data.timer);
            // Request a full update to refresh the display
            requestTimerUpdate();
        });
        
        // Handle timer deletion
        socket.on('timer_deleted', function(data) {
            console.log('Timer deleted:', data.id);
            // Request a full update to refresh the display
            requestTimerUpdate();
        });
        
        // Handle errors
        socket.on('error', function(data) {
            console.error('Socket error:', data.msg);
        });
    } else {
        console.log('SocketIO not available, falling back to HTMX polling');
        // If SocketIO is not available, we'll rely on HTMX polling
        socketConnected = false;
    }
}

// Function to update timers display with live data
function updateTimersDisplay(timers) {
    if (!timers || timers.length === 0) {
        // If no timers, hide the floating timer
        hideFloatingTimer();
        return; // No timers to update
    }
    
    // Update each timer element with new time remaining
    timers.forEach(timer => {
        // Check both regular and modal timer elements
        const timerElement = document.querySelector(`#timer-${timer.id}`) || 
                            document.querySelector(`#timer-modal-${timer.id}`);
        if (timerElement) {
            // Update the countdown display
            const countdownElement = timerElement.querySelector('.timer-countdown');
            if (countdownElement && timer.time_remaining !== null) {
                const minutes = Math.floor(timer.time_remaining / 60);
                const seconds = timer.time_remaining % 60;
                countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                
                // Check if timer has reached 0 and needs special handling
                if (timer.time_remaining <= 0) {
                    // Add visual feedback (flashing)
                    countdownElement.style.animation = 'pulse 1s infinite';
                    
                    // Play sound effect
                    playTimerCompleteSound();
                    
                    // Add CSS for visual feedback
                    const timerLabelElement = timerElement.querySelector('.timer-label');
                    if (timerLabelElement) {
                        timerLabelElement.style.fontWeight = 'bold';
                        timerLabelElement.style.color = 'var(--error-color)';
                    }
                }
            }
        }
    });
    
    // Update the floating timer list with active timers
    renderFloatingTimers(timers);
}

function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
}

// Render the floating timer list sorted from closest to longest
function renderFloatingTimers(timers) {
    const floatingTimer = document.getElementById('floating-timer');
    const listElement = document.getElementById('floating-timer-list');

    if (!floatingTimer || !listElement) {
        return;
    }

    const activeTimers = (timers || [])
        .filter(timer => typeof timer.time_remaining === 'number' && timer.time_remaining > 0)
        .sort((a, b) => a.time_remaining - b.time_remaining);

    if (activeTimers.length === 0) {
        hideFloatingTimer();
        return;
    }

    const itemsHtml = activeTimers.map(timer => {
        const remaining = Math.max(0, timer.time_remaining || 0);
        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        const timeString = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        const label = escapeHtml(timer.label || 'Timer');
        const warningClass = remaining <= 10 ? ' warning' : '';
        return `<li>
            <button type="button" class="floating-timer-item${warningClass}"
                onclick="if (window.loadAndShowModal) { loadAndShowModal('/partials/timers-modal'); }">
                <span class="floating-timer-label">${label}</span>
                <span class="floating-timer-time">${timeString}</span>
            </button>
        </li>`;
    });

    listElement.innerHTML = itemsHtml.join('');
    floatingTimer.style.display = 'block';
}

// Function to update the floating timer with the closest timer
function updateFloatingTimer(timers) {
    renderFloatingTimers(timers);
}

// Function to show the floating timer
function showFloatingTimer(timer) {
    if (!timer) {
        hideFloatingTimer();
        return;
    }
    renderFloatingTimers([timer]);
}

// Function to hide the floating timer
function hideFloatingTimer() {
    const floatingTimer = document.getElementById('floating-timer');
    if (floatingTimer) {
        const listElement = document.getElementById('floating-timer-list');
        if (listElement) {
            listElement.innerHTML = '';
        }
        floatingTimer.style.display = 'none';
    }
}

// Function to play timer completion sound
function playTimerCompleteSound() {
    // Create a simple beep sound using Web Audio API
    if (typeof AudioContext !== 'undefined' || typeof webkitAudioContext !== 'undefined') {
        const audioCtx = new (AudioContext || webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        
        oscillator.type = 'sine';
        oscillator.frequency.value = 800;
        gainNode.gain.value = 0.3;
        
        oscillator.start();
        setTimeout(() => {
            oscillator.stop();
        }, 500);
    } else {
        // Fallback: use a system alert (not ideal but better than nothing)
        console.log("Timer completed!");
    }
}

// Function to update upcoming events display with live data
function updateUpcomingEventsDisplay(events) {
    // Since the upcoming events are typically in a partial that gets updated via HTMX,
    // we would need to trigger an HTMX request to refresh the partial content
    // but only when there's a significant change
    const upcomingEventsPartial = document.querySelector('#upcoming-events-container');
    if (upcomingEventsPartial) {
        // Only update if the content has changed significantly
        // For now, we'll rely on the existing HTMX polling which will be overridden
        // when the partial gets updated from the server via socket
    }
    
    // Trigger refresh of the upcoming events partial via HTMX
    const upcomingEventsDiv = document.querySelector('[hx-get*="/partials/calendar/upnext"]');
    if (upcomingEventsDiv && !socketConnected) {
        // Only refresh via HTMX if socket is not connected (fallback mode)
        htmx.trigger(upcomingEventsDiv, 'every 30s');  // This won't work as expected
    }
}

// Function to request a timer update from the server
function requestTimerUpdate() {
    if (socket && socketConnected) {
        socket.emit('request_timer_update');
    }
}

// Function to request an upcoming events update from the server
function requestUpcomingEventsUpdate() {
    if (socket && socketConnected) {
        socket.emit('request_upcoming_events_update');
    }
}

// Function to create a timer via SocketIO
function createTimerSocket(label, seconds) {
    if (socket && socketConnected) {
        socket.emit('create_timer', {label: label, seconds: seconds});
    } else {
        // Fallback to API call if socket is not available
        fetch('/api/timers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({label: label, seconds: seconds})
        })
        .then(response => response.json())
        .then(data => {
            console.log('Timer created via API:', data);
            // Trigger HTMX to refresh the timers partial
            const timersPartial = document.querySelector('[hx-get*="/partials/timers"]');
            if (timersPartial) {
                htmx.trigger(timersPartial, 'htmx:refresh');
            }
        })
        .catch(error => console.error('Error creating timer:', error));
    }
}

// Function to delete a timer via SocketIO
function deleteTimerSocket(timerId) {
    if (socket && socketConnected) {
        socket.emit('delete_timer', {id: timerId});
    } else {
        // Fallback to API call if socket is not available
        fetch(`/api/timers/${timerId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            console.log('Timer deleted via API:', data);
            // Remove the timer element from the DOM
            const timerElement = document.querySelector(`#timer-${timerId}`);
            if (timerElement) {
                timerElement.remove();
            }
        })
        .catch(error => console.error('Error deleting timer:', error));
    }
}

// Initialize SocketIO when the page loads
document.addEventListener('DOMContentLoaded', function() {
    initSocket();
    
    // Set up fallback HTMX polling for timers and upcoming events
    // This ensures functionality even if SocketIO is not available
    setupHTMXFallbacks();
});

// Set up fallback HTMX polling
function setupHTMXFallbacks() {
    // Continue with existing HTMX-based updates as fallback
    // The existing HTMX attributes in templates will handle polling
    console.log('HTMX fallbacks ready');
}
