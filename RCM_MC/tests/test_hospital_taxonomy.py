"""Tests for the Phase-1 hospital taxonomy module.

Phase 1 of the regression rebuild (replacing the single blind OLS
that flattens academic / community / rural hospitals into one
slope per variable). These tests pin down the segment labels the
regression page will key off of, so future refactors of the
taxonomy can't silently change which rows land in the "Academic"
vs "Large Community" vs "Critical Access" buckets.
"""
import unittest

import pandas as pd

from rcm_mc.data.hospital_taxonomy import (
    derive_taxonomy,
    filter_to_universe,
    segment_counts,
    SEGMENT_LABELS,
    SEGMENT_PRECEDENCE,
)


def _row(ccn, name, beds, medicare_pct=40, medicaid_pct=15):
    return {
        "ccn": ccn,
        "name": name,
        "beds": beds,
        "medicare_day_pct": medicare_pct,
        "medicaid_day_pct": medicaid_pct,
    }


class TaxonomyFlagsTests(unittest.TestCase):
    """Pin the flag derivation for each known hospital archetype."""

    def setUp(self) -> None:
        # One row per regime we expect to surface separately. CCN
        # last-4-digits drive the facility-type classifier (general
        # = 0001-0879, CAH = 1300-1399, children = 3300-3399, etc.)
        self.df = pd.DataFrame([
            # Flagship academic medical centre
            _row("050441", "STANFORD HOSPITAL", 700, medicare_pct=42),
            # Flagship specialty cancer
            _row("450076", "M.D. ANDERSON CANCER CENTER", 700, medicare_pct=35),
            # Generic academic (UNIVERSITY keyword)
            _row("050001", "UNIVERSITY OF FOO MEDICAL CENTER", 500),
            # Large community
            _row("100100", "REGIONAL MEDICAL CENTER", 250),
            # Small community
            _row("220071", "MAIN STREET HOSPITAL", 50),
            # Critical access
            _row("191333", "TINY COUNTY HOSPITAL", 20),
            # Children's
            _row("053301", "CHILDRENS HOSPITAL OF SOMEWHERE", 200),
            # Psychiatric
            _row("054001", "STATE PSYCHIATRIC HOSPITAL", 150),
            # Safety-net community (high Medicaid)
            _row("120200", "URBAN COMMUNITY HOSPITAL", 200,
                 medicare_pct=30, medicaid_pct=45),
        ])
        self.tagged = derive_taxonomy(self.df)
        self.by_name = {r["name"]: r for _, r in self.tagged.iterrows()}

    def test_academic_flag_set_for_known_system(self):
        self.assertTrue(self.by_name["STANFORD HOSPITAL"]["academic_flag"])
        self.assertTrue(self.by_name["STANFORD HOSPITAL"]["teaching_flag"])

    def test_academic_flag_set_for_generic_university_name(self):
        self.assertTrue(
            self.by_name["UNIVERSITY OF FOO MEDICAL CENTER"]["academic_flag"]
        )

    def test_flagship_specialty_flag_distinct_from_academic(self):
        mda = self.by_name["M.D. ANDERSON CANCER CENTER"]
        self.assertTrue(mda["flagship_specialty_flag"])
        # M.D. Anderson isn't tagged academic by the curated list
        # because it's a specialty institution; segment_label picks
        # "Flagship Specialty" rather than "Academic".
        self.assertEqual(mda["segment_label"], "Flagship Specialty")

    def test_critical_access_flag_from_ccn_range(self):
        cah = self.by_name["TINY COUNTY HOSPITAL"]
        self.assertTrue(cah["critical_access_flag"])
        self.assertEqual(cah["segment_label"], "Critical Access")

    def test_children_flag_from_ccn_range(self):
        kid = self.by_name["CHILDRENS HOSPITAL OF SOMEWHERE"]
        self.assertTrue(kid["children_flag"])
        self.assertEqual(kid["segment_label"], "Children's")

    def test_psychiatric_flag_from_ccn_range(self):
        psy = self.by_name["STATE PSYCHIATRIC HOSPITAL"]
        self.assertTrue(psy["psychiatric_flag"])
        self.assertEqual(psy["segment_label"], "Psychiatric / Behavioral")

    def test_safety_net_proxy_from_medicaid_share(self):
        sn = self.by_name["URBAN COMMUNITY HOSPITAL"]
        self.assertTrue(sn["safety_net_proxy_flag"])
        self.assertEqual(sn["segment_label"], "Safety-Net Community")

    def test_segment_label_distinguishes_large_vs_small_community(self):
        self.assertEqual(
            self.by_name["REGIONAL MEDICAL CENTER"]["segment_label"],
            "Large Community",
        )
        self.assertEqual(
            self.by_name["MAIN STREET HOSPITAL"]["segment_label"],
            "Small Community",
        )

    def test_segment_label_academic_wins_over_size(self):
        # A 700-bed academic centre is "Academic", not "Large Community"
        self.assertEqual(
            self.by_name["STANFORD HOSPITAL"]["segment_label"],
            "Academic",
        )

    def test_size_class_buckets(self):
        self.assertEqual(self.by_name["TINY COUNTY HOSPITAL"]["size_class"],
                         "tier1_small")
        self.assertEqual(self.by_name["MAIN STREET HOSPITAL"]["size_class"],
                         "tier2_mid")
        self.assertEqual(self.by_name["REGIONAL MEDICAL CENTER"]["size_class"],
                         "tier3_large")
        self.assertEqual(self.by_name["STANFORD HOSPITAL"]["size_class"],
                         "tier4_mega")

    def test_payer_class_buckets(self):
        # 45% medicare → "mixed" (cuts: 25/50/70)
        self.assertEqual(
            self.by_name["MAIN STREET HOSPITAL"]["payer_class"],
            "mixed",
        )
        # 30% medicare → "mixed" too
        self.assertEqual(
            self.by_name["URBAN COMMUNITY HOSPITAL"]["payer_class"],
            "mixed",
        )


