"""Tests for the observed/prior/assumed source-tagging layer."""
from __future__ import annotations

import os
import unittest

import yaml

from rcm_mc.data.sources import (
    classify_sources,
    confidence_grade,
    iter_meaningful_paths,
    mark_observed,
    observed_fraction,
    path_notes,
    summarize,
)


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ACTUAL_PATH = os.path.join(BASE_DIR, "configs", "actual.yaml")


def _load(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class TestMeaningfulPaths(unittest.TestCase):
    def test_includes_hospital_revenue(self):
        cfg = _load(ACTUAL_PATH)
        paths = [p for p, _ in iter_meaningful_paths(cfg)]
        self.assertIn("hospital.annual_revenue", paths)

    def test_includes_per_payer_idr_when_denials_active(self):
        cfg = _load(ACTUAL_PATH)
        paths = [p for p, _ in iter_meaningful_paths(cfg)]
        # At least one payer should have an IDR path
        self.assertTrue(
            any(p.endswith(".denials.idr") for p in paths),
            msg=f"Expected some .denials.idr path in {paths}",
        )

    def test_yields_nonempty_for_stock_config(self):
        cfg = _load(ACTUAL_PATH)
        paths = list(iter_meaningful_paths(cfg))
        self.assertGreater(len(paths), 10)


class TestClassifySources(unittest.TestCase):
    def test_no_source_map_gives_all_assumed(self):
        cfg = _load(ACTUAL_PATH)
        cfg.pop("_source_map", None)
        classification = classify_sources(cfg)
        self.assertTrue(all(v == "assumed" for v in classification.values()))

    def test_default_prior_tags_everything_prior(self):
        cfg = _load(ACTUAL_PATH)
        cfg["_source_map"] = {"_default": "prior"}
        classification = classify_sources(cfg)
        self.assertTrue(all(v == "prior" for v in classification.values()))

    def test_explicit_entry_overrides_default(self):
        cfg = _load(ACTUAL_PATH)
        # Pick a real path from the config
        idr_path = next(p for p, _ in iter_meaningful_paths(cfg) if p.endswith(".denials.idr"))
        cfg["_source_map"] = {"_default": "assumed", idr_path: "observed"}
        classification = classify_sources(cfg)
        self.assertEqual(classification[idr_path], "observed")
        # Another path should still be assumed
        other = next(p for p in classification if p != idr_path)
        self.assertEqual(classification[other], "assumed")

    def test_invalid_label_falls_back_to_default(self):
        cfg = _load(ACTUAL_PATH)
        idr_path = next(p for p, _ in iter_meaningful_paths(cfg) if p.endswith(".denials.idr"))
        cfg["_source_map"] = {"_default": "prior", idr_path: "bogus_label"}
        classification = classify_sources(cfg)
        self.assertEqual(classification[idr_path], "prior")


class TestSummaryAndGrade(unittest.TestCase):
    def test_summarize_counts_and_total(self):
        classification = {"a": "observed", "b": "observed", "c": "prior", "d": "assumed"}
        counts = summarize(classification)
        self.assertEqual(counts["observed"], 2)
        self.assertEqual(counts["prior"], 1)
        self.assertEqual(counts["assumed"], 1)
        self.assertEqual(counts["total"], 4)

    def test_observed_fraction_zero_for_empty(self):
        self.assertEqual(observed_fraction({}), 0.0)

    def test_confidence_grade_thresholds(self):
        # 0 observed -> D
        self.assertEqual(confidence_grade({"a": "assumed", "b": "prior"}), "D")
        # 1/10 = 10% -> C
        cls = {f"p{i}": "observed" if i == 0 else "prior" for i in range(10)}
        self.assertEqual(confidence_grade(cls), "C")
        # 3/10 = 30% -> B
        cls = {f"p{i}": "observed" if i < 3 else "prior" for i in range(10)}
        self.assertEqual(confidence_grade(cls), "B")
        # 6/10 = 60% -> A
        cls = {f"p{i}": "observed" if i < 6 else "prior" for i in range(10)}
        self.assertEqual(confidence_grade(cls), "A")


class TestMarkObserved(unittest.TestCase):
    def test_creates_source_map_if_missing(self):
        cfg = {"hospital": {"annual_revenue": 100}}
        mark_observed(cfg, "hospital.annual_revenue", note="10-K, FY2024")
        self.assertIn("_source_map", cfg)
        self.assertEqual(cfg["_source_map"]["hospital.annual_revenue"], "observed")
        self.assertEqual(cfg["_source_map"]["hospital.annual_revenue._note"], "10-K, FY2024")

    def test_overwrites_existing_tag(self):
        cfg = {"_source_map": {"x.y": "assumed"}}
        mark_observed(cfg, "x.y")
        self.assertEqual(cfg["_source_map"]["x.y"], "observed")

    def test_ignores_empty_path(self):
        cfg = {}
        mark_observed(cfg, "")
        self.assertNotIn("_source_map", cfg)


class TestPathNotes(unittest.TestCase):
    def test_returns_note_strings_by_path(self):
        cfg = {"_source_map": {
            "payers.Medicare.denials.idr": "observed",
            "payers.Medicare.denials.idr._note": "n=4521",
        }}
        self.assertEqual(path_notes(cfg), {"payers.Medicare.denials.idr": "n=4521"})
