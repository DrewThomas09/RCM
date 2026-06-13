"""Tests for the public-data API catalog (the /data-apis reference table).

The catalog is metadata only — it must be internally consistent, never fetch at
import, and accurately reflect which sources are wired in-repo.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public import public_api_catalog as cat


class CatalogIntegrityTests(unittest.TestCase):
    def test_has_the_named_free_apis(self):
        ids = {s.id for s in cat.all_sources()}
        # The field guide's "wire up first" set, plus the rest it names.
        for needed in ("nppes", "openfda", "clinicaltrials", "rxnorm",
                       "census_acs", "propublica_990", "sec_edgar",
                       "hrsa", "hcupnet", "usaspending", "bls_oews",
                       "who_gho"):
            self.assertIn(needed, ids, f"catalog missing {needed}")

    def test_every_source_has_a_valid_category(self):
        valid = dict(cat.CATEGORIES)
        for s in cat.all_sources():
            self.assertIn(s.category, valid, f"{s.id} bad category")

    def test_every_source_has_valid_access_and_status(self):
        for s in cat.all_sources():
            self.assertIn(s.access, cat.ACCESS_LABELS, f"{s.id} access")
            self.assertIn(s.status, cat.STATUS_LABELS, f"{s.id} status")

    def test_urls_are_https_and_documented(self):
        for s in cat.all_sources():
            self.assertTrue(s.base_url.startswith("https://"), s.id)
            self.assertTrue(s.docs_url.startswith("https://"), s.id)
            # Every source explains what question it answers and why.
            self.assertTrue(s.answers.strip(), f"{s.id} no answers")
            self.assertTrue(s.why.strip(), f"{s.id} no why")

    def test_ids_are_unique(self):
        ids = [s.id for s in cat.all_sources()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_wired_sources_name_an_existing_module(self):
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(cat.__file__)))
        root = os.path.dirname(root)  # repo root above rcm_mc/
        for s in cat.wired_sources():
            self.assertTrue(s.client_module, f"{s.id} wired but no module")
            path = os.path.join(root, s.client_module)
            self.assertTrue(os.path.exists(path),
                            f"{s.id} module {s.client_module} not found")

    def test_registered_sources_have_no_module(self):
        for s in cat.all_sources():
            if s.status == "registered":
                self.assertEqual(s.client_module, "",
                                 f"{s.id} registered but names a module")

    def test_nppes_flagged_as_provider_universe_starting_point(self):
        nppes = cat.get("nppes")
        self.assertIsNotNone(nppes)
        self.assertEqual(nppes.category, "provider_universe")
        self.assertEqual(nppes.status, "live-client")
        self.assertEqual(nppes.access, "none")


class CatalogAggregationTests(unittest.TestCase):
    def test_by_category_partitions_all_sources(self):
        grouped = cat.by_category()
        total = sum(len(members) for _, _, members in grouped)
        self.assertEqual(total, len(cat.all_sources()))
        # Render order matches CATEGORIES.
        self.assertEqual([cid for cid, _, _ in grouped],
                         [cid for cid, _ in cat.CATEGORIES])

    def test_status_counts_sum_to_total(self):
        counts = cat.status_counts()
        self.assertEqual(sum(counts.values()), len(cat.all_sources()))

    def test_summary_shape(self):
        s = cat.summary()
        for k in ("total", "categories", "wired", "no_key", "status", "access"):
            self.assertIn(k, s)
        self.assertEqual(s["total"], len(cat.all_sources()))
        self.assertEqual(s["wired"], len(cat.wired_sources()))

    def test_key_optional_are_access_none(self):
        for s in cat.key_optional_sources():
            self.assertEqual(s.access, "none")


if __name__ == "__main__":
    unittest.main()
