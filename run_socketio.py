"""Run the Family Hub app with Flask-SocketIO instead of `flask run`."""

from __future__ import annotations

import argparse

from app import create_app, socketio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Family Hub with Socket.IO server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--cert", default="", help="Path to SSL certificate file")
    parser.add_argument("--key", default="", help="Path to SSL private key file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = create_app()

    cert = (args.cert or "").strip()
    key = (args.key or "").strip()
    async_mode = getattr(getattr(socketio, "server", None), "eio", None)
    async_mode = getattr(async_mode, "async_mode", "threading")

    run_kwargs = {
        "host": args.host,
        "port": args.port,
    }

    if cert and key:
        # Flask-SocketIO forwards kwargs to the selected async server:
        # - eventlet/gevent expect certfile/keyfile
        # - threading (Werkzeug) expects ssl_context
        if async_mode in {"eventlet", "gevent", "gevent_uwsgi"}:
            run_kwargs["certfile"] = cert
            run_kwargs["keyfile"] = key
        else:
            run_kwargs["ssl_context"] = (cert, key)

    if async_mode == "threading":
        run_kwargs["allow_unsafe_werkzeug"] = True

    socketio.run(app, **run_kwargs)


if __name__ == "__main__":
    main()
