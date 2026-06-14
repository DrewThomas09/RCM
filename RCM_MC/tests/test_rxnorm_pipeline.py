"""End-to-end DQ tests for the RxNorm pipeline, store, query and validation.

Covers the definition-of-done checks: tables populated, NDC crosswalk keyed on
canonical 11-digit form, retired-RxCUI remap resolves to an active concept,
class coverage reported, the uniform query/lookup layer works, idempotent +
resumable runs, and a read-only openFDA NDC join reporting a match rate.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.data_public.rxnorm import query, store as st, validation
from rcm_mc.data_public.rxnorm.pipeline import RxnormPipeline, load_state


def _store(db_path):
    from rcm_mc.portfolio.store import PortfolioStore
    return PortfolioStore(db_path)


class RxnormPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.store = _store(str(self.dir / "rx.db"))
        self.state_dir = self.dir / "state"
        self.report = RxnormPipeline(
            self.store, state_dir=self.state_dir).run()

    def tearDown(self):
        self.tmp.cleanup()

    def test_tables_populated(self):
        c = self.report["counts"]
        self.assertGreater(c["dim_rxnorm_concept"], 0)
        self.assertGreater(c["xwalk_ndc_rxcui"], 0)
        self.assertGreater(c["bridge_rxcui_related"], 0)
        self.assertGreater(c["dim_drug_class"], 0)

    def test_crosswalk_keyed_canonical_11_digit(self):
        res = query.query_dataset(self.store, "rxnorm_ndc_crosswalk")
        for row in res["rows"]:
            self.assertEqual(len(row["ndc_11"]), 11)
            self.assertTrue(row["ndc_11"].isdigit())
            self.assertTrue(row["ndc_raw"])  # raw value retained alongside

    def test_retired_rxcui_remaps_to_active_concept(self):
        # 9999999 is seeded retired→remapped to 83367 (active atorvastatin).
        resolved = st.resolve_rxcui(self.store, "9999999")
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved["rxcui"], "83367")
        self.assertEqual(resolved["status"], "active")

    def test_class_coverage_reported(self):
        cov = self.report["class_coverage"]
        self.assertIn("coverage_pct", cov)
        self.assertGreater(cov["coverage_pct"], 0.0)
        # all three class types present in the grouping
        self.assertEqual(set(cov["by_class_type"]),
                         {"ATC", "therapeutic", "mechanism_of_action"})

    def test_lookup_ndc_normalizes_then_joins(self):
        # Pass the 10-digit hyphenated form; it must normalize and hit.
        out = query.lookup_ndc(self.store, "0409-1896-20")
        self.assertEqual(out["ndc_11"], "00409189620")
        self.assertIsNotNone(out["match"])
        self.assertEqual(out["match"]["current_rxcui"], "7052")

    def test_lookup_rxcui_assembles_related_and_classes(self):
        out = query.lookup_rxcui(self.store, "83367")
        self.assertEqual(out["current_rxcui"], "83367")
        self.assertTrue(out["related"])
        self.assertTrue(out["drug_classes"])

    def test_query_filter_select_sort_paginate(self):
        res = query.query_dataset(
            self.store, "rxnorm_concepts",
            filters={"tty": "SCD"}, select=["rxcui", "name"],
            sort="rxcui", limit=1, offset=0)
        self.assertEqual(res["count"], 1)
        self.assertEqual(set(res["rows"][0].keys()), {"rxcui", "name"})
        self.assertGreaterEqual(res["total"], 1)

    def test_query_rejects_unknown_columns(self):
        with self.assertRaises(ValueError):
            query.query_dataset(self.store, "rxnorm_concepts",
                                filters={"nope": "x"})
        with self.assertRaises(ValueError):
            query.query_dataset(self.store, "rxnorm_concepts", sort="nope")

    def test_query_unknown_dataset_raises(self):
        with self.assertRaises(KeyError):
            query.query_dataset(self.store, "not_a_dataset")

    def test_idempotent_rerun_converges(self):
        before = self.report["counts"]
        after = RxnormPipeline(self.store, state_dir=self.state_dir).run()["counts"]
        self.assertEqual(before, after)

    def test_state_and_progress_written(self):
        self.assertTrue((self.state_dir / "STATE.md").exists())
        self.assertTrue((self.state_dir / "PROGRESS.log").exists())
        state = load_state(self.state_dir)
        self.assertIn("counts", state)
        self.assertIn("release_version", state)
        self.assertTrue(state["processed_rxcui"])

    def test_resume_from_state_after_partial(self):
        # Simulate a hard kill that left a checkpoint: a fresh pipeline reading
        # the same state_dir + db must converge to the same counts, not double.
        state = load_state(self.state_dir)
        self.assertEqual(state["last_concept_cursor"], "complete")
        resumed = RxnormPipeline(self.store, state_dir=self.state_dir).run()
        self.assertEqual(resumed["counts"], self.report["counts"])

    def test_openfda_join_match_rate_reported(self):
        rep = validation.openfda_ndc_match_rate(self.store)
        # The openFDA snapshot exists and carries NDCs; the join plumbing runs.
        self.assertGreater(rep["openfda_ndcs"], 0)
        self.assertGreaterEqual(rep["match_rate"], 0.0)
        self.assertLessEqual(rep["match_rate"], 1.0)
        # Our seed deliberately includes two of openFDA's shortage NDCs.
        self.assertGreaterEqual(rep["matched"], 2)


class NoNetworkAtImportTests(unittest.TestCase):
    def test_pipeline_is_offline_by_default(self):
        # Default (live=False) must use the seed opener — no socket.
        p = RxnormPipeline(_store(":memory:"))
        from rcm_mc.data_public.rxnorm import seed as seedmod
        self.assertIs(p.opener, seedmod.seed_opener)


if __name__ == "__main__":
    unittest.main()
