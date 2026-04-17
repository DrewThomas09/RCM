"""Tests for the intake wizard."""
from __future__ import annotations

import os
import tempfile
import unittest
from typing import List

import yaml

from rcm_mc.infra.config import validate_config
from rcm_mc.data.intake import (
    _blended_mean,
    _hcris_prefill_bundle,
    _parse_percent,
    _resolve_name_to_ccn,
    apply_intake_answers,
    interactive_intake,
    load_template,
    run_intake,
    scale_blended_to_per_payer,
)


def _mock_io(scripted_inputs: List[str]):
    """Builds (input_fn, output_fn, outputs_captured) — scripted terminal."""
    it = iter(scripted_inputs)
    outputs: List[str] = []

    def input_fn(_prompt: str) -> str:
        return next(it)

    def output_fn(s: str) -> None:
        outputs.append(s)

    return input_fn, output_fn, outputs


class TestTemplateLoading(unittest.TestCase):
    def test_shipped_templates_load(self):
        for name in ("community_hospital_500m", "rural_critical_access", "actual"):
            cfg = load_template(name)
            self.assertIn("hospital", cfg)
            self.assertIn("payers", cfg)

    def test_unknown_template_raises(self):
        with self.assertRaises(ValueError):
            load_template("nonexistent")


class TestBlendedAndScaling(unittest.TestCase):
    def setUp(self):
        self.cfg = load_template("community_hospital_500m")

    def test_blended_idr_matches_weighted_mean(self):
        blended = _blended_mean(self.cfg, ("denials", "idr"))
        self.assertIsNotNone(blended)
        # Recompute manually as a cross-check
        payers = self.cfg["payers"]
        manual_num = sum(
            float(p.get("revenue_share") or 0) * float((p.get("denials") or {}).get("idr", {}).get("mean") or 0)
            for p in payers.values()
            if p.get("denials")
        )
        manual_den = sum(
            float(p.get("revenue_share") or 0)
            for p in payers.values()
            if p.get("denials") and (p["denials"].get("idr") or {}).get("mean") is not None
        )
        self.assertAlmostEqual(blended, manual_num / manual_den, places=6)

    def test_scale_lands_on_target_blended(self):
        target = 0.20  # 20% — pushed up from template default
        scale_blended_to_per_payer(self.cfg, ("denials", "idr"), target, min_clamp=0.001, max_clamp=0.80)
        new_blended = _blended_mean(self.cfg, ("denials", "idr"))
        self.assertAlmostEqual(new_blended, target, places=3)

    def test_scale_preserves_relative_ordering(self):
        payers_before = self.cfg["payers"]
        idr_before = {n: p["denials"]["idr"]["mean"] for n, p in payers_before.items() if p.get("denials")}
        order_before = sorted(idr_before, key=idr_before.get)

        scale_blended_to_per_payer(self.cfg, ("denials", "idr"), 0.25, min_clamp=0.001, max_clamp=0.80)
        idr_after = {n: p["denials"]["idr"]["mean"] for n, p in self.cfg["payers"].items() if p.get("denials")}
        order_after = sorted(idr_after, key=idr_after.get)
        self.assertEqual(order_before, order_after, "relative payer ranking must survive scaling")


class TestApplyAnswers(unittest.TestCase):
    def setUp(self):
        self.cfg = load_template("community_hospital_500m")

    def test_overwrites_hospital_and_econ(self):
        apply_intake_answers(self.cfg, {
            "hospital_name": "Acme Health",
            "annual_revenue": 750_000_000,
            "ebitda_margin": 0.10,
            "wacc": 0.11,
        })
        self.assertEqual(self.cfg["hospital"]["name"], "Acme Health")
        self.assertEqual(self.cfg["hospital"]["annual_revenue"], 750_000_000.0)
        self.assertEqual(self.cfg["hospital"]["ebitda_margin"], 0.10)
        self.assertEqual(self.cfg["economics"]["wacc_annual"], 0.11)

    def test_overwrites_payer_mix_and_sets_selfpay_residual(self):
        apply_intake_answers(self.cfg, {
            "mix_medicare": 0.50, "mix_medicaid": 0.20, "mix_commercial": 0.25,
        })
        total = sum(p["revenue_share"] for p in self.cfg["payers"].values())
        self.assertAlmostEqual(total, 1.0, places=6)
        self.assertAlmostEqual(self.cfg["payers"]["SelfPay"]["revenue_share"], 0.05, places=6)

    def test_marks_touched_paths_as_observed(self):
        apply_intake_answers(self.cfg, {
            "annual_revenue": 600_000_000,
            "idr_blended": 0.15,
        })
        sm = self.cfg["_source_map"]
        self.assertEqual(sm.get("hospital.annual_revenue"), "observed")
        # At least one payer IDR should have been tagged
        payer_idr_tags = [v for k, v in sm.items() if k.endswith(".denials.idr")]
        self.assertTrue(payer_idr_tags)
        self.assertTrue(all(v == "observed" for v in payer_idr_tags))

    def test_default_source_is_assumed_when_not_set(self):
        apply_intake_answers(self.cfg, {})
        self.assertEqual(self.cfg["_source_map"]["_default"], "assumed")


