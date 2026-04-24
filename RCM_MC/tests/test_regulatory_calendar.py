"""Tests for the Regulatory Calendar × Thesis Kill-Switch module.

Covers the calendar library, the impact mapper gradient math, the
kill-switch verdict pipeline, the pipeline integration, the UI
render, and the HTTP endpoint.
"""
from __future__ import annotations

import json
import unittest
from datetime import date
from typing import Any, Dict
from urllib.parse import urlencode
from urllib.request import urlopen

from rcm_mc.diligence.regulatory_calendar import (
    DEFAULT_THESIS_DRIVERS, KillSwitchVerdict, REGULATORY_EVENTS,
    RegulatoryEvent, RegulatoryExposureReport, ThesisDriver,
    ThesisImpact, analyze_regulatory_exposure,
    events_for_specialty, map_event_to_drivers, upcoming_events,
)
from rcm_mc.diligence.regulatory_calendar.impact_mapper import (
    DriverCategory, ImpactVerdict,
)
from rcm_mc.diligence.regulatory_calendar.killswitch import (
    DriverKillTimeline, EbitdaOverlay,
)


class CalendarLibraryTests(unittest.TestCase):

    def test_curated_library_present(self):
        """The curated library must ship with events — empty would
        defeat the module's purpose."""
        self.assertGreater(len(REGULATORY_EVENTS), 5)

    def test_every_event_has_dates_and_source(self):
        for ev in REGULATORY_EVENTS:
            self.assertIsNotNone(
                ev.publish_date, f"{ev.event_id} missing publish date",
            )
            self.assertTrue(
                ev.source_url.startswith("http"),
                f"{ev.event_id} missing source url",
            )
            self.assertTrue(
                ev.narrative, f"{ev.event_id} missing narrative",
            )

    def test_v28_event_kills_ma_margin_lift(self):
        v28 = next(
            e for e in REGULATORY_EVENTS
            if e.event_id == "cms_v28_final_cy2027"
        )
        self.assertIn(
            "MA_MARGIN_LIFT", v28.thesis_driver_kill_map,
        )

    def test_kill_map_uses_controlled_vocabulary(self):
        """Every kill_map string must be a valid DriverCategory value."""
        allowed = {d.value for d in DriverCategory}
        for ev in REGULATORY_EVENTS:
            for d in ev.thesis_driver_kill_map:
                self.assertIn(
                    d, allowed,
                    f"{ev.event_id} kill_map has unknown "
                    f"driver {d}",
                )

    def test_events_for_specialty(self):
        hospital = events_for_specialty("HOSPITAL")
        self.assertGreater(len(hospital), 0)
        # Should be sorted by publish_date
        for a, b in zip(hospital, hospital[1:]):
            self.assertLessEqual(a.publish_date, b.publish_date)

    def test_upcoming_events_window(self):
        as_of = date(2026, 4, 1)
        out = upcoming_events(as_of=as_of, months_ahead=24)
        self.assertGreater(len(out), 0)
        # Sorted ascending
        for a, b in zip(out, out[1:]):
            ka = a.effective_date or a.publish_date
            kb = b.effective_date or b.publish_date
            self.assertLessEqual(ka, kb)


class ImpactMapperTests(unittest.TestCase):

    def _v28(self) -> RegulatoryEvent:
        return next(
            e for e in REGULATORY_EVENTS
            if e.event_id == "cms_v28_final_cy2027"
        )

    def test_high_ma_mix_killed(self):
        impacts = map_event_to_drivers(
            self._v28(), DEFAULT_THESIS_DRIVERS,
            target_profile={
                "ma_mix_pct": 0.85,
                "specialties": ["MA_RISK_PRIMARY_CARE"],
            },
        )
        ma = next(
            i for i in impacts
            if i.driver_id == DriverCategory.MA_MARGIN_LIFT.value
        )
        self.assertEqual(ma.verdict, ImpactVerdict.KILLED)
        self.assertGreater(ma.impairment_pct, 0.50)

    def test_low_ma_mix_unaffected(self):
        impacts = map_event_to_drivers(
            self._v28(), DEFAULT_THESIS_DRIVERS,
            target_profile={
                "ma_mix_pct": 0.05,
                "specialties": ["MA_RISK_PRIMARY_CARE"],
            },
        )
        ma = next(
            i for i in impacts
            if i.driver_id == DriverCategory.MA_MARGIN_LIFT.value
        )
        self.assertEqual(ma.verdict, ImpactVerdict.UNAFFECTED)

    def test_specialty_gating_filters_out(self):
        """A dialysis-only target should not see LEJR_MARGIN killed
        even when the event is in the calendar."""
        team = next(
            e for e in REGULATORY_EVENTS
            if e.event_id == "cms_team_cy2026_live"
        )
        impacts = map_event_to_drivers(
            team, DEFAULT_THESIS_DRIVERS,
            target_profile={
                "specialties": ["DIALYSIS"],
                "ma_mix_pct": 0.10,
            },
        )
        lejr = next(
            i for i in impacts
            if i.driver_id == DriverCategory.LEJR_MARGIN.value
        )
        self.assertEqual(lejr.verdict, ImpactVerdict.UNAFFECTED)

    def test_residual_lift_monotonic_with_impairment(self):
        impacts = map_event_to_drivers(
            self._v28(), DEFAULT_THESIS_DRIVERS,
            target_profile={
                "ma_mix_pct": 0.65,
                "specialties": ["MA_RISK_PRIMARY_CARE"],
            },
        )
        for i in impacts:
            # residual + impairment*expected_lift ≈ expected_lift
            driver = next(
                d for d in DEFAULT_THESIS_DRIVERS
                if d.driver_id == i.driver_id
            )
            reconstructed = (
                i.residual_lift_pct
                + i.impairment_pct * driver.expected_lift_pct
            )
            self.assertAlmostEqual(
                reconstructed, driver.expected_lift_pct, places=4,
            )


