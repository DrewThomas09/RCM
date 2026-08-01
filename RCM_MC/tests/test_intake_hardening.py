"""Regression tests for the data/intake hardening pass (Report-0262).

Covers the TRIAGE items closed in that iteration:

- MR1042: run_intake writes atomically (temp + os.replace) so a kill
  mid-dump can never truncate an existing actual.yaml.
- MR1044: DEFAULT_TEMPLATE is the single source for the default
  template name.
- MR1045: an empty/null template file raises at the load site with the
  file path, instead of silently becoming ``{}``.
"""
from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from rcm_mc.data import intake as intake_mod
from rcm_mc.data.intake import (
    DEFAULT_TEMPLATE,
    TEMPLATES,
    load_template,
    run_intake,
)

_ANSWERS = {
    "hospital_name": "Atomic Test Target",
    "annual_revenue": 420_000_000,
    "mix_medicare": 0.40,
    "mix_medicaid": 0.20,
    "mix_commercial": 0.35,
    "idr_blended": 0.14,
    "fwr_blended": 0.30,
    "dar_blended": 50.0,
    "ebitda_margin": 0.07,
    "wacc": 0.10,
}


class TestDefaultTemplateConstant(unittest.TestCase):
    def test_default_template_is_registered(self):
        self.assertIn(DEFAULT_TEMPLATE, TEMPLATES)

    def test_run_intake_signature_uses_constant(self):
        sig = inspect.signature(run_intake)
        self.assertEqual(sig.parameters["template_name"].default, DEFAULT_TEMPLATE)


class TestEmptyTemplateGuard(unittest.TestCase):
    def test_empty_template_file_raises_with_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.yaml"
            empty.write_text("")
            with patch.dict(TEMPLATES, {"_empty_test": empty}):
                with self.assertRaises(ValueError) as ctx:
                    load_template("_empty_test")
            self.assertIn(str(empty), str(ctx.exception))

    def test_null_template_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            nul = Path(tmp) / "null.yaml"
            nul.write_text("null\n")
            with patch.dict(TEMPLATES, {"_null_test": nul}):
                with self.assertRaises(ValueError):
                    load_template("_null_test")

    def test_non_mapping_template_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            lst = Path(tmp) / "list.yaml"
            lst.write_text("- a\n- b\n")
            with patch.dict(TEMPLATES, {"_list_test": lst}):
                with self.assertRaises(ValueError):
                    load_template("_list_test")


class TestAtomicWrite(unittest.TestCase):
    def test_successful_run_leaves_no_tmp_sibling(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            run_intake(_ANSWERS, out_path=out)
            self.assertTrue(os.path.exists(out))
            self.assertFalse(
                os.path.exists(out + ".tmp"),
                "atomic write must clean up its temp file",
            )

    def test_existing_output_survives_failed_dump(self):
        # MR1042: the whole point of temp+replace — a failure mid-dump
        # must leave the previous actual.yaml byte-for-byte intact.
        # Stubbing yaml.safe_dump (external lib) to fail is the
        # documented external-stub exception in CLAUDE.md.
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            with open(out, "w") as f:
                f.write("precious: contents\n")
            with patch.object(intake_mod.yaml, "safe_dump", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    run_intake(_ANSWERS, out_path=out)
            with open(out) as f:
                self.assertEqual(f.read(), "precious: contents\n")
            self.assertFalse(os.path.exists(out + ".tmp"))

    def test_written_yaml_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = run_intake(_ANSWERS, out_path=out)
            with open(out) as f:
                reloaded = yaml.safe_load(f)
            self.assertEqual(reloaded["hospital"]["name"], cfg["hospital"]["name"])


if __name__ == "__main__":
    unittest.main()
