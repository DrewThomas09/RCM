"""Sponsor track record numerical integrity — Phase 6 bug-fix guards.

These tests pin down specific per-sponsor numeric expectations on the
corpus data. Each test documents the bug it was written to catch; if
the test later fails, the corpus or aggregator regressed.
"""
from __future__ import annotations

import unittest


def _walgreens_record():
    from rcm_mc.data_public.sponsor_track_record import sponsor_league_table
    from rcm_mc.ui.chartis._helpers import load_corpus_deals
    recs = sponsor_league_table(load_corpus_deals(), min_deals=2)
    walg = [r for r in recs if "walgreens" in r.sponsor.lower()]
    return walg


def _cvs_record():
    from rcm_mc.data_public.sponsor_track_record import sponsor_league_table
    from rcm_mc.ui.chartis._helpers import load_corpus_deals
    recs = sponsor_league_table(load_corpus_deals(), min_deals=2)
    return [r for r in recs if "cvs" in r.sponsor.lower()]


def _advent_record():
    from rcm_mc.data_public.sponsor_track_record import sponsor_league_table
    from rcm_mc.ui.chartis._helpers import load_corpus_deals
    recs = sponsor_league_table(load_corpus_deals(), min_deals=2)
    return [r for r in recs if "advent" in r.sponsor.lower()]


class TestWalgreensBug2(unittest.TestCase):
    """Phase 6 Bug #2 — Walgreens aggregated to median IRR 78%.

    Root cause: seed_600 (Shields Health Solutions / Summit Partners
    exit) was attributed to Walgreens as buyer, but the realized
    MOIC/IRR on the row belong to Summit Partners — the selling
    sponsor, not the strategic acquirer. Aggregating Summit's 124%
    IRR exit under Walgreens' sponsor ledger produced the implausible
    78% median.
    """

    def test_walgreens_median_irr_within_range(self):
        """Post-fix, Walgreens' median IRR must be inside [-30%, +55%]."""
        walg = _walgreens_record()
        # Walgreens may appear as "Walgreens" and/or "Walgreens Boots
        # Alliance" — check every variant.
        self.assertTrue(walg, "no Walgreens records in league table")
        for r in walg:
            if r.median_irr is None:
                continue
            self.assertGreaterEqual(
                r.median_irr, -0.30,
                f"{r.sponsor} median_irr {r.median_irr} below plausible lower bound",
            )
            self.assertLessEqual(
                r.median_irr, 0.55,
                f"{r.sponsor} median_irr {r.median_irr} above plausible upper bound",
            )


class TestCvsBug1(unittest.TestCase):
    """Phase 6 Bug #1 — CVS Health aggregated to median IRR 60%.

    Root cause: CVS is a strategic acquirer (not a PE sponsor). Both
    seed_187 and seed_569 describe the CVS-Signify acquisition but
    credit CVS with the realizing PE sponsor's MOIC/IRR. The real
    exiting sponsor was New Mountain Capital.
    """

    def test_cvs_realized_irr_attribution_corrected(self):
        """Post-fix, either CVS has no realized rows (all reattributed
        to the selling PE sponsor) OR its median IRR is inside the
        plausible band."""
        cvs = _cvs_record()
        for r in cvs:
            if r.median_irr is None:
                continue
            self.assertGreaterEqual(r.median_irr, -0.30, f"{r.sponsor}")
            self.assertLessEqual(r.median_irr, 0.55, f"{r.sponsor}")


class TestAdventBug4(unittest.TestCase):
    """Phase 6 Bug #4 — Advent International aggregated to median IRR -38%.

    Root cause: seed_162 and seed_340 both describe Advent's 2021
    ATI Physical Therapy SPAC realization. Two rows for one event →
    three total Advent-IRR rows instead of two → median shifts to
    -38% instead of ~-2.5%.
    """

    def test_advent_median_irr_within_range(self):
        adv = _advent_record()
        self.assertTrue(adv, "no Advent records in league table")
        for r in adv:
            if r.median_irr is None:
                continue
            self.assertGreaterEqual(
                r.median_irr, -0.30,
                f"{r.sponsor} median_irr {r.median_irr} below plausible lower bound",
            )
            self.assertLessEqual(
                r.median_irr, 0.55,
                f"{r.sponsor} median_irr {r.median_irr} above plausible upper bound",
            )


if __name__ == "__main__":
    unittest.main()
