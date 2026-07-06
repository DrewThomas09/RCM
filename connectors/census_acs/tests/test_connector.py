import unittest

from ..connector import CensusAcsConnector
from ..endpoints import get_endpoint
from ..tables import CensusAcsStore
from ..transport import CensusAcsTransport
from .fakes import FakeCensusApi


def _connector():
    return CensusAcsConnector(CensusAcsTransport(min_interval_s=0.0))


class ConnectorTests(unittest.TestCase):
    def test_discover_lists_profiles(self):
        keys = {s.key for s in _connector().discover()}
        self.assertEqual(
            keys, {"county_profile", "state_profile", "cbsa_profile"})

    def test_fetch_county_issues_detail_and_subject_calls(self):
        fake = FakeCensusApi.with_defaults()
        res = _connector().fetch("county_profile", year=2023, state="48",
                                 opener=fake)
        self.assertEqual(res.requests, 2)               # one detail + one subject
        self.assertEqual(len(fake.calls), 2)
        self.assertIn("/2023/acs/acs5?", fake.calls[0])
        self.assertIn("/2023/acs/acs5/subject?", fake.calls[1])
        self.assertIn("in=state%3A48", fake.calls[0])   # state narrows via in=
        self.assertIsNone(res.next_cursor)              # ACS is unpaged
        self.assertEqual(len(res.detail), 4)            # header + 3 counties
        self.assertEqual(len(res.subject), 3)           # header + 2 counties

    def test_fetch_accepts_spec_or_key_or_dataset_id(self):
        fake = FakeCensusApi.with_defaults()
        spec = get_endpoint("state_profile")
        by_spec = _connector().fetch(spec, opener=fake)
        by_id = _connector().fetch("census_acs_state_profile",
                                   opener=FakeCensusApi.with_defaults())
        self.assertEqual(by_spec.detail, by_id.detail)

    def test_fetch_state_profile_narrows_for_clause(self):
        fake = FakeCensusApi.with_defaults()
        res = _connector().fetch("state_profile", state="48", opener=fake)
        self.assertIn("for=state%3A48", fake.calls[0])
        # Only Texas survives the fake's state filter.
        self.assertEqual(len(res.detail), 2)
        self.assertEqual(res.detail[1][0], "Texas")

    def test_fetch_cbsa_uses_verified_geography_string(self):
        fake = FakeCensusApi.with_defaults()
        res = _connector().fetch("cbsa_profile", opener=fake)
        self.assertIn(
            "for=metropolitan+statistical+area%2F"
            "micropolitan+statistical+area%3A%2A", fake.calls[0])
        self.assertEqual(len(res.detail), 3)            # header + 2 CBSAs

    def test_fetch_cbsa_rejects_state_filter(self):
        with self.assertRaises(ValueError):
            _connector().fetch("cbsa_profile", state="48",
                               opener=FakeCensusApi.with_defaults())

    def test_refresh_fetches_normalizes_and_upserts(self):
        fake = FakeCensusApi.with_defaults()
        store = CensusAcsStore(":memory:")
        try:
            summary = _connector().refresh(store, "county_profile",
                                           year=2023, opener=fake)
            self.assertEqual(summary["dataset_id"], "census_acs_county_profile")
            self.assertEqual(summary["year"], 2023)
            self.assertEqual(summary["fetched"], 3)
            self.assertEqual(summary["upserted"], {"census_acs_county": 3})
            self.assertEqual(store.count("census_acs_county"), 3)

            # Re-running the same vintage is idempotent (upsert, not insert).
            _connector().refresh(store, "county_profile", year=2023,
                                 opener=FakeCensusApi.with_defaults())
            self.assertEqual(store.count("census_acs_county"), 3)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
