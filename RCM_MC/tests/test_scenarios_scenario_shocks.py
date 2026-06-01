"""Tests for ``rcm_mc/scenarios/scenario_shocks.py``.

The ``apply_shocks_to_config`` helper is the pure-function core
behind the Scenario Explorer's preset payer-shock buttons (e.g.
'Commercial IDR +20% (Prior-Auth risk)'). ``run_preset_shocks``
orchestrates the simulator and depends on file paths — covered by
integration paths; THIS file covers the pure config-transform
helper + the PRESET_SHOCKS registry which is partner-visible
(each preset's name lands in a UI button).

Module had no direct unit-test coverage. Locking the multiplier
math + the max-cap behavior + the preset registry contract before
any tweak silently shifts what partners see when they click 'IDR +20%'.
"""
from __future__ import annotations

import unittest
from copy import deepcopy

from rcm_mc.scenarios.scenario_shocks import (
    PRESET_SHOCKS,
    apply_shocks_to_config,
)


def _base_cfg() -> dict:
    return {
        "payers": {
            "Medicare": {
                "denials": {
                    "idr": {"mean": 0.10, "max": 0.5},
                    "fwr": {"mean": 0.05, "max": 0.8},
                },
                "underpayments": {
                    "upr": {"mean": 0.04, "max": 0.3},
                },
            },
            "Commercial": {
                "denials": {
                    "idr": {"mean": 0.14, "max": 0.5},
                    "fwr": {"mean": 0.04, "max": 0.8},
                },
                "underpayments": {
                    "upr": {"mean": 0.05, "max": 0.3},
                },
            },
        },
    }


# ---------------------------------------------------------------------------
# apply_shocks_to_config — pure config-transform helper
# ---------------------------------------------------------------------------


class ApplyShocksImmutabilityTests(unittest.TestCase):
    """Input config must NOT be mutated — caller depends on this so
    presets can be reused side-by-side."""

    def test_does_not_mutate_input(self):
        cfg = _base_cfg()
        original = deepcopy(cfg)
        _ = apply_shocks_to_config(cfg, {
            "payers": {"Medicare": {"idr_mult": 1.20}}})
        self.assertEqual(cfg, original)

    def test_returns_distinct_object(self):
        cfg = _base_cfg()
        out = apply_shocks_to_config(cfg, {})
        self.assertIsNot(out, cfg)
        # Even with empty shocks, returns deepcopy.
        self.assertEqual(out, cfg)


class IdrShockTests(unittest.TestCase):

    def test_idr_mult_above_1_increases_mean(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"idr_mult": 1.5}},
        })
        # 0.10 * 1.5 = 0.15
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"],
            0.15, places=4,
        )

    def test_idr_mult_below_1_decreases_mean(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"idr_mult": 0.5}},
        })
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"],
            0.05, places=4,
        )

    def test_idr_capped_at_max(self):
        # 0.10 * 10.0 = 1.0 → caps at max=0.5
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"idr_mult": 10.0}},
        })
        self.assertEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"], 0.5)

    def test_default_idr_max_when_missing(self):
        # Drop the max from cfg → default fallback 0.5 is used.
        cfg = _base_cfg()
        del cfg["payers"]["Medicare"]["denials"]["idr"]["max"]
        out = apply_shocks_to_config(cfg, {
            "payers": {"Medicare": {"idr_mult": 10.0}},
        })
        # Caps at hardcoded default 0.5.
        self.assertEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"], 0.5)


class FwrShockTests(unittest.TestCase):

    def test_fwr_mult_applies(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"fwr_mult": 2.0}},
        })
        # 0.05 * 2.0 = 0.10
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["denials"]["fwr"]["mean"],
            0.10, places=4,
        )

    def test_fwr_capped_at_max_080(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"fwr_mult": 100.0}},
        })
        self.assertEqual(
            out["payers"]["Medicare"]["denials"]["fwr"]["mean"], 0.8)


class UprShockTests(unittest.TestCase):

    def test_upr_mult_applies(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"upr_mult": 2.0}},
        })
        # 0.04 * 2.0 = 0.08
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["underpayments"]["upr"]["mean"],
            0.08, places=4,
        )

    def test_upr_capped_at_max_030(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {"upr_mult": 100.0}},
        })
        self.assertEqual(
            out["payers"]["Medicare"]["underpayments"]["upr"]["mean"],
            0.3,
        )


class MultipleShocksTests(unittest.TestCase):
    """Composing shocks across payers + metric kinds."""

    def test_multiple_payers_apply_independently(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {
                "Medicare": {"idr_mult": 1.5},
                "Commercial": {"idr_mult": 1.2},
            },
        })
        # Medicare 0.10 * 1.5 = 0.15
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["denials"]["idr"]["mean"], 0.15)
        # Commercial 0.14 * 1.2 = 0.168
        self.assertAlmostEqual(
            out["payers"]["Commercial"]["denials"]["idr"]["mean"],
            0.168, places=4,
        )

    def test_idr_fwr_upr_compose_within_one_payer(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {
                "idr_mult": 1.5,
                "fwr_mult": 1.4,
                "upr_mult": 1.2,
            }},
        })
        m = out["payers"]["Medicare"]
        self.assertAlmostEqual(m["denials"]["idr"]["mean"], 0.15)
        self.assertAlmostEqual(m["denials"]["fwr"]["mean"], 0.07)
        self.assertAlmostEqual(
            m["underpayments"]["upr"]["mean"], 0.048, places=4)


