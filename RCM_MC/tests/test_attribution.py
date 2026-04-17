"""Unit tests for OAT value attribution."""
from __future__ import annotations

import os
import unittest

from rcm_mc.pe.attribution import (
    compute_remaining_drag,
    run_oat_attribution,
    run_attribution,
    BUCKET_NAMES,
)
from rcm_mc.infra.config import load_and_validate


class TestAttribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        cls.actual_path = os.path.join(base_dir, "configs", "actual.yaml")
        cls.bench_path = os.path.join(base_dir, "configs", "benchmark.yaml")
        cls.actual_cfg = load_and_validate(cls.actual_path)
        cls.bench_cfg = load_and_validate(cls.bench_path)

    def test_all_buckets_swapped_gives_near_zero_drag(self):
        """Full swap to benchmark should reduce drag by >85%."""
        empty_drag = compute_remaining_drag(
            self.actual_cfg, self.bench_cfg, set(), n_sims=500, seed=99, align_profile=True
        )
        all_indices = set(range(len(BUCKET_NAMES)))
        drag = compute_remaining_drag(
            self.actual_cfg,
            self.bench_cfg,
            all_indices,
            n_sims=500,
            seed=99,
            align_profile=True,
        )
        reduction = (abs(empty_drag) - abs(drag)) / (abs(empty_drag) + 1e-9)
        self.assertGreater(
            reduction,
            0.85,
            msg=f"Full swap should reduce drag by >85%; empty={empty_drag:.0f}, full_swap={drag:.0f}",
        )

    def test_oat_uplift_majority_positive_when_actual_worse(self):
        """
        OAT uplift_i = D_empty - D_{i}. When Actual underperforms Benchmark,
        fixing buckets typically reduces drag so uplift >= 0. Some buckets may
        show negative uplift due to interactions; most should be non-negative.
        """
        oat_df = run_oat_attribution(
            self.actual_cfg,
            self.bench_cfg,
            n_sims=500,
            seed=42,
            align_profile=True,
        )
        positive = (oat_df["uplift_oat"] >= 0).sum()
        total = len(oat_df)
        self.assertGreaterEqual(
            positive,
            total // 2,
            msg=f"Expected majority non-negative OAT uplift; got {positive}/{total}",
        )

    def test_run_attribution_bundles_results(self):
        """run_attribution returns oat df + baseline_drag + bucket_names."""
        results = run_attribution(
            self.actual_cfg,
            self.bench_cfg,
            n_sims=500,
            seed=42,
            align_profile=True,
        )
        self.assertIn("oat", results)
        self.assertIn("baseline_drag", results)
        self.assertIn("bucket_names", results)
        self.assertEqual(len(results["oat"]), len(BUCKET_NAMES))
        # OAT should be sorted descending by uplift
        uplifts = results["oat"]["uplift_oat"].tolist()
        self.assertEqual(uplifts, sorted(uplifts, reverse=True))
