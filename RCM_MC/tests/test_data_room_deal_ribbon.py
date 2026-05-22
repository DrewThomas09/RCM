"""The deal Data Room carries the standard deal-context ribbon.

The Data Room (/data-room/<ccn>, reached from the IC memo) used a
bespoke cad-btn cross-links bar. It now leads with the standard
_model_nav pill ribbon — consistent with every other per-deal surface.
Data Room isn't one of the ribbon's own slots, so no pill is
highlighted; it still gives one-click access to every analysis.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.data_room_page import render_data_room


class DataRoomDealRibbonTests(unittest.TestCase):
    def _html(self) -> str:
        d = tempfile.mkdtemp()
        db = os.path.join(d, "p.db")
        with PortfolioStore(db).connect():
            pass
        return render_data_room("010001", "Test Hosp", 200.0, "GA", {}, db)

    def test_carries_model_ribbon_and_sibling_links(self):
        html = self._html()
        self.assertIn("ck-model-pill", html)
        self.assertIn("/ebitda-bridge/010001", html)
        self.assertIn("/models/returns/010001", html)

    def test_bespoke_crosslinks_panel_removed(self):
        html = self._html()
        self.assertNotIn("Cross-links", html)


if __name__ == "__main__":
    unittest.main()
