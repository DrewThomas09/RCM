"""Regression: the predictive screener is honest about data it doesn't have.

Two prior bugs made the screener fabricate values:
  • A hospital with no operating margin (missing NPR or opex) was coerced to
    0.0% and heat-coloured as if it were a real, healthy-ish result.
  • A prediction that couldn't be made (NaN — too little public data) was
    coerced to $0 / 0.0%, reading like a confident estimate of "no
    opportunity".

Both must render "—" (ps-na) instead. Predicted columns stay header-badged
PREDICTED (test_screener_basis_badge). See render_predictive_screener.
"""
import unittest

import pandas as pd

from rcm_mc.ui.predictive_screener import render_predictive_screener

_BASE = dict(bed_days_available=73000, total_patient_days=50000,
             medicare_day_pct=0.4, medicaid_day_pct=0.15)


def _render(rows):
    return render_predictive_screener(pd.DataFrame(rows), "")


class MissingMarginHonestyTests(unittest.TestCase):
    def test_missing_opex_margin_renders_dash_not_zero(self):
        html = _render([
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9, **_BASE},
            {"ccn": "222222", "name": "NO OPEX FILED", "state": "TX",
             "beds": 150, "net_patient_revenue": 3e8,
             "operating_expenses": None, "gross_patient_revenue": 7e8, **_BASE},
        ])
        row = html[html.find("NO OPEX FILED"):html.find("NO OPEX FILED") + 800]
        self.assertIn("ps-na", row)                      # "—" treatment
        self.assertNotIn("0.0%", row)                    # no fabricated zero
        self.assertIn("not reported, not estimated", row)  # honest tooltip

    def test_complete_hospital_still_shows_real_margin(self):
        html = _render([
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9, **_BASE},
            {"ccn": "333333", "name": "OTHER GENERAL", "state": "TX",
             "beds": 180, "net_patient_revenue": 4e8,
             "operating_expenses": 3.7e8, "gross_patient_revenue": 1e9, **_BASE},
        ])
        crow = html[html.find("COMPLETE GENERAL"):html.find("COMPLETE GENERAL") + 800]
        self.assertRegex(crow, r"\d+\.\d%")  # a real percent margin renders


class MissingPredictionHonestyTests(unittest.TestCase):
    def test_thin_data_estimate_renders_dash_not_zero(self):
        # Revenue below the $100k modelling floor → est_* come back NaN.
        # They must show "—", not $0 / 0.0%.
        html = _render([
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9, **_BASE},
            {"ccn": "444444", "name": "TINY CRITICAL ACCESS", "state": "TX",
             "beds": 8, "net_patient_revenue": 4e4,
             "operating_expenses": 5e4, "gross_patient_revenue": 9e4, **_BASE},
        ])
        row = html[html.find("TINY CRITICAL ACCESS"):html.find("TINY CRITICAL ACCESS") + 900]
        self.assertIn("ps-na", row)
        self.assertNotIn("$0", row)       # no fabricated uplift
        self.assertNotIn(">0.0%<", row)   # no fabricated denial


if __name__ == "__main__":
    unittest.main()
