"""Tests for the rcm_mc.ic_memo package — distinct from the
earlier test_ic_memo.py which covers a separate prior module."""
from __future__ import annotations

import http.server
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import urlopen


# ── Scenarios ─────────────────────────────────────────────────

class TestScenarios(unittest.TestCase):
    def test_bull_beats_base_beats_bear(self):
        from rcm_mc.ic_memo import build_scenarios
        s = build_scenarios(entry_ebitda_mm=20.0)
        self.assertGreater(s.bull.moic, s.base.moic)
        self.assertGreater(s.base.moic, s.bear.moic)
        self.assertGreater(s.bull.irr, s.base.irr)
        self.assertGreater(s.base.irr, s.bear.irr)

    def test_irr_solves_from_moic(self):
        from rcm_mc.ic_memo import build_scenarios
        s = build_scenarios(
            entry_ebitda_mm=10.0, hold_years=5.0,
            moic_p25=2.0, moic_p50=2.0, moic_p75=2.0,
        )
        # MOIC 2.0 over 5y → IRR ≈ 14.87%
        self.assertAlmostEqual(s.base.irr, 0.1487, places=2)

    def test_entry_equity_uses_leverage(self):
        from rcm_mc.ic_memo import build_scenarios
        s = build_scenarios(
            entry_ebitda_mm=10.0, entry_multiple=10.0,
            leverage_pct=0.50,
        )
        self.assertAlmostEqual(
            s.base.entry_equity_mm, 50.0, places=1)


# ── Memo build + render ──────────────────────────────────────

class TestMemoBuildAndRender(unittest.TestCase):
    def test_memo_contains_8_sections(self):
        from rcm_mc.ic_memo import (
            build_ic_memo, render_memo_markdown,
        )
        memo = build_ic_memo(
            deal_id="D1", deal_name="Test Co",
            sector="physician_group",
            states=["TX"], revenue_mm=200, ebitda_mm=30,
            ebitda_margin=0.15, growth_rate=0.12,
        )
        md = render_memo_markdown(memo)
        for heading in (
            "## 1. Executive Summary",
            "## 2. Target Overview",
            "## 3. Investment Thesis",
            "## 4. Comparable Transactions",
            "## 5. Predictions & EBITDA Bridge",
            "## 6. Scenarios",
            "## 7. Key Risks",
            "## 8. Methodology Appendix",
        ):
            self.assertIn(heading, md)
        self.assertIn("Test Co", md)

    def test_thesis_bullets_render(self):
        from rcm_mc.ic_memo import (
            build_ic_memo, render_memo_markdown,
        )
        memo = build_ic_memo(
            deal_id="D2", deal_name="Co",
            sector="hospital", ebitda_mm=30.0,
            growth_rate=0.20,
        )
        md = render_memo_markdown(memo)
        self.assertIn("Above-market organic growth", md)

    def test_custom_thesis_overrides_default(self):
        from rcm_mc.ic_memo import (
            build_ic_memo, render_memo_markdown,
        )
        memo = build_ic_memo(
            deal_id="D3", deal_name="Co",
            sector="hospital", ebitda_mm=30.0,
            custom_thesis=["Bespoke partner angle"],
        )
        md = render_memo_markdown(memo)
        self.assertIn("Bespoke partner angle", md)
        self.assertNotIn("Standard PE thesis", md)


# ── HTML render ──────────────────────────────────────────────

class TestHTMLRender(unittest.TestCase):
    def test_html_doctype_and_title(self):
        from rcm_mc.ic_memo import (
            build_ic_memo, render_memo_html,
        )
        memo = build_ic_memo(
            deal_id="D4", deal_name="HTML Co",
            sector="hospital", ebitda_mm=20.0)
        html = render_memo_html(memo)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("IC Memo — HTML Co", html)
        self.assertIn("Investment Committee Memo", html)
        self.assertIn("<h2>", html)


# ── HTTP route ──────────────────────────────────────────────

class TestICRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import RCMHandler, ServerConfig
        cls._tmp = tempfile.TemporaryDirectory()
        cls._db = os.path.join(cls._tmp.name, "p.db")
        from rcm_mc.portfolio.store import PortfolioStore
        store = PortfolioStore(cls._db)
        store.init_db()
        with store.connect() as con:
            con.execute(
                "INSERT INTO deals (deal_id, name, "
                "created_at, profile_json) "
                "VALUES (?, ?, ?, ?)",
                ("D_IC", "IC Test Hospital",
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps({
                     "sector": "hospital",
                     "states": ["TX"],
                     "revenue_mm": 250,
                     "ebitda_mm": 40,
                     "ebitda_margin": 0.16,
                     "growth_rate": 0.08,
                 })))
            con.commit()
        cls._prev = RCMHandler.config
        cfg = ServerConfig()
        cfg.db_path = cls._db
        RCMHandler.config = cfg
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), RCMHandler)
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        from rcm_mc.server import RCMHandler
        cls.server.shutdown()
        cls.server.server_close()
        RCMHandler.config = cls._prev
        cls._tmp.cleanup()

    def test_renders_full_memo(self):
        url = f"http://127.0.0.1:{self.port}/diligence/ic-memo/D_IC"
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("IC Test Hospital", body)
        self.assertIn("Investment Committee Memo", body)
        for n in ("1. Executive Summary", "2. Target Overview",
                  "3. Investment Thesis",
                  "4. Comparable Transactions",
                  "5. Predictions",
                  "6. Scenarios", "7. Key Risks",
                  "8. Methodology"):
            self.assertIn(n, body)

    def test_unknown_deal_404(self):
        url = (f"http://127.0.0.1:{self.port}"
               f"/diligence/ic-memo/UNKNOWN_DEAL")
        try:
            urlopen(url, timeout=15)
            self.fail("Expected HTTPError")
        except HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