class KillSwitchTests(unittest.TestCase):

    def test_pass_verdict_on_unexposed_target(self):
        """A dialysis-only target with no MA exposure should PASS —
        the ESRD event is a tailwind, not a kill."""
        r = analyze_regulatory_exposure(
            target_profile={
                "specialties": ["DIALYSIS"],
                "ma_mix_pct": 0.05,
                "has_hopd_revenue": False,
                "has_reit_landlord": False,
            },
            as_of=date(2026, 4, 1),
            horizon_months=24,
        )
        self.assertIn(
            r.verdict,
            {KillSwitchVerdict.PASS, KillSwitchVerdict.CAUTION},
        )
        self.assertEqual(r.killed_driver_count, 0)

    def test_fail_verdict_on_concentrated_target(self):
        r = analyze_regulatory_exposure(
            target_profile={
                "specialties": [
                    "HOSPITAL", "ACUTE_HOSPITAL",
                    "MA_RISK_PRIMARY_CARE",
                ],
                "ma_mix_pct": 0.70,
                "commercial_payer_share": 0.40,
                "has_hopd_revenue": True,
                "has_reit_landlord": True,
                "revenue_usd": 450_000_000.0,
                "ebitda_usd": 67_500_000.0,
            },
            as_of=date(2026, 4, 1),
            horizon_months=24,
        )
        self.assertIn(
            r.verdict,
            {KillSwitchVerdict.WARNING, KillSwitchVerdict.FAIL},
        )
        self.assertGreater(r.killed_driver_count, 0)
        self.assertGreater(len(r.events), 0)
        self.assertTrue(r.headline)
        self.assertTrue(r.rationale)

    def test_ebitda_overlay_dollars_scale_with_revenue(self):
        r1 = analyze_regulatory_exposure(
            target_profile={
                "specialties": ["HOSPITAL"],
                "revenue_usd": 100_000_000.0,
                "ebitda_usd": 15_000_000.0,
                "has_hopd_revenue": True,
            },
            as_of=date(2026, 4, 1),
        )
        r2 = analyze_regulatory_exposure(
            target_profile={
                "specialties": ["HOSPITAL"],
                "revenue_usd": 400_000_000.0,
                "ebitda_usd": 60_000_000.0,
                "has_hopd_revenue": True,
            },
            as_of=date(2026, 4, 1),
        )
        eb1 = sum(o.ebitda_delta_usd for o in r1.ebitda_overlay)
        eb2 = sum(o.ebitda_delta_usd for o in r2.ebitda_overlay)
        # 4× revenue → roughly 4× absolute overlay
        self.assertGreater(abs(eb2), abs(eb1) * 2.5)

    def test_risk_score_range(self):
        r = analyze_regulatory_exposure(
            target_profile={
                "specialties": ["HOSPITAL", "MA_RISK_PRIMARY_CARE"],
                "ma_mix_pct": 0.70,
                "has_hopd_revenue": True,
                "has_reit_landlord": True,
            },
            as_of=date(2026, 4, 1),
        )
        self.assertGreaterEqual(r.risk_score, 0.0)
        self.assertLessEqual(r.risk_score, 100.0)

    def test_to_dict_roundtrip(self):
        r = analyze_regulatory_exposure(
            target_profile={"specialties": ["HOSPITAL"]},
            as_of=date(2026, 4, 1),
        )
        payload = r.to_dict()
        # Must be JSON serializable end-to-end
        dumped = json.dumps(payload, default=str)
        reloaded = json.loads(dumped)
        self.assertEqual(reloaded["verdict"], r.verdict.value)
        self.assertEqual(
            len(reloaded["driver_timelines"]), len(r.driver_timelines),
        )

    def test_custom_drivers_override_defaults(self):
        custom = [
            ThesisDriver(
                driver_id=DriverCategory.MA_MARGIN_LIFT.value,
                label="custom MA lift",
                expected_lift_pct=0.10,
                requires_ma_mix_above=0.30,
            ),
        ]
        r = analyze_regulatory_exposure(
            target_profile={
                "specialties": ["MA_RISK_PRIMARY_CARE"],
                "ma_mix_pct": 0.80,
            },
            drivers=custom,
            as_of=date(2026, 4, 1),
        )
        self.assertEqual(len(r.driver_timelines), 1)
        self.assertEqual(
            r.driver_timelines[0].driver_label, "custom MA lift",
        )


