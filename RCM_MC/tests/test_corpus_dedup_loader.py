"""Loader-level corpus de-duplication: keep-first, real over synthetic.

load_corpus_deals() promised a corpus "deduplicated of repeat entries" but
never did it, so the same real deal accreted across seed batches (e.g. Oak
Street / CVS as both seed_044 and seed_101) and double-counted in every corpus
analytic. The fix collapses repeats at load time with `_dedup_corpus`, KEEP-
FIRST: the real-tagged base / extended_seed groups load before the later
synthetic batches, so the canonical (real) row must win.

test_corpus_no_exact_duplicates proves the loaded corpus has no dupes, but not
that the *right* row survives. If keep-first ever flipped to keep-last, a
synthetic row could shadow the real one with no dupe-count change. Pin the
keep-first contract (and that distinct deals are never over-collapsed) here.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.chartis._helpers import _dedup_corpus


def _deal(name, buyer, year, ev, tag):
    return {"deal_name": name, "buyer": buyer, "year": year,
            "ev_mm": ev, "tag": tag}


class DedupKeepsFirst(unittest.TestCase):
    def test_repeat_collapses_to_the_first_row(self):
        # Same buyer/year/target, EV within the dup band: one survives, the
        # first (the real-tagged one that loaded earlier).
        rows = [
            _deal("Oak Street Health", "CVS Health", 2020, 10600, "REAL"),
            _deal("Oak Street Health", "CVS Health", 2020, 10500, "SYNTH"),
        ]
        out = _dedup_corpus(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["tag"], "REAL",
                         "dedup must keep the first (real) row, not the synthetic")

    def test_distinct_deals_are_preserved(self):
        rows = [
            _deal("Oak Street Health", "CVS Health", 2020, 10600, "REAL"),
            _deal("Oak Street Health", "CVS Health", 2020, 10500, "SYNTH"),
            _deal("Envision Healthcare", "KKR", 2018, 9900, "OTHER"),
        ]
        out = _dedup_corpus(rows)
        tags = [d["tag"] for d in out]
        self.assertEqual(len(out), 2)
        self.assertIn("REAL", tags)
        self.assertIn("OTHER", tags)
        self.assertNotIn("SYNTH", tags)

    def test_different_year_is_not_a_duplicate(self):
        # Same target/buyer but a different vintage is a distinct deal.
        rows = [
            _deal("Surgery Partners", "Bain", 2017, 3000, "A"),
            _deal("Surgery Partners", "Bain", 2021, 3050, "B"),
        ]
        out = _dedup_corpus(rows)
        self.assertEqual(len(out), 2)

    def test_far_apart_ev_is_not_a_duplicate(self):
        # Same name/buyer/year but EV an order of magnitude apart: treat as
        # distinct rather than collapsing (the dup band is intentionally tight).
        rows = [
            _deal("Acme Health", "Sponsor X", 2019, 500, "small"),
            _deal("Acme Health", "Sponsor X", 2019, 9000, "big"),
        ]
        out = _dedup_corpus(rows)
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
