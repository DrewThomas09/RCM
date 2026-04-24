"""Tests for the Covenant & Capital Structure Stress Lab."""
from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.diligence.covenant_lab import (
    CapitalStack, CovenantDefinition, CovenantKind,
    CovenantStressResult, DEFAULT_COVENANTS, DebtTranche,
    TrancheKind, build_debt_schedule, default_lbo_stack,
    evaluate_covenant, run_covenant_stress,
)
from rcm_mc.diligence.covenant_lab.simulator import (
    _ltm_sum, _lognormal_params_from_bands,
)


class CapitalStackTests(unittest.TestCase):

    def test_default_lbo_stack(self):
        stack = default_lbo_stack(
            total_debt_usd=350_000_000.0,
            revolver_usd=50_000_000.0,
            revolver_draw_pct=0.30,
        )
        # Revolver + TLB + Unitranche + Mezz
        self.assertEqual(len(stack.tranches), 4)
        self.assertAlmostEqual(
            stack.total_committed_usd,
            400_000_000.0, places=0,
        )
        self.assertAlmostEqual(
            stack.total_funded_usd,
            350_000_000.0 + 15_000_000.0, places=0,
        )

    def test_debt_schedule_amortizes(self):
        stack = default_lbo_stack(total_debt_usd=300_000_000.0)
        sched = build_debt_schedule(
            stack, [0.055] * 24, quarters=24,
        )
        self.assertEqual(len(sched), 24)
        # Debt balance should monotonically decrease
        for a, b in zip(sched, sched[1:]):
            self.assertLessEqual(b.total_debt_balance, a.total_debt_balance + 1.0)
        # Total amortization plus ending balance ≈ original principal
        total_amort = sum(s.total_scheduled_amort for s in sched)
        self.assertAlmostEqual(
            total_amort + sched[-1].total_debt_balance,
            stack.total_funded_usd, delta=1.0,
        )

    def test_tranche_to_dict_roundtrip(self):
        t = DebtTranche(
            name="TLB", kind=TrancheKind.TLB,
            principal_usd=200_000_000.0,
            amortization_schedule=(0.01, 0.01, 0.98),
        )
        payload = t.to_dict()
        self.assertEqual(payload["kind"], "TLB")
        self.assertEqual(
            payload["amortization_schedule"],
            [0.01, 0.01, 0.98],
        )


class CovenantEvaluatorTests(unittest.TestCase):

    def test_leverage_ceiling_breach(self):
        cov = CovenantDefinition(
            name="Net Leverage",
            kind=CovenantKind.NET_LEVERAGE,
            opening_threshold=6.0,
        )
        r = evaluate_covenant(
            cov, quarter_idx=0,
            ltm_ebitda=50_000_000.0,
            total_debt=400_000_000.0,
            senior_debt=350_000_000.0,
            ltm_interest=30_000_000.0,
            ltm_debt_service=40_000_000.0,
        )
        # 400/50 = 8.0 > 6.0 → breached
        self.assertTrue(r.breached)
        self.assertAlmostEqual(r.metric_value, 8.0, places=2)

    def test_coverage_floor_breach(self):
        cov = CovenantDefinition(
            name="DSCR",
            kind=CovenantKind.DSCR,
            opening_threshold=1.5,
        )
        r = evaluate_covenant(
            cov, quarter_idx=0,
            ltm_ebitda=40_000_000.0,
            total_debt=300_000_000.0,
            senior_debt=250_000_000.0,
            ltm_interest=30_000_000.0,
            ltm_debt_service=40_000_000.0,
        )
        # 40/40 = 1.0 < 1.5 → breached
        self.assertTrue(r.breached)

    def test_step_down_schedule_activates(self):
        cov = CovenantDefinition(
            name="Leverage Step",
            kind=CovenantKind.NET_LEVERAGE,
            opening_threshold=7.0,
            step_down_schedule=((2, 6.0), (3, 5.0)),
        )
        self.assertEqual(cov.threshold_at_year(1), 7.0)
        self.assertEqual(cov.threshold_at_year(2), 6.0)
        self.assertEqual(cov.threshold_at_year(3), 5.0)
        self.assertEqual(cov.threshold_at_year(10), 5.0)

    def test_cushion_breach_fires_early(self):
        cov = CovenantDefinition(
            name="Leverage Cushion",
            kind=CovenantKind.NET_LEVERAGE,
            opening_threshold=7.0,
            cushion_pct=0.15,
        )
        r = evaluate_covenant(
            cov, quarter_idx=0,
            ltm_ebitda=60_000_000.0,
            total_debt=380_000_000.0,
            senior_debt=320_000_000.0,
            ltm_interest=25_000_000.0,
            ltm_debt_service=35_000_000.0,
        )
        # 380/60 = 6.33 < 7.0 → actual PASS
        # But cushion threshold = 7.0*(1-0.15) = 5.95 → cushion BREACH
        self.assertFalse(r.breached)
        self.assertTrue(r.cushion_breached)


