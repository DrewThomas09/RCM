"""Step 67: Tests for distribution validation (Step 10)."""
import unittest
import yaml

from rcm_mc.infra.config import validate_config, ConfigError, load_and_validate


def _minimal_config():
    """Minimal valid config for testing."""
    return yaml.safe_load("""
hospital:
  name: Test Hospital
  annual_revenue: 100000000
payers:
  Medicare:
    revenue_share: 0.60
    avg_claim_dollars: 5000
    include_denials: true
    include_underpayments: false
    dar_clean_days: {dist: normal_trunc, mean: 20, sd: 3, min: 10, max: 40}
    denials:
      idr: {dist: beta, mean: 0.08, sd: 0.02}
      fwr: {dist: beta, mean: 0.30, sd: 0.05}
      stage_mix: {L1: 0.65, L2: 0.25, L3: 0.10}
      denial_types:
        coding: {share: 0.50, fwr_odds_mult: 1.0}
        other: {share: 0.50, fwr_odds_mult: 1.0}
  SelfPay:
    revenue_share: 0.40
    avg_claim_dollars: 2000
    include_denials: false
    include_underpayments: false
    dar_clean_days: {dist: fixed, value: 30}
appeals:
  stages:
    L1: {cost: {dist: lognormal, mean: 25, sd: 8}, days: {dist: lognormal, mean: 15, sd: 5}}
    L2: {cost: {dist: lognormal, mean: 85, sd: 25}, days: {dist: lognormal, mean: 45, sd: 15}}
    L3: {cost: {dist: lognormal, mean: 250, sd: 80}, days: {dist: lognormal, mean: 120, sd: 40}}
""")


class TestDistributionValidation(unittest.TestCase):

    def test_valid_config_passes(self):
        cfg = _minimal_config()
        result = validate_config(cfg)
        self.assertIn("payers", result)

    def test_unknown_dist_type_fails(self):
        cfg = _minimal_config()
        cfg["payers"]["Medicare"]["dar_clean_days"]["dist"] = "unicorn"
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_missing_mean_fails(self):
        cfg = _minimal_config()
        del cfg["payers"]["Medicare"]["denials"]["idr"]["mean"]
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_negative_sd_fails(self):
        cfg = _minimal_config()
        cfg["payers"]["Medicare"]["denials"]["idr"]["sd"] = -1
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_non_numeric_mean_fails(self):
        cfg = _minimal_config()
        cfg["payers"]["Medicare"]["denials"]["idr"]["mean"] = "abc"
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_denial_types_missing_share_fails(self):
        cfg = _minimal_config()
        del cfg["payers"]["Medicare"]["denials"]["denial_types"]["coding"]["share"]
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_denial_types_empty_fails(self):
        cfg = _minimal_config()
        cfg["payers"]["Medicare"]["denials"]["denial_types"] = {}
        with self.assertRaises(ConfigError):
            validate_config(cfg)

    def test_empirical_dist_valid(self):
        cfg = _minimal_config()
        cfg["payers"]["Medicare"]["dar_clean_days"] = {"dist": "empirical", "values": [15, 20, 25]}
        result = validate_config(cfg)
        self.assertIn("payers", result)

    def test_empirical_dist_empty_values_fails(self):
        cfg = _minimal_config()
        cfg["payers"]["Medicare"]["dar_clean_days"] = {"dist": "empirical", "values": []}
        with self.assertRaises(ConfigError):
            validate_config(cfg)


class TestConfigDiff(unittest.TestCase):

    def test_diff_identical(self):
        from rcm_mc.infra.config import diff_configs
        cfg = _minimal_config()
        diffs = diff_configs(cfg, cfg)
        self.assertEqual(len(diffs), 0)

    def test_diff_detects_change(self):
        from rcm_mc.infra.config import diff_configs
        cfg_a = {"a": 1}
        cfg_b = {"a": 2}
        diffs = diff_configs(cfg_a, cfg_b)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0]["change"], "modified")


if __name__ == "__main__":
    unittest.main()
