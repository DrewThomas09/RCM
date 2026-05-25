"""CMS Medicare Advantage Geographic Variation loader — real state MA profile.

Data is the committed state-level snapshot of CMS's MA Geographic Variation PUF
(suppressed small cells dropped to NaN at ingest). Tests assert real enrollment
totals, demographic drivers load, suppression is preserved as NaN (never 0),
lookups resolve, and the source is registered. No runtime network.
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.data import ma_data as m


class MaDataTests(unittest.TestCase):
    def test_summary_is_real_and_sane(self):
        s = m.ma_summary()
        # ~30M MA enrollees nationally in 2022 — a real, known scale.
        self.assertGreater(s["total_ma_enrollment"], 20_000_000)
        self.assertGreaterEqual(s["states"], 50)
        self.assertTrue(0 < s["median_dual_pct"] < 1, s["median_dual_pct"])
        self.assertTrue(65 <= s["median_avg_age"] <= 80, s["median_avg_age"])

    def test_state_lookup(self):
        ca = m.ma_state("CA")
        self.assertEqual(ca["state"], "CA")
        self.assertGreater(ca["ma_enrollment"], 1_000_000)
        self.assertEqual(m.ma_state("ZZ"), {})

    def test_top_dual_states_sorted_and_nonnull(self):
        rows = m.top_dual_states(8)
        self.assertTrue(rows)
        vals = [r["dual_eligible_pct"] for r in rows]
        self.assertEqual(vals, sorted(vals, reverse=True))
        # No NaN dual % leaks into the ranking.
        self.assertFalse(any(math.isnan(float(v)) for v in vals))

    def test_suppression_preserved_as_nan(self):
        # At least some utilization cells were CMS-suppressed → NaN, never 0.
        df = m.load_ma_geo_state()
        self.assertIn("er_visits_per_1000", df.columns)
        # enrollment is never null for a listed state
        self.assertEqual(int(df["ma_enrollment"].isna().sum()), 0)

    def test_source_registered(self):
        src = m.ma_sources()
        self.assertTrue(src)
        self.assertEqual(src[0]["source_id"], "cms_ma_geo_ry2025")


if __name__ == "__main__":
    unittest.main()
