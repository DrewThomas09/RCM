"""End-to-end tests for the diligence synthesis runner.

The runner ties all 8 packets together. These tests verify:
  • An empty dossier runs without crashing and reports every
    section as skipped.
  • A fully-populated dossier runs every packet and returns
    non-None results for each.
  • Partial dossiers run only the supported packets.
"""
from __future__ import annotations

import os
import tempfile
import unittest


class TestEmptyDossier(unittest.TestCase):
    def test_empty_runs_with_all_sections_missing(self):
        from rcm_mc.diligence_synthesis import (
            DiligenceDossier, run_full_diligence,
        )
        dossier = DiligenceDossier(
            deal_name="Empty Co", sector="hospital",
        )
        result = run_full_diligence(dossier)
        self.assertEqual(result.deal_name, "Empty Co")
        self.assertEqual(result.sections_run, [])
        # Every packet should be flagged as missing inputs
        self.assertEqual(len(result.missing_inputs), 13)


class TestPartialDossier(unittest.TestCase):
    def test_only_qoe_runs_with_financial_panel(self):
        from rcm_mc.diligence_synthesis import (
            DiligenceDossier, run_full_diligence,
        )
        dossier = DiligenceDossier(
            deal_name="QoE Only Co", sector="hospital",
            financial_panel={
                "deal_name": "QoE Only Co",
                "periods": ["2023", "2024", "TTM"],
                "income_statement": {
                    "revenue": [100, 110, 120],
                    "ebitda_reported": [10, 12, 14],
                    "non_recurring_items": [
                        {"period": "TTM", "amount": 1.5,
                         "description": "asset sale"},
                    ],
                },
                "balance_sheet": {
                    "ar": [10, 11, 12], "inventory": [5, 5, 5],
                    "ap": [6, 6, 6],
                },
                "cash_flow": {
                    "cash_receipts": [99, 109, 119],
                },
                "owner_compensation": {
                    "actual": [0.5, 0.5, 0.5],
                    "benchmark": [0.5, 0.5, 0.5],
                },
                "payer_mix": {
                    "self_pay_share": [0.05, 0.05, 0.05],
                    "out_of_network_share": [0.05, 0.05, 0.05],
                },
            },
        )
        result = run_full_diligence(dossier)
        self.assertIn("qoe", result.sections_run)
        self.assertIsNotNone(result.qoe_result)
        # Other 12 packets skipped
        self.assertEqual(len(result.sections_run), 1)
        self.assertEqual(len(result.missing_inputs), 12)


