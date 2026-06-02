"""The verified-deal dataset — real, sourced healthcare-services PE deals.

The bundled 605-deal corpus is synthetic seed data (invented names, seed_NNN
ids). This dataset is the opposite: every row is a real deal with a real source
URL — the seed of the "verify every deal online" effort. EV is recorded only
where publicly disclosed (None otherwise; never fabricated). These guards keep
the dataset honest as it grows.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public.verified_deals import (
    SECTORS,
    VERIFIED_DEALS,
    disclosed_ev_count,
    verified_deal_count,
    verified_deals,
)

_REQUIRED = (
    "target", "sponsor", "year", "ev_usd_mm", "sector", "subsector_note",
    "outcome", "outcome_note", "source_url", "source_note",
)
_OUTCOMES = {"active", "exited", "bankrupt", "distressed", "unknown"}


class VerifiedDealDataTests(unittest.TestCase):
    def test_every_deal_is_well_formed_and_sourced(self) -> None:
        self.assertGreaterEqual(len(VERIFIED_DEALS), 20)
        for d in VERIFIED_DEALS:
            for k in _REQUIRED:
                self.assertIn(k, d, f"{d.get('target')} missing {k}")
            # real source URL on every single deal
            self.assertTrue(str(d["source_url"]).startswith("http"),
                            f"{d['target']} has no real source URL")
            self.assertIn(d["sector"], SECTORS)
            self.assertIn(d["outcome"], _OUTCOMES)
            self.assertIsInstance(d["year"], int)
            # EV is either a positive number or genuinely None — never 0/guess
            ev = d["ev_usd_mm"]
            self.assertTrue(ev is None or (isinstance(ev, (int, float)) and ev > 0))

    def test_includes_marquee_failure_cases(self) -> None:
        # Real, public bankruptcies are the credibility anchors — a corpus of
        # only invented winners is the tell of fabricated data.
        targets = " ".join(d["target"] for d in VERIFIED_DEALS)
        for anchor in ("Steward", "Envision", "Prospect", "Cano"):
            self.assertIn(anchor, targets)
        bankrupts = [d for d in VERIFIED_DEALS if d["outcome"] == "bankrupt"]
        self.assertGreaterEqual(len(bankrupts), 4)

    def test_no_synthetic_seed_ids(self) -> None:
        # Guard against anyone pasting synthetic corpus rows in here.
        for d in VERIFIED_DEALS:
            self.assertNotIn("seed_", str(d.get("source_url", "")))
            self.assertNotEqual(d.get("sponsor"), "Clearfield Capital")

    def test_no_duplicate_targets(self) -> None:
        # A target appearing twice means a deal was double-entered (e.g.
        # Modernizing Medicine once under Warburg and again, mistakenly,
        # under Vista). One row per real company.
        from collections import Counter
        dups = [t for t, c in Counter(
            d["target"] for d in VERIFIED_DEALS).items() if c > 1]
        self.assertEqual(dups, [], f"duplicate verified-deal targets: {dups}")

    def test_sector_filter_and_counts(self) -> None:
        self.assertEqual(verified_deal_count(), len(VERIFIED_DEALS))
        rcm = verified_deals("rcm_healthtech")
        self.assertTrue(rcm and all(d["sector"] == "rcm_healthtech" for d in rcm))
        self.assertEqual(verified_deals("not_a_sector"), [])
        # some EVs disclosed, some honestly null
        self.assertGreater(disclosed_ev_count(), 0)
        self.assertLess(disclosed_ev_count(), verified_deal_count())


if __name__ == "__main__":
    unittest.main()
