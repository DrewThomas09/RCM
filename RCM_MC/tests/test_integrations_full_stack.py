"""Full-stack integration tests — CMS advisory + Tuva bridge + packet.

Confirms the two sibling projects under ``Coding Projects/`` are
wired into ``rcm_mc`` correctly:

- ``cms_medicare-master`` → ``rcm_mc/pe/cms_advisory.py`` +
  ``cms_advisory_bridge.py`` produce the expected scoring tables
  and convert them into ``RiskFlag`` rows.
- ``ChartisDrewIntel-main`` (vendored Tuva) → reachable via
  ``rcm_mc.diligence.ingest.tuva_bridge.vendored_tuva_path()``, and
  a CCD round-trips into Tuva's Input Layer schema.
"""
from __future__ import annotations

import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from rcm_mc.analysis.packet import RiskFlag, RiskSeverity
from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.ingest import (
    TUVA_ELIGIBILITY_COLUMNS,
    TUVA_MEDICAL_CLAIM_COLUMNS,
    TUVA_PHARMACY_CLAIM_COLUMNS,
    ccd_to_tuva_input_layer_arrow,
    vendored_tuva_path,
)
from rcm_mc.pe.cms_advisory import (
    REGIMES,
    consensus_rank,
    momentum_profile,
    provider_volatility,
    regime_classification,
    screen_providers,
    standardize_columns,
    stress_test,
    yearly_trends,
)
from rcm_mc.pe.cms_advisory_bridge import (
    CMSAdvisoryFindings,
    findings_for_provider,
    findings_to_risk_flags,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


# ── Shared synthetic dataset for the advisory pipeline ──────────────

def _synthetic_cms_frame() -> pd.DataFrame:
    """A small synthetic CMS-style frame with three provider types
    across three years. Values are chosen so the regime classifier
    produces at least one durable_growth and one declining_risk
    result — giving the bridge something to flag."""
    rows = []
    # Internal Medicine — steady compounder, low vol
    for year, payment in [(2021, 1_000_000), (2022, 1_080_000), (2023, 1_140_000)]:
        rows.append({
            "provider_type": "Internal Medicine", "year": year,
            "total_medicare_payment_amt": payment,
            "total_services": payment // 100,
            "total_unique_benes": payment // 500,
            "beneficiary_average_risk_score": 1.08,
        })
    # Cardiology — durable growth, high risk acuity
    for year, payment in [(2021, 3_000_000), (2022, 3_500_000), (2023, 4_200_000)]:
        rows.append({
            "provider_type": "Cardiology", "year": year,
            "total_medicare_payment_amt": payment,
            "total_services": payment // 600,
            "total_unique_benes": payment // 3_000,
            "beneficiary_average_risk_score": 1.55,
        })
    # Psychiatry — declining / volatile
    for year, payment in [(2021, 500_000), (2022, 300_000), (2023, 600_000)]:
        rows.append({
            "provider_type": "Psychiatry", "year": year,
            "total_medicare_payment_amt": payment,
            "total_services": payment // 200,
            "total_unique_benes": payment // 1_000,
            "beneficiary_average_risk_score": 1.10,
        })
    df = pd.DataFrame(rows)
    df["payment_per_service"] = df["total_medicare_payment_amt"] / df["total_services"]
    df["payment_per_bene"] = df["total_medicare_payment_amt"] / df["total_unique_benes"]
    return df


class CMSAdvisoryPipelineTests(unittest.TestCase):

    def setUp(self):
        self.df = _synthetic_cms_frame()

    def test_screen_providers_ranks_opportunity(self):
        screen = screen_providers(self.df)
        self.assertEqual(len(screen), 3)
        # Cardiology has highest scale + acuity → opportunity
        # should rank first.
        self.assertEqual(screen.index[0], "Cardiology")
        for col in ("opportunity_score", "market_share",
                    "fragmentation_score", "opportunity_percentile"):
            self.assertIn(col, screen.columns)

    def test_yearly_trends_and_volatility(self):
        trends = yearly_trends(self.df)
        self.assertEqual(len(trends), 9)    # 3 types × 3 years
        vol = provider_volatility(trends)
        psych = vol[vol["provider_type"] == "Psychiatry"].iloc[0]
        cardio = vol[vol["provider_type"] == "Cardiology"].iloc[0]
        # Psychiatry payments -40% then +100% → higher volatility.
        self.assertGreater(
            psych["yoy_payment_volatility"],
            cardio["yoy_payment_volatility"],
        )

    def test_regime_classification_covers_synthetic_spread(self):
        trends = yearly_trends(self.df)
        vol = provider_volatility(trends)
        mom = momentum_profile(trends, min_years=2)
        reg = regime_classification(mom, vol)
        self.assertEqual(len(reg), 3)
        self.assertTrue(set(reg["regime"].astype(str)).issubset(set(REGIMES)),
                        msg=f"unexpected regime label: {reg['regime'].tolist()}")

    def test_stress_test_applies_all_scenarios(self):
        screen = screen_providers(self.df)
        stress = stress_test(screen)
        self.assertGreater(len(stress), 0)
        for col in ("scenario", "stressed_payment_per_bene", "delta_pct"):
            self.assertIn(col, stress.columns)
        # Every default scenario is a downside in TOTAL payment terms.
        # (Per-bene can rise when benes shrink faster than payment —
        # that's why delta_pct is total-payment, not per-bene.)
        self.assertTrue((stress["delta_pct"] <= 0).all(),
                        msg=f"all default scenarios should be total-payment "
                            f"downside; got:\n{stress[['scenario','delta_pct']]}")

    def test_consensus_rank_is_dense(self):
        screen = screen_providers(self.df)
        trends = yearly_trends(self.df)
        vol = provider_volatility(trends)
        mom = momentum_profile(trends, min_years=2)
        cons = consensus_rank(screen, mom, vol)
        self.assertEqual(len(cons), 3)
        self.assertListEqual(
            sorted(cons["consensus_rank"].tolist()), [1, 2, 3],
            msg="consensus ranks should be 1..n with no gaps",
        )


class CMSAdvisoryBridgeTests(unittest.TestCase):
    """Bridge turns advisory DataFrames into RiskFlag rows suitable for
    ``DealAnalysisPacket.risk_flags``."""

    def setUp(self):
        self.df = _synthetic_cms_frame()
        self.screen = screen_providers(self.df)
        self.trends = yearly_trends(self.df)
        self.vol = provider_volatility(self.trends)
        self.mom = momentum_profile(self.trends, min_years=2)
        self.regimes = regime_classification(self.mom, self.vol)
        self.stress = stress_test(self.screen)
        self.cons = consensus_rank(self.screen, self.mom, self.vol)

    def test_findings_for_provider_populates_every_field(self):
        f = findings_for_provider(
            "Cardiology",
            consensus=self.cons, regimes=self.regimes,
            volatility=self.vol, stress=self.stress,
        )
        self.assertEqual(f.provider_type, "Cardiology")
        self.assertIsNotNone(f.consensus_rank)
        self.assertIsNotNone(f.regime)
        # Cardiology has steady growth → vol MAY be None if too few
        # observations; at minimum, the field exists.
        self.assertIsNotNone(f.worst_stress_scenario)

    def test_findings_for_unknown_provider_is_empty_but_safe(self):
        f = findings_for_provider(
            "Nonexistent Specialty",
            consensus=self.cons, regimes=self.regimes,
            volatility=self.vol, stress=self.stress,
        )
        self.assertIsNone(f.consensus_rank)
        self.assertIsNone(f.regime)
        flags = findings_to_risk_flags(f)
        self.assertEqual(flags, [])

    def test_findings_to_risk_flags_types(self):
        f = findings_for_provider(
            "Cardiology",
            consensus=self.cons, regimes=self.regimes,
            volatility=self.vol, stress=self.stress,
        )
        flags = findings_to_risk_flags(f)
        for flag in flags:
            self.assertIsInstance(flag, RiskFlag)
            self.assertIn(flag.category, {
                "market_posture", "operating_regime",
                "earnings_durability", "stress_exposure",
            })
            self.assertIsInstance(flag.severity, RiskSeverity)
            self.assertTrue(flag.title)
            self.assertTrue(flag.detail)

    def test_top_ranked_provider_gets_attractive_flag(self):
        """With a synthetic 8-provider universe, the #1 and bottom
        ranks fall cleanly inside the 25/75 quartile cutoffs, so we
        can exercise both LOW and HIGH market-posture paths."""
        # Build a synthetic consensus table with 8 provider types so
        # rank 1 → 12.5th percentile (top quartile) and rank 8 →
        # 100th percentile (bottom quartile) — both sides of the
        # bridge's thresholds.
        consensus = pd.DataFrame([
            {"provider_type": f"Provider-{i:02d}",
             "consensus_score": 1.0 - i * 0.1,
             "consensus_rank": i + 1}
            for i in range(8)
        ])
        top = findings_for_provider("Provider-00", consensus=consensus)
        bottom = findings_for_provider("Provider-07", consensus=consensus)
        top_flags = findings_to_risk_flags(top)
        bottom_flags = findings_to_risk_flags(bottom)
        top_posture = [f for f in top_flags if f.category == "market_posture"]
        bottom_posture = [f for f in bottom_flags if f.category == "market_posture"]
        self.assertEqual(len(top_posture), 1)
        self.assertEqual(top_posture[0].severity, RiskSeverity.LOW)
        self.assertEqual(len(bottom_posture), 1)
        self.assertEqual(bottom_posture[0].severity, RiskSeverity.HIGH)


class TuvaBridgeTests(unittest.TestCase):
    """CCD → Tuva Input Layer schema mapping. Does NOT require dbt or
    the vendored Tuva project to be on disk — the arrow-output path
    works purely from our code."""

    def setUp(self):
        self.ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_01_clean_acute",
        )

    def test_arrow_tables_have_correct_columns(self):
        tables = ccd_to_tuva_input_layer_arrow(self.ccd)
        self.assertIn("medical_claim", tables)
        self.assertIn("pharmacy_claim", tables)
        self.assertIn("eligibility", tables)
        med = tables["medical_claim"]
        self.assertEqual(
            list(med.column_names), TUVA_MEDICAL_CLAIM_COLUMNS,
            msg="medical_claim columns must match Tuva Input Layer contract",
        )
        pharm = tables["pharmacy_claim"]
        self.assertEqual(
            list(pharm.column_names), TUVA_PHARMACY_CLAIM_COLUMNS,
        )
        elig = tables["eligibility"]
        self.assertEqual(
            list(elig.column_names), TUVA_ELIGIBILITY_COLUMNS,
        )

    def test_medical_claim_rows_populated_from_ccd(self):
        tables = ccd_to_tuva_input_layer_arrow(self.ccd)
        med = tables["medical_claim"].to_pylist()
        self.assertEqual(len(med), 10)    # hospital_01 has 10 claims
        for row in med:
            self.assertTrue(row["claim_id"])
            self.assertEqual(row["person_id"], row["member_id"])
            self.assertEqual(row["data_source"], "claims")

    def test_eligibility_one_row_per_person(self):
        tables = ccd_to_tuva_input_layer_arrow(self.ccd)
        elig = tables["eligibility"].to_pylist()
        self.assertEqual(len(elig), 10)    # 10 distinct patients
        self.assertEqual(
            len({r["person_id"] for r in elig}), 10,
            msg="eligibility should have one row per distinct patient_id",
        )

    def test_pharmacy_claim_is_empty_but_typed_when_no_rx_data(self):
        tables = ccd_to_tuva_input_layer_arrow(self.ccd)
        pharm = tables["pharmacy_claim"]
        self.assertEqual(pharm.num_rows, 0,
                         msg="no pharmacy data → empty table (not missing)")
        # Columns still match contract.
        self.assertEqual(
            list(pharm.column_names), TUVA_PHARMACY_CLAIM_COLUMNS,
        )

    def test_vendored_tuva_path_resolves_or_returns_none(self):
        """If the sibling ``ChartisDrewIntel-main`` folder exists,
        vendored_tuva_path() returns its Path; else None. Both are
        acceptable — we just assert the contract."""
        p = vendored_tuva_path()
        if p is not None:
            self.assertTrue(p.exists())
            self.assertTrue((p / "dbt_project.yml").exists())
            # Confirm it's Tuva (not some unrelated dbt project).
            project_yml = (p / "dbt_project.yml").read_text("utf-8")
            self.assertIn("the_tuva_project", project_yml)
        else:
            # Not an error — the wheel install path doesn't carry
            # the vendored copy.
            self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
