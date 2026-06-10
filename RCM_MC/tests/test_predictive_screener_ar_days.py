"""Est. AR Days column on the predictive screener.

est_ar_days was computed and sortable but had NO table column — a partner
could sort by an invisible value. It now renders as a PREDICTED-badged column
with a '?' calc-explainer and the 25–75 day plausible bound, matching the
Est. Denial / Est. Uplift treatment. Thin-data rows still show '—'.
"""
import unittest

import pandas as pd

from rcm_mc.ui.predictive_screener import render_predictive_screener

_BASE = dict(bed_days_available=73000, total_patient_days=50000,
             medicare_day_pct=0.4, medicaid_day_pct=0.15)


def _render(rows):
    return render_predictive_screener(pd.DataFrame(rows), "")


class ArDaysColumnTests(unittest.TestCase):
    def _complete_rows(self):
        return [
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9, **_BASE},
            {"ccn": "333333", "name": "OTHER GENERAL", "state": "TX",
             "beds": 180, "net_patient_revenue": 4e8,
             "operating_expenses": 3.7e8, "gross_patient_revenue": 1e9, **_BASE},
        ]

    def test_header_has_ar_days_with_predicted_badge_and_explainer(self):
        h = _render(self._complete_rows())
        self.assertIn("Est. AR Days", h)
        # explainer text + the plausible bound are stated
        self.assertIn("Days in accounts receivable modeled", h)
        self.assertIn("25–75 day", h)   # 25–75 day plausible A/R range
        self.assertIn("prediction_bounds", h)

    def test_complete_row_shows_a_day_count_in_range(self):
        import re
        h = _render(self._complete_rows())
        crow = h[h.find("COMPLETE GENERAL"):h.find("COMPLETE GENERAL") + 1100]
        # a whole-number AR-days cell renders (clamped 25..75)
        days = [int(m) for m in re.findall(r'class="num">(\d+)</td>', crow)]
        self.assertTrue(any(25 <= d <= 75 for d in days),
                        f"expected an AR-days value in 25..75, got {days}")

    def test_thin_data_row_shows_dash_for_ar_days(self):
        h = _render([
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9, **_BASE},
            {"ccn": "444444", "name": "TINY CRITICAL ACCESS", "state": "TX",
             "beds": 8, "net_patient_revenue": 4e4,
             "operating_expenses": 5e4, "gross_patient_revenue": 9e4, **_BASE},
        ])
        row = h[h.find("TINY CRITICAL ACCESS"):h.find("TINY CRITICAL ACCESS") + 1100]
        self.assertIn("ps-na", row)

    def test_header_and_body_column_counts_match(self):
        import re
        h = _render(self._complete_rows())
        # Anchor on the results table specifically: its header row is the one
        # carrying the Est.* columns (other <thead>/<tbody> strings live in
        # the page's CSS comments, so a generic regex grabs the wrong block).
        hdr_start = h.find("<th>CCN</th>")
        self.assertGreater(hdr_start, 0)
        header = h[hdr_start:h.find("</tr>", hdr_start)]
        n_th = len(re.findall(r"<th[ >]", header))
        # The data row is the <tr> that contains a hospital CCN link.
        row_start = h.find('<tr>', h.find("COMPLETE GENERAL") - 400)
        data_row = h[row_start:h.find("</tr>", h.find("COMPLETE GENERAL"))]
        n_td = len(re.findall(r"<td[ >]", data_row))
        self.assertEqual(n_th, n_td,
                         f"header {n_th} cols vs row {n_td} cols")


class ModelCardFooterTests(unittest.TestCase):
    """The screener's modeling-discipline line reads ONLY the checked-in
    model-card artifact and states the honesty boundary (this page's Est.*
    are screening formulas, not the conformal model)."""

    def test_line_states_artifact_numbers_and_boundary(self):
        import json
        from pathlib import Path
        from rcm_mc.ui.predictive_screener import _model_card_line
        card = json.loads(
            (Path("rcm_mc/ml/model_card_margin.json")).read_text())
        line = _model_card_line()
        self.assertIn(f'{card["empirical_holdout_coverage"]:.1%}', line)
        self.assertIn(f'{card["n_test"]:,}', line)
        self.assertIn("/methodology", line)
        self.assertIn("simpler screening formulas", line)   # boundary stated

    def test_page_renders_the_line(self):
        h = _render([
            {"ccn": "111111", "name": "COMPLETE GENERAL", "state": "TX",
             "beds": 200, "net_patient_revenue": 5e8,
             "operating_expenses": 4.6e8, "gross_patient_revenue": 1.2e9,
             **_BASE}])
        self.assertIn("Modeling discipline", h)
        self.assertIn("model card", h)


if __name__ == "__main__":
    unittest.main()