class StressSimulatorTests(unittest.TestCase):

    def _bands(self, years: int = 5) -> List[Dict[str, float]]:
        return [
            {
                "p25": 60_000_000 * (1.05 ** y),
                "p50": 70_000_000 * (1.06 ** y),
                "p75": 80_000_000 * (1.07 ** y),
            }
            for y in range(years)
        ]

    def test_stress_runs_with_bands(self):
        r = run_covenant_stress(
            ebitda_bands=self._bands(),
            total_debt_usd=300_000_000.0,
            rate_path_annual=[0.055] * 20,
            quarters=20,
        )
        self.assertEqual(r.n_paths, 500)
        self.assertEqual(r.quarters, 20)
        self.assertTrue(r.per_covenant_curves)
        self.assertTrue(r.first_breach)
        self.assertTrue(r.equity_cures)
        self.assertTrue(r.headline)

    def test_regulatory_overlay_worsens_metrics(self):
        base = run_covenant_stress(
            ebitda_bands=self._bands(),
            total_debt_usd=300_000_000.0,
            quarters=20,
        )
        stressed = run_covenant_stress(
            ebitda_bands=self._bands(),
            total_debt_usd=300_000_000.0,
            quarters=20,
            regulatory_overlay_usd_by_year=[
                0, 0, -15_000_000, -15_000_000, -15_000_000,
            ],
        )
        # Max breach probability should go up (or at least not down)
        self.assertGreaterEqual(
            stressed.max_breach_probability,
            base.max_breach_probability - 0.05,
        )

    def test_to_dict_roundtrip(self):
        r = run_covenant_stress(
            ebitda_bands=self._bands(),
            total_debt_usd=200_000_000.0,
            quarters=12,
        )
        payload = r.to_dict()
        dumped = json.dumps(payload, default=str)
        reloaded = json.loads(dumped)
        self.assertEqual(
            reloaded["n_paths"], r.n_paths,
        )
        self.assertEqual(
            len(reloaded["per_covenant_curves"]),
            len(r.per_covenant_curves),
        )

    def test_paths_override_bands(self):
        paths = [[70_000_000, 72_000_000, 75_000_000]] * 100
        r = run_covenant_stress(
            ebitda_paths=paths,
            total_debt_usd=200_000_000.0,
            quarters=12,
        )
        self.assertEqual(r.n_paths, 100)

    def test_ltm_sum_annualizes_partial_window(self):
        # 2 quarters of 10 each: LTM should = 40 (annualized)
        self.assertAlmostEqual(
            _ltm_sum([10.0, 10.0], 1), 40.0, places=2,
        )

    def test_lognormal_fit_recovers_median(self):
        mu, sigma = _lognormal_params_from_bands(100.0, 80.0, 125.0)
        import math
        self.assertAlmostEqual(math.exp(mu), 100.0, places=2)
        self.assertGreater(sigma, 0.0)


class PipelineIntegrationTests(unittest.TestCase):

    def test_pipeline_runs_covenant_step(self):
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, pipeline_observations, run_thesis_pipeline,
        )
        inp = PipelineInput(
            dataset="hospital_04_mixed_payer",
            deal_name="Covenant Test",
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
        r = run_thesis_pipeline(inp)
        steps = {s["step"]: s for s in r.step_log}
        self.assertIn("covenant_stress", steps)
        self.assertEqual(steps["covenant_stress"]["status"], "ok")
        self.assertIsNotNone(r.covenant_stress)
        self.assertIsNotNone(r.covenant_max_breach_probability)
        obs = pipeline_observations(r)
        self.assertTrue(obs.get("covenant_stress_run"))


class UIRenderTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.covenant_lab_page import (
            render_covenant_lab_page,
        )
        html = render_covenant_lab_page({})
        self.assertIn("<form", html)
        self.assertIn("Covenant", html)

    def test_full_page_renders(self):
        from rcm_mc.ui.covenant_lab_page import (
            render_covenant_lab_page,
        )
        html = render_covenant_lab_page({
            "deal_name": ["Meadowbrook"],
            "ebitda_y0": ["67500000"],
            "ebitda_growth": ["0.06"],
            "total_debt_usd": ["350000000"],
            "revolver_usd": ["50000000"],
            "quarters": ["20"],
            "reg_overlay": ["0,0,-9.9,-9.95,0,0"],
        })
        self.assertIn("Meadowbrook", html)
        self.assertIn("Breach", html)
        self.assertIn("Capital stack", html)
        self.assertIn("data-sortable", html)
        self.assertIn("data-export-json", html)


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

    def test_covenant_lab_route(self):
        qs = urlencode({
            "deal_name": "HTTP Test",
            "ebitda_y0": "67500000",
            "total_debt_usd": "350000000",
            "quarters": "20",
        })
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/diligence/covenant-stress?{qs}"
        )
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("HTTP Test", body)
        self.assertIn("Breach", body)


if __name__ == "__main__":
    unittest.main()