class FilterUniverseTests(unittest.TestCase):
    def setUp(self):
        rows = [
            _row("050441", "STANFORD HOSPITAL", 700),
            _row("450076", "MD ANDERSON CANCER CENTER", 700),
            _row("100100", "REGIONAL MEDICAL CENTER", 250),
            _row("220071", "MAIN STREET HOSPITAL", 50),
            _row("191333", "TINY COUNTY HOSPITAL", 20),
            _row("053301", "CHILDRENS HOSPITAL OF X", 200),
        ]
        self.tagged = derive_taxonomy(pd.DataFrame(rows))

    def test_all_universe_returns_everything(self):
        self.assertEqual(len(filter_to_universe(self.tagged, "all")),
                         len(self.tagged))

    def test_acquisition_targets_drops_academic_and_specialty(self):
        ats = filter_to_universe(self.tagged, "acquisition_targets")
        seg = set(ats["segment_label"])
        self.assertNotIn("Academic", seg)
        self.assertNotIn("Flagship Specialty", seg)
        self.assertNotIn("Children's", seg)
        # Community + CAH stay
        self.assertIn("Large Community", seg)
        self.assertIn("Small Community", seg)
        self.assertIn("Critical Access", seg)

    def test_academic_teaching_universe(self):
        at = filter_to_universe(self.tagged, "academic_teaching")
        seg = set(at["segment_label"])
        self.assertIn("Academic", seg)
        self.assertIn("Flagship Specialty", seg)
        # No community hospitals in this slice
        self.assertNotIn("Large Community", seg)

    def test_explicit_segment_label_filter(self):
        cah = filter_to_universe(self.tagged, "Critical Access")
        self.assertEqual(len(cah), 1)
        self.assertEqual(cah.iloc[0]["segment_label"], "Critical Access")

    def test_unknown_universe_defaults_to_all(self):
        result = filter_to_universe(self.tagged, "nonsense-name")
        # Unknown values fall back to "all" rather than throwing —
        # caller-facing universe strings come from a UI selector,
        # so default-to-all is safer than ValueError.
        self.assertEqual(len(result), len(self.tagged))


