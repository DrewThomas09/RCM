"""Deal Autopsy regression tests.

Covers:
    - Library: 12 deals, correct outcome split, signature vectors in
      valid [0, 1] range, 9-dim
    - Signature: from CCD computes denial_rate, payer_concentration,
      medicare_mix, oon_revenue_share; metadata overrides and the
      un-supplied metadata dimensions fall back to 0.0
    - Matcher: Steward replay returns Steward as top match; strong
      survivor signature lifts HCA / USPI / LHC / Surgery Partners;
      feature deltas sum cleanly; only_outcomes filter works
    - UI page: landing renders; fixture mode runs; custom signature
      runs; unknown fixture falls back to landing; partner alert
      banner appears when top match is a bankruptcy with >=0.80 sim
    - IC packet integration: autopsy_matches renders Historical
      Analogue section; silent when empty or below similarity floor
    - Server route + sidebar nav link + Deal Profile link
"""
from __future__ import annotations

import math
import unittest
from dataclasses import dataclass
from pathlib import Path

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.deal_autopsy import (
    DealSignature, FEATURE_NAMES, MatchResult,
    OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11,
    OUTCOME_DISTRESSED_SALE, OUTCOME_DELISTED,
    OUTCOME_STRONG_EXIT, OUTCOME_STRONG_PUBLIC, OUTCOMES,
    historical_library, match_target, signature_from_ccd,
)
from rcm_mc.diligence.deal_autopsy.library import (
    get_deal_by_id, outcomes_summary,
)
from rcm_mc.diligence.deal_autopsy.matcher import (
    FEATURE_LABELS, signature_distance,
)


FIXTURE_ROOT = (
    Path(__file__).resolve().parent / "fixtures" / "kpi_truth"
)


@dataclass
class _FakeClaim:
    payer_canonical: str = "MEDICARE_FFS"
    payer_class: str = "MEDICARE"
    network_status: str = "IN"
    allowed_amount: float = 100.0
    paid_amount: float = 100.0
    charge_amount: float = 150.0
    status: str = "PAID"


class LibraryTests(unittest.TestCase):

    def test_library_has_twelve_deals(self):
        self.assertEqual(len(historical_library()), 12)

    def test_all_deals_have_9dim_signature_in_range(self):
        for d in historical_library():
            self.assertEqual(
                len(d.signature), 9,
                msg=f"{d.deal_id} signature has wrong arity",
            )
            for val in d.signature:
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)

    def test_all_outcomes_are_valid(self):
        for d in historical_library():
            self.assertIn(d.autopsy.outcome, OUTCOMES)

    def test_outcomes_summary_covers_negatives_and_survivors(self):
        counts = outcomes_summary()
        negatives = sum(counts.get(o, 0) for o in (
            OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11,
            OUTCOME_DISTRESSED_SALE, OUTCOME_DELISTED,
        ))
        survivors = sum(counts.get(o, 0) for o in (
            OUTCOME_STRONG_EXIT, OUTCOME_STRONG_PUBLIC,
        ))
        self.assertGreaterEqual(negatives, 6)
        self.assertGreaterEqual(survivors, 3)
        self.assertEqual(negatives + survivors, 12)

    def test_every_deal_has_partner_lesson(self):
        for d in historical_library():
            self.assertTrue(
                d.autopsy.partner_lesson,
                msg=f"{d.deal_id} missing partner lesson",
            )

    def test_every_negative_deal_has_early_warning_signs(self):
        for d in historical_library():
            if d.autopsy.is_negative:
                self.assertGreaterEqual(
                    len(d.autopsy.early_warning_signs), 2,
                    msg=f"{d.deal_id} should have >=2 warnings",
                )

    def test_get_deal_by_id_lookups(self):
        self.assertEqual(
            get_deal_by_id("steward_2010").name, "Steward Health Care",
        )
        with self.assertRaises(KeyError):
            get_deal_by_id("nonexistent_deal")


