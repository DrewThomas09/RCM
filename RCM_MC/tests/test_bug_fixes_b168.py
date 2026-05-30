"""b168 — kill recursive labels in section dropdowns.

The 2026-05-30 audit walk found two mega-menu dropdowns rendering an
item named after the section itself:

    Library ▾  …  05. Library  06. Catalog          ← recursion
    Portfolio ▾ …  03. Portfolio  04. Monitor       ← recursion

Cause: ``_surface_rankings.RANKINGS['library']`` listed the
``/library`` route with ``label='Library'``, and
``RANKINGS['portfolio']`` listed ``/portfolio`` with
``label='Portfolio'``. Both labels match the section button.

Fix: relabel in the ranking manifest only. ``/library`` becomes
``'Deal Corpus'`` (matching the page's own ``eyebrow='DEAL CORPUS'``);
``/portfolio`` becomes ``'Overview'``. The section button labels
(``Library``, ``Portfolio``) and the routes themselves are unchanged
— bookmarks, ``/library`` URL, ``/portfolio`` URL all keep working.

The fix is intentionally label-only — no route migrations, no 301s.
That keeps blast radius minimal and lets the next audit wave debate
the larger naming questions (``-intel`` vs ``-intelligence``, the
five-route comps family, etc.) without entanglement.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
import re
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestSurfaceRankingLabelsAreNonRecursive(unittest.TestCase):
    """Direct manifest check — cheap, doesn't need an HTTP server."""

    def test_library_section_route_not_called_library(self):
        from rcm_mc.ui._surface_rankings import RANKINGS
        for r in RANKINGS.get("library", []):
            if r.get("route") == "/library":
                self.assertNotEqual(
                    r.get("label"), "Library",
                    "/library entry in library section must not have "
                    "label='Library' (recursive with section button)",
                )
                break
        else:
            self.fail("/library missing from library section ranking")

    def test_portfolio_section_route_not_called_portfolio(self):
        from rcm_mc.ui._surface_rankings import RANKINGS
        for r in RANKINGS.get("portfolio", []):
            if r.get("route") == "/portfolio":
                self.assertNotEqual(
                    r.get("label"), "Portfolio",
                    "/portfolio entry in portfolio section must not have "
                    "label='Portfolio' (recursive with section button)",
                )
                break
        else:
            self.fail("/portfolio missing from portfolio section ranking")


class TestMegaMenuDropdownLabelsAreNonRecursive(unittest.TestCase):
    """End-to-end coverage: render /home and confirm neither section
    dropdown contains a sub-item whose label equals the section's own
    button label."""

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
        """Return the topbar nav's stripped visible text."""
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/home", timeout=10,
        ) as resp:
            body = resp.read().decode()
        m = re.search(r"<nav[^>]*>(.*?)</nav>", body, re.S)
        self.assertIsNotNone(m, "topbar <nav> missing")
        text = re.sub(r"<[^>]+>", " ", m.group(1))
        return re.sub(r"\s+", " ", text).strip()

    def test_library_dropdown_excludes_recursive_library_label(self):
        text = self._nav_text()
        # Find the Library section header in the text, then scan its
        # numbered items (01. … 06. …) until the next "All ... tools"
        # sentinel.
        idx = text.find("Library ▾")
        self.assertGreater(idx, -1)
        end = text.find("All Library tools", idx)
        section = text[idx:end if end > -1 else idx + 800]
        # The standalone token " Library" preceded by a digit dot
        # would be the recursion. Match "0N. Library " specifically.
        m = re.search(r"\b0\d\. Library\b(?! Map)", section)
        self.assertIsNone(
            m, "Library dropdown still contains a 'Library' item "
               f"(recursive). Section text: {section[:300]!r}")
        # Sanity: the replacement label "Deal Corpus" is present.
        self.assertIn("Deal Corpus", section)

    def test_portfolio_dropdown_excludes_recursive_portfolio_label(self):
        text = self._nav_text()
        idx = text.find("Portfolio ▾")
        self.assertGreater(idx, -1)
        end = text.find("All Portfolio tools", idx)
        section = text[idx:end if end > -1 else idx + 800]
        # Recursion would be "0N. Portfolio " (no qualifier).
        # "Portfolio Map" is a different route and stays.
        m = re.search(r"\b0\d\. Portfolio\b(?! Map)", section)
        self.assertIsNone(
            m, "Portfolio dropdown still contains a 'Portfolio' item "
               f"(recursive). Section text: {section[:300]!r}")
        # Sanity: the replacement label "Overview" is present.
        self.assertIn("Overview", section)

    def test_routes_still_resolve(self):
        """Relabeling must not break the routes themselves."""
        for path in ("/library", "/portfolio"):
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=10,
            ) as resp:
                self.assertEqual(resp.status, 200,
                                 msg=f"{path} → {resp.status}")


if __name__ == "__main__":
    unittest.main()
