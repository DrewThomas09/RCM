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


_CHARTIS_UI_V2_SNAPSHOT = os.environ.get("CHARTIS_UI_V2")


@pytest.fixture(autouse=True)
def _isolate_chartis_ui_v2_flag():
    """Restore the ``CHARTIS_UI_V2`` environment variable to its
    session-start state around every test.

    Phase-2 component tests need to flip the flag on (so the v2 shell
    path is exercised) and reload ``rcm_mc.ui._chartis_kit*`` modules
    to re-read the flag. Without this fixture, the env var would
    leak into later test files — e.g. ``test_power_ui`` and
    ``test_universal_palette`` assume the legacy shell, which only
    activates with the flag unset. Snapshot is captured at module
    import (session start), not at fixture entry, so that
    ``setUpClass`` mutations in test files don't poison the snapshot.
    """
    try:
        yield
    finally:
        if _CHARTIS_UI_V2_SNAPSHOT is None:
            os.environ.pop("CHARTIS_UI_V2", None)
        else:
            os.environ["CHARTIS_UI_V2"] = _CHARTIS_UI_V2_SNAPSHOT
        # Drop cached kit modules so the next test reads the flag fresh.
        import sys
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
