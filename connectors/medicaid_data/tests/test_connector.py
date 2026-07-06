import unittest

from ..connector import MedicaidDataConnector
from ..endpoints import get_endpoint
from ..tables import MedicaidDataStore
from ..transport import MedicaidDataTransport
from .fakes import (NADAC_2026_ID, SDUD_2025_ID, FakeMedicaidData,
                    catalog_item, nadac_row, sdud_row)


def _connector(page_limit=2):
    return MedicaidDataConnector(
        MedicaidDataTransport(min_interval_s=0.0), page_limit=page_limit)


def _nadac_rows(n):
    return [nadac_row(ndc=f"0000000000{i}", as_of=f"2026-01-0{i + 1}")
            for i in range(n)]


class ConnectorTests(unittest.TestCase):
    def test_discover_returns_catalog_items(self):
        fake = FakeMedicaidData().add_catalog(
            [catalog_item(), catalog_item("abc-123", "State Drug Utilization "
                                          "Data 2025", "State Drug Utilization")])
        items = _connector().discover(opener=fake)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["identifier"], NADAC_2026_ID)
        self.assertEqual(len(fake.calls), 1)   # one call syncs everything

    def test_endpoints_enumerates_registered_specs(self):
        keys = {s.key for s in _connector().endpoints()}
        self.assertIn("catalog", keys)
        self.assertIn("nadac_2026", keys)
        self.assertIn("sdud_2024", keys)
        self.assertIn("fetched_rows", keys)

    def test_fetch_pages_by_offset_and_stops(self):
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, _nadac_rows(5))
        conn = _connector(page_limit=2)
        spec = get_endpoint("nadac_2026")

        rows, cursor, steps = [], None, 0
        while True:
            step = conn.fetch(spec, cursor=cursor, opener=fake)
            rows.extend(step.rows)
            steps += 1
            if step.next_cursor is None:
                break
            cursor = step.next_cursor
            self.assertIn("offset", cursor)

        self.assertEqual(len(rows), 5)          # every record, no duplicates
        self.assertEqual(steps, 3)              # 2 + 2 + 1 pages
        self.assertEqual({r["ndc"] for r in rows},
                         {f"0000000000{i}" for i in range(5)})
        self.assertEqual(step.total, 5)

    def test_fetch_all_respects_max_pages_guard(self):
        # 5 records, 2/page → a full drain needs 3 pages; cap at 2.
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, _nadac_rows(5))
        conn = _connector(page_limit=2)
        rows = conn.fetch_all(get_endpoint("nadac_2026"), opener=fake,
                              max_pages=2)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len(fake.calls), 2)

    def test_fetch_all_drains_when_pages_suffice(self):
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, _nadac_rows(3))
        rows = _connector(page_limit=2).fetch_all(
            get_endpoint("nadac_2026"), opener=fake, max_pages=5)
        self.assertEqual(len(rows), 3)

    def test_fetch_pushes_equality_filters_down_as_conditions(self):
        fake = FakeMedicaidData().add_datastore(SDUD_2025_ID, [
            sdud_row(state="AK"), sdud_row(state="AL", ndc="99999999999")])
        conn = _connector(page_limit=10)
        step = conn.fetch(get_endpoint("sdud_2025"),
                          {"filters": {"state": "AL"}}, opener=fake)
        self.assertEqual(len(step.rows), 1)
        self.assertEqual(step.rows[0]["state"], "AL")
        self.assertIn("conditions", fake.calls[0])   # pushed to the API

    def test_fetch_dataset_reaches_arbitrary_uuid(self):
        fake = FakeMedicaidData().add_datastore("some-random-uuid",
                                                [{"a": "1"}, {"a": "2"}])
        step = _connector(page_limit=10).fetch_dataset("some-random-uuid",
                                                       opener=fake)
        self.assertEqual(len(step.rows), 2)
        self.assertIsNone(step.next_cursor)

    def test_fetch_generic_spec_directly_is_an_error(self):
        with self.assertRaises(ValueError):
            _connector().fetch(get_endpoint("fetched_rows"))

    def test_refresh_catalog_lands_rows(self):
        fake = FakeMedicaidData().add_catalog([catalog_item()])
        store = MedicaidDataStore(":memory:")
        counts = _connector().refresh_catalog(store, opener=fake)
        self.assertEqual(counts, {"fetched": 1, "written": 1})
        self.assertEqual(store.count("medicaid_data_catalog"), 1)
        store.close()

    def test_refresh_curated_and_rerun_is_idempotent(self):
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, _nadac_rows(3))
        store = MedicaidDataStore(":memory:")
        conn = _connector(page_limit=2)
        counts = conn.refresh(store, "nadac_2026", opener=fake, max_pages=5)
        self.assertEqual(counts, {"fetched": 3, "written": 3})
        # Re-running the same refresh must not double-count (upsert keys).
        conn.refresh(store, "nadac_2026", opener=fake, max_pages=5)
        self.assertEqual(store.count("medicaid_nadac"), 3)
        slice_count = store.count("medicaid_nadac", "source_endpoint = ?",
                                  ("nadac_2026",))
        self.assertEqual(slice_count, 3)
        store.close()

    def test_refresh_unknown_key_lands_generic_rows(self):
        fake = FakeMedicaidData().add_datastore("uuid-xyz",
                                                [{"a": "1"}, {"a": "2"},
                                                 {"a": "3"}])
        store = MedicaidDataStore(":memory:")
        counts = _connector(page_limit=2).refresh(store, "uuid-xyz",
                                                  opener=fake, max_pages=5)
        self.assertEqual(counts, {"fetched": 3, "written": 3})
        # Absolute row_idx across pages → re-running stays idempotent.
        counts2 = _connector(page_limit=2).refresh(store, "uuid-xyz",
                                                   opener=fake, max_pages=5)
        self.assertEqual(counts2["written"], 3)
        self.assertEqual(store.count("medicaid_data_rows"), 3)
        keys = {r["row_key"] for r in store.fetchall(
            "SELECT row_key FROM medicaid_data_rows")}
        self.assertEqual(keys, {"uuid-xyz:0", "uuid-xyz:1", "uuid-xyz:2"})
        store.close()


if __name__ == "__main__":
    unittest.main()
