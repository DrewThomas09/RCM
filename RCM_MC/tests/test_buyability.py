"""Phase-6 buyability tests.

Pins the partner-articulated priors so a future tweak of the
rule weights can't silently flip the partner-facing ordering:

  Academic / Flagship Specialty / Children's → very_low
  Large nonprofit / Catholic / Kaiser system members → very_low
  Community + CAH + Rehab + LTACH at mid-bed size → medium / high

Plus the target_attractiveness multiplicative combiner.
"""
import unittest

import pandas as pd

from rcm_mc.data.hospital_taxonomy import derive_taxonomy
from rcm_mc.finance.buyability import (
    BuyabilityScore,
    attractiveness_tier,
    score_buyability,
    score_buyability_batch,
    summarize_distribution,
    target_attractiveness,
)


def _tagged_row(ccn, name, beds, medicare_pct=40, medicaid_pct=15):
    """Build a single taxonomy-tagged hospital row."""
    df = derive_taxonomy(pd.DataFrame([{
        "ccn": ccn, "name": name, "beds": beds,
        "medicare_day_pct": medicare_pct,
        "medicaid_day_pct": medicaid_pct,
    }]))
    return df.iloc[0].to_dict()


class SegmentPriorTests(unittest.TestCase):
    """Per-segment buyability score must respect partner priors —
    academic + flagship + children's are essentially unbuyable;
    community + CAH are the sweet spot."""

    def test_flagship_specialty_very_low(self):
        # MD Anderson — flagship cancer centre, ~0.02 base
        row = _tagged_row("450076", "MD ANDERSON CANCER CENTER", 700)
        s = score_buyability(row)
        self.assertEqual(s.tier, "very_low")
        self.assertLess(s.score, 0.10)
        # Reason list must call out the segment
        self.assertTrue(any("Flagship Specialty" in r for r in s.reasons))

    def test_academic_very_low(self):
        # Generic UNIVERSITY name → Academic segment, 0.04 base
        row = _tagged_row(
            "050001", "UNIVERSITY OF FOO MEDICAL CENTER", 500,
        )
        s = score_buyability(row)
        self.assertEqual(s.tier, "very_low")
        self.assertLess(s.score, 0.10)

    def test_childrens_almost_zero(self):
        # Children's hospital — capped at 5% even before name penalty
        row = _tagged_row(
            "053301", "CHILDRENS HOSPITAL OF SOMEWHERE", 200,
        )
        s = score_buyability(row)
        self.assertLessEqual(s.score, 0.05)
        self.assertEqual(s.tier, "very_low")

    def test_large_community_at_sweet_spot(self):
        # 250-bed Regional Medical Center — Large Community,
        # mid-size sweet spot (50-400), base 0.55 + 10% bump.
        row = _tagged_row("100100", "REGIONAL MEDICAL CENTER", 250)
        s = score_buyability(row)
        # 0.55 * 1.10 = 0.605
        self.assertGreater(s.score, 0.55)
        self.assertEqual(s.tier, "high")

    def test_small_community_high_tier(self):
        # 80 beds — still in sweet spot
        row = _tagged_row("220071", "MAIN STREET HOSPITAL", 80)
        s = score_buyability(row)
        # 0.65 base × 1.10 sweet spot ≈ 0.715
        self.assertGreater(s.score, 0.55)
        self.assertEqual(s.tier, "high")

    def test_critical_access_medium(self):
        # 20-bed CAH — 0.35 base × 0.75 size penalty ≈ 0.26
        row = _tagged_row("191333", "TINY COUNTY HOSPITAL", 20)
        s = score_buyability(row)
        self.assertLess(s.score, 0.35)
        self.assertEqual(s.tier, "low")

    def test_rehab_medium_high(self):
        row = derive_taxonomy(pd.DataFrame([{
            "ccn": "053025",  # CCN range for rehab
            "name": "REGIONAL REHAB CENTER",
            "beds": 100,
            "medicare_day_pct": 60, "medicaid_day_pct": 10,
        }])).iloc[0].to_dict()
        s = score_buyability(row)
        # Rehab base 0.60 × 1.10 sweet spot ≈ 0.66
        self.assertGreater(s.score, 0.50)
        self.assertEqual(s.tier, "high")


class NameKeywordTests(unittest.TestCase):
    """Curated unbuyable-system list must cap the score for
    member hospitals, even when the rule-based segment looks
    favourable."""

    def test_kaiser_member_penalized(self):
        # Large Community by segment (250 beds, no Academic name)
        # but Kaiser → -80% penalty
        row = _tagged_row("100200", "KAISER FOUNDATION HOSPITAL — OAKLAND", 250)
        s = score_buyability(row)
        # 0.55 × 1.10 sweet spot × 0.20 system penalty ≈ 0.121
        self.assertLess(s.score, 0.20)
        self.assertEqual(s.tier, "very_low")
        self.assertTrue(any("system" in r.lower() for r in s.reasons))

    def test_va_hospital_penalized(self):
        row = _tagged_row(
            "100300", "VA MEDICAL CENTER — PHOENIX", 300,
        )
        s = score_buyability(row)
        self.assertLess(s.score, 0.20)

    def test_ascension_member_penalized(self):
        row = _tagged_row("100400", "ASCENSION ST VINCENT HOSPITAL", 200)
        s = score_buyability(row)
        self.assertLess(s.score, 0.20)


