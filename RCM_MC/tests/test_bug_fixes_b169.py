"""b169 — drop the "01. 02. …" mono ordinal prefix from mega-menu items.

The 2026-05-29 audit (§2.1) flagged the numbered ordinals as
magazine-TOC styling that didn't fit a tool nav. The digits were the
ranking order (from ``_surface_rankings.RANKINGS``), which a partner
has no way to know, so they were noise — every section dropdown read
"01. {label} 02. {label} …" with the numbers contributing nothing.

Fix: emit the mega-menu items without the ``<span class="ck-mega-idx">``
prefix; drop the 28px column from ``.ck-mega-item``'s grid template so
the serif title + italic description take the full row width. The
ranking-driven render order is preserved; only the visual digit
prefix is removed.

This is a layout-only change. No route or label is touched. The audit
preserved test ``test_library_dropdown_excludes_recursive_library_label``
already enumerates dropdown items by " {label} " — no test depends on
the ordinal prefix.
"""
from __future__ import annotations

import os
import re
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestMegaMenuOrdinalsDropped(unittest.TestCase):
    """End-to-end: render /home and confirm every section dropdown
    contains zero numbered ordinals."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        PortfolioStore(cls.db)
        cls.port = _free_port()
        cls.server, _h = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _nav_text(self) -> str:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/home", timeout=10,
        ) as resp:
            body = resp.read().decode()
        m = re.search(r"<nav[^>]*>(.*?)</nav>", body, re.S)
        self.assertIsNotNone(m, "topbar <nav> missing")
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        return re.sub(r"\s+", " ", text).strip()

    def test_no_two_digit_ordinals_in_topbar(self):
        text = self._nav_text()
        # Match the prefix shape "0N." (digits + period) that
        # used to label every dropdown item.
        ordinals = re.findall(r"\b0\d\.\s", text)
        self.assertEqual(
            ordinals, [],
            f"unexpected ordinal prefixes remaining: {ordinals[:5]}",
        )

    def test_dropdowns_still_contain_their_destinations(self):
        """The destinations themselves must still appear — the
        ordinal drop is layout-only, not a content removal."""
        text = self._nav_text()
        # Pick representative leaves we know are present in
        # _surface_rankings for each section.
        for label in (
            "Target Screener",   # Source dropdown
            "Deal Pipeline",     # Pipeline dropdown
            "HCRIS X-Ray",       # Diligence dropdown
            "RCM Benchmarks",    # Library dropdown
            "Regulatory Calendar",  # Research dropdown
            "Risk Scan",         # Portfolio dropdown
        ):
            self.assertIn(label, text,
                          f"dropdown destination {label!r} missing")


class TestMegaMenuMarkupDoesNotReferenceCkMegaIdx(unittest.TestCase):
    """Helper-level check that the renderer no longer emits
    ``ck-mega-idx`` spans. Catches a future regression where someone
    re-introduces a numbered prefix."""

    def test_topbar_renderer_does_not_emit_ordinal_span(self):
        from rcm_mc.ui._chartis_kit import _topbar
        html = _topbar(active_nav=None, user_initials="AT")
        # The CSS rule was also removed; rendered topbar HTML should
        # contain neither the span nor the class name.
        self.assertNotIn("ck-mega-idx", html,
                         "ck-mega-idx span/class re-introduced")
        # Sanity guard: the dropdown items are still rendered.
        self.assertIn("ck-mega-it-label", html)


if __name__ == "__main__":
    unittest.main()
