"""Tests for the public helpers in rcm_mc.infra.config that Report 0253 surfaced as untested.

Six functions had zero coverage in the existing test suite:

- ``is_multi_site``
- ``expand_multi_site``
- ``canonical_payer_name``
- ``export_config_json`` / ``import_config_json``
- ``flatten_config``

Report 0253 flagged each as part of the implicit public surface of
``rcm_mc/infra/config.py`` (no ``__all__`` declared). This file gives
each one a happy path + 1-2 edge cases so a future rename or signature
drift would surface in CI rather than silently breaking downstream
consumers.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.infra.config import (
    ConfigError,
    canonical_payer_name,
    expand_multi_site,
    export_config_json,
    flatten_config,
    import_config_json,
    is_multi_site,
)


class TestIsMultiSite(unittest.TestCase):
    def test_returns_true_for_non_empty_sites_list(self):
        cfg = {"hospital": {}, "sites": [{"name": "A"}, {"name": "B"}]}
        self.assertTrue(is_multi_site(cfg))

    def test_returns_false_when_sites_key_missing(self):
        self.assertFalse(is_multi_site({"hospital": {}}))

    def test_returns_false_for_empty_sites_list(self):
        self.assertFalse(is_multi_site({"sites": []}))

    def test_returns_false_when_sites_is_not_a_list(self):
        # Defensive: dict / string / None must not pass the check.
        self.assertFalse(is_multi_site({"sites": {"not": "a list"}}))
        self.assertFalse(is_multi_site({"sites": "Hospital A"}))


class TestExpandMultiSite(unittest.TestCase):
    def test_single_site_input_returns_single_element_list_unchanged(self):
        cfg = {"hospital": {"name": "Solo"}, "annual_revenue": 100}
        result = expand_multi_site(cfg)
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], cfg)  # passthrough — same object

    def test_two_sites_inherit_base_and_override_name(self):
        cfg = {
            "annual_revenue": 500_000_000,
            "ebitda_margin": 0.08,
            "sites": [
                {"name": "Site A", "annual_revenue": 200_000_000},
                {"name": "Site B"},  # inherits parent annual_revenue
            ],
        }
        out = expand_multi_site(cfg)
        self.assertEqual(len(out), 2)
        # Site A overrides annual_revenue + sets hospital.name from `name`
        self.assertEqual(out[0]["annual_revenue"], 200_000_000)
        self.assertEqual(out[0]["hospital"]["name"], "Site A")
        self.assertEqual(out[0]["ebitda_margin"], 0.08)
        # Site B inherits annual_revenue + still gets hospital.name set
        self.assertEqual(out[1]["annual_revenue"], 500_000_000)
        self.assertEqual(out[1]["hospital"]["name"], "Site B")
        # Neither expanded cfg carries the original `sites` list
        self.assertNotIn("sites", out[0])
        self.assertNotIn("sites", out[1])

    def test_existing_hospital_section_is_preserved_when_present(self):
        cfg = {
            "hospital": {"region": "Northeast"},
            "sites": [{"name": "S1"}],
        }
        out = expand_multi_site(cfg)
        self.assertEqual(out[0]["hospital"]["region"], "Northeast")
        self.assertEqual(out[0]["hospital"]["name"], "S1")


class TestCanonicalPayerName(unittest.TestCase):
    def test_canonical_names_pass_through(self):
        self.assertEqual(canonical_payer_name("Medicare"), "Medicare")
        self.assertEqual(canonical_payer_name("Medicaid"), "Medicaid")
        self.assertEqual(canonical_payer_name("Commercial"), "Commercial")
        self.assertEqual(canonical_payer_name("SelfPay"), "SelfPay")

    def test_self_pay_aliases_normalize_to_selfpay(self):
        # All three forms (Self-Pay / Self Pay / self) collapse to SelfPay.
        self.assertEqual(canonical_payer_name("Self-Pay"), "SelfPay")
        self.assertEqual(canonical_payer_name("Self Pay"), "SelfPay")
        self.assertEqual(canonical_payer_name("self"), "SelfPay")
        self.assertEqual(canonical_payer_name("SELFPAY"), "SelfPay")

    def test_private_and_phi_normalize_to_commercial(self):
        # Non-obvious aliases noted in Report 0253 MR1049.
        self.assertEqual(canonical_payer_name("Private"), "Commercial")
        self.assertEqual(canonical_payer_name("PHI"), "Commercial")
        self.assertEqual(canonical_payer_name("commercial"), "Commercial")

    def test_unknown_segment_passes_through_with_whitespace_stripped(self):
        self.assertEqual(canonical_payer_name(" TRICARE "), "TRICARE")
        self.assertEqual(canonical_payer_name("VA"), "VA")


class TestExportImportConfigJson(unittest.TestCase):
    def test_round_trip_preserves_dict(self):
        cfg = {"hospital": {"name": "X", "annual_revenue": 1234}, "x": [1, 2, 3]}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.json")
            export_config_json(cfg, path)
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as f:
                on_disk = json.load(f)
            self.assertEqual(on_disk, cfg)
            self.assertEqual(import_config_json(path), cfg)

    def test_export_creates_intermediate_directories(self):
        cfg = {"k": 1}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "nested", "deeper", "out.json")
            export_config_json(cfg, path)
            self.assertTrue(os.path.isfile(path))

    def test_import_rejects_non_dict_top_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "list.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump([1, 2, 3], f)
            with self.assertRaises(ConfigError):
                import_config_json(path)


class TestFlattenConfig(unittest.TestCase):
    def test_nested_dicts_flatten_to_dotted_keys(self):
        cfg = {"hospital": {"name": "X", "annual_revenue": 100}, "wacc": 0.12}
        rows = flatten_config(cfg)
        keys = {r["parameter"] for r in rows}
        self.assertIn("hospital.name", keys)
        self.assertIn("hospital.annual_revenue", keys)
        self.assertIn("wacc", keys)

    def test_list_value_renders_as_string_with_type_marker(self):
        rows = flatten_config({"payers": ["A", "B"]})
        match = next(r for r in rows if r["parameter"] == "payers")
        self.assertEqual(match["type"], "list")
        # Value is the str() of the list — round-trip-detectable.
        self.assertIn("A", match["value"])
        self.assertIn("B", match["value"])

    def test_scalar_types_are_named(self):
        rows = flatten_config({"flag": True, "count": 5, "ratio": 0.5, "label": "x"})
        types = {r["parameter"]: r["type"] for r in rows}
        self.assertEqual(types["flag"], "bool")
        self.assertEqual(types["count"], "int")
        self.assertEqual(types["ratio"], "float")
        self.assertEqual(types["label"], "str")


if __name__ == "__main__":
    unittest.main()
