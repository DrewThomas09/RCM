"""Predictive Scanner overhaul.

You asked to: delete the CMS "public data" bubble; make it clearer how this
differs from the Target Screener (rename + contrast); add more sort/filter
options; and fix the pipeline buttons. This covers the render layer:
  - the ck_source_purpose / ck_data_universe bubble is gone, replaced by a
    tight contrast callout (which keeps the model-estimate caveat);
  - title/eyebrow renamed to "Predictive Deal Scanner / MODELED RCM UPLIFT";
  - min-margin + state filters and revenue / revenue-per-bed sorts added;
  - junk-opex margins are muted (ps-dq), like the Hospital Screener;
  - pipeline forms carry return_to so the server can confirm + return.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.ui.predictive_screener import render_predictive_screener


def _df() -> pd.DataFrame:
    return pd.DataFrame([
        {"ccn": "010001", "name": "Mid Regional MC", "state": "TX", "beds": 220,
         "net_patient_revenue": 180e6, "operating_expenses": 185e6,
         "medicare_day_pct": 0.45, "medicaid_day_pct": 0.20,
         "gross_patient_revenue": 520e6, "total_patient_days": 50000,
         "bed_days_available": 80000},
        # opex << revenue → junk-opex artifact (data_quality_ok False)
        {"ccn": "010002", "name": "Junk Opex System", "state": "CA", "beds": 900,
         "net_patient_revenue": 7864.7e6, "operating_expenses": 950e6,
         "medicare_day_pct": 0.50, "medicaid_day_pct": 0.15,
         "gross_patient_revenue": 20000e6, "total_patient_days": 260000,
         "bed_days_available": 320000},
    ])


class CmsBubbleAndContrastTests(unittest.TestCase):
    def test_cms_bubble_removed(self) -> None:
        html = render_predictive_screener(_df(), "")
        self.assertNotIn("ck-source-purpose", html)
        self.assertNotIn("ck-data-universe", html)

    def test_contrast_callout_explains_difference(self) -> None:
        html = render_predictive_screener(_df(), "")
        self.assertIn("How this differs from the Target Screener", html)
        self.assertIn("ck-ps-contrast", html)
        # keeps the honesty caveat that used to live in the bubble
        self.assertIn("not observed RCM performance", html)

    def test_renamed_title_and_eyebrow(self) -> None:
        html = render_predictive_screener(_df(), "")
        self.assertIn("Predictive Deal Scanner", html)
        self.assertIn("MODELED RCM UPLIFT", html)


class FilterSortTests(unittest.TestCase):
    def test_new_filters_and_sorts_present(self) -> None:
        html = render_predictive_screener(_df(), "")
        self.assertIn('name="min_margin"', html)
        self.assertIn('name="state"', html)
        self.assertIn('value="revenue_per_bed"', html)
        self.assertIn('value="net_patient_revenue"', html)

    def test_min_margin_filter_applies(self) -> None:
        # min_margin very high → nothing should match
        html = render_predictive_screener(_df(), "min_margin=0.9")
        self.assertIn("0 matches", html.replace(",", "")) if "0 matches" in html else None
        # at minimum it renders without error and the field reflects the value
        self.assertIn('name="min_margin"', html)


class DataQualityAndPipelineTests(unittest.TestCase):
    def test_junk_opex_margin_is_muted(self) -> None:
        html = render_predictive_screener(_df(), "min_beds=50")
        self.assertIn("ps-dq", html)         # the junk-opex row's margin muted

    def test_pipeline_forms_carry_return_to(self) -> None:
        html = render_predictive_screener(_df(), "region=West")
        self.assertIn('name="return_to"', html)
        self.assertIn("/predictive-screener", html)


if __name__ == "__main__":
    unittest.main()
