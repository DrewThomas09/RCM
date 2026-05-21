"""Two-view Command Center: page-level copy is workspace-mode aware.

The /app command center serves two audiences from one composition. The
PE-partner view frames it as a fund-level command center ("FUND II",
"Portfolio & diligence", hold-period); the Chartis Consulting view
frames it as a client engagement ("Client engagement", "Commercial
diligence", engagement). This is the L1 lexicon layer — vocabulary
only; the blocks, metrics, and layout are identical, and the product
surface name "Command center" is unchanged in both views.

Pinned here:
  * partner (default) carries the fund framing,
  * consulting carries the engagement framing,
  * both keep the "Command center" title (the /app contract), and
  * the mode contextvar is reset between tests so order can't leak.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.chartis.app_page import render_app_page
from rcm_mc.ui._workspace_mode import (
    CONSULTING,
    PARTNER,
    set_workspace_mode,
)


class AppPageModeAwareTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmp.name, "p.db")
        self.store = PortfolioStore(self.db_path)
        self.addCleanup(set_workspace_mode, PARTNER)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _render(self, mode: str) -> str:
        set_workspace_mode(mode)
        return render_app_page(store=self.store)

    def test_partner_view_uses_fund_framing(self) -> None:
        html = self._render(PARTNER)
        self.assertIn("FUND II", html)
        self.assertIn("PORTFOLIO &amp; DILIGENCE", html)
        self.assertIn("hold-period", html)
        self.assertNotIn("CLIENT ENGAGEMENT", html)

    def test_consulting_view_uses_engagement_framing(self) -> None:
        html = self._render(CONSULTING)
        self.assertIn("CLIENT ENGAGEMENT", html)
        self.assertIn("COMMERCIAL DILIGENCE", html)
        self.assertIn("engagement view", html)
        self.assertNotIn("FUND II", html)

    def test_both_views_keep_command_center_title(self) -> None:
        # "Command center" is the product surface name, not partner
        # vocabulary — it stays in both views (and the /app contract
        # test asserts it).
        self.assertIn("Command center", self._render(PARTNER))
        self.assertIn("Command center", self._render(CONSULTING))


if __name__ == "__main__":
    unittest.main()
