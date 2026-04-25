"""Heroku entry point — `python -m web.heroku_adapter`.

Flow: bootstrap → build_server on 0.0.0.0:$PORT → SIGTERM/SIGINT →
server.shutdown() in a thread (shutdown() blocks on serve_forever, so
the signal handler must not call it directly) → serve_forever returns
→ clean exit.
"""
from __future__ import annotations

import os
import signal
import sys
import threading

from rcm_mc.server import build_server

from . import bootstrap


DEFAULT_PORT = 8080
HOST = "0.0.0.0"  # 127.0.0.1 would hide from Heroku router


def main() -> int:
    db_path = bootstrap.ensure_ready()
    port = int(os.environ.get("PORT", DEFAULT_PORT))

    server, _handler = build_server(
        port=port, db_path=db_path, host=HOST, auth=None,
    )

    shutdown_done = threading.Event()

    def handle_signal(signum: int, _frame) -> None:
        print(f"heroku_adapter: signal {signum}; shutting down",
              file=sys.stderr)
        def _close() -> None:
            server.shutdown()
            server.server_close()
            shutdown_done.set()
        threading.Thread(target=_close, daemon=True).start()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    print(f"heroku_adapter: serving on {HOST}:{port} (db={db_path})",
          file=sys.stderr)
    try:
        server.serve_forever()
    finally:
        shutdown_done.wait(timeout=10)  # Heroku kills at SIGTERM+30s
    return 0


if __name__ == "__main__":
    sys.exit(main())
