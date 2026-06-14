"""ClinicalTrials.gov v2 normalization + competitive-landscape rollup.

Pure functions over already-fetched study dicts — no network. Fixtures mirror
the real v2 ``protocolSection`` nesting so the normalizer is exercised against
the actual shape, including missing fields and multi-phase studies.
"""
from __future__ import annotations

import unittest

from rcm_mc.data_public import clinical_trials_v2 as ct


def _study(nct, sponsor, phases, status="RECRUITING", enrollment=None,
           conditions=None, title="A Study"):
    design = {"phases": phases}
    if enrollment is not None:
        design["enrollmentInfo"] = {"count": enrollment}
    return {
        "protocolSection": {
            "identificationModule": {"nctId": nct, "briefTitle": title},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": sponsor}},
            "designModule": design,
            "statusModule": {"overallStatus": status},
            "conditionsModule": {"conditions": conditions or []},
        }
    }


class NormalizeTests(unittest.TestCase):
    def test_flattens_nested_v2_shape(self):
        rec = ct.clinicaltrials_normalize(
            _study("NCT01", "Acme Bio", ["PHASE2"], enrollment=120,
                   conditions=["Psoriasis"]))
        self.assertEqual(rec["nct_id"], "NCT01")
        self.assertEqual(rec["sponsor"], "Acme Bio")
        self.assertEqual(rec["phase"], "PHASE2")
        self.assertEqual(rec["status"], "RECRUITING")
        self.assertEqual(rec["enrollment"], 120)
        self.assertEqual(rec["conditions"], ["Psoriasis"])

    def test_multi_phase_kept_as_joined_string(self):
        rec = ct.clinicaltrials_normalize(
            _study("NCT02", "Acme Bio", ["PHASE2", "PHASE3"]))
        self.assertEqual(rec["phase"], "PHASE2|PHASE3")

    def test_missing_fields_normalize_not_fabricate(self):
        rec = ct.clinicaltrials_normalize({"protocolSection": {}})
        self.assertEqual(rec["nct_id"], "")
        self.assertEqual(rec["sponsor"], "")
        self.assertEqual(rec["conditions"], [])
        self.assertIsNone(rec["enrollment"])

    def test_negative_or_bad_enrollment_is_none(self):
        bad = ct.clinicaltrials_normalize(_study("NCT03", "X", ["PHASE1"],
                                                 enrollment=-5))
        self.assertIsNone(bad["enrollment"])


class LandscapeTests(unittest.TestCase):
    def _studies(self):
        return [
            _study("NCT01", "Acme Bio", ["PHASE2"], enrollment=100),
            _study("NCT02", "Acme Bio", ["PHASE3"], enrollment=200),
            _study("NCT03", "Beta Therapeutics", ["PHASE1"], enrollment=50),
        ]

    def test_rolls_up_by_sponsor_sorted_by_trials(self):
        rows = ct.clinicaltrials_landscape(self._studies())
        self.assertEqual(rows[0]["sponsor"], "Acme Bio")
        self.assertEqual(rows[0]["trials"], 2)
        self.assertEqual(rows[0]["total_enrollment"], 300)
        self.assertEqual(rows[0]["by_phase"], {"PHASE2": 1, "PHASE3": 1})
        self.assertEqual(rows[1]["sponsor"], "Beta Therapeutics")
        self.assertEqual(rows[1]["trials"], 1)

    def test_missing_enrollment_stays_none_not_zero(self):
        rows = ct.clinicaltrials_landscape([
            _study("NCT04", "NoCount Inc", ["PHASE1"]),  # no enrollment
        ])
        self.assertIsNone(rows[0]["total_enrollment"])

    def test_unknown_sponsor_and_no_phase_are_labeled(self):
        rows = ct.clinicaltrials_landscape([
            {"protocolSection": {"designModule": {}}},  # no sponsor, no phase
        ])
        self.assertEqual(rows[0]["sponsor"], "(unknown sponsor)")
        self.assertEqual(rows[0]["by_phase"], {"(no phase)": 1})

    def test_empty_input_is_empty_rollup(self):
        self.assertEqual(ct.clinicaltrials_landscape([]), [])


class FetchLandscapeTests(unittest.TestCase):
    def test_fetch_then_rollup_via_injected_opener(self):
        import json

        payload = {"studies": [
            _study("NCT01", "Acme Bio", ["PHASE2"], enrollment=100),
            _study("NCT02", "Acme Bio", ["PHASE3"], enrollment=200),
        ]}

        def opener(url, headers, timeout):
            assert "clinicaltrials.gov/api/v2/studies" in url
            return json.dumps(payload).encode()

        rows = ct.fetch_landscape(condition="psoriasis", opener=opener)
        self.assertEqual(rows[0]["sponsor"], "Acme Bio")
        self.assertEqual(rows[0]["trials"], 2)
        self.assertEqual(rows[0]["total_enrollment"], 300)


if __name__ == "__main__":
    unittest.main()