class SegmentCountsTests(unittest.TestCase):
    def test_counts_in_canonical_order(self):
        df = pd.DataFrame([
            _row("050441", "STANFORD HOSPITAL", 700),
            _row("050442", "STANFORD HEALTH CARE", 700),
            _row("191333", "TINY COUNTY", 20),
        ])
        counts = segment_counts(df)
        # Ordering matches SEGMENT_LABELS
        self.assertEqual(list(counts.index), SEGMENT_LABELS)
        self.assertEqual(counts["Academic"], 2)
        self.assertEqual(counts["Critical Access"], 1)
        # Segments with zero rows are filled in, not dropped
        self.assertEqual(counts["LTACH"], 0)


class EmptyFrameTests(unittest.TestCase):
    def test_derive_taxonomy_on_empty_frame_returns_typed_columns(self):
        empty = pd.DataFrame(columns=["ccn", "name", "beds"])
        out = derive_taxonomy(empty)
        for col in ("academic_flag", "teaching_flag",
                    "flagship_specialty_flag", "critical_access_flag",
                    "size_class", "payer_class", "segment_label"):
            self.assertIn(col, out.columns)
        self.assertEqual(len(out), 0)


class PrecedenceTests(unittest.TestCase):
    """Reviewer point #3: when a hospital matches multiple flags
    (academic + large + safety-net + system-affiliated) the label
    must be deterministic and follow the documented hierarchy.
    SEGMENT_PRECEDENCE is the single source of truth.
    """

    def test_precedence_constant_matches_implementation(self):
        # Build one row per precedence-level label and confirm that
        # adding a higher-level flag overrides a lower-level one.
        # A 500-bed academic centre with high Medicaid share matches:
        #   teaching_flag, academic_flag, safety_net_proxy_flag,
        #   Large Community (by beds). Expected label: "Academic"
        #   (higher precedence than Teaching / Safety-Net Community
        #   / Large Community).
        df = pd.DataFrame([{
            "ccn": "050001",  # general (academic by name)
            "name": "STANFORD HOSPITAL",
            "beds": 500,
            "medicare_day_pct": 40,
            "medicaid_day_pct": 45,  # would otherwise mark safety-net
        }])
        tagged = derive_taxonomy(df)
        self.assertEqual(tagged.iloc[0]["segment_label"], "Academic")
        # The flags themselves all set — just the LABEL respects precedence
        self.assertTrue(tagged.iloc[0]["academic_flag"])
        self.assertTrue(tagged.iloc[0]["teaching_flag"])
        self.assertTrue(tagged.iloc[0]["safety_net_proxy_flag"])

    def test_flagship_specialty_beats_academic(self):
        # MD Anderson is the canonical case — flagship specialty
        # wins over academic even when both match.
        df = pd.DataFrame([{
            "ccn": "450076",
            "name": "MD ANDERSON UNIVERSITY CANCER CENTER",
            "beds": 700,
            "medicare_day_pct": 30,
            "medicaid_day_pct": 10,
        }])
        tagged = derive_taxonomy(df)
        self.assertTrue(tagged.iloc[0]["academic_flag"])
        self.assertTrue(tagged.iloc[0]["flagship_specialty_flag"])
        self.assertEqual(
            tagged.iloc[0]["segment_label"], "Flagship Specialty"
        )

    def test_children_beats_academic_and_large_community(self):
        # A children's hospital affiliated with a university is
        # "Children's" — partner reasons about it as a different
        # economic regime regardless of academic affiliation.
        df = pd.DataFrame([{
            "ccn": "053301",
            "name": "CHILDRENS HOSPITAL OF UNIVERSITY OF SOMEWHERE",
            "beds": 400,
            "medicare_day_pct": 5,
            "medicaid_day_pct": 50,
        }])
        tagged = derive_taxonomy(df)
        self.assertEqual(tagged.iloc[0]["segment_label"], "Children's")

    def test_critical_access_beats_teaching(self):
        # CAH precedence is intentionally above Teaching — a 20-bed
        # rural CAH that happens to host residents is still a CAH
        # for regression purposes (its economics are CAH-shaped).
        df = pd.DataFrame([{
            "ccn": "191333",
            "name": "TINY COUNTY TEACHING HOSPITAL",
            "beds": 20,
            "medicare_day_pct": 60,
            "medicaid_day_pct": 25,
        }])
        tagged = derive_taxonomy(df)
        self.assertTrue(tagged.iloc[0]["teaching_flag"])
        self.assertTrue(tagged.iloc[0]["critical_access_flag"])
        self.assertEqual(
            tagged.iloc[0]["segment_label"], "Critical Access"
        )

    def test_segment_precedence_constant_covers_all_labels(self):
        # SEGMENT_PRECEDENCE should mention every label the
        # implementation can emit (canary against the table getting
        # out of sync with derive_taxonomy).
        expected = {
            "Other", "Small Community", "Large Community",
            "Safety-Net Community", "Rehab", "LTACH",
            "Psychiatric / Behavioral", "Children's",
            "Critical Access", "Teaching", "Academic",
            "Flagship Specialty",
        }
        self.assertEqual(set(SEGMENT_PRECEDENCE), expected)
        # Ordering matters: most-specific must be last
        self.assertEqual(SEGMENT_PRECEDENCE[-1], "Flagship Specialty")
        self.assertEqual(SEGMENT_PRECEDENCE[0], "Other")


