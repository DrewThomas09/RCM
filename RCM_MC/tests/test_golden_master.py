"""
Golden master regression test.
Fixed seed + baseline config; assert key outputs within tolerance.
"""
from __future__ import annotations

import os
import unittest

from rcm_mc.infra.config import load_and_validate
from rcm_mc.core.kernel import run_simulation

# Baseline config path (use actual.yaml as golden baseline)
_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_ACTUAL = os.path.join(_BASE_DIR, "configs", "actual.yaml")
_BENCHMARK = os.path.join(_BASE_DIR, "configs", "benchmark.yaml")
_SEED = 12345
_N_SIMS = 2000  # Smaller for test speed; tolerance accounts for sampling variance

# Golden values (run once with fixed seed 12345, configs/actual.yaml + benchmark.yaml)
_GOLDEN_EBITDA_MEAN = 16_129_153
_GOLDEN_EBITDA_P10 = 9_711_165
_GOLDEN_EBITDA_P90 = 23_332_629
_TOLERANCE_PCT = 0.15  # 15% tolerance for sampling variance


class TestGoldenMaster(unittest.TestCase):
    def test_ebitda_drag_within_tolerance(self):
        """Assert EBITDA drag mean/P10/P90 within tolerance of golden baseline."""
        actual = load_and_validate(_ACTUAL)
        benchmark = load_and_validate(_BENCHMARK)
        result = run_simulation(
            actual, benchmark,
            n_sims=_N_SIMS, seed=_SEED,
            align_profile=True,
        )
        tol_mean = _GOLDEN_EBITDA_MEAN * _TOLERANCE_PCT
        tol_p10 = _GOLDEN_EBITDA_P10 * _TOLERANCE_PCT
        tol_p90 = _GOLDEN_EBITDA_P90 * _TOLERANCE_PCT

        self.assertAlmostEqual(
            result.ebitda_drag_mean,
            _GOLDEN_EBITDA_MEAN,
            delta=tol_mean,
            msg=f"EBITDA drag mean {result.ebitda_drag_mean} outside tolerance of {_GOLDEN_EBITDA_MEAN}",
        )
        self.assertAlmostEqual(
            result.ebitda_drag_p10,
            _GOLDEN_EBITDA_P10,
            delta=tol_p10,
            msg=f"EBITDA drag P10 {result.ebitda_drag_p10} outside tolerance",
        )
        self.assertAlmostEqual(
            result.ebitda_drag_p90,
            _GOLDEN_EBITDA_P90,
            delta=tol_p90,
            msg=f"EBITDA drag P90 {result.ebitda_drag_p90} outside tolerance",
        )
