"""Step 74: Performance benchmark tests."""
import time
import unittest

from rcm_mc.infra.config import load_and_validate
from rcm_mc.core.simulator import simulate


class TestPerformance(unittest.TestCase):

    def test_1000_iters_under_5s(self):
        cfg = load_and_validate("configs/actual.yaml")
        t0 = time.perf_counter()
        df = simulate(cfg, n_sims=1000, seed=42, early_stop=False)
        elapsed = time.perf_counter() - t0
        self.assertEqual(len(df), 1000)
        self.assertLess(elapsed, 5.0, f"1000 iters took {elapsed:.1f}s (limit: 5s)")

    def test_config_load_under_100ms(self):
        t0 = time.perf_counter()
        for _ in range(10):
            load_and_validate("configs/actual.yaml")
        elapsed = time.perf_counter() - t0
        per_load = elapsed / 10
        self.assertLess(per_load, 0.1, f"Config load took {per_load*1000:.0f}ms (limit: 100ms)")


if __name__ == "__main__":
    unittest.main()
