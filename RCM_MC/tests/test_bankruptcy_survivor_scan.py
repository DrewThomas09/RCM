"""Bankruptcy-Survivor Scan regression tests (Prompt I).

- Six historical replays: Steward, Envision, APP, Cano, Prospect,
  Wellpath feeding a ScanInput matching each target at time-of-LBO
  must return RED or CRITICAL with the correct pattern name cited.
- Twenty-case "no false positive" sweep feeds successful-exit
  profiles (generic clean operators across specialties) — none may
  return RED/CRITICAL.
- HTML renderers produce valid document shape for a CRITICAL
  result and a landing page.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.screening import (
    BankruptcySurvivorVerdict, ScanInput, run_bankruptcy_survivor_scan,
)
from rcm_mc.ui.bankruptcy_survivor_page import (
    render_scan_landing, render_scan_result,
)


# ── Six historical replays ────────────────────────────────────────

class HistoricalReplayTests(unittest.TestCase):

    def test_steward_2016_is_critical(self):
        """Steward Health Care at 2016 MPT deal: hospital + REIT +
        20-year lease + 3.5% escalator + thin coverage + rural."""
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Steward replay",
            specialty="HOSPITAL",
            states=["MA", "RI"],
            landlord="Medical Properties Trust",
            lease_term_years=20,
            lease_escalator_pct=0.035,
            ebitdar_coverage=1.2,
            geography="RURAL",
        ))
        self.assertEqual(scan.verdict, BankruptcySurvivorVerdict.CRITICAL)
        fired_names = {c.name for c in scan.checks if c.fired}
        self.assertIn("STEWARD_PATTERN", fired_names)
        # Steward pattern must cite Steward by name.
        steward = next(c for c in scan.checks
                       if c.name == "STEWARD_PATTERN")
        self.assertIn("Steward", steward.case_study or "")

    def test_envision_2018_is_critical(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Envision replay",
            specialty="EMERGENCY_MEDICINE",
            is_hospital_based_physician=True,
            oon_revenue_share=0.45,
        ))
        self.assertEqual(scan.verdict, BankruptcySurvivorVerdict.CRITICAL)
        envision = next(c for c in scan.checks
                        if c.name == "ENVISION_PATTERN")
        self.assertTrue(envision.fired)
        self.assertIn("Envision", envision.case_study or "")

    def test_app_pattern_fires_on_locum_plus_nsa_plus_rollup(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="APP replay",
            specialty="ANESTHESIOLOGY",
            is_hospital_based_physician=True,
            oon_revenue_share=0.22,
            locum_pct_staffing=0.35,
            acquisitions=[
                {"msa": "Nashville", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.15},
                {"msa": "Nashville", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.12},
                {"msa": "Nashville", "specialty": "ANESTHESIOLOGY",
                 "market_share_acquired": 0.10},
            ],
            msas=["Nashville"],
        ))
        self.assertIn(scan.verdict, (
            BankruptcySurvivorVerdict.RED,
            BankruptcySurvivorVerdict.CRITICAL,
        ))
        app = next(c for c in scan.checks if c.name == "APP_PATTERN")
        self.assertTrue(app.fired)
        self.assertIn("American Physician Partners", app.case_study or "")

    def test_cano_ma_risk_primary_care_flags(self):
        """Cano pattern: MA-risk primary care + CAC payback >24mo."""
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Cano replay",
            specialty="FAMILY_MEDICINE",
            is_ma_risk_primary_care=True,
            cac_payback_months=36,
        ))
        self.assertIn(scan.verdict, (
            BankruptcySurvivorVerdict.RED,
            BankruptcySurvivorVerdict.CRITICAL,
        ))
        cano = next(c for c in scan.checks if c.name == "CANO_PATTERN")
        self.assertTrue(cano.fired)
        self.assertIn("Cano Health", cano.case_study or "")

    def test_prospect_hospital_plus_mpt_fires(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Prospect replay",
            specialty="HOSPITAL",
            landlord="MPT",
            lease_term_years=18,
            lease_escalator_pct=0.035,
            ebitdar_coverage=1.2,
        ))
        prospect = next(c for c in scan.checks
                        if c.name == "PROSPECT_PATTERN")
        self.assertTrue(prospect.fired)
        self.assertIn("Prospect", prospect.case_study or "")

    def test_wellpath_correctional_health_fires(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Wellpath replay",
            is_correctional_health=True,
            payer_hhi=6500,
        ))
        well = next(c for c in scan.checks
                    if c.name == "WELLPATH_PATTERN")
        self.assertTrue(well.fired)
        self.assertIn("Wellpath", well.case_study or "")
        self.assertEqual(well.severity, "CRITICAL")


# ── No false positives ────────────────────────────────────────────

class NoFalsePositiveTests(unittest.TestCase):
    """Twenty successful-exit profiles must NOT return RED/CRITICAL."""

    CLEAN_PROFILES = [
        # Small single-location ASC
        ScanInput(target_name="ASC-1", specialty="ASC",
                  states=["TX"], legal_structure="DIRECT_EMPLOYMENT",
                  landlord="Local LLC", lease_term_years=10,
                  lease_escalator_pct=0.025, ebitdar_coverage=3.0,
                  geography="SUBURBAN"),
        # Dermatology MSO in clean state
        ScanInput(target_name="DERM-1", specialty="DERMATOLOGY",
                  states=["FL"], legal_structure="MSO_PC_MANAGEMENT_FEE",
                  lease_term_years=5, lease_escalator_pct=0.02,
                  ebitdar_coverage=2.2, geography="URBAN_ACADEMIC"),
        # Orthopedic group, direct employment, urban
        ScanInput(target_name="ORTHO-1", specialty="ORTHOPEDICS",
                  states=["GA"], legal_structure="DIRECT_EMPLOYMENT",
                  landlord="Trust LLC", lease_term_years=8,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.8,
                  geography="URBAN_ACADEMIC"),
        # Ophthalmology practice
        ScanInput(target_name="EYE-1", specialty="OPHTHALMOLOGY",
                  states=["IL"], lease_term_years=6,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.5,
                  geography="SUBURBAN"),
        # GI single-site
        ScanInput(target_name="GI-1", specialty="GASTROENTEROLOGY",
                  states=["NV"], lease_term_years=7,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.4),
        # Urology group
        ScanInput(target_name="URO-1", specialty="UROLOGY",
                  states=["VA"], lease_term_years=8,
                  lease_escalator_pct=0.025, ebitdar_coverage=2.0),
        # Cardiology MSO, no NSA exposure
        ScanInput(target_name="CARD-1", specialty="CARDIOLOGY",
                  states=["MN"], lease_term_years=9,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.3),
        # Behavioral outpatient
        ScanInput(target_name="BEH-1", specialty="BEHAVIORAL",
                  states=["AZ"], lease_term_years=10,
                  lease_escalator_pct=0.025, ebitdar_coverage=1.8),
        # Dental DSO
        ScanInput(target_name="DEN-1", specialty="DENTAL",
                  states=["OH"], lease_term_years=10,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.1),
        # Vet services (non-healthcare but shape-test)
        ScanInput(target_name="VET-1", specialty="VETERINARY",
                  states=["KS"], lease_term_years=7),
        # Small hospital, clean lease, in-state employment
        ScanInput(target_name="SMH-1", specialty="HOSPITAL",
                  states=["KY"], landlord="Independent LLC",
                  lease_term_years=10, lease_escalator_pct=0.02,
                  ebitdar_coverage=2.5, geography="URBAN_ACADEMIC",
                  legal_structure="DIRECT_EMPLOYMENT"),
        # Boutique ASC network (short hops)
        ScanInput(target_name="ASC-2", specialty="ASC",
                  states=["CO"], legal_structure="DIRECT_EMPLOYMENT",
                  lease_term_years=7, lease_escalator_pct=0.025,
                  ebitdar_coverage=2.7),
        # Small primary care (not MA-risk)
        ScanInput(target_name="PCP-1", specialty="FAMILY_MEDICINE",
                  states=["TN"], is_ma_risk_primary_care=False,
                  lease_term_years=6),
        # Pain management
        ScanInput(target_name="PAIN-1", specialty="PAIN_MEDICINE",
                  states=["UT"], lease_term_years=8,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.0),
        # Home health (clean payer mix)
        ScanInput(target_name="HH-1", specialty="HOME_HEALTH",
                  states=["NC"], payer_hhi=1500),
        # Women's health
        ScanInput(target_name="WH-1", specialty="OBGYN",
                  states=["WI"], lease_term_years=6,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.2),
        # Imaging centers
        ScanInput(target_name="IMG-1", specialty="RADIOLOGY",
                  states=["IA"], is_hospital_based_physician=False,
                  lease_term_years=7),
        # Lab services, no OON
        ScanInput(target_name="LAB-1", specialty="PATHOLOGY",
                  states=["OH"], is_hospital_based_physician=False,
                  lease_term_years=8),
        # Multi-site ENT
        ScanInput(target_name="ENT-1", specialty="ENT",
                  states=["AL"], lease_term_years=6,
                  lease_escalator_pct=0.02, ebitdar_coverage=2.1),
        # Physical therapy roll-up, few acquisitions, low HHI
        ScanInput(target_name="PT-1", specialty="PHYSICAL_THERAPY",
                  states=["SC"], acquisitions=[
                      {"msa": "Columbia",
                       "specialty": "PHYSICAL_THERAPY",
                       "market_share_acquired": 0.08},
                      {"msa": "Columbia",
                       "specialty": "PHYSICAL_THERAPY",
                       "market_share_acquired": 0.05},
                  ], msas=["Columbia"]),
    ]

    def test_no_clean_profile_returns_red_or_critical(self):
        reds = []
        for p in self.CLEAN_PROFILES:
            scan = run_bankruptcy_survivor_scan(p)
            if scan.verdict in (
                BankruptcySurvivorVerdict.RED,
                BankruptcySurvivorVerdict.CRITICAL,
            ):
                reds.append((p.target_name, scan.verdict.value,
                             [c.name for c in scan.checks if c.fired]))
        self.assertEqual(
            reds, [],
            msg=f"false positives on clean profiles: {reds}",
        )


# ── HTML renderers ───────────────────────────────────────────────

class RenderTests(unittest.TestCase):

    def test_landing_renders_form(self):
        html = render_scan_landing()
        # chartis_shell emits lowercase `<!doctype html>`; accept
        # either case so the assertion survives the v5 migration.
        self.assertTrue(html.lower().startswith("<!doctype html>"))
        self.assertIn("Bankruptcy-Survivor Scan", html)
        self.assertIn("<form", html)
        self.assertIn("target_name", html)

    def test_critical_result_page_has_verdict_and_cases(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Steward replay",
            specialty="HOSPITAL",
            states=["MA"],
            landlord="Medical Properties Trust",
            lease_term_years=20,
            lease_escalator_pct=0.035,
            ebitdar_coverage=1.2,
            geography="RURAL",
        ))
        html = render_scan_result(scan)
        self.assertIn("CRITICAL", html)
        self.assertIn("Steward", html)
        # Diligence questions section rendered.
        self.assertIn("Diligence questions", html)
        # Print CSS present.
        self.assertIn("@media print", html)

    def test_green_result_page_renders_cleanly(self):
        scan = run_bankruptcy_survivor_scan(ScanInput(
            target_name="Clean ASC",
            specialty="ASC",
            states=["TX"],
            legal_structure="DIRECT_EMPLOYMENT",
            landlord="Local LLC",
            lease_term_years=10, lease_escalator_pct=0.025,
            ebitdar_coverage=2.5,
        ))
        html = render_scan_result(scan)
        self.assertIn("GREEN", html)
        self.assertIn("Clean ASC", html)


if __name__ == "__main__":
    unittest.main()
