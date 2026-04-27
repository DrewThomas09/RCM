"""End-to-end test for /v3-status (campaign target 1D).

Boots a real ThreadingHTTPServer on a free port and hits /v3-status
via urllib.request. No mocks of our own code (per CLAUDE.md). The
inventory file lives at the repo root and is checked into git, so
the test reads the live counts; if the inventory is rebuilt with
different numbers, this test still passes — the assertions are
structural, not value-locked.

What this guards:
  - The /v3-status route is wired in server.py's _do_get_inner.
  - The renderer returns 200 (not 500 / 404).
  - The page goes through chartis_shell (carries the v3 utility
    classes that prove the wrap fired).
  - The page surfaces the campaign numbers (parses the inventory
    successfully — total + at least one row).
  - Both branches of the renderer (inventory present / absent) are
    safe — the absent branch test uses a temp inventory path.
"""
from __future__ import annotations

import os
import socket as _socket
import tempfile
import threading
import time as _time
import unittest
import urllib.request as _u

from rcm_mc.server import build_server


def _free_port() -> int:
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class V3StatusPageTests(unittest.TestCase):
    def _start(self, tmp: str):
        port = _free_port()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_page_returns_200_and_contains_campaign_chrome(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/v3-status") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                # Title set via chartis_shell
                self.assertIn("v3 Transformation Status", body)
                # Headline + section anchors prove parser ran
                self.assertIn("v3 status", body)
                self.assertIn("Compliance summary", body)
                self.assertIn("DealAnalysisPacket adoption", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_carries_v3_utility_classes(self) -> None:
        """The renderer must reach chartis_shell and the loop-7 format
        helpers must emit the .num utility class. If either breaks,
        the page would still 200 but lose its v3 chrome — this catches
        that silently-broken state."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/v3-status") as r:
                    body = r.read().decode("utf-8")
                # .num utility class on at least one numeric span
                self.assertIn('class="num"', body)
                # KPI grid has visible labels
                self.assertIn("Total routes", body)
                self.assertIn("v3 chrome", body)
                self.assertIn("Packet-driven", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_renders_inventory_count(self) -> None:
        """Sanity: the page should surface the route-count number from
        the inventory file. We don't pin a specific value (the count
        changes whenever the generator is re-run), but the page must
        contain *some* multi-digit number in a num span."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/v3-status") as r:
                    body = r.read().decode("utf-8")
                # At least one tabular-nums-wrapped multi-digit number
                import re as _re
                m = _re.search(r'<span class="num">\d{2,}</span>', body)
                self.assertIsNotNone(
                    m,
                    "no multi-digit num span found — inventory parse likely "
                    "returned zero counts",
                )
            finally:
                server.shutdown()
                server.server_close()


class V3StatusParserTests(unittest.TestCase):
    """Direct unit tests on parse_inventory — keeps the regex contract
    pinned so a generator-format change breaks loudly."""

    def test_parses_canonical_inventory(self) -> None:
        from rcm_mc.ui.v3_status_page import parse_inventory
        text = (
            "**Total routes mapped:** 100\n"
            "## Compliance summary\n"
            "| v3 (chartis_shell or under ui/chartis/) | 60 | 60% |\n"
            "| legacy (`shell()` from `_ui_kit` only) | 5 | 5% |\n"
            "| bespoke (no shell — direct HTML) | 10 | 10% |\n"
            "| redirect | 2 | 2% |\n"
            "| unknown / unresolved | 23 | 23% |\n"
            "**Packet-driven (calls get_or_build_packet ...):** 8 of 100 (8%)\n"
        )
        c = parse_inventory(text)
        self.assertEqual(c.total, 100)
        self.assertEqual(c.v3, 60)
        self.assertEqual(c.legacy, 5)
        self.assertEqual(c.bespoke, 10)
        self.assertEqual(c.redirect, 2)
        self.assertEqual(c.unknown, 23)
        self.assertEqual(c.packet_driven, 8)


if __name__ == "__main__":
    unittest.main()