class SizeAdjustmentTests(unittest.TestCase):
    def test_micro_bed_penalty(self):
        # Tiny hospital outside CAH range — Small Community (sweet
        # spot in segment terms, but <25 beds triggers penalty)
        row = derive_taxonomy(pd.DataFrame([{
            "ccn": "100500",  # general range, not CAH
            "name": "TINY GENERAL HOSPITAL", "beds": 15,
            "medicare_day_pct": 40, "medicaid_day_pct": 15,
        }])).iloc[0].to_dict()
        s = score_buyability(row)
        # 0.65 × 0.75 size penalty = 0.4875
        self.assertLess(s.score, 0.55)
        self.assertTrue(any("Very small" in r for r in s.reasons))

    def test_flagship_scale_penalty(self):
        # 800-bed hospital that's NOT academic by name — still gets
        # the flagship-scale penalty for being >600 beds
        row = _tagged_row("100600", "MEGA REGIONAL HOSPITAL", 800)
        s = score_buyability(row)
        # 0.55 × 0.50 large-penalty = 0.275
        self.assertLess(s.score, 0.40)


class SafetyNetTests(unittest.TestCase):
    def test_safety_net_penalty(self):
        # Urban hospital with 45% Medicaid → safety_net_proxy
        # fires, segment becomes Safety-Net Community (0.18 base)
        row = _tagged_row(
            "120200", "URBAN COMMUNITY HOSPITAL", 200,
            medicare_pct=30, medicaid_pct=45,
        )
        s = score_buyability(row)
        # Safety-Net Community base 0.18 × 1.10 sweet spot ≈ 0.198,
        # then ×0.65 safety-net penalty ≈ 0.129
        self.assertLess(s.score, 0.18)
        self.assertEqual(s.tier, "very_low")


class BatchScoringTests(unittest.TestCase):
    def test_batch_returns_score_and_tier_columns(self):
        df = derive_taxonomy(pd.DataFrame([
            {"ccn": "050441", "name": "STANFORD HOSPITAL", "beds": 700,
             "medicare_day_pct": 40, "medicaid_day_pct": 10},
            {"ccn": "100100", "name": "REGIONAL MEDICAL CENTER",
             "beds": 250, "medicare_day_pct": 45, "medicaid_day_pct": 15},
            {"ccn": "191333", "name": "TINY COUNTY HOSPITAL", "beds": 20,
             "medicare_day_pct": 60, "medicaid_day_pct": 20},
        ]))
        out = score_buyability_batch(df)
        self.assertIn("buyability_score", out.columns)
        self.assertIn("buyability_tier", out.columns)
        self.assertEqual(len(out), 3)
        # Stanford very_low, Regional high, CAH low
        scores = dict(zip(out["name"], out["buyability_score"]))
        self.assertLess(scores["STANFORD HOSPITAL"], 0.10)
        self.assertGreater(scores["REGIONAL MEDICAL CENTER"], 0.50)

    def test_batch_requires_taxonomy(self):
        df = pd.DataFrame([{"name": "X", "beds": 100}])
        with self.assertRaises(ValueError):
            score_buyability_batch(df)


class CompositeTests(unittest.TestCase):
    def test_target_attractiveness_multiplicative(self):
        # financial 0.8, buyable 0.5, strategic 1.0 → 0.4
        self.assertAlmostEqual(
            target_attractiveness(0.8, 0.5), 0.4, places=6,
        )

    def test_zero_buyability_kills_attractiveness(self):
        # Academic hospital with huge financial profile but
        # buyability ~0 → attractiveness ~0
        self.assertAlmostEqual(
            target_attractiveness(0.95, 0.02), 0.019, places=4,
        )

    def test_clamping(self):
        # Out-of-range inputs clamped to [0, 1]
        self.assertEqual(target_attractiveness(2.0, 0.5), 0.5)
        self.assertEqual(target_attractiveness(-0.5, 0.5), 0.0)

    def test_strategic_fit_third_factor(self):
        self.assertAlmostEqual(
            target_attractiveness(0.8, 0.5, strategic_fit=0.5),
            0.2, places=6,
        )

    def test_tier_thresholds(self):
        self.assertEqual(attractiveness_tier(0.40), "pursue")
        self.assertEqual(attractiveness_tier(0.20), "investigate")
        self.assertEqual(attractiveness_tier(0.08), "monitor")
        self.assertEqual(attractiveness_tier(0.01), "skip")


class DistributionTests(unittest.TestCase):
    def test_summarize_returns_segment_means(self):
        df = derive_taxonomy(pd.DataFrame([
            {"ccn": "050441", "name": "STANFORD HOSPITAL", "beds": 700,
             "medicare_day_pct": 40, "medicaid_day_pct": 10},
            {"ccn": "050442", "name": "STANFORD HEALTH CARE", "beds": 700,
             "medicare_day_pct": 40, "medicaid_day_pct": 10},
            {"ccn": "100100", "name": "REGIONAL MEDICAL CENTER",
             "beds": 250, "medicare_day_pct": 45, "medicaid_day_pct": 15},
            {"ccn": "100101", "name": "ANOTHER REGIONAL CENTER",
             "beds": 200, "medicare_day_pct": 45, "medicaid_day_pct": 15},
        ]))
        scored = score_buyability_batch(df)
        dist = summarize_distribution(scored)
        # Academic mean should be ~ Stanford prior (0.04), much
        # lower than Large Community mean
        academic_mean = dist.segment_means.get("Academic", 1.0)
        large_comm_mean = dist.segment_means.get("Large Community", 0.0)
        self.assertLess(academic_mean, 0.10)
        self.assertGreater(large_comm_mean, 0.50)

    def test_summarize_empty_frame(self):
        df = pd.DataFrame(columns=["buyability_score", "buyability_tier",
                                    "segment_label"])
        dist = summarize_distribution(df)
        self.assertEqual(dist.n, 0)
        self.assertEqual(dist.mean_score, 0.0)


if __name__ == "__main__":
    unittest.main()
