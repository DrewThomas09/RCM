"""Replace-slice semantics on the shared generic ``*_rows`` tables.

The seven catalog connectors key generic rows ``{dataset_key}:{row_idx}``
(or ``{dataset_key}:{sig}:{row_idx}`` for filtered pulls) and historically
only upserted: a re-fetch that returned FEWER rows than the previous pull
stranded the earlier pull's trailing ``row_idx`` rows, serving mixed
vintages with nothing flagging it. ``replace_slice`` deletes exactly the
slice being re-pulled and writes the fresh rows in one transaction
(mirroring ``oig_leie``'s replace-in-transaction semantics).

Store-level cases run identically over all seven stores (data-driven);
the end-to-end cases drive real ``refresh()`` paths through the fake
openers to prove the wiring: a complete pull replaces, a truncated or
resumed pull still upserts (a mid-dataset resume must never delete the
windows it isn't re-pulling).
"""
import importlib
import unittest

from .._spi import load_all

# Connectors whose stores carry a shared generic rows table.
_GENERIC_PKGS = ("cdc_data", "cms_open_data", "healthcare_gov",
                 "healthdata_gov", "medicaid_data", "open_payments",
                 "provider_data")


def _generic_row(table_prefixless_key, dataset_key, row_idx, sig=""):
    if sig:
        key = f"{dataset_key}:{sig}:{row_idx}"
    else:
        key = f"{dataset_key}:{row_idx}"
    return {"row_key": key, "dataset_key": dataset_key, "row_idx": row_idx,
            "row_json": "{}", "fetched_at": "2026-07-01T00:00:00+00:00",
            "source_endpoint": dataset_key}


class ReplaceSliceStoreParityTests(unittest.TestCase):
    """One matrix, asserted identically for every generic store."""

    @classmethod
    def setUpClass(cls):
        cls.adapters = load_all()

    def _each(self):
        for name in _GENERIC_PKGS:
            adapter = self.adapters[name]
            table = f"{name}_rows"
            self.assertIn(table, adapter.tables_mod.TABLES, name)
            store = adapter.open_store(":memory:")
            try:
                yield name, store, table
            finally:
                store.close()

    def _keys(self, store, table):
        return {r["row_key"]
                for r in store.fetchall(f"SELECT row_key FROM {table}")}

    def test_shrunken_refetch_leaves_no_stale_tail(self):
        for name, store, table in self._each():
            store.upsert(table, [_generic_row(table, "aaaa-1111", i)
                                 for i in range(3)])
            n = store.replace_slice(
                table, "aaaa-1111",
                [_generic_row(table, "aaaa-1111", i) for i in range(2)])
            self.assertEqual(n, 2, name)
            self.assertEqual(self._keys(store, table),
                             {"aaaa-1111:0", "aaaa-1111:1"}, name)

    def test_replace_is_scoped_to_one_dataset_and_one_slice(self):
        for name, store, table in self._each():
            store.upsert(table, [
                _generic_row(table, "aaaa-1111", 0),
                _generic_row(table, "aaaa-1111", 1),
                # Same dataset, filtered slice — must survive an
                # unfiltered replace.
                _generic_row(table, "aaaa-1111", 0, sig="deadbeef"),
                # Sibling dataset — must survive entirely.
                _generic_row(table, "bbbb-2222", 0),
            ])
            store.replace_slice(table, "aaaa-1111",
                                [_generic_row(table, "aaaa-1111", 0)])
            self.assertEqual(self._keys(store, table),
                             {"aaaa-1111:0", "aaaa-1111:deadbeef:0",
                              "bbbb-2222:0"}, name)
            # And the sig-scoped replace only touches its own slice.
            store.replace_slice(table, "aaaa-1111", [],
                                slice_sig="deadbeef")
            self.assertEqual(self._keys(store, table),
                             {"aaaa-1111:0", "bbbb-2222:0"}, name)

    def test_replace_slice_rejects_non_generic_tables(self):
        for name, store, table in self._each():
            other = next(t for t in self.adapters[name].tables_mod.TABLES
                         if t != table)
            with self.assertRaises(ValueError, msg=name):
                store.replace_slice(other, "aaaa-1111", [])


