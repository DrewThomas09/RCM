"""Step 75: Config round-trip tests (load -> validate -> save -> load)."""
import os
import tempfile
import unittest

import yaml

from rcm_mc.infra.config import load_and_validate, validate_config


class TestConfigRoundtrip(unittest.TestCase):

    def _roundtrip(self, path):
        cfg1 = load_and_validate(path)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.safe_dump(cfg1, f, sort_keys=False)
            tmp = f.name
        try:
            cfg2 = load_and_validate(tmp)
            for key in ("hospital", "payers", "appeals", "operations"):
                self.assertIn(key, cfg2, f"Missing section '{key}' after round-trip of {path}")
            # Check payer count preserved
            self.assertEqual(len(cfg1["payers"]), len(cfg2["payers"]))
        finally:
            os.unlink(tmp)

    def test_actual_roundtrip(self):
        self._roundtrip("configs/actual.yaml")

    def test_benchmark_roundtrip(self):
        self._roundtrip("configs/benchmark.yaml")

    def test_template_community_roundtrip(self):
        self._roundtrip("configs/templates/community_hospital_500m.yaml")

    def test_template_rural_roundtrip(self):
        self._roundtrip("configs/templates/rural_critical_access.yaml")


if __name__ == "__main__":
    unittest.main()
