import unittest

from ..connector import ProviderDataConnector
from ..endpoints import ENDPOINTS
from ..tables import ProviderDataStore
from ..transport import ProviderDataTransport
from .fakes import (FakeProviderData, catalog_items, generic_hai_rows,
                    hospital_rows)


def _connector(**kw):
    return ProviderDataConnector(
        ProviderDataTransport(min_interval_s=0.0), **kw)


class DiscoverTests(unittest.TestCase):
    def test_discover_returns_normalized_catalog_rows(self):
        fake = FakeProviderData().add_catalog(catalog_items())
        rows = _connector().discover(opener=fake)
        self.assertEqual(len(rows), 3)
        by_id = {r["identifier"]: r for r in rows}
        hosp = by_id["xubh-q36u"]
        self.assertEqual(hosp["title"], "Hospital General Information")
        self.assertEqual(hosp["themes"], "Hospitals")
        self.assertIn("hospital_general.csv", hosp["csv_url"])
        self.assertEqual(hosp["source_endpoint"], "catalog")
        # Entry without a distribution degrades to a NULL csv_url.
        self.assertIsNone(by_id["77hc-ibv8"]["csv_url"])

    def test_registered_endpoints_cover_all_three_kinds(self):
        kinds = {s.kind for s in _connector().endpoints()}
        self.assertEqual(kinds, {"catalog", "curated", "generic"})
        self.assertEqual(len(ENDPOINTS), 20)   # catalog + 18 curated + generic


class ResolveTests(unittest.TestCase):
    def test_resolves_key_dataset_id_and_identifier(self):
        conn = _connector()
        spec, ident = conn.resolve("hospital_general")
        self.assertEqual((spec.key, ident), ("hospital_general", "xubh-q36u"))
        spec, ident = conn.resolve("provider_data_hospital_general")
        self.assertEqual(spec.key, "hospital_general")
        # A raw 4x4 identifier falls through to the generic spec.
        spec, ident = conn.resolve("77hc-ibv8")
        self.assertEqual((spec.key, ident), ("fetched_rows", "77hc-ibv8"))

    def test_unknown_dataset_raises(self):
        with self.assertRaises(KeyError):
            _connector().resolve("not_a_dataset")
        with self.assertRaises(KeyError):
            _connector().fetch("fetched_rows")   # needs a concrete 4x4 id


