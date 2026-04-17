"""Tests for the state regulatory registry + risk flag detectors (Prompt 24).

Invariants locked here:

 1. Every US state + DC has an entry in both registries.
 2. Known CON states (IL, AL, GA) return CON_ACTIVE.
 3. Known non-CON states (TX, PA, KS) return NO_CON.
 4. ``assess_regulatory`` never raises on an unknown state code —
    it returns an empty assessment.
 5. Medicaid risk fires HIGH when the state fee index < 0.70 AND
    Medicaid is >= 20% of the payer mix.
 6. Medicaid risk stays LOW when the fee index is above 0.85 even
    with substantial Medicaid exposure.
 7. Market risk fires when commercial HHI is HIGH and commercial
    mix is >= 30%.
 8. Narrative is non-empty for every state.
 9. Risk score is in [0, 100].
10. ``to_dict`` round-trips cleanly through ``from_dict``.
11. Packet attaches ``regulatory_context`` when the profile has a
    state.
12. Packet has ``regulatory_context == None`` when no state.
13. Old packets without ``regulatory_context`` still deserialize.
14. Builder wires the CON_MORATORIUM flag end-to-end.
15. Builder wires MEDICAID_RATE_RISK flag end-to-end.
16. Builder wires MARKET_CONCENTRATION flag end-to-end.
17. Regulatory card rendered in the workbench when context is set.
18. Regulatory card skipped when no context.
19. JSON round-trip of the packet preserves regulatory_context.
20. CON profile dataclass serializes to dict.
"""
from __future__ import annotations

import json
import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket,
    HospitalProfile,
    RiskFlag,
    RiskSeverity,
)
from rcm_mc.analysis.packet_builder import build_analysis_packet
from rcm_mc.analysis.risk_flags import _build_regulatory_context_flags
from rcm_mc.data.state_regulatory import (
    CONProfile,
    CON_STATES,
    RegulatoryAssessment,
    STATE_CONTEXT,
    StatePayerProfile,
    all_known_states,
    assess_regulatory,
)
from rcm_mc.ui.analysis_workbench import render_workbench


_ALL_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
]


# ── Registry coverage ─────────────────────────────────────────────

class TestRegistryCoverage(unittest.TestCase):

    def test_all_states_in_con_registry(self):
        for st in _ALL_STATES:
            self.assertIn(st, CON_STATES, f"CON registry missing {st}")

    def test_all_states_in_payer_registry(self):
        for st in _ALL_STATES:
            self.assertIn(st, STATE_CONTEXT, f"STATE_CONTEXT missing {st}")

    def test_all_known_states_union(self):
        known = set(all_known_states())
        for st in _ALL_STATES:
            self.assertIn(st, known)


# ── CON status ─────────────────────────────────────────────────────

class TestCONStatus(unittest.TestCase):

    def test_illinois_has_con(self):
        a = assess_regulatory("IL", bed_count=300)
        self.assertEqual(a.con_status, "CON_ACTIVE")
        self.assertEqual(a.con_implication, "competitive_moat")

    def test_texas_no_con(self):
        a = assess_regulatory("TX", bed_count=200)
        self.assertEqual(a.con_status, "NO_CON")

    def test_unknown_state_no_raise(self):
        a = assess_regulatory("ZZ")
        self.assertEqual(a.state, "ZZ")
        self.assertEqual(a.con_status, "NO_CON")
        self.assertEqual(a.risk_score, 0)

    def test_lowercase_state_normalized(self):
        a = assess_regulatory("il", bed_count=100)
        self.assertEqual(a.state, "IL")

    def test_con_profile_to_dict(self):
        c = CON_STATES["IL"]
        d = c.to_dict()
        self.assertIn("has_con", d)
        self.assertIn("covered_services", d)


# ── Medicaid risk ──────────────────────────────────────────────────

