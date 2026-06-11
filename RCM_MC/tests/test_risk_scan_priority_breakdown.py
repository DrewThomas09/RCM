"""Wave-16 visual: portfolio risk-scan priority decomposition.

The scan sorts deals by a composite priority score the reader never
sees — "first row because covenant tripped" vs "first row because
four deadlines slipped" was invisible. Pins the stacked-bar SVG:
component arithmetic matches _priority_rank exactly, quiet deals are
skipped, and an all-quiet portfolio renders nothing.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.portfolio_risk_scan_page import (
    _priority_breakdown_svg,
    _priority_components,
    _priority_rank,
)


def _deal(**kw):
    base = {
        "name": "Test Deal", "covenant_status": None,
        "overdue_deadlines": 0, "alerts": 0, "score": None,
        "snap_age_days": None,
    }
    base.update(kw)
    return base


class PriorityComponentsTests(unittest.TestCase):
    def test_components_sum_to_priority_rank(self):
        deals = [
            _deal(covenant_status="TRIPPED", alerts=2, score=35,
                  snap_age_days=70, overdue_deadlines=1),
            _deal(covenant_status="TIGHT", score=55, snap_age_days=40),
            _deal(),
        ]
        for d in deals:
            self.assertEqual(sum(_priority_components(d)),
                             _priority_rank(d))


class PriorityBreakdownSvgTests(unittest.TestCase):
    def test_renders_ranked_bars_with_legend(self):
        svg = _priority_breakdown_svg([
            _deal(name="Quiet Deal"),
            _deal(name="Tripped Deal", covenant_status="TRIPPED"),
            _deal(name="Stale Deal", snap_age_days=45),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("rs-priority-breakdown", svg)
        self.assertIn("Why these deals rank first", svg)
        # Highest priority leads; quiet deal skipped entirely.
        self.assertLess(svg.index("Tripped Deal"), svg.index("Stale Deal"))
        self.assertNotIn("Quiet Deal", svg)
        # Legend names every source.
        for lbl in ("Covenant", "Overdue deadlines", "Alerts",
                    "Health score", "Stale snapshot"):
            self.assertIn(lbl, svg)

    def test_totals_printed(self):
        svg = _priority_breakdown_svg(
            [_deal(name="D", covenant_status="TRIPPED", alerts=1)])
        self.assertIn(">105</text>", svg)  # 100 covenant + 5 alerts

    def test_all_quiet_portfolio_renders_nothing(self):
        self.assertEqual(_priority_breakdown_svg([_deal(), _deal()]), "")
        self.assertEqual(_priority_breakdown_svg([]), "")


if __name__ == "__main__":
    unittest.main()