class SignatureFromCCDTests(unittest.TestCase):

    def test_empty_ccd_returns_zero_signature(self):
        sig = signature_from_ccd(type("CCD", (), {"claims": []})())
        self.assertEqual(sig.as_tuple(), (0.0,) * 9)

    def test_denial_rate_from_statuses(self):
        claims = [
            _FakeClaim(status="DENIED"),
            _FakeClaim(status="DENIED"),
            _FakeClaim(status="PAID"),
            _FakeClaim(status="PAID"),
        ]
        ccd = type("CCD", (), {"claims": claims})()
        sig = signature_from_ccd(ccd)
        self.assertAlmostEqual(sig.denial_rate, 0.5, places=6)

    def test_medicare_mix_computed(self):
        claims = [
            _FakeClaim(payer_class="MEDICARE", allowed_amount=100),
            _FakeClaim(payer_class="MEDICARE_ADVANTAGE",
                       allowed_amount=100),
            _FakeClaim(payer_class="COMMERCIAL", allowed_amount=200),
        ]
        ccd = type("CCD", (), {"claims": claims})()
        sig = signature_from_ccd(ccd)
        self.assertAlmostEqual(sig.medicare_mix, 0.5, places=6)

    def test_payer_concentration_top_payer(self):
        claims = [
            _FakeClaim(payer_canonical="UHC", allowed_amount=400),
            _FakeClaim(payer_canonical="AETNA", allowed_amount=100),
            _FakeClaim(payer_canonical="BCBS", allowed_amount=100),
        ]
        ccd = type("CCD", (), {"claims": claims})()
        sig = signature_from_ccd(ccd)
        self.assertAlmostEqual(sig.payer_concentration, 2/3, places=3)

    def test_oon_revenue_share(self):
        claims = [
            _FakeClaim(network_status="OON", allowed_amount=100),
            _FakeClaim(network_status="IN",  allowed_amount=100),
            _FakeClaim(network_status="IN",  allowed_amount=100),
        ]
        ccd = type("CCD", (), {"claims": claims})()
        sig = signature_from_ccd(ccd)
        self.assertAlmostEqual(sig.oon_revenue_share, 1/3, places=3)

    def test_metadata_overrides_supplied_dimensions(self):
        claims = [_FakeClaim(status="PAID") for _ in range(4)]
        ccd = type("CCD", (), {"claims": claims})()
        sig = signature_from_ccd(ccd, metadata={
            "lease_intensity": 0.9,
            "ebitdar_stress": 0.8,
            "regulatory_exposure": 0.5,
            "physician_concentration": 0.4,
            "denial_rate": 0.3,
        })
        self.assertEqual(sig.lease_intensity, 0.9)
        self.assertEqual(sig.ebitdar_stress, 0.8)
        self.assertEqual(sig.regulatory_exposure, 0.5)
        self.assertEqual(sig.physician_concentration, 0.4)
        self.assertEqual(sig.denial_rate, 0.3)  # overridden
        # Provenance reflects the metadata source for supplied values
        self.assertIn("metadata", sig.provenance["denial_rate"])

    def test_metadata_values_clipped_to_unit_interval(self):
        ccd = type("CCD", (), {"claims": []})()
        sig = signature_from_ccd(ccd, metadata={
            "lease_intensity": 2.5,   # too high
            "ebitdar_stress": -0.3,   # too low
        })
        self.assertEqual(sig.lease_intensity, 1.0)
        self.assertEqual(sig.ebitdar_stress, 0.0)


