"""HCRIS X-Ray input page = Input B · Workstation (PR 1).

The no-query route renders the two-up workstation (intake + a clearly-labeled
SAMPLE preview). Critically, the static SAMPLE values must NOT leak into a real
?q= result, and no raw CSS appears in the body.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page


def _body_without_styles(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "", html, flags=re.DOTALL)


class InputWorkstationTests(unittest.TestCase):
    def setUp(self):
        self.h = render_hcris_xray_page({})

    def test_workstation_structure(self):
        self.assertIn("xr-ws", self.h)                 # two-up layout
        self.assertIn("xr-crumb", self.h)              # breadcrumb
        self.assertIn("HCRIS X-Ray", self.h)
        self.assertIn("① Identify", self.h)
        self.assertIn("② Peer engine", self.h)
        self.assertIn("Run X-Ray", self.h)
        self.assertIn("fiscal_year", self.h)           # FY segmented control

    def test_sample_preview_is_labeled(self):
        self.assertIn("Sample output", self.h)
        # the static demo is explicitly an illustrative SAMPLE
        self.assertIn("SAMPLE", self.h.upper())

    def test_no_raw_css_in_body(self):
        body = _body_without_styles(self.h)
        for frag in (".xr-ws{", ".xr-seg{", "grid-template-columns:"):
            self.assertNotIn(frag, body)


class NoSampleLeakTests(unittest.TestCase):
    def test_sample_values_absent_from_real_result(self):
        # The static SAMPLE preview uses Stroger / CCN 140124 numbers. A real
        # report (?ccn= for a DIFFERENT provider) must not echo those demo
        # values — the sample lives only on the input landing.
        res = render_hcris_xray_page({"ccn": ["050100"]})  # Sharp Memorial
        self.assertIn("SHARP MEMORIAL", res.upper())       # real provider rendered
        for sample_literal in ("$13,169", "CCN 140124", "Illustrative SAMPLE"):
            self.assertNotIn(sample_literal, res,
                             msg=f"sample literal {sample_literal!r} leaked into a real result")


if __name__ == "__main__":
    unittest.main()
