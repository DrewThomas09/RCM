"""Regression: operating margin is gated on cost-structure + debt-service too.

The X-Ray / screener gate junk-opex margins (outside -40%…+30%) to "—". The
cost-structure and debt-service "Real HCRIS" tables showed the same margin RAW
(e.g. +87.9%), so one hospital read as a confident outlier on those pages and
"—" on the X-Ray. Now they gate it identically, with the red gap dot, and the
debt-service operating-cash proxy (margin × NPR) is dropped too when the margin
is an artifact. See margin_is_plausible.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.data.hcris import load_hcris
from rcm_mc.diligence.hcris_xray import find_hospital
from rcm_mc.ui._chartis_kit import margin_is_plausible


def _find(predicate, limit=4000):
    for c in load_hcris()["ccn"].astype(str).unique().tolist()[:limit]:
        h = find_hospital(c)
        if h and predicate(h):
            return c
    return None


class CostStructureMarginGateTests(unittest.TestCase):
    def test_artifact_margin_gated(self):
        from rcm_mc.ui.data_public.cost_structure_page import render_cost_structure
        ccn = _find(lambda h: not margin_is_plausible(h.operating_margin_on_npr))
        self.assertIsNotNone(ccn)
        html = render_cost_structure({"ccn": ccn})
        self.assertIn("ck-gap-dot", html)

    def test_plausible_margin_shown(self):
        from rcm_mc.ui.data_public.cost_structure_page import render_cost_structure
        ccn = _find(lambda h: margin_is_plausible(h.operating_margin_on_npr)
                    and h.operating_margin_on_npr not in (None, 0))
        self.assertIsNotNone(ccn)
        html = render_cost_structure({"ccn": ccn})
        self.assertRegex(html, r"[+-]\d+\.\d%")


class DebtServiceMarginGateTests(unittest.TestCase):
    def test_artifact_margin_and_proxy_gated(self):
        from rcm_mc.ui.data_public.debt_service_page import render_debt_service
        ccn = _find(lambda h: not margin_is_plausible(h.operating_margin_on_npr))
        self.assertIsNotNone(ccn)
        html = render_debt_service({"ccn": ccn})
        self.assertIn("ck-gap-dot", html)


if __name__ == "__main__":
    unittest.main()
