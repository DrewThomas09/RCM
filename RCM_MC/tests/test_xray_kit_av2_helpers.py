"""xray_kit Results A-v2 primitives (PR 1).

New helpers for the HCRIS X-Ray rebuild: trend chart, row sparkline, payer
stack, deviation card, EBITDA bridge. All must render honest empty states (no
fabricated geometry / values) and ship no external scripts.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui import xray_kit as k


class TrendChartTests(unittest.TestCase):
    def test_two_line_renders(self):
        h = k.xr_trend_chart([1.0, 2.0, 3.0], [1.5, 1.6, 1.7],
                             labels=["FY20", "FY21", "FY22"])
        self.assertIn("<svg", h)
        self.assertIn("polyline", h)
        self.assertIn("FY22", h)

    def test_target_only_notes_peer_unavailable(self):
        h = k.xr_trend_chart([1.0, 2.0, 3.0], None)
        self.assertIn("Peer trend unavailable", h)   # honest, not fabricated

    def test_too_sparse_is_empty_state(self):
        self.assertIn("Trend unavailable", k.xr_trend_chart([1.0], None))


class RowSparkTests(unittest.TestCase):
    def test_renders_and_sparse_state(self):
        self.assertIn("polyline", k.xr_row_spark([1, 2, 3], "above"))
        self.assertIn("unavailable", k.xr_row_spark([1], "above"))


class PayerStackTests(unittest.TestCase):
    def test_renders_segments_and_legend(self):
        h = k.xr_payer_stack("STROGER", {"medicare": 9.5, "medicaid": 11.8,
                                         "commercial": 78.7})
        for seg in ("Medicare", "Medicaid", "Commercial"):
            self.assertIn(seg, h)

    def test_empty_mix_is_honest(self):
        self.assertIn("unavailable", k.xr_payer_stack("X", {}))


class DevCardTests(unittest.TestCase):
    def test_renders_with_band_and_trend(self):
        h = k.xr_dev_card(
            "Net-to-gross", state="above", value_html="1.20x", delta_html="+10%",
            band={"lo": 0, "hi": 2, "p25": 0.5, "median": 1.0, "p75": 1.5,
                  "target": 1.2, "state": "above"},
            trend=[1.0, 1.1, 1.2], caption="vs peer median")
        self.assertIn("xr-dev", h)
        self.assertIn("Net-to-gross", h)
        self.assertIn("ABOVE", h)


class EbitdaBridgeTests(unittest.TestCase):
    def test_renders_rows_and_labeled_assumption(self):
        h = k.xr_ebitda_bridge(
            [{"label": "Target op margin", "pp": -22.4, "kind": "target",
              "value_label": "-22.4pp"},
             {"label": "Close gap to peer median", "pp": -8.1, "kind": "step",
              "value_label": "+14.3pp"}],
            recoverable_html="+$135M EBITDA gap",
            assumption_note="Illustrative EV @ 9.0x — an assumption, not a valuation.")
        self.assertIn("xr-bridge-row", h)
        self.assertIn("assumption", h.lower())          # EV is labeled assumption
        self.assertNotIn("recoverable value", h.lower())  # never claims valuation

    def test_empty_is_honest(self):
        self.assertIn("unavailable", k.xr_ebitda_bridge([]))


class NoExternalScriptsTests(unittest.TestCase):
    def test_helpers_have_no_cdn(self):
        blobs = [
            k.xr_trend_chart([1, 2, 3]), k.xr_row_spark([1, 2, 3]),
            k.xr_payer_stack("X", {"medicare": 1, "medicaid": 1, "commercial": 1}),
            k.xr_ebitda_bridge([{"label": "x", "pp": 1, "kind": "target", "value_label": "1"}]),
        ]
        for h in blobs:
            low = h.lower()
            for bad in ("http://", "https://", "unpkg", "cdn", "<script"):
                self.assertNotIn(bad, low)


if __name__ == "__main__":
    unittest.main()
