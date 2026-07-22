import json
import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize

_PAYLOAD = {
    "npi": "1234567893",
    "firstName": "JANE", "middleName": "Q", "lastName": "DOE",
    "nationalProviderIdentifierType": 1,
    "newlyEnrolled": False,
    "specialty": {"specialtyDescription": "Internal Medicine",
                  "typeDescription": "Physicians",
                  "categoryReference": "Allopathic"},
    "isMaqi": False,
    "organizations": [
        {"prvdrOrgName": "ACME MEDICAL GROUP", "isFacilityBased": True,
         "apms": [{"apmId": "x"}], "virtualGroups": []},
        {"prvdrOrgName": "BETA CLINIC"},
    ],
    "futureShapeField": {"unknown": True},
}


class EligibilityNormalizeTests(unittest.TestCase):
    def _res(self):
        rec = {"kind": "eligibility", "npi": "1234567893", "year": "2025",
               "payload": _PAYLOAD}
        return normalize(get_endpoint("eligibility"), [rec])

    def test_clinician_row_composes_key_and_maps(self):
        res = self._res()
        row = res.rows["qpp_clinician"][0]
        self.assertEqual(row["npi_year"], "1234567893:2025")
        self.assertEqual(row["first_name"], "JANE")
        self.assertEqual(row["specialty_description"], "Internal Medicine")
        self.assertEqual(row["newly_enrolled"], "0")   # bool → "0"/"1"
        self.assertEqual(row["n_organizations"], "2")
        self.assertEqual(row["source_endpoint"], "eligibility")
        # The full payload survives verbatim in raw.
        self.assertEqual(json.loads(row["raw"])["futureShapeField"],
                         {"unknown": True})
        self.assertIn("1234567893", res.npis)
        self.assertIn("futureShapeField", res.unmapped)

    def test_organizations_fan_out_one_row_each(self):
        res = self._res()
        orgs = res.rows["qpp_organization"]
        self.assertEqual(len(orgs), 2)
        self.assertEqual(orgs[0]["org_key"], "1234567893:2025:0")
        self.assertEqual(orgs[0]["org_name"], "ACME MEDICAL GROUP")
        self.assertEqual(orgs[0]["facility_based"], "1")
        self.assertEqual(orgs[0]["apms_count"], "1")
        self.assertEqual(orgs[1]["org_name"], "BETA CLINIC")
        self.assertEqual(orgs[1]["apms_count"], "0")
        self.assertEqual(orgs[0]["source_endpoint"], "organizations")

    def test_missing_npi_is_skipped(self):
        res = normalize(get_endpoint("eligibility"),
                        [{"kind": "eligibility", "year": "2025",
                          "payload": {"firstName": "GHOST"}}])
        self.assertEqual(res.rows, {})


class BenchmarkNormalizeTests(unittest.TestCase):
    def test_benchmark_row_composes_key_and_maps(self):
        payload = {"measureId": "001", "performanceYear": 2025,
                   "benchmarkYear": 2023, "submissionMethod": "registry",
                   "status": "current", "isToppedOut": True,
                   "isInverse": False, "deciles": [10.0, 20.5, 30.0]}
        rec = {"kind": "benchmark", "year": "2025", "payload": payload}
        res = normalize(get_endpoint("benchmarks"), [rec])
        row = res.rows["qpp_benchmark"][0]
        self.assertEqual(row["benchmark_key"], "2025:001:registry:2023")
        self.assertEqual(row["measure_id"], "001")
        self.assertEqual(row["is_topped_out"], "1")
        self.assertEqual(json.loads(row["deciles"]), [10.0, 20.5, 30.0])
        self.assertEqual(row["source_endpoint"], "benchmarks")

    def test_missing_measure_id_is_skipped(self):
        rec = {"kind": "benchmark", "year": "2025",
               "payload": {"submissionMethod": "claims"}}
        res = normalize(get_endpoint("benchmarks"), [rec])
        self.assertEqual(res.rows, {})

    def test_performance_year_falls_back_to_fetch_year(self):
        rec = {"kind": "benchmark", "year": "2024",
               "payload": {"measureId": "047"}}
        res = normalize(get_endpoint("benchmarks"), [rec])
        row = res.rows["qpp_benchmark"][0]
        self.assertEqual(row["performance_year"], "2024")


if __name__ == "__main__":
    unittest.main()
