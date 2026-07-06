import unittest

from ..connector import BlsQcewConnector
from ..endpoints import get_endpoint
from ..tables import BlsQcewStore
from ..transport import QcewTransport
from .fakes import FakeQcew, area_48453_csv, industry_622_csv

_IND_622_PATH = "/cew/data/api/2025/4/industry/622.csv"
_IND_62_DEFAULT_PATH = "/cew/data/api/2025/4/industry/62.csv"
_AREA_48453_PATH = "/cew/data/api/2025/4/area/48453.csv"
_AREA_DEFAULT_PATH = "/cew/data/api/2025/4/area/US000.csv"


def _connector():
    return BlsQcewConnector(QcewTransport(min_interval_s=0.0),
                            sleep=lambda s: None)


class ConnectorTests(unittest.TestCase):
    def test_discover_lists_both_slice_kinds(self):
        keys = {s.key for s in _connector().discover()}
        self.assertEqual(keys, {"industry_area", "area_industry"})

    def test_fetch_is_single_step_no_cursor(self):
        fake = FakeQcew().add(_IND_622_PATH, industry_622_csv())
        step = _connector().fetch(get_endpoint("industry_area"),
                                  {"industry": "622", "year": 2025,
                                   "qtr": 4},
                                  opener=fake)
        self.assertIsNone(step.next_cursor)     # one slice = one step
        self.assertTrue(step.done)
        self.assertEqual(len(step.rows), 6)
        self.assertFalse(step.truncated)
        self.assertEqual(step.endpoint, "industry_area")
        self.assertEqual(step.path, _IND_622_PATH)
        self.assertEqual(step.params,
                         {"industry": "622", "year": "2025", "qtr": "4"})
        self.assertEqual(step.requests, 1)      # exactly one download
        self.assertEqual(len(fake.calls), 1)

    def test_fetch_defaults_to_pinned_latest_quarter(self):
        # No params at all → the pinned latest published quarter and the
        # default slice codes (industry 62 / area US000).
        fake = (FakeQcew()
                .add(_IND_62_DEFAULT_PATH, industry_622_csv())
                .add(_AREA_DEFAULT_PATH, area_48453_csv()))
        conn = _connector()
        step = conn.fetch("industry_area", opener=fake)
        self.assertIn("/2025/4/industry/62.csv", fake.calls[0])
        self.assertEqual(step.params["year"], "2025")
        self.assertEqual(step.params["qtr"], "4")
        conn.fetch("area_industry", opener=fake)
        self.assertIn("/2025/4/area/US000.csv", fake.calls[1])

    def test_fetch_area_slice(self):
        fake = FakeQcew().add(_AREA_48453_PATH, area_48453_csv())
        step = _connector().fetch("area_industry", {"area": "48453"},
                                  opener=fake)
        self.assertEqual(len(step.rows), 6)
        self.assertEqual(step.rows[0]["industry_code"], "10")

    def test_fetch_max_rows_caps_ingest(self):
        fake = FakeQcew().add(_IND_622_PATH, industry_622_csv())
        step = _connector().fetch("industry_area",
                                  {"industry": "622"}, max_rows=2,
                                  opener=fake)
        self.assertEqual(len(step.rows), 2)
        self.assertTrue(step.truncated)

    def test_fetch_all_is_uncapped(self):
        fake = FakeQcew().add(_AREA_48453_PATH, area_48453_csv())
        rows = _connector().fetch_all("area_industry", {"area": "48453"},
                                      opener=fake)
        self.assertEqual(len(rows), 6)

    def test_bad_qtr_fails_before_any_network_call(self):
        fake = FakeQcew()
        with self.assertRaises(ValueError) as ctx:
            _connector().fetch("industry_area",
                               {"industry": "622", "qtr": "5"}, opener=fake)
        self.assertIn("latest published quarter", str(ctx.exception))
        self.assertEqual(fake.calls, [])        # validation is pre-network

    def test_annual_qtr_a_is_rejected_with_pointer(self):
        fake = FakeQcew()
        with self.assertRaises(ValueError) as ctx:
            _connector().fetch("industry_area",
                               {"industry": "62", "qtr": "a"}, opener=fake)
        self.assertIn("annual-average", str(ctx.exception))
        self.assertEqual(fake.calls, [])

    def test_bad_codes_fail_before_any_network_call(self):
        fake = FakeQcew()
        with self.assertRaises(ValueError):
            _connector().fetch("industry_area",
                               {"industry": "62; DROP"}, opener=fake)
        with self.assertRaises(ValueError):
            _connector().fetch("area_industry",
                               {"area": "../etc"}, opener=fake)
        with self.assertRaises(ValueError):
            _connector().fetch("industry_area",
                               {"industry": "622", "year": "20x5"},
                               opener=fake)
        self.assertEqual(fake.calls, [])

    def test_wrong_slice_code_param_is_rejected(self):
        # --area on industry_area (and vice versa) must error, not
        # silently fetch the default slice.
        with self.assertRaises(ValueError):
            _connector().fetch("industry_area", {"area": "48453"},
                               opener=FakeQcew())
        with self.assertRaises(ValueError):
            _connector().fetch("area_industry", {"industry": "622"},
                               opener=FakeQcew())

    def test_unknown_dataset_key_raises(self):
        with self.assertRaises(KeyError):
            _connector().fetch("nope", opener=FakeQcew())

    def test_refresh_ingests_end_to_end_and_reports_counts(self):
        fake = FakeQcew().add(_IND_622_PATH, industry_622_csv())
        store = BlsQcewStore(":memory:")
        try:
            counts = _connector().refresh(
                store, "industry_area",
                {"industry": "622", "year": 2025, "qtr": 1 + 3},
                opener=fake)
            self.assertEqual(counts["dataset_id"], "bls_qcew_industry_area")
            self.assertEqual(counts["fetched"], 6)
            self.assertEqual(counts["upserted"], {"qcew_industry_area": 6})
            self.assertFalse(counts["truncated"])
            self.assertEqual(counts["unmapped_fields"], {})
            self.assertEqual(store.count("qcew_industry_area"), 6)
        finally:
            store.close()

    def test_refresh_is_idempotent(self):
        fake = FakeQcew().add(_IND_622_PATH, industry_622_csv())
        store = BlsQcewStore(":memory:")
        try:
            conn = _connector()
            for _ in range(2):
                conn.refresh(store, "industry_area",
                             {"industry": "622"}, opener=fake)
            self.assertEqual(store.count("qcew_industry_area"), 6)
        finally:
            store.close()

    def test_refresh_collapses_duplicate_source_lines(self):
        fake = FakeQcew().add(_IND_622_PATH,
                              industry_622_csv(duplicate_last_row=True))
        store = BlsQcewStore(":memory:")
        try:
            counts = _connector().refresh(store, "industry_area",
                                          {"industry": "622"}, opener=fake)
            self.assertEqual(counts["fetched"], 7)                # raw lines
            self.assertEqual(store.count("qcew_industry_area"), 6)  # unique
        finally:
            store.close()

    def test_cross_slice_overlap_keeps_both_datasets_complete(self):
        # The same physical observation (Travis County hospitals) arrives
        # through BOTH slices; the slice-prefixed key must keep each
        # dataset's rows intact instead of re-tagging source_endpoint.
        fake = (FakeQcew()
                .add(_IND_622_PATH, industry_622_csv())
                .add(_AREA_48453_PATH, area_48453_csv()))
        store = BlsQcewStore(":memory:")
        try:
            conn = _connector()
            conn.refresh(store, "industry_area", {"industry": "622"},
                         opener=fake)
            conn.refresh(store, "area_industry", {"area": "48453"},
                         opener=fake)
            self.assertEqual(store.count("qcew_industry_area"), 12)  # 6 + 6
            self.assertEqual(
                store.count("qcew_industry_area",
                            "source_endpoint = ?", ("industry_area",)), 6)
            self.assertEqual(
                store.count("qcew_industry_area",
                            "source_endpoint = ?", ("area_industry",)), 6)
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
