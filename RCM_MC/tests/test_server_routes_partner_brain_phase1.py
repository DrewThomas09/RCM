"""Tests for Partner Brain Phase 1 category pages.

Covers four new routes:
- /partner-brain/failures   (named_failure_library_v2, deal_smell_detectors,
                             denial_fix_pace_detector, medicare_advantage_bridge_trap,
                             payer_renegotiation_timing_model)
- /partner-brain/ic-decision (ic_decision_synthesizer, thesis_validator,
                              red_team_review, bear_book)
- /partner-brain/sniff       (unrealistic_on_face_check,
                              healthcare_thesis_archetype_recognizer)
- /partner-brain/100-day     (day_one_action_plan, post_close_90_day_reality_check,
                              ehr_transition_risk_assessor, integration_readiness)

Unit-level renderer tests for structural assertions, plus a live-server
check that all four routes return 200.
"""
from __future__ import annotations

import os
import socket as _socket
import tempfile
import threading
import time
import unittest
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server
from rcm_mc.ui.data_public.partner_brain_failures_page import (
    render_partner_brain_failures,
)
from rcm_mc.ui.data_public.partner_brain_ic_decision_page import (
    render_partner_brain_ic_decision,
)
from rcm_mc.ui.data_public.partner_brain_sniff_page import (
    render_partner_brain_sniff,
)
from rcm_mc.ui.data_public.partner_brain_100_day_page import (
    render_partner_brain_100_day,
)
from rcm_mc.ui.data_public.partner_brain_hub_page import render_partner_brain_hub


def _start_server(db_path: str):
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server, _ = build_server(port=port, db_path=db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    return server, port


class TestPartnerBrainFailuresPage(unittest.TestCase):
    def test_renders_demo(self):
        html = render_partner_brain_failures({})
        self.assertIn("Named Failures", html)
        self.assertIn("DEMO DATA", html)
        self.assertIn("/partner-brain", html)  # back-link to hub

    def test_surfaces_named_traps(self):
        html = render_partner_brain_failures({})
        self.assertIn("Denial-fix pace detector", html)
        self.assertIn("MA bridge trap", html)
        self.assertIn("Payer renegotiation", html)

    def test_surfaces_smell_detectors(self):
        html = render_partner_brain_failures({})
        self.assertIn("Deal smell detectors", html)

    def test_surfaces_v2_patterns(self):
        html = render_partner_brain_failures({})
        # At least one v2 pattern match should appear given seeded MA-heavy ctx
        self.assertIn("Named failure patterns", html)


class TestPartnerBrainICDecisionPage(unittest.TestCase):
    def test_renders_demo(self):
        html = render_partner_brain_ic_decision({})
        self.assertIn("IC Decision", html)
        self.assertIn("DEMO DATA", html)

    def test_decision_banner_has_recommendation(self):
        html = render_partner_brain_ic_decision({})
        self.assertIn("Recommendation", html)
        self.assertIn("Chair opening line", html)

    def test_sections_present(self):
        html = render_partner_brain_ic_decision({})
        self.assertIn("Thesis consistency", html)
        self.assertIn("Bear book", html)
        self.assertIn("Red team", html)


class TestPartnerBrainSniffPage(unittest.TestCase):
    def test_renders_demo(self):
        html = render_partner_brain_sniff({})
        self.assertIn("Sniff Test", html)
        self.assertIn("Archetype", html)

    def test_fires_expected_traps_on_seeded_input(self):
        html = render_partner_brain_sniff({})
        # Seeded inputs include aggressive IRR + unnamed MA bridge + 400bps
        # 1yr margin expansion; the sniff test should surface hits (not "No
        # on-face concerns")
        self.assertNotIn("No on-face concerns", html)

    def test_archetype_recognition_section_present(self):
        html = render_partner_brain_sniff({})
        self.assertIn("Archetype recognition", html)


class TestPartnerBrain100DayPage(unittest.TestCase):
    def test_renders_demo(self):
        html = render_partner_brain_100_day({})
        self.assertIn("100-Day", html)
        self.assertIn("DEMO DATA", html)

    def test_four_sections_present(self):
        html = render_partner_brain_100_day({})
        self.assertIn("Day-1 action plan", html)
        self.assertIn("90-day reality check", html)
        self.assertIn("EHR transition risk", html)
        self.assertIn("Integration readiness", html)

    def test_ehr_block_shows_payback(self):
        html = render_partner_brain_100_day({})
        self.assertIn("Payback", html)


class TestHubReflectsLiveCategories(unittest.TestCase):
    def test_hub_now_marks_phase1_categories_as_live(self):
        html = render_partner_brain_hub({})
        # Count LIVE badges — after Phase 1 there should be 5: review +
        # failures + ic-decision + sniff + 100-day
        self.assertGreaterEqual(html.count(">LIVE<"), 5)
        # PHASE 1 stubs still exist for the remaining 13 categories
        self.assertIn("PHASE 1", html)


class TestPartnerBrainPhase1LiveRoutes(unittest.TestCase):
    def test_all_four_routes_return_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            PortfolioStore(os.path.join(tmp, "p.db"))
            server, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                for path, needle in [
                    ("/partner-brain/failures", "Named Failures"),
                    ("/partner-brain/ic-decision", "IC Decision"),
                    ("/partner-brain/sniff", "Sniff Test"),
                    ("/partner-brain/100-day", "100-Day"),
                ]:
                    with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}{path}"
                    ) as r:
                        self.assertEqual(r.status, 200, f"{path} did not return 200")
                        body = r.read().decode()
                        self.assertIn(needle, body, f"{path} missing expected content")
            finally:
                server.shutdown()
                server.server_close()

    def test_unknown_slug_still_falls_through_to_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            PortfolioStore(os.path.join(tmp, "p.db"))
            server, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain/regulatory"
                ) as r:
                    # regulatory is still a PHASE 1 stub at this point
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("Regulatory Stress", body)
                    self.assertIn("Coming in Phase 1", body)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
