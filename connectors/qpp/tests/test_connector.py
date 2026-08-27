import unittest

from ..connector import QppConnector
from ..endpoints import get_endpoint
from ..transport import QppTransport
from .fakes import FakeQpp


def _conn(max_npis_per_step=25):
    t = QppTransport(min_interval_s=0.0)
    return QppConnector(t, max_npis_per_step=max_npis_per_step)


_CLIN = {
    "npi": "1234567893",
    "firstName": "JANE", "lastName": "DOE",
    "nationalProviderIdentifierType": 1,
    "specialty": {"specialtyDescription": "Internal Medicine"},
    "organizations": [{"prvdrOrgName": "ACME MEDICAL GROUP"}],
}


class EligibilityFetchTests(unittest.TestCase):
    def test_roster_is_required(self):
        conn = _conn()
        with self.assertRaises(ValueError):
            conn.fetch(get_endpoint("eligibility"), {}, opener=FakeQpp())

    def test_roster_drains_and_resumes(self):
        fake = FakeQpp()
        for i in range(5):
            fake.add_clinician(f"100000000{i}", dict(_CLIN, npi=f"100000000{i}"))
        conn = _conn(max_npis_per_step=2)
        spec = get_endpoint("eligibility")
        params = {"npis": ",".join(f"100000000{i}" for i in range(5)),
                  "year": "2025"}
        rows, cursor, steps = [], None, 0
        while True:
            res = conn.fetch(spec, params, cursor, opener=fake)
            rows.extend(res.rows)
            steps += 1
            if res.next_cursor is None:
                break
            cursor = res.next_cursor
        self.assertEqual(len(rows), 5)
        self.assertEqual(steps, 3)  # 2 + 2 + 1
        self.assertTrue(all(r["kind"] == "eligibility" for r in rows))
        self.assertTrue(all(r["year"] == "2025" for r in rows))

    def test_missing_npi_is_skipped_not_fatal(self):
        fake = FakeQpp().add_clinician("1234567893", _CLIN)
        conn = _conn()
        spec = get_endpoint("eligibility")
        res = conn.fetch(spec, {"npis": ["1234567893", "9999999999"]},
                         opener=fake)
        self.assertEqual(len(res.rows), 1)
        self.assertEqual(res.skipped_npis, ["9999999999"])
        self.assertIsNone(res.next_cursor)

    def test_organizations_spec_shares_the_eligibility_fetch(self):
        fake = FakeQpp().add_clinician("1234567893", _CLIN)
        conn = _conn()
        res = conn.fetch(get_endpoint("organizations"),
                         {"npis": "1234567893"}, opener=fake)
        self.assertEqual(len(res.rows), 1)
        self.assertEqual(res.rows[0]["payload"]["organizations"][0]
                         ["prvdrOrgName"], "ACME MEDICAL GROUP")


class BenchmarksFetchTests(unittest.TestCase):
    def test_single_request_returns_all_rows(self):
        fake = FakeQpp().add_benchmarks("2025", [
            {"measureId": "001", "submissionMethod": "registry",
             "deciles": [1, 2, 3]},
            {"measureId": "002", "submissionMethod": "claims"},
        ])
        conn = _conn()
        res = conn.fetch(get_endpoint("benchmarks"), {"year": "2025"},
                         opener=fake)
        self.assertIsNone(res.next_cursor)
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(res.requests, 1)
        self.assertTrue(all(r["kind"] == "benchmark" for r in res.rows))

    def test_default_year_comes_from_the_spec(self):
        fake = FakeQpp().add_benchmarks("2025", [{"measureId": "001"}])
        conn = _conn()
        res = conn.fetch(get_endpoint("benchmarks"), {}, opener=fake)
        self.assertEqual(res.year, "2025")
        self.assertEqual(len(res.rows), 1)


if __name__ == "__main__":
    unittest.main()