class CdcRefreshReplaceE2ETests(unittest.TestCase):
    """Real refresh() through the fake Socrata server: replace on a
    complete pull, plain upsert when the page cap truncates."""

    def setUp(self):
        fakes = importlib.import_module("connectors.cdc_data.tests.fakes")
        tables = importlib.import_module("connectors.cdc_data.tables")
        connector = importlib.import_module("connectors.cdc_data.connector")
        self.FakeCdcData = fakes.FakeCdcData
        self.store = tables.CdcDataStore(":memory:")
        self.conn = connector.CdcDataConnector()

    def tearDown(self):
        self.store.close()

    def _rows(self, n):
        return [{"some_col": f"v{i}", "other": str(i)} for i in range(n)]

    def test_complete_refetch_replaces_the_shrunken_slice(self):
        fake = self.FakeCdcData().add("/resource/zzzz-9999.json",
                                      self._rows(3))
        out = self.conn.refresh(self.store, "zzzz-9999", opener=fake)
        self.assertTrue(out["replaced"])
        self.assertEqual(self.store.count("cdc_data_rows"), 3)
        # Upstream shrinks: the refetch must not strand zzzz-9999:2.
        fake2 = self.FakeCdcData().add("/resource/zzzz-9999.json",
                                       self._rows(2))
        out = self.conn.refresh(self.store, "zzzz-9999", opener=fake2)
        self.assertTrue(out["replaced"])
        keys = {r["row_key"] for r in self.store.fetchall(
            "SELECT row_key FROM cdc_data_rows")}
        self.assertEqual(keys, {"zzzz-9999:0", "zzzz-9999:1"})

    def test_truncated_pull_upserts_and_keeps_existing_rows(self):
        fake = self.FakeCdcData().add("/resource/zzzz-9999.json",
                                      self._rows(4))
        self.conn.refresh(self.store, "zzzz-9999", opener=fake)
        self.assertEqual(self.store.count("cdc_data_rows"), 4)
        # A capped pull (1 page of 2) is NOT a complete snapshot — it
        # must upsert in place, never delete the rows it didn't re-pull.
        fake2 = self.FakeCdcData().add("/resource/zzzz-9999.json",
                                       self._rows(4))
        out = self.conn.refresh(self.store, "zzzz-9999", opener=fake2,
                                max_pages=1, page_size=2)
        self.assertFalse(out["replaced"])
        self.assertFalse(out["exhausted"])
        self.assertEqual(self.store.count("cdc_data_rows"), 4)

    def test_filtered_slices_replace_independently(self):
        fake = self.FakeCdcData().add("/resource/zzzz-9999.json",
                                      self._rows(3))
        self.conn.refresh(self.store, "zzzz-9999", {"some_col": "v1"},
                          opener=fake)
        self.conn.refresh(self.store, "zzzz-9999", {"some_col": "v2"},
                          opener=fake)
        self.assertEqual(self.store.count("cdc_data_rows"), 2)
        # Re-pulling one filter slice replaces only that slice.
        self.conn.refresh(self.store, "zzzz-9999", {"some_col": "v1"},
                          opener=fake)
        self.assertEqual(self.store.count("cdc_data_rows"), 2)


class CmsOpenDataRefreshReplaceE2ETests(unittest.TestCase):
    """Same contract on the data-api-shaped twin (offset-resume aware)."""

    def setUp(self):
        fakes = importlib.import_module(
            "connectors.cms_open_data.tests.fakes")
        tables = importlib.import_module("connectors.cms_open_data.tables")
        connector = importlib.import_module(
            "connectors.cms_open_data.connector")
        self.fakes = fakes
        self.tables = tables
        self.connector = connector
        self.store = tables.CmsOpenDataStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_complete_generic_refetch_replaces(self):
        fk = self.fakes
        uuid = "12345678-1234-1234-1234-123456789012"
        rows3 = [{"col_a": f"v{i}"} for i in range(3)]
        rows2 = [{"col_a": f"v{i}"} for i in range(2)]
        conn = self.connector.CmsOpenDataConnector()
        fake = fk.FakeCmsOpenData().add_dataset(uuid, rows3)
        out = conn.refresh(self.store, uuid, opener=fake)
        self.assertTrue(out["replaced"])
        self.assertEqual(self.store.count("cms_open_data_rows"), 3)
        fake2 = fk.FakeCmsOpenData().add_dataset(uuid, rows2)
        out = conn.refresh(self.store, uuid, opener=fake2)
        self.assertTrue(out["replaced"])
        self.assertEqual(self.store.count("cms_open_data_rows"), 2)


if __name__ == "__main__":
    unittest.main()
