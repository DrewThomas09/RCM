"""HCRIS X-Ray seeds the cross-linked LBO models (Deal MC / Bear Case /
covenant / payer stress) with an EBITDA proxy = filed NPR x filed operating
margin. ~58% of HCRIS hospitals file a *negative* operating margin, which
would seed those models with a non-runnable (<=0) EBITDA — so the seed is
floored at 5% of NPR.

Credibility guard: when that floor bites, the page must SAY SO (and quote the
real filed margin) rather than silently presenting a fabricated positive
EBITDA as if it came from the filed margin. These tests are data-driven —
they discover a floored and a non-floored hospital via find_hospital (the same
resolver the page uses), so they self-adapt to a HCRIS data refresh.
"""

import re
import unittest

from rcm_mc.diligence.hcris_xray import find_hospital, load_all_metrics
from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page

_FLOOR_NOTE = "5% NPR floor"


def _discover():
    """Return (floored_ccn, healthy_ccn) as the page's own resolver sees them.

    load_all_metrics gives us candidate CCNs cheaply; find_hospital is the
    authoritative per-CCN view the page renders from (it can disagree with
    load_all_metrics on filing period), so the margin is re-checked there.
    """
    floored = healthy = None
    for m in load_all_metrics():
        if not (m.net_patient_revenue and m.net_patient_revenue > 0):
            continue
        h = find_hospital(m.ccn)
        if not (h and h.net_patient_revenue and h.net_patient_revenue > 0):
            continue
        if floored is None and h.operating_margin_on_npr < 0:
            floored = m.ccn
        # >6% clears the 5% floor with margin to spare.
        if healthy is None and h.operating_margin_on_npr > 0.06:
            healthy = m.ccn
        if floored and healthy:
            break
    return floored, healthy


class TestHcrisXrayEbitdaFloor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.floored_ccn, cls.healthy_ccn = _discover()

    def test_floored_hospital_discloses_the_floor(self):
        if not self.floored_ccn:
            self.skipTest("no negative-margin hospital in current HCRIS data")
        page = render_hcris_xray_page({"ccn": [self.floored_ccn]})
        self.assertIn(_FLOOR_NOTE, page)
        # The note must quote the real filed (negative) margin, not hide it.
        self.assertIn("filed op. margin", page)
        h = find_hospital(self.floored_ccn)
        self.assertIn(f"{h.operating_margin_on_npr * 100:.1f}%", page)

    def test_healthy_hospital_has_no_floor_note(self):
        if not self.healthy_ccn:
            self.skipTest("no >6%-margin hospital in current HCRIS data")
        page = render_hcris_xray_page({"ccn": [self.healthy_ccn]})
        self.assertNotIn(_FLOOR_NOTE, page)

    def test_healthy_seed_ebitda_equals_npr_times_margin(self):
        """Above the floor, the seed EBITDA must be the honest filed number
        (NPR x margin), not the floor and not something invented."""
        if not self.healthy_ccn:
            self.skipTest("no >6%-margin hospital in current HCRIS data")
        h = find_hospital(self.healthy_ccn)
        expected_m = h.net_patient_revenue * h.operating_margin_on_npr / 1e6
        page = render_hcris_xray_page({"ccn": [self.healthy_ccn]})
        m = re.search(r"\(9\.0. \$([0-9,]+(?:\.[0-9])?)M EBITDA", page)
        self.assertIsNotNone(m, "EBITDA seed line not found")
        shown = float(m.group(1).replace(",", ""))
        self.assertAlmostEqual(shown, round(expected_m, 1), delta=0.15)


if __name__ == "__main__":
    unittest.main()
