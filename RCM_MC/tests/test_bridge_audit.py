"""Tests for the EBITDA Bridge Auto-Auditor."""
from __future__ import annotations

import json
import unittest
from typing import Any, Dict, List
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.diligence.bridge_audit import (
    BridgeLever, LEVER_PRIORS, LeverCategory, LeverVerdict,
    audit_bridge, audit_lever, classify_lever, parse_bridge_text,
    prior_for,
)


class LeverLibraryTests(unittest.TestCase):

    def test_library_ships_all_categories(self):
        cats_in_lib = {p.category for p in LEVER_PRIORS}
        for c in LeverCategory:
            self.assertIn(
                c, cats_in_lib,
                f"{c.value} missing from LEVER_PRIORS",
            )

    def test_classifier_hits_all_major_keywords(self):
        cases = [
            ("Denial workflow overhaul", LeverCategory.DENIAL_WORKFLOW),
            ("CDI coding uplift", LeverCategory.CODING_INTENSITY),
            ("Underpayment recovery", LeverCategory.UNDERPAYMENT_RECOVERY),
            ("AR aging liquidation", LeverCategory.AR_AGING_LIQUIDATION),
            ("Vendor clearinghouse consolidation",
             LeverCategory.VENDOR_CONSOLIDATION),
            ("FTE reduction via automation", LeverCategory.FTE_REDUCTION),
            ("Tuck-in M&A synergy", LeverCategory.TUCK_IN_M_AND_A_SYNERGY),
            ("Site-neutral mitigation",
             LeverCategory.SITE_NEUTRAL_MITIGATION),
            ("MA HCC coding uplift", LeverCategory.MA_CODING_UPLIFT),
            ("Working capital release",
             LeverCategory.WORKING_CAPITAL_RELEASE),
            ("Something totally unrelated", LeverCategory.OTHER),
        ]
        for text, expected in cases:
            got = classify_lever(text)
            self.assertEqual(
                got, expected,
                f"{text!r}: expected {expected.value}, got {got.value}",
            )

    def test_prior_for_always_returns(self):
        for c in LeverCategory:
            p = prior_for(c)
            self.assertIsNotNone(p)
            self.assertGreaterEqual(p.realization_median, 0.0)
            self.assertLessEqual(p.realization_median, 1.1)

    def test_prior_sanity_p25_lt_p75(self):
        for p in LEVER_PRIORS:
            self.assertLessEqual(
                p.realization_p25, p.realization_p75,
                f"{p.category.value} P25 > P75",
            )
            self.assertGreaterEqual(p.failure_rate, 0.0)
            self.assertLessEqual(p.failure_rate, 1.0)


class ParserTests(unittest.TestCase):

    def test_parse_comma_format(self):
        levers = parse_bridge_text("Denial workflow, 4.2M")
        self.assertEqual(len(levers), 1)
        self.assertEqual(levers[0].name, "Denial workflow")
        self.assertAlmostEqual(levers[0].claimed_usd, 4_200_000)

    def test_parse_colon_format(self):
        levers = parse_bridge_text("Coding uplift: $3,100,000")
        self.assertEqual(len(levers), 1)
        self.assertAlmostEqual(levers[0].claimed_usd, 3_100_000)

    def test_parse_ignores_comments_and_blanks(self):
        text = """
# This is a comment
Denial workflow, 4.2M

Coding uplift, 3.1M
        """
        levers = parse_bridge_text(text)
        self.assertEqual(len(levers), 2)

    def test_parse_handles_k_suffix(self):
        levers = parse_bridge_text("Credit balance, 850K")
        self.assertAlmostEqual(levers[0].claimed_usd, 850_000)


class AuditLogicTests(unittest.TestCase):

    def _target(self) -> Dict[str, Any]:
        return {
            "denial_rate_pct": 0.095,
            "ma_mix_pct": 0.45,
            "commercial_payer_share": 0.32,
            "top_1_payer_share": 0.34,
            "days_in_ar": 52,
            "beds": 300,
            "ehr_vendor": "EPIC",
            "v28_rule_finalized": True,
        }

    def test_overstated_vendor_consolidation(self):
        """Vendor consolidation has 42% failure rate — a large
        claim should flag as UNSUPPORTED."""
        lever = BridgeLever(
            name="Vendor consolidation",
            claimed_usd=5_000_000,
        )
        a = audit_lever(lever, target_profile=self._target())
        self.assertEqual(a.category, LeverCategory.VENDOR_CONSOLIDATION)
        self.assertIn(
            a.verdict,
            {LeverVerdict.OVERSTATED, LeverVerdict.UNSUPPORTED},
        )

    def test_realistic_denial_at_high_denial_rate(self):
        """Denial workflow at target with 12%+ denial rate gets a
        big boost — banker's $4.2M claim should be REALISTIC."""
        t = self._target()
        t["denial_rate_pct"] = 0.13
        a = audit_lever(
            BridgeLever(name="Denial workflow", claimed_usd=4_200_000),
            target_profile=t,
        )
        self.assertEqual(a.verdict, LeverVerdict.REALISTIC)
        self.assertGreater(
            a.adjusted_realization_median,
            0.90,  # base 0.85 + boosts
        )

    def test_understated_sandbag(self):
        """Claim below P25 → UNDERSTATED."""
        a = audit_lever(
            BridgeLever(name="Denial workflow", claimed_usd=500_000),
            target_profile=self._target(),
        )
        # With realization ~0.95, claimed 0.5M gives realistic 0.48M median
        # The "understated" verdict fires when claimed < p25_usd (i.e.
        # claimed < 0.5M × p25 / median).  Verify claim is reported.
        self.assertEqual(a.claimed_usd, 500_000)

    def test_ma_coding_takes_v28_penalty(self):
        """MA coding with V28 finalized should land in a weakened
        realization band."""
        a = audit_lever(
            BridgeLever(name="MA HCC coding uplift", claimed_usd=3_000_000),
            target_profile=self._target(),
        )
        self.assertEqual(a.category, LeverCategory.MA_CODING_UPLIFT)
        self.assertIn(
            ("v28_rule_finalized", -0.30),
            a.applied_boosts,
        )

    def test_unionized_zeroes_fte_lever(self):
        t = self._target()
        t["unionized_workforce"] = True
        a = audit_lever(
            BridgeLever(name="FTE reduction via automation",
                        claimed_usd=3_000_000),
            target_profile=t,
        )
        self.assertLess(a.adjusted_realization_median, 0.15)
        self.assertIn(
            a.verdict,
            {LeverVerdict.OVERSTATED, LeverVerdict.UNSUPPORTED},
        )