class TestRunIntakeEndToEnd(unittest.TestCase):
    def test_run_intake_writes_valid_yaml(self):
        answers = {
            "hospital_name": "Test Target",
            "annual_revenue": 420_000_000,
            "mix_medicare": 0.40, "mix_medicaid": 0.20, "mix_commercial": 0.35,
            "idr_blended": 0.14,
            "fwr_blended": 0.30,
            "dar_blended": 50.0,
            "ebitda_margin": 0.07,
            "wacc": 0.10,
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = run_intake(answers, template_name="community_hospital_500m", out_path=out)
            # File on disk
            self.assertTrue(os.path.exists(out))
            # Loads back valid
            with open(out) as f:
                reloaded = yaml.safe_load(f)
            validate_config(reloaded)
            # Applied values present
            self.assertEqual(reloaded["hospital"]["name"], "Test Target")
            self.assertEqual(reloaded["hospital"]["annual_revenue"], 420_000_000.0)
            self.assertAlmostEqual(
                _blended_mean(reloaded, ("denials", "idr")) or 0, 0.14, places=3
            )

    def test_run_intake_rejects_invalid_config(self):
        # Mix that sums > 1 after residual => SelfPay becomes 0 but Medicare/etc. > 1 breaks shares sum
        bad_answers = {
            "mix_medicare": 0.80, "mix_medicaid": 0.80, "mix_commercial": 0.80,
        }
        with tempfile.TemporaryDirectory() as tmp:
            # validate_config should catch this (payer shares > 1)
            with self.assertRaises(ValueError):
                run_intake(bad_answers, template_name="community_hospital_500m",
                           out_path=os.path.join(tmp, "actual.yaml"))


class TestInteractiveShell(unittest.TestCase):
    def test_full_scripted_walkthrough_writes_valid_file(self):
        scripted = [
            "1",               # template menu: first choice
            "Happy Hospital",  # name
            "450000000",       # NPSR
            "45",              # Medicare %
            "18",              # Medicaid %
            "32",              # Commercial %  (→ SelfPay = 5%)
            "13",              # IDR %
            "28",              # FWR %
            "55",              # A/R days
            "9",               # EBITDA margin %
            "11",              # WACC %
        ]
        input_fn, output_fn, _captured = _mock_io(scripted)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = interactive_intake(out, input_fn=input_fn, output_fn=output_fn)
            self.assertTrue(os.path.exists(out))
            self.assertEqual(cfg["hospital"]["name"], "Happy Hospital")
            self.assertAlmostEqual(cfg["hospital"]["annual_revenue"], 4.5e8)
            self.assertAlmostEqual(cfg["payers"]["SelfPay"]["revenue_share"], 0.05, places=3)

    def test_enter_accepts_defaults_and_still_validates(self):
        # Empty string = accept default for every prompt.
        scripted = [""] * 11
        input_fn, output_fn, _ = _mock_io(scripted)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = interactive_intake(out, input_fn=input_fn, output_fn=output_fn)
            self.assertTrue(os.path.exists(out))
            # Validates back
            with open(out) as f:
                validate_config(yaml.safe_load(f))


class TestHcrisPrefillBundle(unittest.TestCase):
    """The _hcris_prefill_bundle helper returns the dict passed to the wizard."""

    def test_known_ccn_with_yes_returns_bundle(self):
        """CCN 360180 (Cleveland Clinic) is in the shipped HCRIS data."""
        scripted = [""]  # press Enter at "Use this as starting point? [Y/n]"
        input_fn, output_fn, _ = _mock_io(scripted)
        bundle = _hcris_prefill_bundle("360180", input_fn=input_fn, output_fn=output_fn)
        self.assertIsNotNone(bundle)
        a = bundle["answers"]
        self.assertEqual(a["hospital_name"], "CLEVELAND CLINIC HOSPITAL")
        self.assertGreater(a["annual_revenue"], 1e9)
        self.assertGreater(a["mix_medicare"], 0.10)
        self.assertLess(a["mix_medicare"], 0.40)
        self.assertIn("CMS HCRIS", bundle["note"])
        self.assertIn("360180", bundle["note"])
        # hcris_paths must include annual_revenue + both payer shares
        self.assertIn("hospital.annual_revenue", bundle["hcris_paths"])
        self.assertIn("payers.Medicare.revenue_share", bundle["hcris_paths"])
        self.assertIn("payers.Medicaid.revenue_share", bundle["hcris_paths"])

    def test_unknown_ccn_returns_none(self):
        input_fn, output_fn, outputs = _mock_io([])  # no prompts expected
        bundle = _hcris_prefill_bundle("999999", input_fn=input_fn, output_fn=output_fn)
        self.assertIsNone(bundle)
        # User-facing warning should mention the CCN
        joined = "\n".join(outputs)
        self.assertIn("999999", joined)

    def test_user_declines_returns_none(self):
        input_fn, output_fn, _ = _mock_io(["n"])
        bundle = _hcris_prefill_bundle("360180", input_fn=input_fn, output_fn=output_fn)
        self.assertIsNone(bundle)


class TestInteractiveIntakeWithCcn(unittest.TestCase):
    """End-to-end: --from-ccn skips hospital prompts and stamps HCRIS provenance."""

    def test_ccn_prefill_skips_hospital_prompts_and_tags_source(self):
        # With HCRIS providing name, NPSR, Medicare %, Medicaid % we only need
        # to answer: [accept prefill=""], template=1, Commercial %, IDR, FWR,
        # DAR, EBITDA margin, WACC = 8 prompts total.
        scripted = [
            "",       # accept HCRIS prefill (Y default)
            "1",      # template: actual (or whatever index 1 is — sorted list)
            "35",     # Commercial %
            "14",     # IDR %
            "30",     # FWR %
            "55",     # A/R days
            "9",      # EBITDA margin
            "11",     # WACC
        ]
        input_fn, output_fn, _ = _mock_io(scripted)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = interactive_intake(
                out, input_fn=input_fn, output_fn=output_fn,
                ccn_prefill="360180",
            )
            self.assertTrue(os.path.exists(out))
            # Hospital name came from HCRIS
            self.assertEqual(cfg["hospital"]["name"], "CLEVELAND CLINIC HOSPITAL")
            # Source map marks HCRIS-derived paths with the HCRIS note
            sm = cfg["_source_map"]
            note_key = "hospital.annual_revenue._note"
            self.assertIn(note_key, sm)
            self.assertIn("HCRIS", sm[note_key])
            self.assertIn("360180", sm[note_key])
            # And Medicare revenue share carries the HCRIS note
            medicare_note = sm.get("payers.Medicare.revenue_share._note", "")
            self.assertIn("HCRIS", medicare_note)
            # User-provided IDR path carries the DEFAULT wizard note, not HCRIS
            # (Find any payer IDR note)
            idr_notes = [v for k, v in sm.items() if k.endswith(".denials.idr._note")]
            self.assertTrue(idr_notes)
            self.assertTrue(all("intake wizard" in n for n in idr_notes),
                            msg=f"IDR notes should be wizard-sourced; got {idr_notes}")

    def test_ccn_prefill_writes_hospital_ccn_to_yaml(self):
        """hospital.ccn must land in the YAML so downstream peer-compare triggers."""
        scripted = ["", "2", "35", "14", "30", "55", "9", "11"]
        input_fn, output_fn, _ = _mock_io(scripted)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = interactive_intake(
                out, input_fn=input_fn, output_fn=output_fn,
                ccn_prefill="360180",
            )
            self.assertEqual(cfg["hospital"]["ccn"], "360180")
            # And it persists to disk too
            with open(out) as f:
                reloaded = yaml.safe_load(f)
            self.assertEqual(reloaded["hospital"]["ccn"], "360180")

    def test_ccn_not_found_falls_back_to_full_wizard(self):
        # Unknown CCN: prefill returns None; wizard prompts for all 11 fields.
        scripted = [
            "1",              # template pick
            "Fallback Hosp",  # name (no HCRIS, so prompt is asked)
            "400000000",      # NPSR
            "40", "20", "35", # payer mix
            "13", "28", "50", # IDR / FWR / DAR
            "8", "11",        # EBITDA margin / WACC
        ]
        input_fn, output_fn, _ = _mock_io(scripted)
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = interactive_intake(
                out, input_fn=input_fn, output_fn=output_fn,
                ccn_prefill="999999",  # unknown
            )
            self.assertEqual(cfg["hospital"]["name"], "Fallback Hosp")
            # No HCRIS note anywhere in the source map
            sm = cfg["_source_map"]
            hcris_notes = [v for k, v in sm.items()
                           if k.endswith("._note") and "HCRIS" in str(v)]
            self.assertEqual(hcris_notes, [])


class TestResolveNameToCcn(unittest.TestCase):
    """Brick 40: fuzzy name → CCN with strict ambiguity handling."""

    def test_no_match_returns_error_code_1(self):
        import io
        import sys as _sys
        err = io.StringIO()
        saved = _sys.stderr
        _sys.stderr = err
        try:
            code, ccn = _resolve_name_to_ccn("nonexistent hospital name xyz")
        finally:
            _sys.stderr = saved
        self.assertEqual(code, 1)
        self.assertIsNone(ccn)
        self.assertIn("No HCRIS match", err.getvalue())

    def test_multiple_matches_returns_error_code_2(self):
        import io
        import sys as _sys
        err = io.StringIO()
        saved = _sys.stderr
        _sys.stderr = err
        try:
            code, ccn = _resolve_name_to_ccn("memorial")
        finally:
            _sys.stderr = saved
        self.assertEqual(code, 2)
        self.assertIsNone(ccn)
        self.assertIn("Multiple HCRIS matches", err.getvalue())
        # Guidance should include --from-ccn
        self.assertIn("--from-ccn", err.getvalue())

    def test_multiple_matches_lists_candidates_with_ccns(self):
        import io
        import sys as _sys
        err = io.StringIO()
        saved = _sys.stderr
        _sys.stderr = err
        try:
            _resolve_name_to_ccn("memorial")
        finally:
            _sys.stderr = saved
        # Each candidate line should have 6 leading digits (a CCN)
        import re
        ccns = re.findall(r"\b\d{6}\b", err.getvalue())
        self.assertGreaterEqual(len(ccns), 2)


class TestRunIntakeExtraObservations(unittest.TestCase):
    def test_extra_observations_override_default_note(self):
        """run_intake's extra_observations should stamp specific paths."""
        answers = {
            "hospital_name": "Test",
            "annual_revenue": 500_000_000,
            "mix_medicare": 0.40, "mix_medicaid": 0.20, "mix_commercial": 0.35,
            "idr_blended": 0.14, "fwr_blended": 0.30, "dar_blended": 50.0,
            "ebitda_margin": 0.08, "wacc": 0.12,
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "actual.yaml")
            cfg = run_intake(
                answers,
                template_name="community_hospital_500m",
                out_path=out,
                extra_observations={"hospital.annual_revenue": "from audited 10-K FY2024"},
            )
            sm = cfg["_source_map"]
            # The override note replaced the default wizard note
            self.assertEqual(sm["hospital.annual_revenue._note"], "from audited 10-K FY2024")
            # Other fields still carry the default note
            self.assertIn("intake wizard", sm.get("payers.Medicare.revenue_share._note", ""))


class TestParsePercent(unittest.TestCase):
    def test_accepts_bare_percent(self):
        self.assertAlmostEqual(_parse_percent("13"), 0.13)

    def test_accepts_percent_sign(self):
        self.assertAlmostEqual(_parse_percent("13%"), 0.13)

    def test_accepts_decimal(self):
        self.assertAlmostEqual(_parse_percent("0.13"), 0.13)

    def test_small_decimals_unchanged(self):
        self.assertAlmostEqual(_parse_percent("0.08"), 0.08)
