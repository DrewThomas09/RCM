"""Tests for the corpus provenance system.

Verifies:
  1. load_corpus_deals("all") returns the full corpus.
  2. load_corpus_deals("real") filters to real-tagged deals only.
  3. load_corpus_deals("synthetic") filters to synthetic-tagged only.
  4. Every deal has a provenance field (no untagged rows ever leak).
  5. Every real deal has plausible financial values (MOIC ≤ 6.0x,
     IRR ≤ 60%). Outliers named individually for review.
"""
from __future__ import annotations

import unittest
from typing import Any, Dict, List

from rcm_mc.data_public.corpus_loader import (
    corpus_counts,
    load_corpus_deals,
)
from rcm_mc.data_public.corpus_provenance import (
    PROVENANCE_REGISTRY,
    tag_for_group,
)


def _moic(deal: Dict[str, Any]) -> Any:
    # Schema drift: early files use realized_moic, later use moic.
    return deal.get("realized_moic") if deal.get("realized_moic") is not None else deal.get("moic")


def _irr(deal: Dict[str, Any]) -> Any:
    return deal.get("realized_irr") if deal.get("realized_irr") is not None else deal.get("irr")


def _label(deal: Dict[str, Any]) -> str:
    return (
        deal.get("deal_name")
        or deal.get("company_name")
        or deal.get("source_id")
        or "(unnamed)"
    )


class TestCorpusLoaderModes(unittest.TestCase):

    def test_load_all_returns_full_corpus(self):
        deals = load_corpus_deals("all")
        # The corpus is expected to hold well over 1000 rows given
        # the ~105 seed groups. Floor the assertion generously so
        # the test doesn't flake on a single-group removal.
        self.assertGreater(len(deals), 1000,
                           "'all' mode should return the full corpus")

    def test_load_real_filters_correctly(self):
        deals = load_corpus_deals("real")
        # Every returned row must be tagged real.
        self.assertTrue(all(d["provenance"] == "real" for d in deals))
        # Real corpus is small by construction (~55 deals).
        self.assertGreater(len(deals), 30,
                           "real mode should return ≥30 deals")
        self.assertLess(len(deals), 200,
                        "real mode should be well below 200 until "
                        "extended_seed_2..40 is re-verified per row")

    def test_load_synthetic_filters_correctly(self):
        deals = load_corpus_deals("synthetic")
        self.assertTrue(all(d["provenance"] == "synthetic" for d in deals))
        # Synthetic is the bulk of the corpus.
        self.assertGreater(len(deals), 1000)

    def test_counts_sum_to_all(self):
        c = corpus_counts()
        self.assertEqual(c["real"] + c["synthetic"], c["all"],
                         "real + synthetic should equal all — no rows "
                         "should be in a third bucket")

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            load_corpus_deals("unknown")


class TestProvenanceFieldIntegrity(unittest.TestCase):

    def test_every_deal_has_provenance_field(self):
        """provenance is a required field — no row can be untagged."""
        deals = load_corpus_deals("all")
        missing = [
            _label(d) for d in deals
            if "provenance" not in d or d["provenance"] not in ("real", "synthetic")
        ]
        self.assertEqual(missing, [],
                         f"{len(missing)} deals missing provenance: "
                         f"{missing[:5]}")

    def test_every_deal_has_source_group(self):
        """source_group traces each row back to a registry entry."""
        deals = load_corpus_deals("all")
        for d in deals:
            self.assertIn("source_group", d,
                          f"{_label(d)} lacks source_group")
            self.assertIn(d["source_group"], PROVENANCE_REGISTRY,
                          f"{_label(d)} has unknown source_group "
                          f"{d['source_group']}")

    def test_registry_tag_lookup_is_total(self):
        """Every group name in the registry resolves."""
        for group in PROVENANCE_REGISTRY:
            tag = tag_for_group(group)
            self.assertIn(tag, ("real", "synthetic"))

    def test_registry_unknown_group_raises(self):
        with self.assertRaises(KeyError):
            tag_for_group("not_a_registered_group")


class TestRealDealsPlausibility(unittest.TestCase):
    """Real deals must have plausible financials. Outliers are either
    real-but-extreme (need a ``plausibility_note`` on the row) or
    mistagged. The test fails only on unnoted outliers — annotated
    ones pass because the note itself is the review record."""

    MOIC_CEILING = 6.0
    IRR_CEILING = 0.60

    def test_real_deals_moic_ceiling(self):
        deals = load_corpus_deals("real")
        unnoted = []
        for d in deals:
            m = _moic(d)
            if m is not None and m > self.MOIC_CEILING:
                if not d.get("plausibility_note"):
                    unnoted.append((_label(d), m))
        self.assertEqual(
            unnoted, [],
            f"{len(unnoted)} real deals with MOIC > {self.MOIC_CEILING:.1f}x "
            f"and no plausibility_note — either add a note or retag "
            f"synthetic: {unnoted}",
        )

    def test_real_deals_irr_ceiling(self):
        deals = load_corpus_deals("real")
        unnoted = []
        for d in deals:
            irr = _irr(d)
            if irr is not None and irr > self.IRR_CEILING:
                if not d.get("plausibility_note"):
                    unnoted.append((_label(d), irr))
        self.assertEqual(
            unnoted, [],
            f"{len(unnoted)} real deals with IRR > {self.IRR_CEILING*100:.0f}% "
            f"and no plausibility_note — add a note or retag "
            f"synthetic: {unnoted}",
        )


if __name__ == "__main__":
    unittest.main()
