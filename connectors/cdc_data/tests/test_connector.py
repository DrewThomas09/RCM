import unittest
from urllib.parse import parse_qs, urlparse

from ..connector import CdcDataConnector, DEFAULT_MAX_PAGES
from ..endpoints import get_endpoint
from ..tables import CdcDataStore
from ..transport import CdcSodaTransport
from .fakes import (CATALOG_PATH, FakeCdcData, catalog_items, generic_rows,
                    leading_causes_rows, places_rows)

_PLACES_PATH = "/resource/swc5-untb.json"
_CAUSES_PATH = "/resource/bi63-dtpu.json"


def _connector():
    return CdcDataConnector(CdcSodaTransport(min_interval_s=0.0))


class DiscoverTests(unittest.TestCase):
    def test_discover_pages_catalog_by_limit_and_page_until_short_page(self):
        fake = FakeCdcData().add(CATALOG_PATH, catalog_items(5))
        conn = _connector()
        rows = conn.discover(opener=fake, page_size=2)
        self.assertEqual(len(rows), 5)
        # 2 + 2 + 1: the short third page terminates the loop.
        self.assertEqual(len(fake.calls), 3)
        pages = [parse_qs(urlparse(u).query).get("page", ["?"])[0]
                 for u in fake.calls]
        self.assertEqual(pages, ["1", "2", "3"])  # 1-based page, not offset

    def test_discover_normalizes_and_syncs_store(self):
        fake = FakeCdcData().add(CATALOG_PATH, catalog_items(3))
        store = CdcDataStore(":memory:")
        try:
            rows = _connector().discover(opener=fake, store=store, page_size=10)
            self.assertEqual(store.count("cdc_data_catalog"), 3)
            self.assertEqual(rows[0]["dataset_uid"], "aaa0-bbb0")
            self.assertEqual(rows[0]["update_frequency"], "Annually")
        finally:
            store.close()

    def test_discover_respects_max_pages_cap(self):
        fake = FakeCdcData().add(CATALOG_PATH, catalog_items(5))
        rows = _connector().discover(opener=fake, page_size=2, max_pages=1)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(fake.calls), 1)


