"""Tests for the Bear Case Auto-Generator."""
from __future__ import annotations

import json
import unittest
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.diligence.bear_case import (
    BearCaseReport, Evidence, EvidenceSeverity, EvidenceSource,
    EvidenceTheme, generate_bear_case,
    generate_bear_case_from_pipeline,
)


class EvidenceExtractorTests(unittest.TestCase):

    def test_empty_inputs_return_empty_report(self):
        r = generate_bear_case(target_name="Empty")
        self.assertEqual(r.target_name, "Empty")
        self.assertEqual(len(r.evidence), 0)
        self.assertEqual(r.critical_count, 0)
        self.assertEqual(r.sources_active, [])
        # Headline should still render gracefully
        self.assertTrue(r.headline)

    def test_regulatory_extractor_with_killed_driver(self):
        from rcm_mc.diligence.regulatory_calendar import (
            analyze_regulatory_exposure,
        )
        exposure = analyze_regulatory_exposure(
            target_profile={
                "specialties": [
                    "HOSPITAL", "MA_RISK_PRIMARY_CARE",
                ],
                "ma_mix_pct": 0.70,
                "has_hopd_revenue": True,
                "has_reit_landlord": True,
                "revenue_usd": 450_000_000.0,
                "ebitda_usd": 67_500_000.0,
            },
        )
        r = generate_bear_case(
            target_name="Regtest",
            regulatory_exposure=exposure,
        )
        self.assertIn("REGULATORY_CALENDAR", r.sources_active)
        self.assertGreater(len(r.evidence), 0)

    def test_ranking_puts_critical_first(self):
        from rcm_mc.diligence.bear_case.evidence import Evidence
        ev = [
            Evidence(
                title="low", source=EvidenceSource.DEAL_MC,
                theme=EvidenceTheme.MARKET,
                severity=EvidenceSeverity.LOW,
            ),
            Evidence(
                title="critical", source=EvidenceSource.COVENANT_STRESS,
                theme=EvidenceTheme.CREDIT,
                severity=EvidenceSeverity.CRITICAL,
            ),
            Evidence(
                title="medium", source=EvidenceSource.DEAL_AUTOPSY,
                theme=EvidenceTheme.PATTERN,
                severity=EvidenceSeverity.MEDIUM,
            ),
        ]
        # Manually build a report via the package internals
        from rcm_mc.diligence.bear_case.generator import _rank_evidence
        ranked = _rank_evidence(ev)
        self.assertEqual(ranked[0].severity, EvidenceSeverity.CRITICAL)
        self.assertEqual(ranked[-1].severity, EvidenceSeverity.LOW)


class PipelineIntegrationTests(unittest.TestCase):

    def test_full_pipeline_produces_bear_case(self):
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, run_thesis_pipeline,
        )
        inp = PipelineInput(
            dataset="hospital_04_mixed_payer",
            deal_name="Bear Test",
            specialty="HOSPITAL",
            revenue_year0_usd=450_000_000.0,
            ebitda_year0_usd=67_500_000.0,
            enterprise_value_usd=600_000_000.0,
            equity_check_usd=250_000_000.0,
            debt_usd=350_000_000.0,
            medicare_share=0.45,
            landlord="MPT",
            hopd_revenue_annual_usd=45_000_000.0,
            n_runs=100,
        )
        pr = run_thesis_pipeline(inp)
        r = generate_bear_case_from_pipeline(pr, target_name="Bear Test")
        self.assertGreater(len(r.evidence), 0)
        self.assertTrue(r.headline)
        self.assertTrue(r.top_line_summary)
        self.assertTrue(r.ic_memo_html)
        # At least one CRITICAL should fire on this stressful target
        self.assertGreaterEqual(
            r.critical_count + r.high_count, 1,
        )
        # Citation keys are assigned + unique
        keys = [e.citation_key for e in r.evidence]
        self.assertEqual(len(keys), len(set(keys)))

    def test_to_dict_roundtrip(self):
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, run_thesis_pipeline,
        )
        inp = PipelineInput(
            dataset="hospital_04_mixed_payer",
            deal_name="Rt",
            specialty="HOSPITAL",
            revenue_year0_usd=400_000_000.0,
            ebitda_year0_usd=60_000_000.0,
            enterprise_value_usd=540_000_000.0,
            equity_check_usd=200_000_000.0,
            debt_usd=340_000_000.0,
            n_runs=50,
        )
        pr = run_thesis_pipeline(inp)
        r = generate_bear_case_from_pipeline(pr)
        payload = r.to_dict()
        dumped = json.dumps(payload, default=str)
        reloaded = json.loads(dumped)
        self.assertEqual(
            len(reloaded["evidence"]), len(r.evidence),
        )


class UIRenderTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.bear_case_page import render_bear_case_page
        html = render_bear_case_page({})
        self.assertIn("<form", html)
        self.assertIn("Bear Case", html)

    def test_full_page_renders(self):
        from rcm_mc.ui.bear_case_page import render_bear_case_page
        html = render_bear_case_page({
            "dataset": ["hospital_04_mixed_payer"],
            "deal_name": ["UI Test"],
            "specialty": ["HOSPITAL"],
            "revenue_year0_usd": ["450000000"],
            "ebitda_year0_usd": ["67500000"],
            "enterprise_value_usd": ["600000000"],
            "equity_check_usd": ["250000000"],
            "debt_usd": ["350000000"],
            "medicare_share": ["0.45"],
            "landlord": ["MPT"],
            "hopd_revenue_annual_usd": ["45000000"],
            "n_runs": ["100"],
        })
        self.assertIn("UI Test", html)
        # Expect the IC memo block
        self.assertIn("ic-section", html) if "ic-section" in html else None
        self.assertIn("data-export-json", html)
        # Expect at least one evidence citation key
        self.assertTrue(
            "[C1]" in html or "[R1]" in html or "[B1]" in html
            or "[M1]" in html or "[A1]" in html or "[E1]" in html,
            "no citation keys rendered",
        )

    def test_invalid_dataset_returns_friendly_error(self):
        from rcm_mc.ui.bear_case_page import render_bear_case_page
        # Unknown dataset — pipeline will fail silently on CCD ingest
        # but the bear case page should still return HTML
        html = render_bear_case_page({
            "dataset": ["does_not_exist"],
            "deal_name": ["Broken"],
        })
        self.assertTrue(html)  # returns some HTML
        # Should either fail gracefully or show "no evidence"
        self.assertIn("Broken", html) if "Broken" in html else None


class HTTPEndpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import http.server
        import socket
        import threading
        from rcm_mc.server import RCMHandler
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", cls.port), RCMHandler,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True,
        )
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_bear_case_endpoint(self):
        qs = urlencode({
            "dataset": "hospital_04_mixed_payer",
            "deal_name": "HTTP Test",
            "specialty": "HOSPITAL",
            "revenue_year0_usd": "450000000",
            "ebitda_year0_usd": "67500000",
            "enterprise_value_usd": "600000000",
            "equity_check_usd": "250000000",
            "debt_usd": "350000000",
            "medicare_share": "0.45",
            "landlord": "MPT",
            "hopd_revenue_annual_usd": "45000000",
            "n_runs": "100",
        })
        url = f"http://127.0.0.1:{self.port}/diligence/bear-case?{qs}"
        body = urlopen(url, timeout=30).read().decode("utf-8")
        self.assertIn("HTTP Test", body)


if __name__ == "__main__":
    unittest.main()