class SilentSkipTests(unittest.TestCase):
    """Robust to malformed cfgs/shocks — silently skip rather than
    crash so the preset button never fails on a partial cfg."""

    def test_unknown_payer_silently_skipped(self):
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Aetna": {"idr_mult": 1.5}},
        })
        # No matching payer → cfg returned unchanged.
        self.assertEqual(out, _base_cfg())

    def test_missing_denials_idr_silently_skipped(self):
        cfg = _base_cfg()
        del cfg["payers"]["Medicare"]["denials"]["idr"]
        out = apply_shocks_to_config(cfg, {
            "payers": {"Medicare": {"idr_mult": 1.5}},
        })
        # Commercial unchanged; Medicare idr key still absent.
        self.assertNotIn(
            "idr", out["payers"]["Medicare"]["denials"])

    def test_missing_underpayments_silently_skipped(self):
        cfg = _base_cfg()
        del cfg["payers"]["Medicare"]["underpayments"]
        out = apply_shocks_to_config(cfg, {
            "payers": {"Medicare": {"upr_mult": 1.5}},
        })
        # No upr_mult applied; cfg compares equal-but-distinct.
        self.assertNotIn("underpayments", out["payers"]["Medicare"])

    def test_empty_shocks_returns_copy(self):
        # Empty shocks → deep copy of original returned, unchanged.
        out = apply_shocks_to_config(_base_cfg(), {})
        self.assertEqual(out, _base_cfg())

    def test_shocks_with_no_payers_key_returns_copy(self):
        out = apply_shocks_to_config(_base_cfg(), {"unrelated": "data"})
        self.assertEqual(out, _base_cfg())

    def test_default_mult_is_1_when_omitted(self):
        # Shock dict with no mults → default 1.0 applies → no change.
        out = apply_shocks_to_config(_base_cfg(), {
            "payers": {"Medicare": {}},
        })
        self.assertEqual(out, _base_cfg())


# ---------------------------------------------------------------------------
# PRESET_SHOCKS registry — partner-visible scenario button list
# ---------------------------------------------------------------------------


class PresetRegistryTests(unittest.TestCase):
    """Each preset id and name lands in the Scenario Explorer UI as
    a clickable button. Lock the registry shape so a refactor can't
    silently break the button bar."""

    def test_is_a_non_empty_list(self):
        self.assertIsInstance(PRESET_SHOCKS, list)
        self.assertGreater(len(PRESET_SHOCKS), 0)

    def test_each_preset_has_id_name_shocks(self):
        for p in PRESET_SHOCKS:
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("shocks", p)
            self.assertIsInstance(p["shocks"], dict)

    def test_preset_ids_are_unique(self):
        ids = [p["id"] for p in PRESET_SHOCKS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_each_preset_targets_at_least_one_payer(self):
        for p in PRESET_SHOCKS:
            payers = p["shocks"].get("payers", {})
            self.assertGreater(
                len(payers), 0,
                f"preset {p['id']} has no payer shocks",
            )

    def test_canonical_preset_ids_present(self):
        # Lock the IDs partners see in the UI button bar.
        ids = {p["id"] for p in PRESET_SHOCKS}
        for pid in ("commercial_idr_20", "medicare_idr_15",
                     "all_payers_idr_10"):
            self.assertIn(pid, ids, f"missing canonical preset: {pid}")

    def test_each_preset_is_apply_shocks_compatible(self):
        # Smoke-test that every preset can be applied without error
        # to a reasonable base cfg.
        base = _base_cfg()
        # Add Medicaid since one of the presets references it.
        base["payers"]["Medicaid"] = {
            "denials": {
                "idr": {"mean": 0.12, "max": 0.5},
                "fwr": {"mean": 0.06, "max": 0.8},
            },
            "underpayments": {"upr": {"mean": 0.05, "max": 0.3}},
        }
        for p in PRESET_SHOCKS:
            out = apply_shocks_to_config(base, p["shocks"])
            self.assertIsInstance(out, dict)
            # Shocks should produce ≥ baseline IDR for affected payers.
            for payer_name in p["shocks"].get("payers", {}):
                if payer_name in base["payers"]:
                    new_idr = (
                        out["payers"][payer_name]
                        ["denials"]["idr"]["mean"]
                    )
                    old_idr = (
                        base["payers"][payer_name]
                        ["denials"]["idr"]["mean"]
                    )
                    self.assertGreaterEqual(
                        new_idr, old_idr - 1e-9,
                        f"preset {p['id']} lowered IDR for {payer_name}",
                    )


if __name__ == "__main__":
    unittest.main()
