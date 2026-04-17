from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
from typing import Generator, Tuple

import pytest

from rcm_mc.portfolio.store import PortfolioStore


@pytest.fixture
def tmp_store() -> Generator[Tuple[PortfolioStore, str], None, None]:
    """Yield (store, db_path) backed by a temp file. Cleaned up after."""
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    store = PortfolioStore(tf.name)
    try:
        yield store, tf.name
    finally:
        os.unlink(tf.name)


@pytest.fixture
def server_port(tmp_store) -> Generator[Tuple[int, PortfolioStore], None, None]:
    """Start a test server and yield (port, store). Shut down after."""
    from rcm_mc.server import build_server
    _, db_path = tmp_store
    store = tmp_store[0]
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)
    try:
        yield port, store
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(autouse=True)
def _reset_handler_class_state():
    """Keep server-handler globals from leaking between tests.

    Several auth/CSRF tests intentionally drive failed logins, which
    populate ``RCMHandler._login_fail_log``. Resetting the shared state
    around every test keeps the suite order-independent and prevents
    unrelated tests from inheriting stale rate-limit history.
    """
    from rcm_mc.server import RCMHandler

    RCMHandler._login_fail_log = {}
    try:
        yield
    finally:
        RCMHandler._login_fail_log = {}
