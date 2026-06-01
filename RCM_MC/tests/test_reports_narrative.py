"""Tests for ``rcm_mc/reports/narrative.py`` — the 3-paragraph
plain-English summary that lands in the partner brief.

Module is small (83 LOC, one public function) but partner-visible:
the narrative paragraphs are the first thing a PE partner reads in
the diligence packet. Locks the contract (paragraph count, currency
formatting, hospital-name interpolation, sensitivity callout) before
any tweak silently changes the wording in the brief.
"""
from __future__ import annotations

import unittest

import pandas as pd

from rcm_mc.reports.narrative import (
    _fmt_money,
    generate_narrative,
)


# ---------------------------------------------------------------------------
# _fmt_money (module-local formatter — separate from reporting.pretty_money)
# ---------------------------------------------------------------------------


class FmtMoneyTests(unittest.TestCase):
    """Mirrors reporting.pretty_money in spirit but uses a slightly
    different format spec (with comma separators in K/M tier).
    Locked here so the narrative paragraphs don't drift."""

    def test_millions_with_one_decimal(self):
        self.assertEqual(_fmt_money(5_000_000), "$5.0M")
        self.assertEqual(_fmt_money(8_800_000), "$8.8M")

    def test_thousands_no_decimals(self):
        self.assertEqual(_fmt_money(50_000), "$50K")
        self.assertEqual(_fmt_money(1_500), "$2K")  # rounds

    def test_below_thousand(self):
        self.assertEqual(_fmt_money(500), "$500")
        self.assertEqual(_fmt_money(0), "$0")

    def test_negative_keeps_sign_inline(self):
        # Note: unlike reporting.pretty_money (which puts the sign
        # BEFORE the dollar), narrative._fmt_money allows the negative
        # to land inside the comma format (Python default).
        self.assertEqual(_fmt_money(-1_500_000), "$-1.5M")

    def test_boundary_at_1m(self):
        # 1_000_000 → '$1.0M'
        self.assertEqual(_fmt_money(1_000_000), "$1.0M")

    def test_boundary_at_1k(self):
        self.assertEqual(_fmt_money(1_000), "$1K")


# ---------------------------------------------------------------------------
# generate_narrative
# ---------------------------------------------------------------------------


def _summary(**overrides) -> pd.DataFrame:
    """Build a summary DataFrame indexed by metric name with mean/p10/p90."""
    base = {
        "ebitda_drag":             dict(mean=5_000_000, p10=3_000_000, p90=7_500_000),
        "drag_denial_writeoff":    dict(mean=2_500_000, p10=1_500_000, p90=3_500_000),
        "drag_underpay_leakage":   dict(mean=1_000_000, p10=600_000,   p90=1_400_000),
        "drag_denial_rework_cost": dict(mean=300_000,   p10=200_000,   p90=400_000),
        "economic_drag":           dict(mean=400_000,   p10=200_000,   p90=600_000),
    }
    base.update(overrides)
    rows = [{"metric": k, **v} for k, v in base.items()]
    return pd.DataFrame(rows).set_index("metric")


class StructureTests(unittest.TestCase):

    def test_returns_string(self):
        out = generate_narrative(_summary())
        self.assertIsInstance(out, str)

    def test_three_paragraphs_when_full_data(self):
        # ebitda + drivers + risks = 3 paragraphs separated by blank line.
        out = generate_narrative(_summary())
        paragraphs = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paragraphs), 3)

    def test_drops_ebitda_paragraph_when_missing(self):
        # No ebitda_drag row → headline paragraph skipped (only
        # drivers + risks = 2 paragraphs).
        df = _summary()
        df = df.drop(index="ebitda_drag")
        out = generate_narrative(df)
        paragraphs = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paragraphs), 2)
        self.assertFalse(any("recovery opportunity" in p for p in paragraphs))

    def test_drops_drivers_paragraph_when_no_driver_metrics(self):
        # Drop every driver metric → only ebitda + risks.
        df = _summary()
        df = df.drop(index=[
            "drag_denial_writeoff", "drag_underpay_leakage",
            "drag_denial_rework_cost", "economic_drag",
        ])
        out = generate_narrative(df)
        paragraphs = [p for p in out.split("\n\n") if p.strip()]
        self.assertEqual(len(paragraphs), 2)
        self.assertFalse(any("primary value drivers" in p for p in paragraphs))

    def test_risks_paragraph_always_present(self):
        # Even with NO data, the risks paragraph (boilerplate) appears.
        out = generate_narrative(pd.DataFrame().set_index(
            pd.Index([], name="metric")))
        self.assertIn("Key risks include", out)


