import os
import tempfile
import unittest

from rcm_mc.infra.config import load_and_validate, ConfigError


class TestConfig(unittest.TestCase):
    def test_missing_mandatory_payer_raises(self):
        # Minimal invalid config
        import yaml
        bad = {
            "hospital": {"annual_revenue": 100},
            "appeals": {"stages": {"L1": {"cost": {"dist": "fixed", "value": 1}, "days": {"dist": "fixed", "value": 1}},
                                   "L2": {"cost": {"dist": "fixed", "value": 1}, "days": {"dist": "fixed", "value": 1}},
                                   "L3": {"cost": {"dist": "fixed", "value": 1}, "days": {"dist": "fixed", "value": 1}}}},
            "payers": {
                "Medicare": {"revenue_share": 1.0, "avg_claim_dollars": 1000, "dar_clean_days": {"dist": "fixed", "value": 30},
                             "include_denials": False, "include_underpayments": False},
            },
        }
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "_bad.yaml")
            with open(path, "w") as f:
                yaml.safe_dump(bad, f)
            with self.assertRaises(ConfigError):
                load_and_validate(path)

    def test_valid_configs_load(self):
        base_dir = os.path.dirname(os.path.dirname(__file__))
        actual = os.path.join(base_dir, "configs", "actual.yaml")
        bench = os.path.join(base_dir, "configs", "benchmark.yaml")
        a = load_and_validate(actual)
        b = load_and_validate(bench)
        self.assertAlmostEqual(sum(float(v["revenue_share"]) for v in a["payers"].values()), 1.0, places=3)
        self.assertAlmostEqual(sum(float(v["revenue_share"]) for v in b["payers"].values()), 1.0, places=3)
