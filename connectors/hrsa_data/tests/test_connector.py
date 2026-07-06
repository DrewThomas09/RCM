import unittest

from ..connector import HrsaDataConnector
from ..endpoints import get_endpoint
from ..tables import HrsaDataStore
from ..transport import HrsaTransport
from .fakes import FakeHrsa, hpsa_pc_csv, mua_csv, sites_csv

_PC_PATH = "/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
_MUA_PATH = "/DataDownload/DD_Files/MUA_DET.csv"
_SITES_PATH = "/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.csv"


def _connector():
    return HrsaDataConnector(HrsaTransport(min_interval_s=0.0),
                             sleep=lambda s: None)


class ConnectorTests(unittest.TestCase):
    def test_discover_lists_all_five_files(self):
        keys = {s.key for s in _connector().discover()}
        self.assertEqual(keys, {"hpsa_primary_care", "hpsa_dental",
                                "hpsa_mental_health", "mua",
                                "health_center_sites"})

    def test_fetch_is_single_step_no_cursor(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        step = _connector().fetch(get_endpoint("hpsa_primary_care"),
                                  opener=fake)
        self.assertIsNone(step.next_cursor)     # one file = one step
        self.assertTrue(step.done)
        self.assertEqual(len(step.rows), 3)
        self.assertFalse(step.truncated)
        self.assertEqual(step.endpoint, "hpsa_primary_care")
        self.assertEqual(step.requests, 1)      # exactly one download
        self.assertEqual(len(fake.calls), 1)

    def test_fetch_accepts_key_string(self):
        fake = FakeHrsa().add(_MUA_PATH, mua_csv())
        step = _connector().fetch("mua", opener=fake)
        self.assertEqual(len(step.rows), 3)

    def test_fetch_max_rows_caps_ingest(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        step = _connector().fetch("hpsa_primary_care", max_rows=1, opener=fake)
        self.assertEqual(len(step.rows), 1)
        self.assertTrue(step.truncated)

    def test_fetch_all_is_uncapped(self):
        fake = FakeHrsa().add(_SITES_PATH, sites_csv())
        rows = _connector().fetch_all("health_center_sites", opener=fake)
        self.assertEqual(len(rows), 2)

    def test_refresh_ingests_end_to_end_and_reports_counts(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        store = HrsaDataStore(":memory:")
        try:
            counts = _connector().refresh(store, "hpsa_primary_care",
                                          opener=fake)
            self.assertEqual(counts["dataset_id"], "hrsa_data_hpsa_primary_care")
            self.assertEqual(counts["fetched"], 3)
            self.assertEqual(counts["upserted"], {"hrsa_hpsa": 3})
            self.assertFalse(counts["truncated"])
            self.assertEqual(counts["unmapped_fields"], {})
            self.assertEqual(store.count("hrsa_hpsa"), 3)
        finally:
            store.close()

    def test_refresh_collapses_duplicate_source_lines(self):
        # The live HPSA files contain a handful of byte-identical duplicate
        # lines; the composed key + upsert must collapse them.
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv(duplicate_last_row=True))
        store = HrsaDataStore(":memory:")
        try:
            counts = _connector().refresh(store, "hpsa_primary_care",
                                          opener=fake)
            self.assertEqual(counts["fetched"], 4)          # raw lines
            self.assertEqual(store.count("hrsa_hpsa"), 3)   # unique rows
        finally:
            store.close()

    def test_unknown_dataset_key_raises(self):
        with self.assertRaises(KeyError):
            _connector().fetch("nope", opener=FakeHrsa())


if __name__ == "__main__":
    unittest.main()
