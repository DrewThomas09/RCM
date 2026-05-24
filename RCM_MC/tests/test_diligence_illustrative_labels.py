"""PR 2 — priority illustrative analyzers carry an honest source-and-purpose
header so none masquerades as live evidence.

These three `data_public` analyzers are hardcoded models today (no real
loader). Each must render the `ck_source_purpose` header with an ILLUSTRATIVE
chip + a next-action pointing to the real HCRIS path. (PRs 4/5 wire them.)
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.payer_stress_page import render_payer_stress
from rcm_mc.ui.data_public.cost_structure_page import render_cost_structure
from rcm_mc.ui.data_public.debt_service_page import render_debt_service

_PAGES = {
    "payer_stress": lambda: render_payer_stress({}),
    "cost_structure": lambda: render_cost_structure({}),
    "debt_service": lambda: render_debt_service({}),
}


class IllustrativeLabelTests(unittest.TestCase):
    def test_each_priority_page_has_honest_header(self):
        for name, render in _PAGES.items():
            h = render()
            with self.subTest(page=name):
                self.assertIn("ck-sp", h)                 # source-purpose header
                self.assertIn("ILLUSTRATIVE", h)          # not shown as live
                self.assertIn("ck-sp-purpose", h)         # purpose stated
                self.assertIn("/diligence/hcris-xray", h)  # next action → real path

    def test_illustrative_chip_tooltip_is_honest(self):
        # The ILLUSTRATIVE chip's tooltip must say it is not a real source.
        h = render_payer_stress({})
        self.assertIn("NOT a real source", h)


if __name__ == "__main__":
    unittest.main()
