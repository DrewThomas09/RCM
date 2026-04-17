"""Tests for the standalone LP-update builder + CLI (Brick 120)."""
from __future__ import annotations

import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from rcm_mc import portfolio_cmd
from rcm_mc.deals.deal_tags import add_tag
from rcm_mc.reports.lp_update import build_lp_update_html
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


class TestBuildLpUpdate(unittest.TestCase):
    def test_empty_store_renders(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            doc = build_lp_update_html(store, days=30)
            self.assertIn("LP Update", doc)
            self.assertIn("Active deals", doc)
            self.assertIn("Active alerts", doc)

    def test_shows_headline_kpis_and_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            doc = build_lp_update_html(store)
            self.assertIn("Weighted MOIC", doc)
            self.assertIn("RED", doc)
            self.assertIn("Covenant TRIPPED", doc)

    def test_cohort_section_shown_when_tags_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            add_tag(store, deal_id="ccf", tag="growth")
            doc = build_lp_update_html(store)
            self.assertIn("Cohort breakdown", doc)
            self.assertIn("growth", doc)

    def test_custom_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            doc = build_lp_update_html(
                store, title="Fund III — Q2 2026 LP Update",
            )
            self.assertIn("Fund III — Q2 2026 LP Update", doc)


class TestLpUpdateCli(unittest.TestCase):
    def test_cli_writes_html_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            db_path = os.path.join(tmp, "p.db")
            out_path = os.path.join(tmp, "lp.html")
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = portfolio_cmd.main([
                    "--db", db_path,
                    "lp-update", "--out", out_path, "--days", "14",
                ])
            self.assertEqual(rc, 0)
            self.assertIn(f"Wrote {out_path}", buf.getvalue())
            self.assertTrue(os.path.isfile(out_path))
            with open(out_path, encoding="utf-8") as fh:
                content = fh.read()
            self.assertIn("LP Update", content)
            self.assertIn("window 14 days", content)
            self.assertIn("Covenant TRIPPED", content)


if __name__ == "__main__":
    unittest.main()
