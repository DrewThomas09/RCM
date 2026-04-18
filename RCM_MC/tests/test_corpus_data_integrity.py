"""Corpus data integrity guards — Phase 6C proactive scan.

Asserts that every seed deal in the 655-deal corpus has its numeric
fields inside plausible envelopes. Bounds here are intentionally
WIDER than the UI sanity guards in rcm_mc/ui/chartis/_sanity.py so
only genuine unit bugs / sign flips / data-entry typos fire — not
legitimate tail events.

If a new failing row appears, investigate before widening the
envelope further. The point of this file is to catch regressions
where a new corpus entry slips in with a bad value.
"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List, Tuple


def _load_corpus() -> List[Dict[str, Any]]:
    # Use the same loader the UI uses so any bug in the loader
    # surfaces here too.
    from rcm_mc.ui.chartis._helpers import load_corpus_deals
    return load_corpus_deals()


def _collect_offenders(
    corpus: List[Dict[str, Any]],
    field: str,
    lo: float,
    hi: float,
) -> List[Tuple[str, float]]:
    """Return (source_id, value) for every row whose ``field`` falls
    outside [lo, hi]. Nil values are skipped — they're not integrity
    violations."""
    bad: List[Tuple[str, float]] = []
    for d in corpus:
        v = d.get(field)
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f < lo or f > hi:
            bad.append((str(d.get("source_id", "?")), f))
    return bad


class TestCorpusIntegrity(unittest.TestCase):
    """Integrity bounds per field. These envelopes are wider than the
    UI sanity bands because they're calibrated for corpus *data*
    sanity, not per-deal *partner* sanity — a legitimate 80% single-
    deal IRR can exist, but a 15,000% one cannot; a legitimate 0.0x
    MOIC (total loss) can exist, but a -0.5x one cannot."""

    @classmethod
    def setUpClass(cls):
        cls.corpus = _load_corpus()

    def test_realized_irr_envelope(self):
        """Realized IRR must be in [-1.0, 2.0]. -100% = total loss;
        above 200% requires extraordinary short hold + high MOIC and
        should be spot-checked."""
        bad = _collect_offenders(self.corpus, "realized_irr", -1.0, 2.0)
        self.assertEqual(
            [], bad,
            f"corpus has {len(bad)} row(s) with out-of-envelope "
            f"realized_irr: {bad[:10]}",
        )

    def test_realized_moic_envelope(self):
        """Realized MOIC must be in [0.0, 15.0]. Below 0 is non-sense
        (MOIC is multiple OF invested capital — cannot be negative);
        above 15x is an extraordinary home run that should be spot-
        checked."""
        bad = _collect_offenders(self.corpus, "realized_moic", 0.0, 15.0)
        self.assertEqual(
            [], bad,
            f"corpus has {len(bad)} row(s) with out-of-envelope "
            f"realized_moic: {bad[:10]}",
        )

    def test_hold_years_envelope(self):
        """Hold period must be in [0.1, 20.0]. Above 20y is implausible
        (even zombie funds wind down eventually); below 0.1y = days,
        which the backend doesn't model."""
        bad = _collect_offenders(self.corpus, "hold_years", 0.1, 20.0)
        self.assertEqual(
            [], bad,
            f"corpus has {len(bad)} row(s) with out-of-envelope "
            f"hold_years: {bad[:10]}",
        )

    def test_leverage_envelope(self):
        """Leverage at close must be in [0.0, 15.0]. >15x is covenant-
        trip-at-close territory. Note: leverage_pct in the corpus is
        a % (fraction of EV as debt), not a multiple — that's range
        [0, 1]."""
        bad = _collect_offenders(self.corpus, "leverage_multiple", 0.0, 15.0)
        self.assertEqual(
            [], bad,
            f"corpus has {len(bad)} row(s) with out-of-envelope "
            f"leverage_multiple: {bad[:10]}",
        )

    def test_ebitda_margin_envelope(self):
        """EBITDA margin in [-0.50, 0.60]. Negative = operating loss;
        positive extremes = high-margin specialty businesses (ASCs,
        dental DSOs). Above 60% = data bug."""
        bad = _collect_offenders(self.corpus, "ebitda_margin", -0.50, 0.60)
        self.assertEqual(
            [], bad,
            f"corpus has {len(bad)} row(s) with out-of-envelope "
            f"ebitda_margin: {bad[:10]}",
        )

    def test_irr_moic_no_order_of_magnitude_error(self):
        """For rows carrying realized_moic + realized_irr + hold_years,
        verify (1 + irr)^hold ≈ moic within 2× / ½× — i.e. no order-
        of-magnitude unit mix-up (e.g. IRR stored as 78 instead of
        0.78, or sign-flipped IRR paired with positive MOIC).

        Tolerance is intentionally loose (2×) because many seed rows
        were hand-crafted with IRR and MOIC entered independently;
        20-30% compounding discrepancies are common and acceptable.
        What we're catching is the class of bug Phase 6 started with:
        Walgreens' 124% IRR on a 5x 2y deal was math-consistent but
        the REATTRIBUTION was wrong; this test catches a different
        class — where the row's own IRR/MOIC numbers are mutually
        inconsistent by a large factor.
        """
        bad = []
        for d in self.corpus:
            moic = d.get("realized_moic")
            irr = d.get("realized_irr")
            hold = d.get("hold_years")
            if None in (moic, irr, hold):
                continue
            try:
                m, r, h = float(moic), float(irr), float(hold)
            except (TypeError, ValueError):
                continue
            if h <= 0 or m <= 0:
                continue
            implied_moic = (1.0 + r) ** h
            # 2× / ½× tolerance — catches order-of-magnitude errors
            # (e.g. IRR 78 vs 0.78) but not hand-crafted rounding.
            ratio = implied_moic / m
            if not (0.5 <= ratio <= 2.0):
                bad.append(
                    (str(d.get("source_id", "?")), m, r, h, round(implied_moic, 2))
                )
        self.assertEqual(
            [], bad,
            f"{len(bad)} corpus rows have IRR/MOIC/hold math that "
            f"fails the (1+irr)^hold ≈ moic check by > 2×; "
            f"{bad}",
        )


if __name__ == "__main__":
    unittest.main()
