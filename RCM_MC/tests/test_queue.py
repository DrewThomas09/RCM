import os
import unittest
import numpy as np

from rcm_mc.infra.config import load_and_validate
from rcm_mc.core.simulator import simulate_compare


class TestQueueMode(unittest.TestCase):
    def test_queue_mode_runs(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")
        a = load_and_validate(actual)
        b = load_and_validate(bench)

        # Enable queue mode (Leap 4) on both so comparison remains fair.
        a["operations"]["denial_capacity"]["mode"] = "queue"
        b["operations"]["denial_capacity"]["mode"] = "queue"

        df = simulate_compare(a, b, n_sims=200, seed=123, align_profile=True)
        self.assertIn("ebitda_drag", df.columns)
        self.assertTrue(np.isfinite(df["ebitda_drag"]).all())
        # Should produce queue columns too
        self.assertIn("drag_queue_wait_days", df.columns)
