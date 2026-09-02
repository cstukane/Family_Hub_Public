import time
from threading import Timer as ThreadTimer

from flask import current_app, request
from flask_socketio import emit, join_room, leave_room

from hub.services import calendar, timers


def init_socket_handlers(socketio):
    """Initialize all socket event handlers."""

    @socketio.on("connect")
    def handle_connect():
        """Handle client connection."""
        current_app.logger.info("Client %s connected", request.sid)
        emit("status", {"msg": "Connected to server"})

    @socketio.on("disconnect")
    def handle_disconnect():
        """Handle client disconnection."""
        current_app.logger.info("Client %s disconnected", request.sid)

    @socketio.on("join_room")
    def handle_join_room(data):
        """Handle room joining."""
        room = data.get("room", "general")
        join_room(room)
        emit("status", {"msg": f"Joined room: {room}"}, room=room)

    @socketio.on("leave_room")
    def handle_leave_room(data):
        """Handle room leaving."""
        room = data.get("room", "general")
        leave_room(room)
        emit("status", {"msg": f"Left room: {room}"}, room=room)

    @socketio.on("get_timers")
    def handle_get_timers():
        """Handle request for active timers."""
        active_timers = timers.list_active_timers()
        timer_data = [timer.to_dict() for timer in active_timers]
        emit("timer_list", {"timers": timer_data})

    @socketio.on("get_upcoming_events")
    def handle_get_upcoming_events():
        """Handle request for upcoming events."""
        upcoming_events = calendar.get_upcoming_events(5)
        event_data = [event.to_dict() for event in upcoming_events]
        emit("upcoming_events", {"events": event_data})

    @socketio.on("create_timer")
    def handle_create_timer(data):
        """Handle timer creation."""
        label = data.get("label", "New Timer")
        seconds = data.get("seconds", 60)  # Default to 60 seconds

        try:
            new_timer = timers.create_timer(label, seconds)
            timer_data = new_timer.to_dict()

            # Emit to all clients in the timers room
            emit("timer_created", {"timer": timer_data}, broadcast=True)
        except Exception as e:
            emit("error", {"msg": f"Failed to create timer: {str(e)}"})

    @socketio.on("delete_timer")
    def handle_delete_timer(data):
        """Handle timer deletion."""
        timer_id = data.get("id")

        if timer_id:
            success = timers.delete_timer(timer_id)
            if success:
                emit("timer_deleted", {"id": timer_id}, broadcast=True)
            else:
                emit("error", {"msg": f"Timer {timer_id} not found"})

    @socketio.on("request_timer_update")
    def handle_request_timer_update():
        """Handle request for immediate timer update."""
        active_timers = timers.list_active_timers()
        timer_data = [timer.to_dict() for timer in active_timers]
        emit("timer_update", {"timers": timer_data})

    @socketio.on("request_upcoming_events_update")
    def handle_request_upcoming_events_update():
        """Handle request for immediate upcoming events update."""
        upcoming_events = calendar.get_upcoming_events(5)
        event_data = [event.to_dict() for event in upcoming_events]
        emit("upcoming_events_update", {"events": event_data})


def start_timer_monitor(socketio, app):
    """Start monitoring for timer updates and send them via SocketIO."""
    if app.config.get("TESTING"):
        return

    # Keep high-frequency updates only when active timers exist.
    ACTIVE_TIMER_INTERVAL_SECONDS = 1.0
    IDLE_TIMER_INTERVAL_SECONDS = 5.0
    EVENTS_INTERVAL_SECONDS = 30.0
    IDLE_EMPTY_TIMER_BROADCAST_SECONDS = 120.0

    last_events_emit = [0.0]
    last_empty_timer_emit = [0.0]
    had_active_timers = [False]

    def check_and_emit_timers():
        """Check for expired timers and emit updates."""
        next_interval = IDLE_TIMER_INTERVAL_SECONDS
        try:
            with app.app_context():
                # Check for expired timers and deactivate them
                expired_count = timers.deactivate_expired_timers()
                if expired_count > 0:
                    app.logger.info("Deactivated %s expired timers", expired_count)

                # Emit timer updates frequently only while active timers exist.
                active_timers = timers.list_active_timers()
                timer_data = [timer.to_dict() for timer in active_timers]
                now = time.monotonic()

                if timer_data:
                    socketio.emit("timer_update", {"timers": timer_data}, room="timers")
                    had_active_timers[0] = True
                    next_interval = ACTIVE_TIMER_INTERVAL_SECONDS
                else:
                    # Send an empty state only on transition or periodic keepalive.
                    should_emit_empty = (
                        had_active_timers[0] or (now - last_empty_timer_emit[0]) >= IDLE_EMPTY_TIMER_BROADCAST_SECONDS
                    )
                    if should_emit_empty:
                        socketio.emit("timer_update", {"timers": []}, room="timers")
                        last_empty_timer_emit[0] = now
                    had_active_timers[0] = False

                # Upcoming events change slowly; emit on a coarse cadence.
                if (now - last_events_emit[0]) >= EVENTS_INTERVAL_SECONDS:
                    upcoming_events = calendar.get_upcoming_events(5)
                    event_data = [event.to_dict() for event in upcoming_events]
                    socketio.emit("upcoming_events_update", {"events": event_data}, room="upcoming_events")
                    last_events_emit[0] = now

        except Exception:
            try:
                app.logger.exception("Error in timer monitor")
            except Exception:  # nosec B110
                pass

        # Schedule the next check; stay cheap while idle.
        timer = ThreadTimer(next_interval, check_and_emit_timers)
        timer.daemon = True
        timer.start()

    # Start the initial check
    timer_thread = ThreadTimer(1.0, check_and_emit_timers)
    timer_thread.daemon = True
    timer_thread.start()


def broadcast_upcoming_events(socketio):
    """Broadcast upcoming events to all connected clients."""
    try:
        upcoming_events = calendar.get_upcoming_events(5)
        event_data = [event.to_dict() for event in upcoming_events]
        socketio.emit("upcoming_events_update", {"events": event_data})
    except Exception:
        current_app.logger.exception("Error broadcasting upcoming events")
