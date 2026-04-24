"""Tests for the Payer Mix Stress Lab."""
from __future__ import annotations

import json
import unittest
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.diligence.payer_stress import (
    PAYER_PRIORS, PayerCategory, PayerMixEntry,
    PayerStressVerdict, classify_payer,
    default_hospital_mix, get_payer, list_payers,
    run_payer_stress,
)


class PayerLibraryTests(unittest.TestCase):

    def test_library_has_canonical_payers(self):
        ids = {p.payer_id for p in PAYER_PRIORS}
        for canonical in (
            "UHC", "ANTHEM", "AETNA", "CIGNA", "HUMANA",
            "MEDICARE_FFS", "MA_AGGREGATE", "MEDICAID_FFS",
            "KAISER", "CENTENE", "MOLINA", "TRICARE",
            "WORKERS_COMP", "SELF_PAY",
        ):
            self.assertIn(canonical, ids, f"missing {canonical}")

    def test_priors_have_plausible_bands(self):
        for p in PAYER_PRIORS:
            self.assertLessEqual(p.rate_move_p25, p.rate_move_median + 0.001)
            self.assertLessEqual(
                p.rate_move_median - 0.001, p.rate_move_p75,
            )
            self.assertGreaterEqual(p.negotiating_leverage, 0.0)
            self.assertLessEqual(p.negotiating_leverage, 1.0)
            self.assertGreaterEqual(p.renewal_prob_12mo, 0.0)
            self.assertLessEqual(p.renewal_prob_12mo, 1.0)

    def test_classify_common_aliases(self):
        cases = [
            ("UnitedHealthcare", "UHC"),
            ("United", "UHC"),
            ("Anthem", "ANTHEM"),
            ("Aetna", "AETNA"),
            ("Cigna", "CIGNA"),
            ("Kaiser Permanente", "KAISER"),
            ("Medicare FFS", "MEDICARE_FFS"),
            ("Medicare Advantage", "MA_AGGREGATE"),
            ("Medicaid FFS", "MEDICAID_FFS"),
            ("TRICARE", "TRICARE"),
        ]
        for name, expected in cases:
            p = classify_payer(name)
            self.assertIsNotNone(p, f"could not classify: {name}")
            self.assertEqual(
                p.payer_id, expected,
                f"{name!r}: got {p.payer_id}, expected {expected}",
            )

    def test_classify_unknown_returns_none(self):
        # Clearly off-topic name — no keyword match
        self.assertIsNone(classify_payer("XYZ Regional Plan"))

    def test_get_payer_case_insensitive(self):
        self.assertEqual(get_payer("uhc").payer_id, "UHC")
        self.assertEqual(get_payer("UHC").payer_id, "UHC")


class StressSimulatorTests(unittest.TestCase):

    def test_default_mix_runs(self):
        r = run_payer_stress(
            mix=default_hospital_mix(),
            total_npr_usd=450_000_000,
            total_ebitda_usd=67_500_000,
            horizon_years=5,
            n_paths=200,
        )
        self.assertGreater(len(r.per_payer), 5)
        self.assertEqual(len(r.yearly_impact), 5)
        self.assertTrue(r.headline)
        self.assertIn(
            r.verdict,
            {PayerStressVerdict.PASS, PayerStressVerdict.CAUTION,
             PayerStressVerdict.WARNING, PayerStressVerdict.FAIL},
        )

    def test_empty_mix_returns_pass(self):
        r = run_payer_stress(
            mix=[], total_npr_usd=0.0,
            total_ebitda_usd=0.0,
        )
        self.assertEqual(r.verdict, PayerStressVerdict.PASS)
        self.assertEqual(len(r.per_payer), 0)

    def test_high_concentration_flags_warning(self):
        mix = [
            PayerMixEntry("UnitedHealthcare", 0.65),
            PayerMixEntry("Anthem", 0.25),
            PayerMixEntry("Self-pay", 0.10),
        ]
        r = run_payer_stress(
            mix=mix, total_npr_usd=300_000_000,
            total_ebitda_usd=45_000_000,
            horizon_years=5, n_paths=300,
        )
        self.assertIn(
            r.verdict,
            {PayerStressVerdict.WARNING, PayerStressVerdict.FAIL},
        )
        self.assertGreaterEqual(r.top_1_share, 0.60)
        self.assertGreater(r.concentration_amplifier, 1.0)

    def test_diversified_mix_tends_to_pass(self):
        mix = [
            PayerMixEntry(f"PayerX{i}", 0.05) for i in range(20)
        ]
        r = run_payer_stress(
            mix=mix, total_npr_usd=200_000_000,
            total_ebitda_usd=30_000_000,
            horizon_years=5, n_paths=300,
        )
        # Top-1 is 5% — no concentration penalty
        self.assertEqual(r.concentration_amplifier, 1.0)

    def test_to_dict_roundtrip(self):
        r = run_payer_stress(
            mix=default_hospital_mix()[:3],
            total_npr_usd=100_000_000,
            horizon_years=3, n_paths=100,
        )
        payload = r.to_dict()
        dumped = json.dumps(payload, default=str)
        reloaded = json.loads(dumped)
        self.assertEqual(
            reloaded["target_name"], r.target_name,
        )
        self.assertEqual(
            len(reloaded["per_payer"]), len(r.per_payer),
        )

    def test_reproducible_with_seed(self):
        mix = default_hospital_mix()
        r1 = run_payer_stress(
            mix=mix, total_npr_usd=450e6,
            n_paths=200, seed=42,
        )
        r2 = run_payer_stress(
            mix=mix, total_npr_usd=450e6,
            n_paths=200, seed=42,
        )
        self.assertAlmostEqual(
            r1.median_cumulative_npr_delta_usd,
            r2.median_cumulative_npr_delta_usd, places=2,
        )


