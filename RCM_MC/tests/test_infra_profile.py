"""Tests for hospital-profile extraction + application.

`rcm_mc/infra/profile.py` defines the structural "hospital
profile" (annual revenue + per-payer revenue_share + avg_claim)
that MUST be identical between Actual and Benchmark scenarios so
the comparison is apples-to-apples. Three public functions, only
``align_benchmark_to_actual`` had any test coverage; the two
underlying helpers — ``extract_hospital_profile`` and
``apply_hospital_profile`` — had no direct tests.

Bugs here silently distort the bridge math (different volumes →
different denial counts → different rework costs).
"""
from __future__ import annotations

import copy
import unittest

from rcm_mc.infra.profile import (
    DEFAULT_PROFILE_KEYS,
    HospitalProfile,
    apply_hospital_profile,
    extract_hospital_profile,
)


def _basic_cfg(
    revenue=500_000_000,
    medicare_share=0.40, medicaid_share=0.15, commercial_share=0.45,
    avg_claim=2_500,
):
    return {
        "hospital": {"annual_revenue": revenue},
        "payers": {
            "Medicare": {"revenue_share": medicare_share,
                          "avg_claim_dollars": avg_claim},
            "Medicaid": {"revenue_share": medicaid_share,
                          "avg_claim_dollars": avg_claim * 0.8},
            "Commercial": {"revenue_share": commercial_share,
                            "avg_claim_dollars": avg_claim * 1.2},
        },
    }


class ExtractHospitalProfileTests(unittest.TestCase):

    def test_returns_hospital_profile_dataclass(self):
        cfg = _basic_cfg()
        out = extract_hospital_profile(cfg)
        self.assertIsInstance(out, HospitalProfile)

    def test_extracts_annual_revenue_as_float(self):
        cfg = _basic_cfg(revenue=750_000_000)
        out = extract_hospital_profile(cfg)
        self.assertEqual(out.annual_revenue, 750_000_000.0)
        self.assertIsInstance(out.annual_revenue, float)

    def test_extracts_default_keys_per_payer(self):
        cfg = _basic_cfg()
        out = extract_hospital_profile(cfg)
        self.assertEqual(set(out.payer_profile.keys()),
                          {"Medicare", "Medicaid", "Commercial"})
        for payer in out.payer_profile:
            for k in DEFAULT_PROFILE_KEYS:
                self.assertIn(k, out.payer_profile[payer])

    def test_missing_annual_revenue_defaults_to_zero(self):
        cfg = {"hospital": {}, "payers": {}}
        out = extract_hospital_profile(cfg)
        self.assertEqual(out.annual_revenue, 0.0)

    def test_missing_hospital_section_defaults_to_zero(self):
        cfg = {"payers": {}}
        out = extract_hospital_profile(cfg)
        self.assertEqual(out.annual_revenue, 0.0)

    def test_missing_payers_section_returns_empty_dict(self):
        cfg = {"hospital": {"annual_revenue": 1e9}}
        out = extract_hospital_profile(cfg)
        self.assertEqual(out.payer_profile, {})

    def test_payer_missing_a_key_silently_skipped(self):
        # If a payer config is missing one of the requested keys,
        # that key is just not present in the per-payer dict (the
        # other keys still extracted).
        cfg = {
            "hospital": {"annual_revenue": 1e9},
            "payers": {
                "Medicare": {"revenue_share": 0.4},  # no avg_claim
                "Commercial": {"revenue_share": 0.6,
                                "avg_claim_dollars": 2000},
            },
        }
        out = extract_hospital_profile(cfg)
        self.assertEqual(out.payer_profile["Medicare"],
                          {"revenue_share": 0.4})
        self.assertEqual(out.payer_profile["Commercial"],
                          {"revenue_share": 0.6,
                           "avg_claim_dollars": 2000.0})

    def test_custom_keys_override_defaults(self):
        cfg = _basic_cfg()
        # Pull only revenue_share, drop avg_claim_dollars.
        out = extract_hospital_profile(cfg, keys=("revenue_share",))
        for payer, vals in out.payer_profile.items():
            self.assertIn("revenue_share", vals)
            self.assertNotIn("avg_claim_dollars", vals)


