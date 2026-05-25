"""Regression guard: the RED→NAVY pages converted with real public-data
anchors must keep rendering their LIVE panel.

Each of these pages got a source-labeled "· LIVE" panel from a real committed
dataset (CMS / CDC / HRSA / CIVHC / Census-via-CHR). A silent edit that drops
the panel would quietly revert the page to illustrative-only — this test fails
loudly if that happens. It exercises the real render path (no mocks).
"""
import unittest

# (render callable import path, kwargs, marker substring that only the real
#  LIVE panel produces, expected surface tier)
_CASES = [
    ("rcm_mc.ui.data_public.provider_network_page", "render_provider_network",
     {"sector": "Physician Group"}, "Real CMS provider supply", "/provider-network"),
    ("rcm_mc.ui.data_public.concentration_risk_page", "render_concentration_risk",
     None, "Real CMS consolidation backdrop", "/concentration-risk"),
    ("rcm_mc.ui.data_public.msa_concentration_page", "render_msa_concentration",
     {}, "Real CMS consolidation by state", "/msa-concentration"),
    ("rcm_mc.ui.data_public.payer_concentration_page", "render_payer_concentration",
     {}, "Real CMS Medicare Advantage payer landscape", "/payer-concentration"),
    ("rcm_mc.ui.data_public.competitive_intel_page", "render_competitive_intel",
     {}, "Real CMS ownership-change activity", "/competitive-intel"),
    ("rcm_mc.ui.data_public.gpo_supply_tracker_page", "render_gpo_supply_tracker",
     {}, "Real CMS Open Payments", "/gpo-supply"),
    ("rcm_mc.ui.data_public.medicaid_unwinding_page", "render_medicaid_unwinding",
     {}, "Real CMS dual-eligible population", "/medicaid-unwinding"),
    ("rcm_mc.ui.data_public.payer_contracts_page", "render_payer_contracts",
     {}, "Real commercial-vs-Medicare benchmark", "/payer-contracts"),
    ("rcm_mc.ui.data_public.health_equity_page", "render_health_equity",
     {}, "Real CDC PLACES social determinants", "/health-equity"),
    ("rcm_mc.ui.data_public.telehealth_econ_page", "render_telehealth_econ",
     {}, "Real CDC PLACES access barriers", "/telehealth-econ"),
    ("rcm_mc.ui.data_public.patient_experience_page", "render_patient_experience",
     {}, "Real CMS HCAHPS patient experience", "/patient-experience"),
    ("rcm_mc.ui.data_public.locum_tracker_page", "render_locum_tracker",
     {}, "Real HRSA shortage areas", "/locum-tracker"),
    ("rcm_mc.ui.data_public.workforce_retention_page", "render_workforce_retention",
     {}, "Real HRSA shortage areas", "/workforce-retention"),
    ("rcm_mc.ui.data_public.antitrust_screener_page", "render_antitrust_screener",
     {}, "Real CMS ownership-change activity", "/antitrust-screener"),
    ("rcm_mc.ui.data_public.cin_analyzer_page", "render_cin_analyzer",
     {}, "Real CMS MSSP ACO landscape", "/cin-analyzer"),
    ("rcm_mc.ui.data_public.nsa_tracker_page", "render_nsa_tracker",
     {}, "the OON / QPA reference", "/nsa-tracker"),
    ("rcm_mc.ui.data_public.workforce_planning_page", "render_workforce_planning",
     {}, "workforce supply", "/workforce-planning"),
    ("rcm_mc.ui.data_public.drug_pricing_340b_page", "render_drug_pricing_340b",
     {}, "Real CMS Part D drug spend", "/drug-pricing-340b"),
    ("rcm_mc.ui.data_public.tracker_340b_page", "render_tracker_340b",
     {}, "Real CMS Part D drug spend", "/tracker-340b"),
    ("rcm_mc.ui.data_public.trial_site_econ_page", "render_trial_site_econ",
     {}, "Real ClinicalTrials.gov landscape", "/trial-site-econ"),
]


class LiveDataPanelRegressionTests(unittest.TestCase):
    def test_converted_pages_render_live_panel(self):
        import importlib
        missing = []
        for mod_path, fn_name, kwargs, marker, route in _CASES:
            mod = importlib.import_module(mod_path)
            fn = getattr(mod, fn_name)
            html = fn() if kwargs is None else fn(kwargs)
            if marker not in html:
                missing.append(f"{route}: missing LIVE marker {marker!r}")
            # the LIVE panel carries the explicit honesty caveat
            if "illustrative" not in html.lower() and route != "/workforce-planning":
                missing.append(f"{route}: missing illustrative caveat")
        self.assertEqual(missing, [], "LIVE panels dropped:\n" + "\n".join(missing))

    def test_converted_pages_are_navy_not_red(self):
        from rcm_mc.diligence.surface_status import classify_surface
        red = []
        for *_unused, route in _CASES:
            tier = classify_surface(route)["tier"]
            if tier == "red":
                red.append(route)
        self.assertEqual(red, [], f"converted pages regressed to RED: {red}")


if __name__ == "__main__":
    unittest.main()
