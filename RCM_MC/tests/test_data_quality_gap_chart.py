"""Wave-33 visual: data-quality gap census chart.

The gap census listed gaps per metric in a table; which metrics are
most gapped — and whether the gaps are fixable (re-ingest/external)
or filing artifacts — required reading every row. Pins the bar
chart: worst-first order, fill-kind tones, zero-gap metrics skipped,
the 15-row cap, and the empty state.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_quality_page import _FILL_KIND_TONES, _gap_census_svg


def _r(label, gap_pct, gaps, kind):
    return {"label": label, "gap_pct": gap_pct, "gaps": gaps,
            "fill_kind": kind, "source": "src"}


class GapCensusChartTests(unittest.TestCase):
    def test_renders_bars_with_fill_kind_tones(self):
        svg = _gap_census_svg([
            _r("Operating margin", 12.5, 7650, "reingest"),
            _r("Bad debt", 4.2, 2570, "external"),
            _r("Negative days", 0.8, 490, "artifact"),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("ck-gap-census", svg)
        for kind in ("reingest", "external", "artifact"):
            self.assertIn(_FILL_KIND_TONES[kind], svg)
        self.assertIn("12.5% · 7,650", svg)
        self.assertIn("Filing artifact", svg)

    def test_worst_first_order(self):
        svg = _gap_census_svg([
            _r("Mild", 1.0, 600, "reingest"),
            _r("Severe", 20.0, 12000, "external"),
        ])
        self.assertLess(svg.index("Severe"), svg.index("Mild"))

    def test_zero_gap_metrics_skipped_and_cap(self):
        rows = [_r(f"m{i}", float(i), i * 10, "reingest")
                for i in range(0, 30)]
        svg = _gap_census_svg(rows)
        self.assertNotIn(">m0<", svg)          # zero-gap skipped
        self.assertEqual(svg.count("<rect"), 15)
        self.assertIn("worst 15 shown", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_gap_census_svg([]), "")
        self.assertEqual(
            _gap_census_svg([_r("Clean", 0.0, 0, "reingest")]), "")


if __name__ == "__main__":
    unittest.main()