class BearCaseIntegrationTests(unittest.TestCase):

    def test_payer_stress_feeds_bear_case(self):
        from rcm_mc.diligence.bear_case import (
            extract_payer_stress_evidence, generate_bear_case,
        )
        # Concentrated mix → evidence should fire
        r = run_payer_stress(
            mix=[
                PayerMixEntry("UnitedHealthcare", 0.45),
                PayerMixEntry("Anthem", 0.30),
                PayerMixEntry("Medicare FFS", 0.25),
            ],
            total_npr_usd=400_000_000,
            total_ebitda_usd=60_000_000,
            n_paths=300,
        )
        evidence = extract_payer_stress_evidence(r)
        self.assertGreater(len(evidence), 0)

        # Full bear case with only payer stress input
        bc = generate_bear_case(
            target_name="Test", payer_stress=r,
        )
        self.assertIn("PAYER_STRESS", bc.sources_active)
        self.assertGreater(len(bc.evidence), 0)


class UIRenderTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.payer_stress_page import render_payer_stress_page
        html = render_payer_stress_page({})
        self.assertIn("<form", html)
        self.assertIn("Payer", html)

    def test_full_page_renders(self):
        from rcm_mc.ui.payer_stress_page import render_payer_stress_page
        mix_text = (
            "UnitedHealthcare, 34%\n"
            "Anthem, 20%\n"
            "Medicare FFS, 20%\n"
            "Medicare Advantage, 15%\n"
            "Medicaid managed, 11%"
        )
        html = render_payer_stress_page({
            "mix": [mix_text],
            "target_name": ["UI Test"],
            "total_npr_usd": ["450000000"],
            "total_ebitda_usd": ["67500000"],
            "horizon_years": ["5"],
            "n_paths": ["200"],
        })
        self.assertIn("UI Test", html)
        self.assertIn("data-sortable", html)
        self.assertIn("data-export-json", html)
        # Verdict badge should show
        self.assertTrue(
            any(v in html for v in
                ("PASS", "CAUTION", "WARNING", "FAIL")),
        )

    def test_empty_mix_shows_friendly_error(self):
        from rcm_mc.ui.payer_stress_page import render_payer_stress_page
        html = render_payer_stress_page({
            "mix": ["# only comments"],
            "target_name": ["Empty"],
        })
        self.assertIn("Could not parse", html)


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

    def test_payer_stress_route(self):
        qs = urlencode({
            "mix": "UnitedHealthcare, 34%\nMedicare FFS, 25%\nAnthem, 20%\nMedicaid managed, 21%",
            "target_name": "HTTP Test",
            "total_npr_usd": "300000000",
            "total_ebitda_usd": "45000000",
            "horizon_years": "5",
            "n_paths": "200",
        })
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/diligence/payer-stress?{qs}"
        )
        r = urlopen(url, timeout=20)
        self.assertEqual(r.status, 200)
        body = r.read().decode("utf-8")
        self.assertIn("HTTP Test", body)


if __name__ == "__main__":
    unittest.main()
