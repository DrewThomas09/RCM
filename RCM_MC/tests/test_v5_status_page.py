"""End-to-end test for /v5-status (campaign targets 1B + 1D)."""
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


class V5StatusPageTests(unittest.TestCase):
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
                with _u.urlopen(f"http://127.0.0.1:{port}/v5-status") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertIn("v5 Transformation Status", body)
                self.assertIn("v5 status", body)
                self.assertIn("Compliance summary", body)
                self.assertIn("DealAnalysisPacket adoption", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_carries_numeric_utility_classes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/v5-status") as r:
                    body = r.read().decode("utf-8")
                self.assertIn('class="num"', body)
                self.assertIn("Total routes", body)
                self.assertIn("v5 chrome", body)
                self.assertIn("Packet-driven", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_renders_inventory_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/v5-status") as r:
                    body = r.read().decode("utf-8")
                import re as _re

                m = _re.search(r'<span class="num">\d{2,}</span>', body)
                self.assertIsNotNone(m)
            finally:
                server.shutdown()
                server.server_close()


class V5StatusParserTests(unittest.TestCase):
    def test_parses_v5_inventory_row(self) -> None:
        from rcm_mc.ui.v3_status_page import parse_inventory

        text = (
            "**Total routes mapped:** 100\n"
            "## Compliance summary\n"
            "| v5 (chartis_shell or under ui/chartis/) | 60 | 60% |\n"
            "| legacy (`shell()` from `_ui_kit` only) | 5 | 5% |\n"
            "| bespoke (no shell — direct HTML) | 10 | 10% |\n"
            "| redirect | 2 | 2% |\n"
            "| unknown / unresolved | 23 | 23% |\n"
            "**Packet-driven (calls get_or_build_packet ...):** 8 of 100 (8%)\n"
        )
        c = parse_inventory(text, chrome_prefix="v5")
        self.assertEqual(c.total, 100)
        self.assertEqual(c.v3, 60)
        self.assertEqual(c.packet_driven, 8)


if __name__ == "__main__":
    unittest.main()