class HeadlineParagraphTests(unittest.TestCase):

    def test_hospital_name_interpolated(self):
        out = generate_narrative(_summary(), hospital_name="St. Foo Medical")
        self.assertIn("St. Foo Medical", out)

    def test_default_hospital_name(self):
        out = generate_narrative(_summary())
        self.assertIn("the target hospital", out)

    def test_default_ev_multiple_is_8x(self):
        out = generate_narrative(_summary())
        # ev_multiple=8 → 5M × 8 = $40M EV
        self.assertIn("$40.0M", out)
        self.assertIn("8x multiple", out)

    def test_custom_ev_multiple(self):
        out = generate_narrative(_summary(), ev_multiple=12.0)
        self.assertIn("$60.0M", out)  # 5M × 12
        self.assertIn("12x multiple", out)

    def test_p10_and_p90_appear_in_headline(self):
        out = generate_narrative(_summary())
        self.assertIn("$3.0M", out)  # p10
        self.assertIn("$7.5M", out)  # p90

    def test_headline_words_are_present(self):
        out = generate_narrative(_summary())
        self.assertIn("Monte Carlo analysis", out)
        self.assertIn("recovery opportunity", out)
        self.assertIn("enterprise value", out)


class DriversParagraphTests(unittest.TestCase):

    def test_caps_at_3_drivers(self):
        # Even though 4 driver metrics are present, only the first 3
        # land in the paragraph.
        out = generate_narrative(_summary())
        drivers_text = next(
            p for p in out.split("\n\n") if "value drivers" in p)
        self.assertEqual(drivers_text.count(" ("), 3)

    def test_titles_driver_labels(self):
        # 'drag_denial_writeoff' → 'Denial Writeoff', etc. (title-case
        # after stripping drag_ prefix and underscores).
        out = generate_narrative(_summary())
        self.assertIn("Denial Writeoff", out)
        self.assertIn("Underpay Leakage", out)

    def test_dollar_amounts_appear_for_each_driver(self):
        out = generate_narrative(_summary())
        drivers_text = next(
            p for p in out.split("\n\n") if "value drivers" in p)
        # Each driver tuple is wrapped in parens with the formatted $.
        self.assertEqual(drivers_text.count("$"), 3)


class SensitivityClauseTests(unittest.TestCase):

    def test_no_sensitivity_no_clause(self):
        out = generate_narrative(_summary(), sensitivity_df=None)
        self.assertNotIn("Sensitivity analysis identifies", out)

    def test_empty_sensitivity_no_clause(self):
        out = generate_narrative(
            _summary(), sensitivity_df=pd.DataFrame())
        self.assertNotIn("Sensitivity analysis identifies", out)

    def test_with_sensitivity_uses_driver_label(self):
        sens = pd.DataFrame([
            {"driver": "idr_medicare",
             "driver_label": "Medicare IDR",
             "corr": 0.55},
            {"driver": "fwr_medicaid",
             "driver_label": "Medicaid FWR",
             "corr": 0.42},
            {"driver": "dar_other",
             "driver_label": "Other DAR",
             "corr": 0.30},
        ])
        out = generate_narrative(_summary(), sensitivity_df=sens)
        self.assertIn("Sensitivity analysis identifies", out)
        # Top 2 driver labels appear in the clause.
        self.assertIn("Medicare IDR", out)
        self.assertIn("Medicaid FWR", out)

    def test_sensitivity_falls_back_to_driver_column(self):
        # No 'driver_label' column → uses 'driver'.
        sens = pd.DataFrame([
            {"driver": "idr_medicare", "corr": 0.55},
            {"driver": "fwr_medicaid", "corr": 0.42},
        ])
        out = generate_narrative(_summary(), sensitivity_df=sens)
        self.assertIn("idr_medicare", out)
        self.assertIn("fwr_medicaid", out)

    def test_sensitivity_takes_top_2_of_3(self):
        # Helper caps clause to top 2 drivers even if 3+ in df.
        sens = pd.DataFrame([
            {"driver": "a", "driver_label": "Driver A", "corr": 0.5},
            {"driver": "b", "driver_label": "Driver B", "corr": 0.4},
            {"driver": "c", "driver_label": "Driver C", "corr": 0.3},
        ])
        out = generate_narrative(_summary(), sensitivity_df=sens)
        # First 2 labels present, 3rd is NOT in the clause body.
        # (May still appear elsewhere — checked only inside the
        # 'Sensitivity analysis identifies' fragment.)
        clause = out.split("Sensitivity analysis identifies")[1]
        clause = clause.split(".")[0]  # the one sentence
        self.assertIn("Driver A", clause)
        self.assertIn("Driver B", clause)
        self.assertNotIn("Driver C", clause)


class RisksParagraphTests(unittest.TestCase):

    def test_mentions_payer_policy_and_staffing(self):
        out = generate_narrative(_summary())
        self.assertIn("payer policy changes", out)
        self.assertIn("staffing constraints", out)

    def test_recommends_claims_audit(self):
        out = generate_narrative(_summary())
        self.assertIn("claims-level audit", out)


if __name__ == "__main__":
    unittest.main()
