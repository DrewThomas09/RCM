"""Tests for RxNorm diligence analytics + fuzzy/name-match connector endpoints."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.data_public.rxnorm import analytics, run as rxrun
from rcm_mc.data_public.rxnorm import seed as seedmod
from rcm_mc.data_public.rxnorm.connector import RxNormConnector


def _store():
    d = tempfile.mkdtemp()
    store = PortfolioStore(os.path.join(d, "rx.db"))
    rxrun(store, state_dir=tempfile.mkdtemp())
    return store


class AnalyticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = _store()

    def test_coverage_summary(self):
        s = analytics.coverage_summary(self.store)
        self.assertGreater(s["counts"]["dim_rxnorm_concept"], 0)
        self.assertGreater(s["rxcui_with_ndc"], 0)
        self.assertGreaterEqual(s["retired_or_remapped"], 1)
        self.assertIn("match_rate", s["openfda_join"])

    def test_search_concepts_active_first_and_escaped(self):
        hits = analytics.search_concepts(self.store, "atorvastatin")
        self.assertTrue(hits)
        self.assertTrue(all("atorvastatin" in h["name"].lower() for h in hits))
        # LIKE wildcard chars must be treated literally, not as wildcards.
        self.assertEqual(analytics.search_concepts(self.store, "%"), [])

    def test_competitive_set_by_class_ranked(self):
        rows = analytics.competitive_set_by_class(self.store)
        self.assertTrue(rows)
        ns = [r["n_rxcui"] for r in rows]
        self.assertEqual(ns, sorted(ns, reverse=True))  # ranked desc

    def test_competitive_set_filter_by_type(self):
        rows = analytics.competitive_set_by_class(self.store,
                                                  class_type="mechanism_of_action")
        self.assertTrue(rows)
        self.assertTrue(all(r["class_type"] == "mechanism_of_action" for r in rows))

    def test_class_members(self):
        members = analytics.class_members(self.store, "C10AA")
        self.assertTrue(any(m["rxcui"] == "83367" for m in members))

    def test_molecule_competitive_set_resolves_remap(self):
        # 9999999 is remapped → 83367; competitive set roots at the active one.
        comp = analytics.molecule_competitive_set(self.store, "9999999")
        self.assertEqual(comp["root_rxcui"], "83367")
        self.assertGreaterEqual(comp["branded_drug_count"]
                                + comp["clinical_drug_count"], 1)

    def test_retired_remapped_audit_resolves_forward(self):
        audit = analytics.retired_remapped_audit(self.store)
        row = next(a for a in audit if a["rxcui"] == "9999999")
        self.assertEqual(row["resolves_to_rxcui"], "83367")
        self.assertEqual(row["resolves_to_status"], "active")


class FuzzyEndpointTests(unittest.TestCase):
    def setUp(self):
        self.c = RxNormConnector()
        self.kw = {"opener": seedmod.seed_opener,
                   "sleep": lambda s: None, "now": lambda: 0.0}

    def test_approximate_term(self):
        rows, _ = self.c.fetch("approximateterm", {"term": "atorvastatin"},
                               **self.kw)
        self.assertTrue(any(r["rxcui"] == "83367" for r in rows))

    def test_drugs_by_name(self):
        rows, _ = self.c.fetch("drugs", {"name": "aspirin"}, **self.kw)
        self.assertTrue(any(r["rxcui"] == "1191" for r in rows))


if __name__ == "__main__":
    unittest.main()