class FetchTests(unittest.TestCase):
    def test_fetch_absorbs_limit_offset_paging(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(5))
        res = _connector().fetch("hospital_general", opener=fake, page_size=2)
        self.assertEqual(len(res.rows), 5)      # every record, no duplicates
        self.assertEqual(res.pages, 3)          # 2 + 2 + 1
        self.assertEqual(res.total, 5)
        self.assertFalse(res.truncated)
        self.assertEqual({r["facility_id"] for r in res.rows},
                         {f"01000{i}" for i in range(5)})

    def test_fetch_stops_at_max_pages_and_flags_truncation(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(5))
        res = _connector().fetch("hospital_general", opener=fake,
                                 page_size=2, max_pages=1)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)          # 3 more rows were available
        self.assertEqual(len(fake.calls), 1)    # the cap really capped requests

    def test_fetch_sends_equality_conditions_serverside(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(5))
        res = _connector().fetch("hospital_general", opener=fake,
                                 conditions={"state": "TX"})
        self.assertEqual({r["state"] for r in res.rows}, {"TX"})
        self.assertEqual(res.total, 2)          # count reflects the filter
        self.assertIn("conditions%5B0%5D%5Bproperty%5D=state", fake.calls[0])

    def test_fetch_dataset_generic_by_identifier(self):
        fake = FakeProviderData().add("77hc-ibv8", generic_hai_rows(4))
        res = _connector().fetch_dataset("77hc-ibv8", opener=fake, page_size=3)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(res.dataset_key, "77hc-ibv8")
        with self.assertRaises(KeyError):
            _connector().fetch_dataset("hospital_general")  # not a 4x4 id

    def test_fetch_catalog_returns_raw_items(self):
        fake = FakeProviderData().add_catalog(catalog_items())
        res = _connector().fetch("catalog", opener=fake)
        self.assertEqual(len(res.rows), 3)
        self.assertIn("identifier", res.rows[0])


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.store = ProviderDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_refresh_catalog_syncs_table(self):
        fake = FakeProviderData().add_catalog(catalog_items())
        counts = _connector().refresh(self.store, "catalog", opener=fake)
        self.assertEqual(counts["upserted"], 3)
        self.assertEqual(self.store.count("provider_data_catalog"), 3)

    def test_refresh_curated_lands_in_canonical_table(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(5))
        counts = _connector().refresh(self.store, "hospital_general",
                                      opener=fake, page_size=2)
        self.assertEqual(counts["fetched"], 5)
        self.assertEqual(counts["upserted"], 5)
        self.assertEqual(counts["table"], "hospital_general")
        self.assertEqual(self.store.count("hospital_general"), 5)

    def test_refresh_generic_lands_in_rows_table(self):
        fake = FakeProviderData().add("77hc-ibv8", generic_hai_rows(4))
        counts = _connector().refresh(self.store, "77hc-ibv8", opener=fake)
        self.assertEqual(counts["table"], "provider_data_rows")
        self.assertEqual(self.store.count("provider_data_rows"), 4)
        row = self.store.fetchall(
            "SELECT * FROM provider_data_rows ORDER BY row_idx LIMIT 1")[0]
        self.assertEqual(row["row_key"], "77hc-ibv8:0")
        self.assertEqual(row["source_endpoint"], "77hc-ibv8")

    def test_refresh_generic_mid_dataset_offset_keeps_absolute_keys(self):
        # Regression guard: a refresh resumed mid-dataset (offset>0)
        # must key rows by absolute offset, never re-key them as 0..N.
        conn = _connector()
        fake = FakeProviderData().add("77hc-ibv8", generic_hai_rows(4))
        conn.refresh(self.store, "77hc-ibv8", opener=fake)
        fake2 = FakeProviderData().add("77hc-ibv8", generic_hai_rows(4))
        conn.refresh(self.store, "77hc-ibv8", {"offset": 2}, opener=fake2)
        keys = {r["row_key"] for r in self.store.fetchall(
            "SELECT row_key FROM provider_data_rows")}
        self.assertEqual(keys, {f"77hc-ibv8:{i}" for i in range(4)})
        row0 = self.store.fetchall(
            "SELECT row_json FROM provider_data_rows WHERE row_key = ?",
            ("77hc-ibv8:0",))[0]
        self.assertIn("010000", row0["row_json"])   # first record intact

    def test_refresh_generic_different_conditions_coexist(self):
        # Regression: row_idx is positional within the FILTERED result
        # set, so refreshes of the same dataset with different conditions
        # used to silently overwrite each other at row_key {key}:0.
        conn = _connector()
        fake = FakeProviderData().add("77hc-ibv8", generic_hai_rows(4))
        conn.refresh(self.store, "77hc-ibv8", opener=fake,
                     conditions={"facility_id": "010001"})
        conn.refresh(self.store, "77hc-ibv8", opener=fake,
                     conditions={"facility_id": "010002"})
        rows = self.store.fetchall(
            "SELECT row_key, row_json FROM provider_data_rows")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r["row_key"] for r in rows}), 2)
        # The human-readable filter params ride along in the row JSON.
        self.assertIn('"_slice_params"', rows[0]["row_json"])
        # Re-running one filtered refresh upserts in place (idempotent).
        conn.refresh(self.store, "77hc-ibv8", opener=fake,
                     conditions={"facility_id": "010002"})
        self.assertEqual(self.store.count("provider_data_rows"), 2)

    def test_refresh_is_idempotent(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(3))
        conn = _connector()
        conn.refresh(self.store, "hospital_general", opener=fake)
        fake2 = FakeProviderData().add("xubh-q36u", hospital_rows(3))
        conn.refresh(self.store, "hospital_general", opener=fake2)
        self.assertEqual(self.store.count("hospital_general"), 3)


if __name__ == "__main__":
    unittest.main()
