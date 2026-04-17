import os
import unittest
import numpy as np

from rcm_mc.infra.config import load_and_validate
from rcm_mc.core.simulator import simulate_compare


class TestClaimDistribution(unittest.TestCase):
    def test_claim_distribution_and_priority_runs(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")
        a = load_and_validate(actual)
        b = load_and_validate(bench)

        # Enable queue + high-dollar-first
        a["operations"]["denial_capacity"]["mode"] = "queue"
        b["operations"]["denial_capacity"]["mode"] = "queue"
        a["operations"]["denial_capacity"]["queue"]["priority"] = "high_dollar_first"
        b["operations"]["denial_capacity"]["queue"]["priority"] = "high_dollar_first"

        # Enable claim distribution for Commercial only (largest impact).
        a["payers"]["Commercial"]["claim_distribution"]["enabled"] = True
        b["payers"]["Commercial"]["claim_distribution"]["enabled"] = True

        df = simulate_compare(a, b, n_sims=200, seed=321, align_profile=True)
        self.assertTrue(np.isfinite(df["ebitda_drag"]).all())
        self.assertIn("drag_queue_wait_days_dollar_weighted", df.columns)
