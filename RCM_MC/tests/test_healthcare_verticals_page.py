"""End-to-end + unit tests for /healthcare-verticals (Library reference page)."""
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


class HealthcareVerticalsPageTests(unittest.TestCase):
    def _start(self, tmp: str):
        port = _free_port()
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_page_returns_200_and_renders_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/healthcare-verticals"
                ) as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                # Editorial head title + a few vertical families and codes
                # that must survive markdown conversion.
                self.assertIn("US Healthcare Verticals", body)
                self.assertIn("Gastroenterology", body)
                self.assertIn("Dialysis Centers", body)
                self.assertIn("45378", body)  # colonoscopy CPT in the GI block
                # Group headings get jump-rail anchors.
                self.assertIn('id="facility-site-types"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_page_in_library_subnav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/healthcare-verticals"
                ) as r:
                    body = r.read().decode("utf-8")
                # Active section is Library — its sub-nav siblings render.
                self.assertIn("/healthcare-verticals", body)
                self.assertIn("Metric Glossary", body)
            finally:
                server.shutdown()
                server.server_close()


class MarkdownConverterTests(unittest.TestCase):
    def test_headings_bold_and_lists(self) -> None:
        from rcm_mc.ui.healthcare_verticals_page import _md_to_html

        md = (
            "## Section\n"
            "#### Vertical\n"
            "Plain paragraph with **bold** run.\n"
            "\n"
            "- first bullet\n"
            "- second bullet\n"
            "\n"
            "1. first step\n"
            "2. second step\n"
        )
        html = _md_to_html(md)
        self.assertIn("<h2>Section</h2>", html)
        self.assertIn("<h4>Vertical</h4>", html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<ul", html)
        self.assertIn("<li>first bullet</li>", html)
        self.assertIn("<ol", html)
        self.assertIn("<li>first step</li>", html)

    def test_inline_escapes_before_bolding(self) -> None:
        from rcm_mc.ui.healthcare_verticals_page import _inline

        # Angle brackets in code-like text must be escaped; bold still works.
        out = _inline("**N18.6** maps K50/K51 & <stage>")
        self.assertIn("<strong>N18.6</strong>", out)
        self.assertIn("&amp;", out)
        self.assertIn("&lt;stage&gt;", out)


if __name__ == "__main__":
    unittest.main()