class ApplyHospitalProfileTests(unittest.TestCase):

    def test_overwrites_annual_revenue(self):
        cfg = _basic_cfg(revenue=100_000_000)
        profile = HospitalProfile(annual_revenue=999_000_000,
                                    payer_profile={})
        out = apply_hospital_profile(cfg, profile)
        self.assertEqual(out["hospital"]["annual_revenue"],
                          999_000_000.0)

    def test_overwrites_payer_profile_keys(self):
        cfg = _basic_cfg(medicare_share=0.40)
        profile = HospitalProfile(
            annual_revenue=1e9,
            payer_profile={
                "Medicare": {"revenue_share": 0.55,
                              "avg_claim_dollars": 3000},
            },
        )
        out = apply_hospital_profile(cfg, profile)
        self.assertEqual(out["payers"]["Medicare"]["revenue_share"],
                          0.55)
        self.assertEqual(
            out["payers"]["Medicare"]["avg_claim_dollars"], 3000.0)

    def test_payer_in_profile_but_not_in_cfg_silently_skipped(self):
        # If the profile references a payer not in the target cfg
        # (e.g. cfg never had MedicareAdvantage), it's silently
        # skipped — the target cfg gets back unchanged for that
        # payer.
        cfg = _basic_cfg()
        profile = HospitalProfile(
            annual_revenue=1e9,
            payer_profile={
                "MedicareAdvantage": {"revenue_share": 0.20},
            },
        )
        out = apply_hospital_profile(cfg, profile)
        self.assertNotIn("MedicareAdvantage", out["payers"])
        # Pre-existing Medicare untouched
        self.assertAlmostEqual(
            out["payers"]["Medicare"]["revenue_share"], 0.40)

    def test_creates_hospital_section_if_missing(self):
        # cfg with no 'hospital' key → setdefault creates it before
        # writing annual_revenue.
        cfg = {"payers": {}}
        profile = HospitalProfile(annual_revenue=5e8, payer_profile={})
        out = apply_hospital_profile(cfg, profile)
        self.assertIn("hospital", out)
        self.assertEqual(out["hospital"]["annual_revenue"], 5e8)

    def test_handles_none_payers_section(self):
        # Edge case: cfg has a 'payers' key set to None. The code
        # does `payers = cfg.get('payers', {}) or {}` so None →
        # empty dict (defensive).
        cfg = {"hospital": {}, "payers": None}
        profile = HospitalProfile(annual_revenue=1e9,
                                    payer_profile={"X": {"revenue_share": 1.0}})
        # Must not raise.
        out = apply_hospital_profile(cfg, profile)
        self.assertEqual(out["payers"], {})

    def test_returns_same_dict_object_for_chaining(self):
        # The function mutates AND returns; mutation is intentional
        # (caller can deepcopy first if they need immutability).
        cfg = _basic_cfg()
        profile = HospitalProfile(annual_revenue=1e9,
                                    payer_profile={})
        out = apply_hospital_profile(cfg, profile)
        self.assertIs(out, cfg)

    def test_partial_keys_apply_only_listed(self):
        # Profile has both keys but only one is requested via keys
        # arg → only that one overwritten.
        cfg = _basic_cfg()
        original_avg = cfg["payers"]["Medicare"]["avg_claim_dollars"]
        profile = HospitalProfile(
            annual_revenue=1e9,
            payer_profile={
                "Medicare": {"revenue_share": 0.99,
                              "avg_claim_dollars": 99999},
            },
        )
        apply_hospital_profile(cfg, profile, keys=("revenue_share",))
        # revenue_share overwritten...
        self.assertAlmostEqual(
            cfg["payers"]["Medicare"]["revenue_share"], 0.99)
        # ...but avg_claim_dollars unchanged (not in keys)
        self.assertAlmostEqual(
            cfg["payers"]["Medicare"]["avg_claim_dollars"],
            original_avg)


class RoundTripTests(unittest.TestCase):
    """extract + apply should round-trip cleanly so the existing
    align_benchmark_to_actual workflow is preserved."""

    def test_extract_then_apply_preserves_target(self):
        # Extract from a source cfg, apply to a deepcopy of the
        # same cfg → identical to original.
        src = _basic_cfg(revenue=300_000_000, medicare_share=0.33)
        target = copy.deepcopy(src)
        profile = extract_hospital_profile(src)
        apply_hospital_profile(target, profile)
        self.assertEqual(target, src)

    def test_apply_aligns_a_different_target(self):
        # The intended use: extract from Actual, apply to Benchmark
        # so they share the structural profile.
        actual = _basic_cfg(revenue=500_000_000,
                              medicare_share=0.50,
                              avg_claim=3000)
        bench = _basic_cfg(revenue=100_000_000,  # different
                            medicare_share=0.30,
                            avg_claim=1500)
        profile = extract_hospital_profile(actual)
        apply_hospital_profile(bench, profile)
        # After alignment, profile fields match Actual.
        self.assertEqual(bench["hospital"]["annual_revenue"],
                          500_000_000.0)
        self.assertAlmostEqual(
            bench["payers"]["Medicare"]["revenue_share"], 0.50)
        self.assertAlmostEqual(
            bench["payers"]["Medicare"]["avg_claim_dollars"],
            3000.0)


if __name__ == "__main__":
    unittest.main()