class FetchTests(unittest.TestCase):
    def test_fetch_absorbs_offset_paging_and_stops_on_short_page(self):
        fake = FakeCdcData().add(_CAUSES_PATH, leading_causes_rows())
        conn = _connector()
        res = conn.fetch("nchs_leading_causes", opener=fake, page_size=2)
        self.assertEqual(len(res.rows), 3)
        self.assertEqual(res.pages, 2)          # 2 rows + short page of 1
        self.assertTrue(res.exhausted)
        offsets = [parse_qs(urlparse(u).query)["$offset"][0]
                   for u in fake.calls]
        self.assertEqual(offsets, ["0", "2"])

    def test_fetch_pins_stable_order_and_passes_filters(self):
        fake = FakeCdcData().add(_PLACES_PATH, places_rows())
        conn = _connector()
        res = conn.fetch("cdc_data_places_county",   # full dataset id ok too
                         {"stateabbr": "AR"}, opener=fake)
        self.assertEqual(len(res.rows), 2)
        qs = parse_qs(urlparse(fake.calls[0]).query)
        self.assertEqual(qs["$order"], [":id"])  # deterministic paging
        self.assertEqual(qs["stateabbr"], ["AR"])

    def test_fetch_max_pages_cap_reports_not_exhausted(self):
        fake = FakeCdcData().add(_CAUSES_PATH, leading_causes_rows())
        res = _connector().fetch("nchs_leading_causes", opener=fake,
                                 page_size=1, max_pages=2)
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(res.pages, 2)
        self.assertFalse(res.exhausted)         # cap hit, more may remain

    def test_fetch_default_max_pages_is_modest(self):
        # 20 rows at page_size 1 with the default cap → exactly 5 requests.
        many = [{"year": str(2000 + i), "state": "X", "cause_name": f"c{i}"}
                for i in range(20)]
        fake = FakeCdcData().add(_CAUSES_PATH, many)
        res = _connector().fetch("nchs_leading_causes", opener=fake, page_size=1)
        self.assertEqual(res.pages, DEFAULT_MAX_PAGES)
        self.assertEqual(len(res.rows), DEFAULT_MAX_PAGES)

    def test_fetch_dataset_pulls_arbitrary_4x4(self):
        fake = FakeCdcData().add("/resource/zzzz-9999.json", generic_rows(3))
        res = _connector().fetch_dataset("zzzz-9999", opener=fake)
        self.assertEqual(len(res.rows), 3)
        self.assertEqual(res.endpoint, "zzzz-9999")

    def test_fetch_unknown_4x4_yields_empty_not_error(self):
        fake = FakeCdcData()  # nothing registered → live-style 404
        res = _connector().fetch_dataset("nope-nope", opener=fake)
        self.assertEqual(res.rows, [])

    def test_fetch_generic_key_directly_raises(self):
        with self.assertRaises(ValueError):
            _connector().fetch("fetched_rows", opener=FakeCdcData())

    def test_fetch_unknown_key_raises(self):
        with self.assertRaises(KeyError):
            _connector().fetch("not_a_dataset", opener=FakeCdcData())


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.store = CdcDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_refresh_curated_writes_canonical_table(self):
        fake = FakeCdcData().add(_PLACES_PATH, places_rows())
        out = _connector().refresh(self.store, "places_county", opener=fake)
        self.assertEqual(out["fetched"], 3)
        self.assertEqual(out["written"], {"cdc_places_county": 3})
        self.assertEqual(self.store.count("cdc_places_county"), 3)

    def test_refresh_catalog_syncs_catalog_table(self):
        fake = FakeCdcData().add(CATALOG_PATH, catalog_items(4))
        out = _connector().refresh(self.store, "catalog", opener=fake)
        self.assertEqual(out["written"], {"cdc_data_catalog": 4})
        self.assertEqual(self.store.count("cdc_data_catalog"), 4)

    def test_refresh_raw_4x4_lands_in_generic_rows(self):
        fake = FakeCdcData().add("/resource/zzzz-9999.json", generic_rows(2))
        out = _connector().refresh(self.store, "zzzz-9999", opener=fake)
        self.assertEqual(out["dataset"], "cdc_data_fetched_rows")
        self.assertEqual(out["written"], {"cdc_data_rows": 2})
        self.assertEqual(
            self.store.count("cdc_data_rows", "dataset_key = ?", ("zzzz-9999",)),
            2)
        # The unfiltered full-crawl key shape is a compatibility contract.
        keys = {r["row_key"] for r in self.store.fetchall(
            "SELECT row_key FROM cdc_data_rows")}
        self.assertEqual(keys, {"zzzz-9999:0", "zzzz-9999:1"})

    def test_refresh_generic_different_filters_coexist(self):
        # Regression: row_idx is positional within the FILTERED result
        # set, so refreshes of the same dataset with different filters
        # used to silently overwrite each other at row_key {key}:0.
        fake = FakeCdcData().add("/resource/zzzz-9999.json", generic_rows(3))
        conn = _connector()
        conn.refresh(self.store, "zzzz-9999", {"some_col": "v1"}, opener=fake)
        conn.refresh(self.store, "zzzz-9999", {"some_col": "v2"}, opener=fake)
        rows = self.store.fetchall(
            "SELECT row_key, row_json FROM cdc_data_rows")
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({r["row_key"] for r in rows}), 2)
        # The human-readable filter params ride along in the row JSON.
        self.assertIn('"_slice_params"', rows[0]["row_json"])
        # Re-running one filtered refresh upserts in place (idempotent).
        conn.refresh(self.store, "zzzz-9999", {"some_col": "v2"}, opener=fake)
        self.assertEqual(self.store.count("cdc_data_rows"), 2)

    def test_refresh_generic_where_clauses_get_distinct_slices(self):
        # $where is opaque to the fake (returns everything), but the key
        # signature must still keep the two slices apart in the store.
        fake = FakeCdcData().add("/resource/zzzz-9999.json", generic_rows(2))
        conn = _connector()
        conn.refresh(self.store, "zzzz-9999", {"$where": "other > 0"},
                     opener=fake)
        conn.refresh(self.store, "zzzz-9999", {"$where": "other > 1"},
                     opener=fake)
        self.assertEqual(self.store.count("cdc_data_rows"), 4)
        self.assertEqual(
            len({r["row_key"] for r in self.store.fetchall(
                "SELECT row_key FROM cdc_data_rows")}), 4)


if __name__ == "__main__":
    unittest.main()
