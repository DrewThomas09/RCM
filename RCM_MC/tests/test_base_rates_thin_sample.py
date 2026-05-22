"""Base-rate percentile rows over a thin sample are flagged honestly.

Percentiles computed over fewer than 10 matched deals swing on
individual exits, so they're directional only. The percentile table
now marks low-n rows (warning tone + a † marker) and footnotes the
caveat, so an n=4 row never reads as authoritatively as an n=200 row.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.data_public.base_rates_page import _percentile_table


class _Row:
    def __init__(self, metric, n):
        self.metric = metric
        self.n = n
        self.p25, self.p50, self.p75, self.p90 = 1.0, 2.0, 3.0, 4.0
        self.mean, self.min, self.max = 2.5, 0.5, 5.0


class BaseRatesThinSampleTests(unittest.TestCase):
    def test_thin_row_flagged_with_footnote(self):
        html = _percentile_table([_Row("EV/EBITDA", 220), _Row("IRR", 4)])
        self.assertIn("†", html)              # dagger marker
        self.assertIn("thin sample", html)
        self.assertIn("directional only", html)

    def test_no_footnote_when_all_robust(self):
        html = _percentile_table([_Row("EV/EBITDA", 220), _Row("IRR", 180)])
        self.assertNotIn("†", html)
        self.assertNotIn("thin sample", html)


if __name__ == "__main__":
    unittest.main()