class TestFullySupportedDossier(unittest.TestCase):
    """A dossier that hits every packet's input requirements."""

    def setUp(self):
        from rcm_mc.pricing import PricingStore
        from rcm_mc.referral import ReferralGraph
        from rcm_mc.regulatory import (
            RegulatoryCorpus, RegulatoryDocument,
        )
        from rcm_mc.vbc import Cohort, ContractTerms
        from rcm_mc.buyandbuild import Platform, AddOnCandidate
        from rcm_mc.exit_readiness import ExitTarget

        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        store = PricingStore(self.db)
        store.init_db()
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        with store.connect() as con:
            for payer, npi, rate in (
                ("Aetna", "N1", 24500),
                ("BCBS", "N1", 25500),
                ("UHC", "N1", 26500),
            ):
                con.execute(
                    "INSERT INTO pricing_payer_rates "
                    "(payer_name, plan_name, npi, code, code_type, "
                    " negotiation_arrangement, negotiated_rate, "
                    " loaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (payer, "PPO", npi, "27447", "CPT", "ffs",
                     rate, now),
                )
            con.commit()
        self.store = store

        graph = ReferralGraph()
        graph.set_node_org("P1", "Plat")
        graph.set_node_org("Ext1", "Outside")
        graph.add_edge("Ext1", "P1", 100)
        self.graph = graph

        corpus = RegulatoryCorpus()
        corpus.add(RegulatoryDocument(
            doc_id="FR-1",
            source="federal_register",
            title="FTC non-compete final rule",
            body="Federal Trade Commission final rule on non-compete "
                 "agreements affecting physician mobility.",
            states=[], sector_tags=["hospital"]))
        self.corpus = corpus

        self.cohort = Cohort(
            cohort_id="C1", size=1500, avg_age=70,
            hcc_distribution={"HCC_DM_NO_COMP": 0.30},
            annual_pmpm_cost=1080.0,
        )
        self.contract = ContractTerms(
            contract_type="TCC", benchmark_pmpm=1180.0,
        )

        self.platform = Platform(
            platform_id="PLAT", sector="physician_group",
            base_ebitda_mm=20, base_ev_mm=200,
            state="TX", cbsa="26420")
        self.candidates = [
            AddOnCandidate(
                add_on_id="A1", name="Houston",
                purchase_price_mm=20.0, standalone_ebitda_mm=2.5,
                state="TX", cbsa="26420", closing_risk_pct=0.05),
        ]

        self.exit_target = ExitTarget(
            target_name="Test Co", sector="hospital",
            ttm_revenue_mm=350.0, ttm_ebitda_mm=63.0,
            growth_rate=0.10, ebitda_margin=0.18,
            net_debt_mm=180.0,
            public_comp_multiple=12.5, private_comp_multiple=11.0,
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_dossier_runs_every_packet(self):
        from rcm_mc.diligence_synthesis import (
            DiligenceDossier, run_full_diligence,
        )
        dossier = DiligenceDossier(
            deal_name="Full Co",
            sector="hospital",
            states=["TX"],
            ebitda_mm=63.0,
            revenue_mm=350.0,
            pricing_store=self.store,
            target_npis=["N1"],
            target_codes=["27447"],
            cohort=self.cohort,
            contract=self.contract,
            referral_graph=self.graph,
            platform_orgs=["Plat"],
            regulatory_corpus=self.corpus,
            financial_panel={
                "deal_name": "Full Co",
                "periods": ["2023", "2024", "TTM"],
                "income_statement": {
                    "revenue": [320, 335, 350],
                    "ebitda_reported": [55, 60, 63],
                    "non_recurring_items": [],
                },
                "balance_sheet": {
                    "ar": [40, 42, 44], "inventory": [12, 12, 12],
                    "ap": [25, 25, 25],
                },
                "cash_flow": {"cash_receipts": [318, 333, 348]},
                "owner_compensation": {
                    "actual": [1.0, 1.0, 1.0],
                    "benchmark": [1.0, 1.0, 1.0],
                },
                "payer_mix": {
                    "self_pay_share": [0.05, 0.05, 0.06],
                    "out_of_network_share": [0.05, 0.05, 0.05],
                },
            },
            platform=self.platform,
            add_on_candidates=self.candidates,
            exit_target=self.exit_target,
            program_ids=["mssp_basic_a", "aco_reach_professional"],
        )
        # Wire ESG inputs too
        from rcm_mc.esg import (
            Facility, FacilityType, WorkforceProfile,
            GovernanceProfile,
        )
        dossier.facilities = [Facility(
            facility_id="F1", name="Hospital",
            facility_type=FacilityType.HOSPITAL,
            state="TX", annual_kwh=1_000_000,
        )]
        dossier.workforce = WorkforceProfile(
            total_headcount=1000, female_count=620,
            urm_count=200, female_in_management_count=45,
            management_count=100, board_members=8,
            board_female=3, board_urm=2,
            median_male_earnings=85000,
            median_female_earnings=80750,
            annual_voluntary_turnover_count=120,
        )
        dossier.governance_profile = GovernanceProfile(
            has_cpom_msot_structure=True,
            cpom_structure_disclosed=True,
            board_total=8, board_independent=5,
            annual_third_party_audit=True,
            named_compliance_officer=True,
            anonymous_reporting_channel=True,
        )
        dossier.issb_attested = True
        dossier.cybersecurity_attested = True

        # Wire the remaining packets — IRR-Attribution, MC v3
        # joint-tail, and SectorThemeDetector — so this test
        # asserts the full 13-section runner.
        from rcm_mc.irr_attribution import DealCashflows
        from rcm_mc.sector_themes import Document
        dossier.realized_cashflows = DealCashflows(
            deal_name="Full Co",
            entry_year=2021, exit_year=2026,
            ev_at_entry_mm=300.0, ev_at_exit_mm=600.0,
            ebitda_at_entry_mm=30.0, ebitda_at_exit_mm=50.0,
            revenue_at_entry_mm=167.0, revenue_at_exit_mm=227.0,
            net_debt_at_entry_mm=150.0, net_debt_at_exit_mm=120.0,
            addon_revenue_contribution_mm=15.0,
            cashflows=[(0.0, -150.0), (5.0, 480.0)],
        )
        dossier.run_joint_tail_shock = True
        dossier.joint_tail_n_samples = 200
        dossier.theme_documents = [
            Document(doc_id="T1", date="2025-03-01",
                     text="GLP-1 specialty pharmacy compounding "
                          "semaglutide for obesity demand."),
            Document(doc_id="T2", date="2025-04-01",
                     text="AI-enabled RCM denial management "
                          "platform with computer-assisted coding."),
        ]
        dossier.thesis_theme_ids = ["glp1_specialty_pharmacy"]
        # Also wire DealComparablesEngine so we hit all 13.
        # Mirror the corpus shape the comparables tests use.
        dossier.deal_corpus = [
            {"source_id": f"comp_{i}", "deal_name": f"C{i}",
             "sector": "hospital", "ev_mm": 200 + i*30,
             "ebitda_at_entry_mm": 25, "year": 2020 + (i % 5),
             "state": "TX", "buyer": "Sponsor", "realized_moic": 2.0,
             "ebitda_margin_at_entry": 0.13,
             "ebitda_margin_at_exit": 0.18,
             "payer_mix": {"medicare": 0.4, "medicaid": 0.2,
                           "commercial": 0.35, "self_pay": 0.05}}
            for i in range(20)
        ]
        dossier.target_deal_profile = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 250, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.4},
        }

        result = run_full_diligence(dossier)
        # Every section ran (now 13)
        for section in (
            "payer_negotiation", "cohort_ltv", "referral_leakage",
            "regulatory_exposure", "qoe", "buyandbuild",
            "exit_readiness", "vbc_track_choice", "esg_scorecard",
            "comparables", "irr_attribution",
            "joint_tail_shock", "sector_themes",
        ):
            self.assertIn(section, result.sections_run,
                          f"{section} did not run; "
                          f"missing: {result.missing_inputs}")
        self.assertEqual(len(result.sections_run), 13)
        # Every result attribute is non-None
        self.assertIsNotNone(result.payer_negotiation)
        self.assertIsNotNone(result.cohort_ltv)
        self.assertIsNotNone(result.referral_leakage)
        self.assertIsNotNone(result.regulatory_exposure)
        self.assertIsNotNone(result.qoe_result)
        self.assertIsNotNone(result.buyandbuild_optimal)
        self.assertIsNotNone(result.exit_readiness)
        self.assertIsNotNone(result.vbc_track_choice)
        self.assertIsNotNone(result.esg_scorecard)
        self.assertIsNotNone(result.comparables)
        self.assertIsNotNone(result.irr_attribution)
        self.assertIsNotNone(result.joint_tail_shock)
        self.assertIsNotNone(result.sector_themes)
        self.assertIsNotNone(result.theme_heatmap)
        self.assertIsNotNone(result.target_universe)
        self.assertIn("ESG Disclosure", result.esg_disclosure_md)


if __name__ == "__main__":
    unittest.main()
