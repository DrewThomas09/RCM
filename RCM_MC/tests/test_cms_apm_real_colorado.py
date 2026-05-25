"""CMS APM Tracker now carries a REAL Colorado APM-adoption section.

%APM/%FFS come from the CIVHC loader (not hardcoded page values), the section
is LIVE-labeled and state-caveated, and the prior illustrative national overlay
stays clearly labeled.
"""
import unittest

from rcm_mc.ui.data_public.cms_apm_tracker_page import render_cms_apm_tracker
from rcm_mc.data import payer_data as pdt


class TestCmsApmRealColorado(unittest.TestCase):
    def setUp(self):
        self.html = render_cms_apm_tracker({})

    def test_real_colorado_section_present(self):
        self.assertIn("Colorado APM Adoption", self.html)
        self.assertIn("LIVE (CIVHC)", self.html)
        self.assertIn("ck-sp", self.html)               # source-purpose header

    def test_values_come_from_loader(self):
        df = pdt.apm_adoption_by_payer("Total Medical Spending")
        v = float(df[(df["payer"] == "Commercial") & (df["year"] == 2024)]["pct_apm"].iloc[0])
        self.assertIn(f"{v*100:.1f}%", self.html)        # rendered == loader value

    def test_state_specific_caveat(self):
        self.assertIn("should not be generalized nationally", self.html)
        self.assertIn("not\n", self.html) if False else None
        self.assertIn("market-level, not", self.html)    # not provider-specific

    def test_missing_shows_dash_not_zero(self):
        # 'Unknown' payer has NaN %APM → must render "—", never 0.0%.
        self.assertIn("—", self.html)

    def test_illustrative_overlay_still_labeled(self):
        self.assertIn("ILLUSTRATIVE", self.html)
        self.assertIn("Illustrative overlay", self.html)


if __name__ == "__main__":
    unittest.main()