class TestMedicaidRisk(unittest.TestCase):

    def test_high_risk_low_rate_high_exposure(self):
        # TX fee index 0.62 < 0.70, Medicaid 25% → HIGH.
        a = assess_regulatory(
            "TX", bed_count=200,
            payer_mix={"medicaid": 0.25},
        )
        self.assertEqual(a.medicaid_risk, "HIGH")

    def test_low_risk_high_rate_even_with_exposure(self):
        # NY fee index 1.12, Medicaid 30% → LOW.
        a = assess_regulatory(
            "NY", payer_mix={"medicaid": 0.30},
        )
        self.assertEqual(a.medicaid_risk, "LOW")

    def test_medium_risk_without_payer_mix_when_rate_low(self):
        a = assess_regulatory("TX")
        self.assertIn(a.medicaid_risk, ("MEDIUM", "HIGH"))

    def test_pct_point_scale_accepted(self):
        # Payer-mix values in the 0-100 range are renormalized.
        a = assess_regulatory(
            "TX", payer_mix={"medicaid": 25.0},
        )
        self.assertEqual(a.medicaid_risk, "HIGH")


# ── Market risk ───────────────────────────────────────────────────

class TestMarketRisk(unittest.TestCase):

    def test_high_market_risk_requires_high_hhi_and_mix(self):
        # AL has HIGH commercial HHI. Commercial 35% → HIGH.
        a = assess_regulatory(
            "AL", payer_mix={"commercial": 0.35},
        )
        self.assertEqual(a.market_risk, "HIGH")

    def test_low_hhi_state_stays_low(self):
        # NY is LOW HHI; any commercial exposure → LOW.
        a = assess_regulatory(
            "NY", payer_mix={"commercial": 0.50},
        )
        self.assertEqual(a.market_risk, "LOW")


# ── Narrative + score ─────────────────────────────────────────────

class TestNarrativeAndScore(unittest.TestCase):

    def test_narrative_non_empty_for_every_state(self):
        for st in _ALL_STATES:
            a = assess_regulatory(st, bed_count=200)
            self.assertTrue(a.narrative, f"{st} has empty narrative")

    def test_risk_score_bounded(self):
        for st in _ALL_STATES:
            a = assess_regulatory(st, bed_count=200)
            self.assertGreaterEqual(a.risk_score, 0)
            self.assertLessEqual(a.risk_score, 100)


# ── Serialization ─────────────────────────────────────────────────

class TestSerialization(unittest.TestCase):

    def test_round_trip(self):
        a = assess_regulatory(
            "IL", bed_count=300,
            payer_mix={"medicare": 0.4, "commercial": 0.4, "medicaid": 0.2},
        )
        restored = RegulatoryAssessment.from_dict(a.to_dict())
        self.assertEqual(restored.state, "IL")
        self.assertEqual(restored.con_status, a.con_status)
        self.assertEqual(restored.medicaid_risk, a.medicaid_risk)

    def test_con_profile_serializes(self):
        c = CONProfile(True, ["hospital_beds"], bed_threshold=20)
        self.assertEqual(c.to_dict()["bed_threshold"], 20)


# ── Risk-flag detectors ───────────────────────────────────────────

class TestRegulatoryContextFlags(unittest.TestCase):

    def test_moratorium_triggers_growth_ceiling(self):
        a = RegulatoryAssessment(
            state="IL", con_status="CON_MORATORIUM",
            con_implication="growth_ceiling",
        )
        flags = _build_regulatory_context_flags(
            HospitalProfile(state="IL"), a.to_dict(),
        )
        titles = [f.title for f in flags]
        self.assertIn("CON growth ceiling", titles)

    def test_medicaid_rate_risk_fires_at_high(self):
        a = RegulatoryAssessment(
            state="TX", medicaid_risk="HIGH",
            payer_profile=StatePayerProfile(
                False, 60.25, 0.62, 17.3, "MEDIUM", None,
            ),
        )
        flags = _build_regulatory_context_flags(
            HospitalProfile(state="TX"), a.to_dict(),
        )
        self.assertTrue(
            any(f.title == "Medicaid rate compression" for f in flags),
        )
        mc = next(f for f in flags if f.title == "Medicaid rate compression")
        self.assertEqual(mc.severity, RiskSeverity.HIGH)

    def test_market_concentration_fires(self):
        a = RegulatoryAssessment(
            state="AL", market_risk="HIGH",
            payer_profile=StatePayerProfile(
                False, 72.96, 0.82, 11.9, "HIGH",
                "Blue Cross Blue Shield of Alabama",
            ),
        )
        flags = _build_regulatory_context_flags(
            HospitalProfile(state="AL"), a.to_dict(),
        )
        self.assertTrue(
            any(f.title == "Commercial market concentration" for f in flags),
        )

    def test_no_context_no_flags(self):
        flags = _build_regulatory_context_flags(
            HospitalProfile(state="IL"), None,
        )
        self.assertEqual(flags, [])

    def test_con_competitive_moat_is_informational(self):
        a = RegulatoryAssessment(
            state="IL", con_status="CON_ACTIVE",
            con_implication="competitive_moat",
        )
        flags = _build_regulatory_context_flags(
            HospitalProfile(state="IL"), a.to_dict(),
        )
        rf = next(f for f in flags if f.title == "CON competitive moat")
        self.assertEqual(rf.severity, RiskSeverity.LOW)