class NameNormalizationTests(unittest.TestCase):
    """Reviewer point #4: HCRIS names arrive with varying case,
    punctuation, and spacing. The taxonomy must tag all spelling
    variants of the same system consistently.
    """

    def test_stanford_variants_all_tag_academic(self):
        variants = [
            "STANFORD HEALTH CARE",
            "Stanford Health Care",          # mixed-case
            "stanford hospital",             # lower-case
            "STANFORD UNIVERSITY MEDICAL CENTER",
            "STANFORD HOSPITAL ",            # trailing whitespace
        ]
        df = pd.DataFrame([
            {"ccn": f"05000{i}", "name": n, "beds": 700,
             "medicare_day_pct": 40, "medicaid_day_pct": 10}
            for i, n in enumerate(variants)
        ])
        tagged = derive_taxonomy(df)
        self.assertTrue(tagged["academic_flag"].all(),
                        f"variants tagged: {tagged['academic_flag'].tolist()}")
        self.assertTrue((tagged["segment_label"] == "Academic").all())

    def test_ucsf_variants(self):
        df = pd.DataFrame([
            {"ccn": "050100", "name": "UCSF MEDICAL CENTER", "beds": 600,
             "medicare_day_pct": 35, "medicaid_day_pct": 15},
            {"ccn": "050101", "name": "ucsf medical center", "beds": 600,
             "medicare_day_pct": 35, "medicaid_day_pct": 15},
            {"ccn": "050102", "name": "UCSF Medical Center", "beds": 600,
             "medicare_day_pct": 35, "medicaid_day_pct": 15},
        ])
        tagged = derive_taxonomy(df)
        self.assertTrue(tagged["academic_flag"].all())

    def test_punctuation_does_not_break_match(self):
        # "M.D. ANDERSON" vs "MD ANDERSON" — both in the curated list
        df = pd.DataFrame([
            {"ccn": "450076", "name": "M.D. ANDERSON CANCER CENTER",
             "beds": 700, "medicare_day_pct": 30, "medicaid_day_pct": 10},
            {"ccn": "450077", "name": "MD ANDERSON CANCER CENTER",
             "beds": 700, "medicare_day_pct": 30, "medicaid_day_pct": 10},
        ])
        tagged = derive_taxonomy(df)
        self.assertTrue(tagged["flagship_specialty_flag"].all())


if __name__ == "__main__":
    unittest.main()
