"""b167 — no dead "future:" search/filter placeholder text.

PROMPTS.md Phase 1 / Prompt 6: an earlier draft of /alerts and
/escalations carried a non-functional search input with placeholder
text such as "future: filter by deal name, alert title". Dead UI is
worse than missing UI — it suggests the page is half-finished.

The current code does not emit either string; this regression test
pins the property so a future redesign can't accidentally re-land a
non-functional placeholder under the same wording.
"""
from __future__ import annotations

import re
import socket
import threading
import time
import unittest
import urllib.request


def _start_server(db_path: str) -> tuple[object, str]:
    """Boot a real RCM-MC HTTP server on a random free port.

    A real HTTP path is the only way to fetch /alerts and /escalations
    body content because both routes assemble their HTML inline inside
    server.py rather than via a separate render() function.
    """
    from rcm_mc.server import build_server

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server, _ = build_server(port=port, db_path=db_path)
    base = f"http://127.0.0.1:{port}"
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    # Allow the listener a moment.
    time.sleep(0.05)
    return server, base


class NoFuturePlaceholderText(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        import os
        import tempfile

        cls.tmp = tempfile.mkdtemp(prefix="rcm_b167_")
        cls.db = os.path.join(cls.tmp, "p.db")
        # Touching the path is enough — PortfolioStore creates tables
        # on demand. The /alerts route works on an empty DB.
        from rcm_mc.portfolio.store import PortfolioStore
        PortfolioStore(cls.db)
        cls.server, cls.base = _start_server(cls.db)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def _get(self, path: str) -> str:
        with urllib.request.urlopen(self.base + path, timeout=5) as resp:
            return resp.read().decode("utf-8", errors="replace")

    def _assert_no_future_placeholder(self, body: str, where: str) -> None:
        # Match the literal "future:" or "future filter" patterns the
        # PROMPT cited. Case-insensitive so a styling change can't
        # smuggle them back in.
        self.assertFalse(
            re.search(r"future\s*:\s*filter", body, flags=re.IGNORECASE),
            f"{where} re-introduced a 'future: filter' placeholder",
        )
        self.assertFalse(
            re.search(r"future\s+filter", body, flags=re.IGNORECASE),
            f"{where} re-introduced a 'future filter' placeholder",
        )
        self.assertFalse(
            re.search(r"future\s+search", body, flags=re.IGNORECASE),
            f"{where} re-introduced a 'future search' placeholder",
        )

    def test_alerts_has_no_future_placeholder(self) -> None:
        self._assert_no_future_placeholder(self._get("/alerts"), "/alerts")

    def test_escalations_has_no_future_placeholder(self) -> None:
        self._assert_no_future_placeholder(
            self._get("/escalations"), "/escalations",
        )


if __name__ == "__main__":
    unittest.main()
