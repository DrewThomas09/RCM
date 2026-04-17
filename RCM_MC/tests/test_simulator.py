import os
import unittest

import numpy as np

from rcm_mc.infra.config import load_and_validate
from rcm_mc.core.simulator import simulate_compare


class TestSimulator(unittest.TestCase):
    def test_simulation_runs_and_has_columns(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")
        a = load_and_validate(actual)
        b = load_and_validate(bench)

        df = simulate_compare(a, b, n_sims=300, seed=123)
        self.assertIn("ebitda_drag", df.columns)
        self.assertIn("economic_drag", df.columns)
        self.assertIn("drag_denial_writeoff", df.columns)
        self.assertTrue(np.isfinite(df["ebitda_drag"]).all())

        # With these configs, Actual is worse than Benchmark on average
        self.assertGreater(df["ebitda_drag"].mean(), 0.0)