class ThesisPipelineIntegrationTests(unittest.TestCase):

    def test_pipeline_runs_regulatory_step(self):
        """The regulatory-calendar step must appear in step_log when
        the full pipeline runs over a valid CCD fixture."""
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, run_thesis_pipeline,
            pipeline_observations,
        )
        inp = PipelineInput(
            dataset="hospital_04_mixed_payer",
            deal_name="Test Target",
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
        self.assertIn("regulatory_exposure", steps)
        self.assertEqual(steps["regulatory_exposure"]["status"], "ok")
        self.assertIsNotNone(r.regulatory_exposure)
        self.assertIsNotNone(r.regulatory_verdict)
        # The overlay should feed the DealScenario's reg_headwind_usd
        self.assertIsNotNone(r.deal_scenario)
        self.assertGreaterEqual(
            r.deal_scenario.reg_headwind_usd, 0.0,
        )
        # Observations dict picks up the new signal
        obs = pipeline_observations(r)
        self.assertTrue(obs.get("regulatory_calendar_run"))


class UIRenderTests(unittest.TestCase):

    def test_landing_renders_without_params(self):
        from rcm_mc.ui.regulatory_calendar_page import (
            render_regulatory_calendar_page,
        )
        html = render_regulatory_calendar_page({})
        self.assertIn("<form", html)
        self.assertIn("Regulatory Calendar", html)

    def test_full_page_renders(self):
        from rcm_mc.ui.regulatory_calendar_page import (
            render_regulatory_calendar_page,
        )
        html = render_regulatory_calendar_page({
            "specialties": ["HOSPITAL,MA_RISK_PRIMARY_CARE"],
            "ma_mix_pct": ["0.55"],
            "commercial_payer_share": ["0.35"],
            "has_hopd_revenue": ["1"],
            "has_reit_landlord": ["1"],
            "revenue_usd": ["450000000"],
            "ebitda_usd": ["67500000"],
            "target_name": ["Meadowbrook"],
        })
        self.assertIn("Meadowbrook", html)
        self.assertIn("KILLED", html)
        self.assertIn("Kill-switch timeline", html)
        self.assertIn("EBITDA Bridge Overlay", html)


class HTTPEndpointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import http.server
        import socketserver
        import threading
        from rcm_mc.server import RCMHandler
        # Free port
        import socket
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

    def test_regulatory_calendar_page_http(self):
        qs = urlencode({
            "specialties": "HOSPITAL,MA_RISK_PRIMARY_CARE",
            "ma_mix_pct": "0.55",
            "has_hopd_revenue": "1",
            "has_reit_landlord": "1",
            "revenue_usd": "450000000",
            "ebitda_usd": "67500000",
            "target_name": "API Test",
        })
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/diligence/regulatory-calendar?{qs}"
        )
        body = urlopen(url, timeout=10).read().decode("utf-8")
        self.assertIn("API Test", body)
        self.assertIn("KILLED", body)

    def test_regulatory_calendar_api_json(self):
        qs = urlencode({
            "specialties": "HOSPITAL",
            "ma_mix_pct": "0.70",
            "has_hopd_revenue": "1",
            "revenue_usd": "400000000",
        })
        url = (
            f"http://127.0.0.1:{self.port}"
            f"/api/regulatory-calendar/exposure?{qs}"
        )
        body = urlopen(url, timeout=10).read().decode("utf-8")
        payload = json.loads(body)
        self.assertIn("verdict", payload)
        self.assertIn("driver_timelines", payload)
        self.assertIn("ebitda_overlay", payload)
        self.assertIn("events", payload)


if __name__ == "__main__":
    unittest.main()
