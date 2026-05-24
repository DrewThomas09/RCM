"""PR 5 — Cost Structure + Debt Service wire to real HCRIS when a CCN is
attached; honest illustrative/proxy degradation otherwise. No fabricated data.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.cost_structure_page import render_cost_structure
from rcm_mc.ui.data_public.debt_service_page import render_debt_service

_PAGES = [render_cost_structure, render_debt_service]


class CostDebtHcrisTests(unittest.TestCase):
    def test_no_ccn_illustrative(self):
        for fn in _PAGES:
            self.assertIn("ILLUSTRATIVE", fn({}))

    def test_attached_ccn_uses_real_hcris(self):
        for fn in _PAGES:
            h = fn({"ccn": "050100"})
            with self.subTest(fn=fn.__name__):
                self.assertIn("HCRIS PUBLIC DATA", h)
                self.assertIn("DERIVED", h)
                self.assertIn("CCN 050100", h)
                self.assertIn("Real HCRIS", h)      # real fact strip

    def test_bad_ccn_degrades(self):
        for fn in _PAGES:
            h = fn({"ccn": "ZZZZZZ"})
            self.assertIn("ILLUSTRATIVE", h)
            self.assertNotIn("HCRIS PUBLIC DATA", h)

    def test_debt_service_labels_proxy_honestly(self):
        h = render_debt_service({"ccn": "050100"})
        self.assertIn("PROXY", h)                   # margin × NPR proxy, not true DSCR
        self.assertIn("DATA REQUIRED", h)           # debt terms not in HCRIS


if __name__ == "__main__":
    unittest.main()
