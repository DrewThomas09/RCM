"""Regression tests for the infra/config hardening pass (Report-0262).

Covers the TRIAGE items closed in that iteration:

- MR1046: explicit ``__all__`` on rcm_mc/infra/config.py.
- MR1047: ``_extends`` cycle detection (self- and mutual-extension must
  raise ConfigError, not RecursionError).
- MR1048: ``${VAR}`` / ``${VAR:default}`` resolution contract — set vars
  substitute, defaults apply when unset, and an unset var without a
  default keeps the literal text while warning (never silently).
- MR1050: ``validate_config_from_path`` is the never-raises soft wrapper
  around the canonical hard-fail ``load_and_validate``.
- MR1051: ``MANDATORY_PAYERS`` (dead since Step 31) is gone.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import yaml

from rcm_mc.infra import config as config_mod
from rcm_mc.infra.config import (
    ConfigError,
    load_and_validate,
    load_yaml,
    validate_config_from_path,
)


class TestPublicSurface(unittest.TestCase):
    def test_all_declared_and_resolvable(self):
        self.assertTrue(hasattr(config_mod, "__all__"))
        for name in config_mod.__all__:
            self.assertTrue(hasattr(config_mod, name), f"__all__ lists missing name {name}")

    def test_all_has_no_private_names(self):
        for name in config_mod.__all__:
            self.assertFalse(name.startswith("_"), f"__all__ lists private name {name}")

    def test_mandatory_payers_removed(self):
        # MR1051: dead constant deleted; canonical_payer_name is the
        # one payer-key contract.
        self.assertFalse(hasattr(config_mod, "MANDATORY_PAYERS"))


class TestExtendsCycleDetection(unittest.TestCase):
    def _write(self, tmp: str, name: str, body: dict) -> str:
        path = os.path.join(tmp, name)
        with open(path, "w") as f:
            yaml.safe_dump(body, f)
        return path

    def test_self_extending_raises_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, "a.yaml", {"_extends": "a.yaml", "k": 1})
            with self.assertRaises(ConfigError) as ctx:
                load_yaml(path)
            self.assertIn("Circular _extends", str(ctx.exception))

    def test_mutual_extension_raises_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "b.yaml", {"_extends": "a.yaml", "k": 2})
            path = self._write(tmp, "a.yaml", {"_extends": "b.yaml", "k": 1})
            with self.assertRaises(ConfigError) as ctx:
                load_yaml(path)
            self.assertIn("Circular _extends", str(ctx.exception))

    def test_legitimate_chain_still_merges(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "base.yaml", {"a": 1, "nested": {"x": 1, "y": 2}})
            self._write(tmp, "mid.yaml", {"_extends": "base.yaml", "nested": {"y": 3}})
            path = self._write(tmp, "leaf.yaml", {"_extends": "mid.yaml", "b": 2})
            data = load_yaml(path)
            self.assertEqual(data["a"], 1)
            self.assertEqual(data["b"], 2)
            self.assertEqual(data["nested"], {"x": 1, "y": 3})


class TestEnvVarResolution(unittest.TestCase):
    def _load(self, body: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cfg.yaml")
            with open(path, "w") as f:
                yaml.safe_dump(body, f)
            return load_yaml(path)

    def test_set_variable_substitutes(self):
        with patch.dict(os.environ, {"RCM_TEST_ENV_VAR": "hello"}):
            data = self._load({"k": "${RCM_TEST_ENV_VAR}"})
        self.assertEqual(data["k"], "hello")

    def test_unset_variable_with_default_uses_default(self):
        env = {k: v for k, v in os.environ.items() if k != "RCM_TEST_ENV_VAR"}
        with patch.dict(os.environ, env, clear=True):
            data = self._load({"k": "${RCM_TEST_ENV_VAR:fallback}"})
        self.assertEqual(data["k"], "fallback")

    def test_unset_variable_without_default_warns_and_keeps_literal(self):
        env = {k: v for k, v in os.environ.items() if k != "RCM_TEST_ENV_VAR"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertLogs("rcm_mc", level="WARNING") as captured:
                data = self._load({"k": "${RCM_TEST_ENV_VAR}"})
        self.assertEqual(data["k"], "${RCM_TEST_ENV_VAR}")
        self.assertTrue(
            any("RCM_TEST_ENV_VAR" in line for line in captured.output),
            "expected a warning naming the unset variable",
        )


class TestSoftValidationWrapper(unittest.TestCase):
    def test_soft_wrapper_reports_what_hard_entry_raises(self):
        # MR1050: the two contracts must stay tied together — anything
        # that makes load_and_validate raise must come back as
        # (False, [message]) from the soft wrapper.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bad.yaml")
            with open(path, "w") as f:
                yaml.safe_dump({"not_hospital": {}}, f)
            with self.assertRaises(ConfigError):
                load_and_validate(path)
            ok, issues = validate_config_from_path(path)
            self.assertFalse(ok)
            self.assertEqual(len(issues), 1)
            self.assertTrue(issues[0])


if __name__ == "__main__":
    unittest.main()
