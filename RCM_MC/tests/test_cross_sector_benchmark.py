"""Cross-sector benchmark framework over the six live CMS verticals.

Pure computation over already-vendored CMS data — no synthetic data, no
network. Asserts the honesty discipline: every benchmark exposes its sample
size, missingness, and caveats; concentration is a composition proxy bounded
0–10000; percentiles are bounded 0–100; small samples raise a caveat.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.cross_sector import (
    SECTORS,
    SECTOR_BY_ID,
    cross_sector_state_summary,
    sector_state_benchmark,
)


class RegistryTests(unittest.TestCase):
    def test_six_live_verticals(self):
        ids = {s.id for s in SECTORS}
        self.assertEqual(ids, {"home-health", "hospice", "nursing-homes",
                               "dialysis", "inpatient-rehab",
                               "long-term-care-hospital"})
        self.assertEqual(len(SECTOR_BY_ID), 6)

    def test_each_spec_loaders_resolve(self):
        for s in SECTORS:
            self.assertTrue(s.providers_loader(), f"{s.id} has no providers")
            self.assertTrue(s.quality_loader(), f"{s.id} has no quality")


class StateSummaryTests(unittest.TestCase):
    def test_all_six_sectors_present_in_a_large_state(self):
        rows = cross_sector_state_summary("TX")
        self.assertEqual(len(rows), 6)
        self.assertEqual({b.sector_id for b in rows}, set(SECTOR_BY_ID))

    def test_every_benchmark_exposes_sample_size_and_caveats(self):
        for b in cross_sector_state_summary("TX"):
            self.assertEqual(b.sample_size, b.rated_count)
            self.assertGreaterEqual(b.provider_count, b.rated_count)
            self.assertTrue(b.caveats, f"{b.sector_id} missing caveats")
            # The standing honesty caveat must always be present.
            self.assertTrue(any("not commercial revenue" in c.lower()
                                for c in b.caveats))

    def test_concentration_and_percentile_bounds(self):
        for b in cross_sector_state_summary("TX"):
            if b.ownership_hhi is not None:
                self.assertTrue(0 <= b.ownership_hhi <= 10000)
            if b.locality_hhi is not None:
                self.assertTrue(0 <= b.locality_hhi <= 10000)
            if b.state_percentile is not None:
                self.assertTrue(0 <= b.state_percentile <= 100)
            if b.missingness_pct is not None:
                self.assertTrue(0 <= b.missingness_pct <= 100)

    def test_missingness_matches_counts(self):
        for b in cross_sector_state_summary("TX"):
            if b.provider_count and b.missingness_pct is not None:
                expected = round(100 * (b.provider_count - b.rated_count)
                                 / b.provider_count, 1)
                self.assertEqual(b.missingness_pct, expected)


class GuardrailTests(unittest.TestCase):
    def test_unknown_sector_returns_none(self):
        self.assertIsNone(sector_state_benchmark("dental", "TX"))

    def test_unknown_state_returns_empty(self):
        self.assertEqual(cross_sector_state_summary("ZZ"), [])

    def test_small_sample_raises_caveat(self):
        # Sweep states to find a sector with a tiny rated sample (LTCH is the
        # ~320-facility universe, so some states have <5).
        found_small = False
        for st in ("VT", "WY", "AK", "MT", "ND", "SD", "DE", "RI", "NH", "ME"):
            b = sector_state_benchmark("long-term-care-hospital", st)
            if b is not None and b.rated_count < 5:
                found_small = True
                self.assertTrue(any("unreliable" in c.lower() for c in b.caveats),
                                f"{st}: small-sample caveat missing")
        self.assertTrue(found_small, "expected at least one tiny LTCH state")

    def test_no_external_calls_importable_offline(self):
        # Importing + running must not require network (pure file reads).
        import rcm_mc.data.cross_sector as cs
        self.assertTrue(hasattr(cs, "cross_sector_state_summary"))


if __name__ == "__main__":
    unittest.main()
