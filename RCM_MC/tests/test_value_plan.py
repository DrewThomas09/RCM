import os
import unittest

from rcm_mc.infra.config import load_and_validate
from rcm_mc.pe.value_plan import build_target_config


class TestValuePlan(unittest.TestCase):
    def test_build_target_config_validates_and_improves_in_right_direction(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")

        a = load_and_validate(actual)
        b = load_and_validate(bench)

        plan = {
            "gap_closure": {"idr": 0.5, "fwr": 0.5, "dar_clean_days": 0.5},
            "gap_closure_by_payer": {"Commercial": {"fwr": 0.8}},
        }

        t = build_target_config(a, b, plan)

        # Basic schema checks
        self.assertIn("payers", t)
        self.assertIn("Commercial", t["payers"])

        # Directional sanity checks (lower is better)
        a_idr = float(a["payers"]["Commercial"]["denials"]["idr"].get("mean", 0.0))
        b_idr = float(b["payers"]["Commercial"]["denials"]["idr"].get("mean", 0.0))
        t_idr = float(t["payers"]["Commercial"]["denials"]["idr"].get("mean", 0.0))
        # Target should not be worse than Actual
        self.assertLessEqual(t_idr, a_idr + 1e-9)
        # If benchmark is better, target should move at least a bit toward it
        if b_idr < a_idr:
            self.assertLess(t_idr, a_idr)

        a_fwr = float(a["payers"]["Commercial"]["denials"]["fwr"].get("mean", 0.0))
        b_fwr = float(b["payers"]["Commercial"]["denials"]["fwr"].get("mean", 0.0))
        t_fwr = float(t["payers"]["Commercial"]["denials"]["fwr"].get("mean", 0.0))
        self.assertLessEqual(t_fwr, a_fwr + 1e-9)
        if b_fwr < a_fwr:
            self.assertLess(t_fwr, a_fwr)