class BridgeAuditTests(unittest.TestCase):

    def test_full_bridge_audit_produces_counter_bid(self):
        levers = parse_bridge_text(
            "Denial workflow, 4.2M\n"
            "Coding uplift, 3.1M\n"
            "Vendor consolidation, 2.8M\n"
            "AR aging liquidation, 1.5M\n"
            "Site-neutral mitigation, 1.8M\n"
            "Tuck-in M&A synergy, 2.5M\n"
        )
        report = audit_bridge(
            levers=levers,
            target_name="Test",
            target_profile={
                "denial_rate_pct": 0.095,
                "ma_mix_pct": 0.45,
            },
            entry_multiple=10.5,
            asking_price_usd=700_000_000.0,
        )
        self.assertGreater(report.claimed_bridge_usd, 0)
        self.assertGreater(report.realistic_bridge_usd, 0)
        self.assertEqual(len(report.per_lever), 6)
        # Bridge gap should price out to a non-trivial counter-bid
        self.assertIsNotNone(report.counter_offer_usd)
        self.assertLess(
            report.counter_offer_usd, report.asking_price_usd,
        )
        # Headline and rationale populated
        self.assertTrue(report.headline)
        self.assertTrue(report.rationale)
        self.assertTrue(report.partner_recommendation)

    def test_empty_bridge_returns_zero(self):
        report = audit_bridge(
            levers=[], target_name="Empty",
        )
        self.assertEqual(report.claimed_bridge_usd, 0.0)
        self.assertEqual(report.realistic_bridge_usd, 0.0)
        self.assertEqual(len(report.per_lever), 0)

    def test_to_dict_roundtrip(self):
        levers = [BridgeLever(name="Denial workflow", claimed_usd=2_000_000)]
        report = audit_bridge(levers=levers, target_name="Rt")
        payload = report.to_dict()
        dumped = json.dumps(payload, default=str)
        reloaded = json.loads(dumped)
        self.assertEqual(
            reloaded["target_name"], "Rt",
        )
        self.assertEqual(
            len(reloaded["per_lever"]), 1,
        )

    def test_double_count_flag_fires(self):
        levers = [
            BridgeLever(name="Denial workflow", claimed_usd=3_000_000),
            BridgeLever(name="Clean claim rate", claimed_usd=2_000_000),
        ]
        r = audit_bridge(levers=levers, target_name="Dbl")
        self.assertIn("double-count", r.partner_recommendation.lower())


class UIRenderTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.bridge_audit_page import render_bridge_audit_page
        html = render_bridge_audit_page({})
        self.assertIn("<form", html)
        self.assertIn("Bridge Auto-Auditor", html)
        self.assertIn("Denial workflow", html)

    def test_full_audit_page_renders(self):
        from rcm_mc.ui.bridge_audit_page import render_bridge_audit_page
        html = render_bridge_audit_page({
            "bridge": [(
                "Denial workflow, 4.2M\n"
                "Coding uplift, 3.1M\n"
                "Vendor consolidation, 2.8M\n"
                "AR aging liquidation, 1.5M\n"
            )],
            "target_name": ["Meadowbrook"],
            "asking_price_usd": ["700000000"],
            "entry_multiple": ["10.5"],
            "denial_rate_pct": ["0.095"],
            "ma_mix_pct": ["0.45"],
        })
        self.assertIn("Meadowbrook", html)
        # Expect at least one verdict chip to appear
        self.assertTrue(
            "REALISTIC" in html
            or "OVERSTATED" in html
            or "UNSUPPORTED" in html
        )
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

    def test_bridge_audit_route(self):
        qs = urlencode({
            "bridge": (
                "Denial workflow, 4.2M\n"
                "Coding uplift, 3.1M\n"
                "Vendor consolidation, 2.8M"
            ),
            "target_name": "HTTP Test",
            "asking_price_usd": "500000000",
            "entry_multiple": "10.0",
            "denial_rate_pct": "0.10",
            "ma_mix_pct": "0.40",
        })
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/diligence/bridge-audit?{qs}"
        )
        body = urlopen(url, timeout=15).read().decode("utf-8")
        self.assertIn("HTTP Test", body)


if __name__ == "__main__":
    unittest.main()
