"""Tests for the denial-type → root-cause + initiative taxonomy.

`rcm_mc/infra/taxonomy.py` is the simulator's heuristic mapping
from raw denial_type strings (e.g. 'auth_missing', 'eligibility',
'late_filing') into 7 standardized root-cause buckets, plus a
lookup from root-cause → recommended Initiative(s) from the
INITIATIVE_LIBRARY.

Used by pe/breakdowns + the analysis workbench to drive the
'why is this denial happening?' panel. Both functions had no
direct test coverage despite gating which initiative cards the
partner sees on a given deal.
"""
from __future__ import annotations

import unittest

from rcm_mc.infra.taxonomy import (
    INITIATIVE_LIBRARY,
    ROOT_CAUSE_DESCRIPTIONS,
    Initiative,
    infer_root_cause,
    recommended_initiatives_for_root_cause,
)


class InferRootCauseTests(unittest.TestCase):
    """Heuristic mapping denial_type → 1 of 7 standardized buckets."""

    def test_authorization_variants(self):
        # Any string containing 'auth', 'prior', 'oonauth',
        # 'out-of-network', or 'oon' maps to 'authorization'.
        for s in ("auth_missing", "prior_auth", "oonauth",
                  "out-of-network", "oon_referral",
                  "AUTHORIZATION_REQUIRED"):
            self.assertEqual(infer_root_cause(s), "authorization",
                              f"failed for {s!r}")

    def test_eligibility_variants(self):
        for s in ("eligibility", "coverage_lapsed", "cob_issue",
                  "benefit_mismatch", "member_id_invalid"):
            self.assertEqual(infer_root_cause(s), "eligibility",
                              f"failed for {s!r}")

    def test_coding_variants(self):
        for s in ("code_error", "coding_issue", "modifier_missing",
                  "drg_dispute", "apc_mismatch", "charge_capture"):
            self.assertEqual(infer_root_cause(s), "coding",
                              f"failed for {s!r}")

    def test_medical_necessity_variants(self):
        for s in ("clinical_review", "med_necessity",
                  "necessity_dispute", "loc_review",
                  "validation_pending"):
            self.assertEqual(infer_root_cause(s),
                              "medical_necessity",
                              f"failed for {s!r}")

    def test_timely_filing_variants(self):
        for s in ("timely_filing", "late_submission",
                  "deadline_miss"):
            self.assertEqual(infer_root_cause(s),
                              "timely_filing",
                              f"failed for {s!r}")

    def test_other_admin_variants(self):
        for s in ("admin_error", "format_issue", "duplicate_claim",
                  "missing_info"):
            self.assertEqual(infer_root_cause(s), "other_admin",
                              f"failed for {s!r}")

    def test_unknown_string_returns_other(self):
        self.assertEqual(infer_root_cause("unrecognized_thing"),
                          "other")
        self.assertEqual(infer_root_cause("xyz"), "other")

    def test_empty_string_returns_other(self):
        self.assertEqual(infer_root_cause(""), "other")

    def test_none_safe(self):
        # str(None or "") = "" → 'other'. Defensive against
        # missing data.
        self.assertEqual(infer_root_cause(None), "other")  # type: ignore

    def test_case_insensitive(self):
        self.assertEqual(infer_root_cause("AUTH"), "authorization")
        self.assertEqual(infer_root_cause("Coding"), "coding")
        self.assertEqual(infer_root_cause("eLiGiBiLiTy"),
                          "eligibility")

    def test_whitespace_stripped(self):
        self.assertEqual(infer_root_cause("  auth  "), "authorization")

    def test_priority_order_first_match_wins(self):
        # If a string matches multiple categories, the first check
        # wins. 'auth' is checked before 'coding' → 'authorization'.
        self.assertEqual(infer_root_cause("auth_code_dispute"),
                          "authorization")


