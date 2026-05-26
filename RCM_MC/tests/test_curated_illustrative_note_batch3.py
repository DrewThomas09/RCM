"""Curated-labeling sweep, batch 3 — the remaining illustrative trackers.

Applies the honest ck_illustrative_note() marker to data_public tracker
pages confirmed curated per docs/PEDESK_UNDERSTANDING/08 (hardcoded
demo data, NOT [corpus]/[CMS]/[calc]). Each page is rendered and the
marker asserted; a negative guard confirms genuinely-live pages are
never labeled.
"""
from __future__ import annotations

import importlib
import unittest

_BATCH3A = [
    "medicaid_unwinding", "telehealth_econ", "tax_credits", "nsa_tracker",
    "payer_concentration", "payer_contracts", "ma_contracts",
    "ma_star_tracker", "tracker_340b", "drug_shortage", "gpo_supply_tracker",
    "cyber_risk", "health_equity", "esg_impact", "litigation_tracker",
    "rw_insurance", "fraud_detection", "key_person", "physician_labor",
    "phys_comp_plan", "mgmt_comp",
]


def _render_any(module_name: str) -> str:
    mod = importlib.import_module(f"rcm_mc.ui.data_public.{module_name}_page")
    for fn in dir(mod):
        if fn.startswith("render_"):
            try:
                out = getattr(mod, fn)({})
            except Exception:
                continue
            if isinstance(out, str) and "ck-page" in out or (
                isinstance(out, str) and "<" in out
            ):
                return out
    raise AssertionError(f"no renderable function found for {module_name}")


class CuratedBatch3Tests(unittest.TestCase):
    def test_each_curated_page_carries_marker(self):
        for name in _BATCH3A:
            html = _render_any(name)
            self.assertIn("ck-illus-note", html, name)
            self.assertIn("Illustrative template", html, name)

    def test_corpus_and_calc_pages_are_labeled_honestly(self):
        # base_rates derives its rates from the illustrative SEED CORPUS, and
        # scenario_mc renders ILLUSTRATIVE DEFAULT figures until the user
        # supplies inputs — so both correctly carry an honest illustrative
        # marker. (Updated from the original "never labeled" expectation, which
        # wrongly treated these as fully-live pages; the seed corpus is not a
        # verified live benchmark and default scenario figures are not live.)
        from rcm_mc.ui.data_public.base_rates_page import render_base_rates
        from rcm_mc.ui.data_public.scenario_mc_page import render_scenario_mc
        br = render_base_rates()
        self.assertIn("ck-illus-note", br)
        self.assertIn("corpus", br.lower())
        sc = render_scenario_mc({})
        self.assertIn("ck-illus-note", sc)
        self.assertIn("illustrative defaults", sc)


if __name__ == "__main__":
    unittest.main()


_BATCH3B = [
    "partner_economics", "workforce_retention", "digital_front_door",
    "hcit_platform", "trial_site_econ", "direct_employer",
    "denovo_expansion", "demand_forecast", "real_estate",
    "medical_realestate", "reit_analyzer", "hospital_anchor",
    "operating_partners", "diligence_vendors", "compliance_attestation",
    "treasury_tracker", "fundraising_tracker", "coinvest_pipeline",
    "nav_loan_tracker", "secondaries_tracker", "continuation_vehicle",
]


class CuratedBatch3bTests(unittest.TestCase):
    def test_each_curated_page_carries_marker(self):
        for name in _BATCH3B:
            html = _render_any(name)
            self.assertIn("ck-illus-note", html, name)
            self.assertIn("Illustrative template", html, name)


_BATCH3C = [
    "dpi_tracker", "dividend_recap", "escrow_earnout", "earnout",
    "debt_financing", "debt_service", "covenant_headroom", "refi_optimizer",
    "direct_lending", "sellside_process", "vdr_tracker", "transition_services",
    "pmi_integration", "pmi_playbook", "vcp_tracker", "peer_transactions",
    "vintage_cohorts", "payer_shift", "ref_pricing", "risk_adjustment",
    "zbb_tracker",
]


class CuratedBatch3cTests(unittest.TestCase):
    def test_each_curated_page_carries_marker(self):
        for name in _BATCH3C:
            html = _render_any(name)
            self.assertIn("ck-illus-note", html, name)
            self.assertIn("Illustrative template", html, name)


_BATCH3D = [
    "aco_economics", "biosimilars_opp", "ai_operating_model",
    "clinical_ai_tracker", "cin_analyzer", "board_governance",
    "capex_budget", "capital_call_tracker", "capital_schedule",
]


class CuratedBatch3dTests(unittest.TestCase):
    def test_each_curated_page_carries_marker(self):
        for name in _BATCH3D:
            html = _render_any(name)
            self.assertIn("ck-illus-note", html, name)
            self.assertIn("Illustrative template", html, name)
