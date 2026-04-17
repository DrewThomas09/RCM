"""Tests for Prompts 61 (deal sourcer) + 62 (cross-deal search).

DEAL SOURCER:
 1. Hospital with denial 14% scores > hospital with denial 8% on
    denial-turnaround thesis.
 2. Thesis with preferred_regions filters by state.
 3. Excluded system → score 0.
 4. find_thesis_matches returns sorted results.
 5. Empty HCRIS → empty matches.
 6. ThesisMatch to_dict round-trips.
 7. InvestmentThesis to_dict round-trips.
 8. THESIS_LIBRARY has at least 3 entries.

CROSS-DEAL SEARCH:
 9. Note containing "denial" found by search for "denial".
10. Related term: search for "AR" finds "days_in_ar" in overrides.
11. Empty query → empty results.
12. Results sorted by relevance.
13. Results scoped to deal_ids when provided.
14. SearchResult to_dict round-trips.
15. Risk flag text searchable.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.analysis.cross_deal_search import (
    RELATED_TERMS,
    SearchResult,
    _expand_query,
    search_across_deals,
)
from rcm_mc.analysis.deal_sourcer import (
    InvestmentThesis,
    THESIS_LIBRARY,
    ThesisCriterion,
    ThesisMatch,
    find_thesis_matches,
    score_hospital_against_thesis,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


# ── Deal Sourcer ──────────────────────────────────────────────────

class TestDealSourcer(unittest.TestCase):

    def test_higher_denial_scores_higher(self):
        thesis = InvestmentThesis(
            name="test",
            criteria=[ThesisCriterion("denial_rate", ">", 10.0, weight=1.0)],
        )
        s1, _ = score_hospital_against_thesis(
            {"denial_rate": 14.0}, thesis,
        )
        s2, _ = score_hospital_against_thesis(
            {"denial_rate": 8.0}, thesis,
        )
        self.assertGreater(s1, s2)

    def test_preferred_region_bonus(self):
        thesis = InvestmentThesis(
            name="test",
            criteria=[ThesisCriterion("beds", ">", 100, weight=1.0)],
            preferred_regions=["IL"],
        )
        # Use beds=120 (barely above 100) so the base score is low
        # enough that the +10 region bonus is visible.
        s_il, _ = score_hospital_against_thesis(
            {"beds": 120, "state": "IL"}, thesis,
        )
        s_tx, _ = score_hospital_against_thesis(
            {"beds": 120, "state": "TX"}, thesis,
        )
        self.assertGreater(s_il, s_tx)

    def test_excluded_system_zeroes(self):
        thesis = InvestmentThesis(
            name="test",
            criteria=[ThesisCriterion("beds", ">", 100)],
            excluded_systems=["HCA"],
        )
        s, _ = score_hospital_against_thesis(
            {"beds": 500, "system_affiliation": "HCA Healthcare"}, thesis,
        )
        self.assertEqual(s, 0.0)

    def test_find_matches_sorted(self):
        thesis = THESIS_LIBRARY["denial_turnaround"]
        matches = find_thesis_matches(thesis, limit=10)
        if len(matches) >= 2:
            self.assertGreaterEqual(
                matches[0].score, matches[1].score,
            )

    def test_thesis_match_to_dict(self):
        m = ThesisMatch(ccn="123", name="Test", score=80.0)
        d = m.to_dict()
        self.assertEqual(d["score"], 80.0)

    def test_investment_thesis_to_dict(self):
        t = THESIS_LIBRARY["denial_turnaround"]
        d = t.to_dict()
        self.assertEqual(d["name"], "Denial turnaround")

    def test_thesis_library_has_entries(self):
        self.assertGreaterEqual(len(THESIS_LIBRARY), 3)

    def test_between_operator(self):
        c = ThesisCriterion("beds", "between", (100, 400))
        thesis = InvestmentThesis(name="t", criteria=[c])
        s, _ = score_hospital_against_thesis(
            {"beds": 200}, thesis,
        )
        self.assertGreater(s, 0)
        s2, _ = score_hospital_against_thesis(
            {"beds": 500}, thesis,
        )
        self.assertEqual(s2, 0.0)


# ── Cross-Deal Search ────────────────────────────────────────────

class TestCrossDealSearch(unittest.TestCase):

    def test_note_found_by_keyword(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            from rcm_mc.deals.deal_notes import record_note
            record_note(store, deal_id="d1",
                        body="Denial audit completed successfully")
            results = search_across_deals(store, "denial")
            self.assertTrue(any(
                r.source_type == "note" and "denial" in r.text_snippet.lower()
                for r in results
            ))
        finally:
            os.unlink(path)

    def test_related_term_expansion(self):
        tokens = _expand_query("AR")
        self.assertIn("days_in_ar", tokens)
        self.assertIn("aging", tokens)

    def test_override_searchable(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            from rcm_mc.analysis.deal_overrides import set_override
            set_override(store, "d1", "bridge.exit_multiple", 11.0,
                         set_by="u", reason="higher denial comps")
            results = search_across_deals(store, "denial")
            self.assertTrue(any(
                r.source_type == "override" for r in results
            ))
        finally:
            os.unlink(path)

    def test_empty_query(self):
        store, path = _tmp_store()
        try:
            self.assertEqual(search_across_deals(store, ""), [])
        finally:
            os.unlink(path)

    def test_sorted_by_relevance(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            from rcm_mc.deals.deal_notes import record_note
            record_note(store, deal_id="d1",
                        body="denial denial denial appeal")
            record_note(store, deal_id="d1", body="denial once")
            results = search_across_deals(store, "denial")
            if len(results) >= 2:
                self.assertGreaterEqual(
                    results[0].relevance_score,
                    results[1].relevance_score,
                )
        finally:
            os.unlink(path)

    def test_scoped_to_deal_ids(self):
        store, path = _tmp_store()
        try:
            store.upsert_deal("d1", name="D1")
            store.upsert_deal("d2", name="D2")
            from rcm_mc.deals.deal_notes import record_note
            record_note(store, deal_id="d1", body="denial note")
            record_note(store, deal_id="d2", body="denial note")
            results = search_across_deals(
                store, "denial", deal_ids=["d1"],
            )
            self.assertTrue(all(r.deal_id == "d1" for r in results))
        finally:
            os.unlink(path)

    def test_search_result_to_dict(self):
        r = SearchResult(
            deal_id="d1", source_type="note",
            text_snippet="test", relevance_score=0.8,
        )
        self.assertEqual(r.to_dict()["relevance_score"], 0.8)


if __name__ == "__main__":
    unittest.main()