class RecommendedInitiativesForRootCauseTests(unittest.TestCase):
    """Look up Initiative objects by root cause."""

    def test_authorization_includes_pa_automation(self):
        out = recommended_initiatives_for_root_cause("authorization")
        codes = [i.code for i in out]
        self.assertIn("PA_AUTOMATION", codes)
        # WORKQUEUE_RPA covers authorization too
        self.assertIn("WORKQUEUE_RPA", codes)

    def test_eligibility_includes_pa_automation(self):
        out = recommended_initiatives_for_root_cause("eligibility")
        codes = [i.code for i in out]
        self.assertIn("PA_AUTOMATION", codes)
        self.assertIn("WORKQUEUE_RPA", codes)

    def test_coding_includes_cdi_and_workqueue(self):
        out = recommended_initiatives_for_root_cause("coding")
        codes = [i.code for i in out]
        self.assertIn("CDI_CODING", codes)
        self.assertIn("WORKQUEUE_RPA", codes)

    def test_medical_necessity_includes_cdi(self):
        out = recommended_initiatives_for_root_cause(
            "medical_necessity")
        codes = [i.code for i in out]
        self.assertIn("CDI_CODING", codes)

    def test_timely_filing_only_workqueue(self):
        # timely_filing only matches WORKQUEUE_RPA in
        # primary_root_causes.
        out = recommended_initiatives_for_root_cause("timely_filing")
        codes = [i.code for i in out]
        self.assertEqual(codes, ["WORKQUEUE_RPA"])

    def test_other_admin_includes_contract_recovery(self):
        # other_admin matches WORKQUEUE_RPA + CONTRACT_RECOVERY.
        out = recommended_initiatives_for_root_cause("other_admin")
        codes = [i.code for i in out]
        self.assertIn("WORKQUEUE_RPA", codes)
        self.assertIn("CONTRACT_RECOVERY", codes)

    def test_unknown_root_cause_falls_back_to_workqueue(self):
        # Unrecognized root_cause → universal fallback to
        # WORKQUEUE_RPA (so partner always sees AT LEAST one
        # initiative card).
        out = recommended_initiatives_for_root_cause(
            "unrecognized_cause")
        codes = [i.code for i in out]
        self.assertEqual(codes, ["WORKQUEUE_RPA"])

    def test_other_falls_back_to_workqueue(self):
        out = recommended_initiatives_for_root_cause("other")
        codes = [i.code for i in out]
        self.assertEqual(codes, ["WORKQUEUE_RPA"])

    def test_returns_initiative_dataclass_objects(self):
        out = recommended_initiatives_for_root_cause("authorization")
        for i in out:
            self.assertIsInstance(i, Initiative)
            self.assertTrue(i.code)
            self.assertTrue(i.title)
            self.assertIsInstance(i.primary_root_causes, list)

    def test_none_safe(self):
        # None → 'other' → fallback. Defensive.
        out = recommended_initiatives_for_root_cause(None)  # type: ignore
        codes = [i.code for i in out]
        self.assertEqual(codes, ["WORKQUEUE_RPA"])

    def test_case_insensitive(self):
        out_lower = recommended_initiatives_for_root_cause("authorization")
        out_upper = recommended_initiatives_for_root_cause("AUTHORIZATION")
        self.assertEqual(
            [i.code for i in out_lower],
            [i.code for i in out_upper],
        )


class LibraryAndDescriptionsContract(unittest.TestCase):
    """Locks the structural contract on INITIATIVE_LIBRARY +
    ROOT_CAUSE_DESCRIPTIONS so additions/removals are intentional."""

    def test_root_cause_descriptions_cover_all_buckets(self):
        # The 7 root-cause buckets that infer_root_cause can emit
        # MUST all have a description string.
        expected = {"authorization", "eligibility", "coding",
                    "medical_necessity", "timely_filing",
                    "other_admin", "other"}
        self.assertTrue(
            expected.issubset(set(ROOT_CAUSE_DESCRIPTIONS.keys())),
            "infer_root_cause emits a bucket without a description: "
            f"{expected - set(ROOT_CAUSE_DESCRIPTIONS.keys())}",
        )

    def test_initiative_library_codes_unique(self):
        codes = [i.code for i in INITIATIVE_LIBRARY.values()]
        self.assertEqual(len(codes), len(set(codes)))

    def test_initiative_library_codes_match_dict_keys(self):
        # Convention: each entry's code == its dict key.
        for key, init in INITIATIVE_LIBRARY.items():
            self.assertEqual(init.code, key)

    def test_initiative_time_to_impact_positive(self):
        for init in INITIATIVE_LIBRARY.values():
            self.assertGreater(init.typical_time_to_impact_months, 0,
                                f"{init.code}")

    def test_initiative_root_causes_are_valid(self):
        # Every primary_root_cause string on every initiative MUST
        # be in the ROOT_CAUSE_DESCRIPTIONS keys (otherwise it would
        # never match a real infer_root_cause output).
        valid = set(ROOT_CAUSE_DESCRIPTIONS.keys())
        for init in INITIATIVE_LIBRARY.values():
            for rc in init.primary_root_causes:
                self.assertIn(
                    rc, valid,
                    f"Initiative {init.code} references unknown "
                    f"root cause {rc!r}")


if __name__ == "__main__":
    unittest.main()
