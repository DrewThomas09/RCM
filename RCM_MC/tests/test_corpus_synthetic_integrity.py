"""Structural integrity check over synthetic corpus rows.

The synthetic corpus contains rows with factually impossible dates
(sponsors who already owned the target at the claimed year). This
pattern shouldn't survive even in synthetic mode, because any partner
who opens mode="synthetic" as "illustrative examples" will notice,
and the credibility cost is high.

Assertions (structural only — not trying to detect all fabrication):

  1. No deal has buyer == seller (can't acquire from yourself).
  2. No deal's year precedes the buyer's founded year (where the
     buyer's founding is known with high confidence).
  3. Deal year is plausible — 1990 ≤ year ≤ current_year + 1.

Violations are collected, asserted-against (test fails if any found),
and expected to fail initially. Per the Phase-B sprint plan the
offending rows are NOT modified — they're logged to
docs/SYNTHETIC_CORPUS_BUGS.md for a future corpus-regen pass and the
test is marked ``expectedFailure`` for now so CI stays green.
"""
from __future__ import annotations

import datetime as _dt
import re
import unittest
from typing import Any, Dict, List, Optional, Set, Tuple

from rcm_mc.data_public.corpus_loader import load_corpus_deals


# Sponsors whose founding year is documented and unambiguous. Small
# list by design — we'd rather miss a few violations than false-
# positive on a sponsor we got wrong. Add carefully.
SPONSOR_FOUNDED_YEAR = {
    "Apollo Global Management": 1990,
    "Ares Management": 1997,
    "Audax Private Equity": 1999,
    "Bain Capital": 1984,
    "Blackstone Group": 1985,
    "Carlyle Group": 1987,
    "Clayton Dubilier & Rice": 1978,  # CD&R
    "Francisco Partners": 1999,
    "General Atlantic": 1980,
    "Goldman Sachs Capital Partners": 1992,
    "GTCR": 1980,
    "H.I.G. Capital": 1993,
    "Hellman & Friedman": 1984,
    "KKR": 1976,
    "Kohlberg Kravis Roberts": 1976,  # alias for KKR
    "Leonard Green & Partners": 1989,
    "Madison Dearborn Partners": 1992,
    "New Mountain Capital": 1999,
    "Nordic Capital": 1989,
    "Partners Group": 1996,
    "Providence Equity Partners": 1989,
    "Silver Lake": 1999,
    "TA Associates": 1968,
    "TPG Capital": 1992,
    "Thoma Bravo": 2008,  # spin-off; Thoma Cressey predecessor 1980
    "Vista Equity Partners": 2000,
    "Warburg Pincus": 1966,
    "Welsh Carson Anderson & Stowe": 1979,
    "WCAS": 1979,  # alias
}


def _year(deal: Dict[str, Any]) -> Optional[int]:
    y = deal.get("year") or deal.get("deal_year")
    try:
        return int(y) if y is not None else None
    except (TypeError, ValueError):
        return None


def _label(deal: Dict[str, Any]) -> str:
    return (
        deal.get("deal_name")
        or deal.get("company_name")
        or deal.get("source_id")
        or "(unnamed)"
    )


def _match_founded_year(buyer_str: str) -> Optional[Tuple[str, int]]:
    """Return (sponsor, founded_year) if a sponsor name in our table
    appears as a substring of the buyer string; None otherwise."""
    if not isinstance(buyer_str, str):
        return None
    for sponsor, year in SPONSOR_FOUNDED_YEAR.items():
        # Word-boundary match so "KKR" doesn't match "WeKKR" or similar
        pattern = r"\b" + re.escape(sponsor) + r"\b"
        if re.search(pattern, buyer_str):
            return sponsor, year
    return None


class TestSyntheticCorpusIntegrity(unittest.TestCase):
    """Assertions are expected to fail on today's corpus — the failure
    surface is what lets us log specific offending rows. Each method
    collects violations and fails loudly with a row-count; see
    docs/SYNTHETIC_CORPUS_BUGS.md for the rolled-up list."""

    def setUp(self):
        self.deals = load_corpus_deals("synthetic")

    @unittest.expectedFailure  # 1 known violation — see docs/SYNTHETIC_CORPUS_BUGS.md
    def test_no_buyer_equals_seller(self):
        violations: List[str] = []
        for d in self.deals:
            buyer = (d.get("buyer") or "").strip()
            seller = (d.get("seller") or "").strip()
            if buyer and seller and buyer == seller:
                violations.append(f"{_label(d)} — buyer == seller == {buyer!r}")
        self.assertEqual(
            violations, [],
            f"{len(violations)} synthetic rows where buyer == seller",
        )

    def test_no_deal_year_before_buyer_founded(self):
        violations: List[str] = []
        for d in self.deals:
            y = _year(d)
            if y is None:
                continue
            match = _match_founded_year(d.get("buyer") or "")
            if match is None:
                continue
            sponsor, founded = match
            if y < founded:
                violations.append(
                    f"{_label(d)} — year={y} but {sponsor} "
                    f"wasn't founded until {founded}"
                )
        self.assertEqual(
            violations, [],
            f"{len(violations)} synthetic rows with a deal year "
            f"predating the buyer's founded year",
        )

    def test_deal_year_is_plausible(self):
        current_year = _dt.date.today().year
        lo, hi = 1990, current_year + 1
        violations: List[str] = []
        for d in self.deals:
            y = _year(d)
            if y is None:
                continue
            if y < lo or y > hi:
                violations.append(f"{_label(d)} — year={y} (outside {lo}..{hi})")
        self.assertEqual(
            violations, [],
            f"{len(violations)} synthetic rows with implausible deal years "
            f"(expected {lo}..{hi})",
        )


def _collect_violations() -> Dict[str, List[str]]:
    """Helper used by the reporting script (not a test). Returns a
    dict of violation_type -> list-of-row-labels so the commit log
    can emit counts + examples without re-running the tests."""
    deals = load_corpus_deals("synthetic")
    out: Dict[str, List[str]] = {
        "buyer_equals_seller": [],
        "year_before_buyer_founded": [],
        "year_out_of_range": [],
    }
    current_year = _dt.date.today().year
    for d in deals:
        buyer = (d.get("buyer") or "").strip()
        seller = (d.get("seller") or "").strip()
        if buyer and seller and buyer == seller:
            out["buyer_equals_seller"].append(
                f"{_label(d)} — buyer == seller == {buyer!r}"
            )
        y = _year(d)
        if y is not None:
            match = _match_founded_year(buyer)
            if match is not None:
                sponsor, founded = match
                if y < founded:
                    out["year_before_buyer_founded"].append(
                        f"{_label(d)} (year={y}) — {sponsor} founded {founded}"
                    )
            if y < 1990 or y > current_year + 1:
                out["year_out_of_range"].append(f"{_label(d)} — year={y}")
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(_collect_violations(), indent=2))
