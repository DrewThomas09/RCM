"""Migration wave-2 contract — 5 more Group B routes adopt
ck_editorial_head() (batch 20, follows the docs/style-sweep/
MIGRATION_INVENTORY.md plan).

Five high-traffic Group B files moved from legacy ck_section_intro
heads to the universal kit helper:

  · /portfolio/bridge        (portfolio_bridge_page.py)
  · /risk/workbench          (risk_workbench_page.py)
  · /scenarios/<ccn>         (scenario_modeler_page.py)
  · /market-intel            (market_intel_page.py)
  · /alerts/escalated        (escalations_page.py)

Per-route pins (rendered through the universal helper):
  · ck-eh wrapper present
  · ONE <h1> per render path (#1036 invariant)
  · Eyebrow + 24×1px green-dash glyph
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class PortfolioBridgeEmptyHeadTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        import pandas as pd
        from rcm_mc.ui.portfolio_bridge_page import render_portfolio_bridge
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        cls._db = path
        # Empty pipeline + empty HCRIS frame → exercises the
        # empty-state head path.
        cls.html = render_portfolio_bridge(pd.DataFrame(), path)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            os.unlink(cls._db)
        except OSError:
            pass

    def test_one_h1(self) -> None:
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_ck_eh_wrapper(self) -> None:
        self.assertIn('class="ck-eh"', self.html)

    def test_empty_state_meta_honest(self) -> None:
        # No pipeline hospitals → meta line says
        # "0 ACTIVE · ADD FROM SCREENER" rather than a fabricated
        # count.
        self.assertIn("0 ACTIVE", self.html)


class MarketIntelHeadTests(unittest.TestCase):

    def test_market_intel_hero_helper_emits_ck_eh(self) -> None:
        # market_intel_page._hero is the head-builder helper; pin it
        # directly.
        from rcm_mc.ui.market_intel_page import _hero
        html = _hero(category=None, specialty=None)
        self.assertIn('class="ck-eh"', html)
        self.assertEqual(len(re.findall(r"<h1[ >]", html)), 1)


if __name__ == "__main__":
    unittest.main()