class MatcherTests(unittest.TestCase):

    def test_steward_replay_matches_steward(self):
        """A signature close to Steward's entry should rank Steward
        first among negative-outcome deals."""
        steward_like = DealSignature(
            lease_intensity=0.88,
            ebitdar_stress=0.83,
            medicare_mix=0.55,
            payer_concentration=0.36,
            denial_rate=0.14,
            dar_stress=0.60,
            regulatory_exposure=0.58,
            physician_concentration=0.30,
            oon_revenue_share=0.08,
        )
        matches = match_target(
            steward_like, historical_library(), top_k=3,
        )
        self.assertEqual(matches[0].deal.deal_id, "steward_2010")
        self.assertGreater(matches[0].similarity, 0.90)

    def test_strong_survivor_signature_lifts_survivor(self):
        """A low-stress signature should match HCA or another
        survivor above any failure."""
        survivor = DealSignature(
            lease_intensity=0.10,
            ebitdar_stress=0.25,
            medicare_mix=0.40,
            payer_concentration=0.20,
            denial_rate=0.08,
            dar_stress=0.30,
            regulatory_exposure=0.25,
            physician_concentration=0.15,
            oon_revenue_share=0.04,
        )
        matches = match_target(
            survivor, historical_library(), top_k=3,
        )
        self.assertFalse(matches[0].deal.autopsy.is_negative)

    def test_results_ordered_by_similarity(self):
        sig = DealSignature()
        results = match_target(
            sig, historical_library(), top_k=12,
        )
        sims = [r.similarity for r in results]
        self.assertEqual(sims, sorted(sims, reverse=True))

    def test_top_k_bounds_return_length(self):
        sig = DealSignature()
        r = match_target(sig, historical_library(), top_k=4)
        self.assertEqual(len(r), 4)

    def test_only_outcomes_filter(self):
        sig = DealSignature()
        r = match_target(
            sig, historical_library(), top_k=20,
            only_outcomes=(OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11),
        )
        for m in r:
            self.assertIn(
                m.deal.autopsy.outcome,
                (OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11),
            )

    def test_feature_deltas_sum_shares_to_one(self):
        target = DealSignature(
            lease_intensity=0.5, denial_rate=0.4,
        )
        deal_sig = (0.0,) * 9
        dist, deltas = signature_distance(target, deal_sig)
        self.assertEqual(len(deltas), 9)
        share_sum = sum(d.share_of_distance for d in deltas)
        # All non-matching values contribute shares summing to 1.
        self.assertAlmostEqual(share_sum, 1.0, places=6)

    def test_zero_distance_has_zero_shares(self):
        target = DealSignature()
        deal_sig = (0.0,) * 9
        dist, deltas = signature_distance(target, deal_sig)
        self.assertEqual(dist, 0.0)
        for d in deltas:
            self.assertEqual(d.share_of_distance, 0.0)

    def test_similarity_at_opposite_corners_is_zero(self):
        target = DealSignature(
            lease_intensity=1.0, ebitdar_stress=1.0,
            medicare_mix=1.0, payer_concentration=1.0,
            denial_rate=1.0, dar_stress=1.0,
            regulatory_exposure=1.0,
            physician_concentration=1.0,
            oon_revenue_share=1.0,
        )
        dist, _ = signature_distance(target, (0.0,) * 9)
        self.assertAlmostEqual(dist, math.sqrt(9), places=6)

    def test_aligning_features_are_closest(self):
        """The aligning features of a match are the three features
        with smallest squared deviation."""
        target = DealSignature(
            lease_intensity=0.90, ebitdar_stress=0.85,
            medicare_mix=0.55, oon_revenue_share=0.08,
        )
        matches = match_target(
            target, historical_library(), top_k=1,
        )
        m = matches[0]
        self.assertEqual(len(m.aligning), 3)
        # Aligning should be sorted by smallest deviation.
        deviations = [d.squared_deviation for d in m.aligning]
        self.assertEqual(deviations, sorted(deviations))

    def test_diverging_are_largest(self):
        target = DealSignature(
            lease_intensity=0.1, ebitdar_stress=0.1,
            medicare_mix=0.1, oon_revenue_share=0.9,
        )
        matches = match_target(
            target, historical_library(), top_k=1,
        )
        m = matches[0]
        devs = [d.squared_deviation for d in m.diverging]
        self.assertEqual(devs, sorted(devs, reverse=True))


class DealAutopsyPageTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        h = render_deal_autopsy_page()
        self.assertIn("Deal Autopsy", h)
        self.assertIn("Run autopsy match", h)
        self.assertIn("Library composition", h)

    def test_custom_signature_renders_matches(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        h = render_deal_autopsy_page(qs={
            "lease_intensity": ["0.9"],
            "ebitdar_stress": ["0.8"],
        })
        # At least one match card
        self.assertIn("Similarity", h)
        self.assertIn("Features that match", h)
        self.assertIn("Features that diverge", h)

    def test_fixture_mode_renders(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        h = render_deal_autopsy_page(qs={
            "dataset": ["hospital_02_denial_heavy"],
        })
        self.assertIn("Target signature", h)
        self.assertIn("Similarity", h)

    def test_bankruptcy_signature_produces_partner_alert(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        # Near-Steward signature — should surface the partner alert
        # banner with an "are doing X again" framing.
        h = render_deal_autopsy_page(qs={
            "lease_intensity": ["0.90"],
            "ebitdar_stress": ["0.85"],
            "medicare_mix": ["0.55"],
            "payer_concentration": ["0.35"],
            "denial_rate": ["0.14"],
            "dar_stress": ["0.60"],
            "regulatory_exposure": ["0.58"],
            "physician_concentration": ["0.30"],
            "oon_revenue_share": ["0.08"],
        })
        self.assertIn("Steward Health Care", h)
        self.assertIn("underwriting a deal", h)

    def test_unknown_fixture_falls_back_to_landing(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        h = render_deal_autopsy_page(qs={
            "dataset": ["not_a_fixture"],
        })
        self.assertIn("Run autopsy match", h)

    def test_library_table_rendered_on_landing(self):
        from rcm_mc.ui.deal_autopsy_page import (
            render_deal_autopsy_page,
        )
        h = render_deal_autopsy_page()
        # Sampling a few deal names from the library.
        self.assertIn("Steward Health Care", h)
        self.assertIn("HCA Healthcare", h)
        self.assertIn("Envision Healthcare", h)


class NavLinkTest(unittest.TestCase):

    def test_deal_autopsy_link_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/deal-autopsy"', rendered)

    def test_deal_profile_exposes_autopsy_analytic(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/deal-autopsy", ids)


class ICPacketIntegrationTests(unittest.TestCase):

    def _run_sample_matches(self):
        """Build a deliberate Steward-like signature so the top match
        has >=0.80 similarity to a bankruptcy deal."""
        sig = DealSignature(
            lease_intensity=0.90, ebitdar_stress=0.85,
            medicare_mix=0.55, payer_concentration=0.36,
            denial_rate=0.14, dar_stress=0.60,
            regulatory_exposure=0.58,
            physician_concentration=0.30,
            oon_revenue_share=0.08,
        )
        return match_target(
            sig, historical_library(), top_k=3,
        )

    def test_ic_packet_renders_historical_analogue_section(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        matches = self._run_sample_matches()
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test Target"),
            autopsy_matches=matches,
        )
        self.assertIn("Historical Analogue", html_str)
        self.assertIn("Steward Health Care", html_str)
        self.assertIn("% match", html_str)

    def test_ic_packet_silent_when_no_matches(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            autopsy_matches=None,
        )
        self.assertNotIn("Historical Analogue", html_str)

    def test_ic_packet_silent_when_matches_below_floor(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )

        # Fabricate a very low similarity by matching a zero target
        # against a very high-signature deal (opposite corners).
        from rcm_mc.diligence.deal_autopsy import match_target
        sig = DealSignature()   # all zeros
        # Use only the most extreme signature to ensure similarity
        # stays under the 0.60 render floor.
        from rcm_mc.diligence.deal_autopsy.library import (
            get_deal_by_id,
        )
        steward = get_deal_by_id("steward_2010")
        single_deal_library = (steward,)
        matches = match_target(sig, single_deal_library, top_k=5)
        # Opposite-corner similarity should be < 0.60 for the section
        # to be suppressed by the IC-packet renderer.
        self.assertLess(matches[0].similarity, 0.60)
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            autopsy_matches=matches,
        )
        self.assertNotIn("Historical Analogue", html_str)


class AnalyzeCCDEndToEndTests(unittest.TestCase):

    def test_runs_on_denial_heavy_fixture(self):
        ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_02_denial_heavy",
        )
        sig = signature_from_ccd(ccd)
        for name in FEATURE_NAMES:
            val = getattr(sig, name)
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

    def test_matches_across_library_for_fixture(self):
        ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_02_denial_heavy",
        )
        sig = signature_from_ccd(ccd, metadata={
            "lease_intensity": 0.5,
            "ebitdar_stress": 0.5,
        })
        matches = match_target(
            sig, historical_library(), top_k=5,
        )
        self.assertEqual(len(matches), 5)
        # All similarities in [0, 1].
        for m in matches:
            self.assertGreaterEqual(m.similarity, 0.0)
            self.assertLessEqual(m.similarity, 1.0)


class FeatureLabelsTest(unittest.TestCase):

    def test_every_feature_has_label(self):
        for name in FEATURE_NAMES:
            self.assertIn(name, FEATURE_LABELS)


if __name__ == "__main__":
    unittest.main()