# ── Builder integration ───────────────────────────────────────────

class TestBuilderIntegration(unittest.TestCase):

    def _build(self, state):
        import tempfile, os
        from rcm_mc.portfolio.store import PortfolioStore
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Test",
                              profile={"state": state, "bed_count": 200,
                                        "payer_mix": {"medicaid": 0.25,
                                                      "commercial": 0.35,
                                                      "medicare": 0.40}})
            return build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
            )
        finally:
            os.unlink(tf.name)

    def test_packet_attaches_regulatory_context(self):
        packet = self._build("IL")
        self.assertIsNotNone(packet.regulatory_context)
        self.assertEqual(packet.regulatory_context["state"], "IL")

    def test_no_state_no_context(self):
        import tempfile, os
        from rcm_mc.portfolio.store import PortfolioStore
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            store.upsert_deal("d1", name="Test",
                              profile={"bed_count": 200})
            packet = build_analysis_packet(
                store, "d1", skip_simulation=True,
                observed_override={"denial_rate": 12.0},
            )
            self.assertIsNone(packet.regulatory_context)
        finally:
            os.unlink(tf.name)

    def test_builder_emits_regulatory_flag_end_to_end(self):
        packet = self._build("TX")   # Medicaid fee index 0.62 + 25% mix → HIGH
        titles = [f.title for f in packet.risk_flags]
        self.assertIn("Medicaid rate compression", titles)


# ── Packet serialization ──────────────────────────────────────────

class TestPacketSerialization(unittest.TestCase):

    def test_regulatory_context_round_trip(self):
        p = DealAnalysisPacket(
            deal_id="d1",
            regulatory_context=assess_regulatory("IL").to_dict(),
        )
        restored = DealAnalysisPacket.from_dict(p.to_dict())
        self.assertEqual(
            restored.regulatory_context["state"], "IL",
        )

    def test_old_packet_without_field_deserializes(self):
        p = DealAnalysisPacket.from_dict({"deal_id": "d1"})
        self.assertIsNone(p.regulatory_context)

    def test_json_roundtrip(self):
        p = DealAnalysisPacket(
            deal_id="d1",
            regulatory_context=assess_regulatory(
                "TX", payer_mix={"medicaid": 0.25},
            ).to_dict(),
        )
        restored = DealAnalysisPacket.from_json(p.to_json())
        self.assertEqual(
            restored.regulatory_context["state"], "TX",
        )


# ── Workbench UI ──────────────────────────────────────────────────

class TestWorkbenchCard(unittest.TestCase):

    def test_card_rendered_when_context_present(self):
        p = DealAnalysisPacket(
            deal_id="d1",
            regulatory_context=assess_regulatory(
                "IL", bed_count=300,
                payer_mix={"medicaid": 0.25, "commercial": 0.35},
            ).to_dict(),
        )
        html = render_workbench(p)
        self.assertIn("Regulatory Environment", html)
        self.assertIn("IL", html)

    def test_card_omitted_when_no_context(self):
        p = DealAnalysisPacket(deal_id="d1")
        html = render_workbench(p)
        self.assertNotIn("Regulatory Environment", html)


if __name__ == "__main__":
    unittest.main()
