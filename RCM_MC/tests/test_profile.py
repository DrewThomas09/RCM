
import os
import unittest

from rcm_mc.infra.config import load_and_validate
from rcm_mc.infra.profile import align_benchmark_to_actual


class TestProfileAlignment(unittest.TestCase):
    def test_align_copies_revenue_and_claim_sizes(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")
        a = load_and_validate(actual)
        b = load_and_validate(bench)

        # Intentionally distort Benchmark profile
        b["hospital"]["annual_revenue"] = 123
        b["payers"]["Commercial"]["revenue_share"] = 0.10
        b["payers"]["Commercial"]["avg_claim_dollars"] = 9999

        a2, b2 = align_benchmark_to_actual(a, b, deepcopy_inputs=True)

        self.assertEqual(float(b2["hospital"]["annual_revenue"]), float(a2["hospital"]["annual_revenue"]))
        self.assertEqual(float(b2["payers"]["Commercial"]["revenue_share"]), float(a2["payers"]["Commercial"]["revenue_share"]))
        self.assertEqual(float(b2["payers"]["Commercial"]["avg_claim_dollars"]), float(a2["payers"]["Commercial"]["avg_claim_dollars"]))
