import unittest

from ..connector import CmsOpenDataConnector
from ..endpoints import ENDPOINTS, get_endpoint
from ..tables import CmsOpenDataStore
from ..transport import CmsOpenDataTransport
from .fakes import (
    CAT_COST_UUID,
    CAT_PHYS_UUID,
    FakeCmsOpenData,
    cost_rows,
    phys_rows,
)

_PINNED_PHYS_UUID = get_endpoint("mup_physician_by_provider").uuid


def _connector(**kw):
    kw.setdefault("page_size", 2)
    return CmsOpenDataConnector(CmsOpenDataTransport(min_interval_s=0.0), **kw)


class DiscoverTests(unittest.TestCase):
    def test_discover_normalizes_the_catalog(self):
        fake = FakeCmsOpenData()
        rows = _connector().discover(opener=fake)
        self.assertEqual(len(rows), 3)
        by_key = {r["dataset_key"]: r for r in rows}
        phys = by_key["medicare_physician_other_practitioners_by_provider"]
        self.assertEqual(phys["uuid"], CAT_PHYS_UUID)   # the "latest" API dist
        self.assertTrue(phys["api_url"].endswith(f"{CAT_PHYS_UUID}/data"))
        self.assertEqual(phys["themes"], "Medicare")
        self.assertEqual(phys["periodicity"], "R/P1Y")
        # ZIP-only dataset: no API url, uuid still recovered from identifier.
        hrr = by_key["medicare_geographic_variation_by_hospital_referral_region"]
        self.assertEqual(hrr["api_url"], "")
        self.assertEqual(hrr["uuid"], "6d7b229d-5bfb-4666-a2d2-38cea44a112c")

    def test_sync_catalog_upserts_and_is_idempotent(self):
        fake = FakeCmsOpenData()
        store = CmsOpenDataStore(":memory:")
        conn = _connector()
        self.assertEqual(conn.sync_catalog(store, opener=fake), 3)
        self.assertEqual(conn.sync_catalog(store, opener=fake), 3)  # re-run
        self.assertEqual(store.count("cms_open_data_catalog"), 3)
        store.close()


class FetchPagingTests(unittest.TestCase):
    def test_fetch_absorbs_size_offset_paging(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(5))
        res = _connector().fetch("mup_physician_by_provider", opener=fake)
        self.assertEqual(len(res.rows), 5)          # every record, no dupes
        self.assertEqual(res.pages, 3)              # 2 + 2 + 1 (short page stops)
        self.assertFalse(res.truncated)
        self.assertEqual({r["Rndrng_NPI"] for r in res.rows},
                         {str(1003000126 + i) for i in range(5)})
        self.assertIn("offset=2", fake.calls[1])
        self.assertIn("offset=4", fake.calls[2])

    def test_max_pages_caps_and_flags_truncation(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(5))
        res = _connector().fetch("mup_physician_by_provider", opener=fake,
                                 max_pages=1)
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(res.pages, 1)
        self.assertTrue(res.truncated)
        self.assertEqual(len(fake.calls), 1)

    def test_filters_become_native_filter_params(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(5))
        res = _connector().fetch("mup_physician_by_provider",
                                 {"Rndrng_NPI": "1003000127"}, opener=fake)
        self.assertEqual(len(res.rows), 1)
        self.assertEqual(res.rows[0]["Rndrng_NPI"], "1003000127")
        self.assertIn("filter%5BRndrng_NPI%5D=1003000127", fake.calls[0])

    def test_accepts_full_dataset_id_and_rejects_unknown(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(1))
        res = _connector().fetch("cms_open_data_mup_physician_by_provider",
                                 opener=fake)
        self.assertEqual(res.endpoint, "mup_physician_by_provider")
        with self.assertRaises(KeyError):
            _connector().fetch("not_a_dataset", opener=fake)
        with self.assertRaises(KeyError):
            _connector().fetch("fetched_rows", opener=fake)  # needs a concrete key


class UuidResolutionTests(unittest.TestCase):
    """Dataset version UUIDs rotate; the catalog must win over the pin."""

    def test_without_store_uses_pinned_uuid(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(1))
        res = _connector().fetch("mup_physician_by_provider", opener=fake)
        self.assertEqual(res.uuid, _PINNED_PHYS_UUID)
        self.assertIn(_PINNED_PHYS_UUID, fake.calls[0])

    def test_with_synced_catalog_prefers_resolved_uuid(self):
        # The fake catalog advertises CAT_PHYS_UUID (a "newer version");
        # rows exist ONLY under it, so hitting the pin would return 404/[].
        fake = FakeCmsOpenData().add_dataset(CAT_PHYS_UUID, phys_rows(3))
        store = CmsOpenDataStore(":memory:")
        conn = _connector()
        conn.sync_catalog(store, opener=fake)
        res = conn.fetch("mup_physician_by_provider", opener=fake, store=store)
        self.assertEqual(res.uuid, CAT_PHYS_UUID)
        self.assertEqual(len(res.rows), 3)
        store.close()

    def test_unsynced_store_falls_back_to_pin(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(2))
        store = CmsOpenDataStore(":memory:")   # catalog table empty
        res = _connector().fetch("mup_physician_by_provider", opener=fake,
                                 store=store)
        self.assertEqual(res.uuid, _PINNED_PHYS_UUID)
        self.assertEqual(len(res.rows), 2)
        store.close()


class FetchDatasetGenericTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeCmsOpenData().add_dataset(CAT_COST_UUID, cost_rows())
        self.store = CmsOpenDataStore(":memory:")
        self.conn = _connector()
        self.conn.sync_catalog(self.store, opener=self.fake)

    def tearDown(self):
        self.store.close()

    def test_fetch_dataset_by_catalog_slug(self):
        key, res = self.conn.fetch_dataset("hospital_provider_cost_report",
                                           opener=self.fake, store=self.store)
        self.assertEqual(key, "hospital_provider_cost_report")
        self.assertEqual(res.uuid, CAT_COST_UUID)
        self.assertEqual(len(res.rows), 2)

    def test_fetch_dataset_by_title_is_slugified(self):
        key, _res = self.conn.fetch_dataset("Hospital Provider Cost Report",
                                            opener=self.fake, store=self.store)
        self.assertEqual(key, "hospital_provider_cost_report")

    def test_fetch_dataset_by_uuid_maps_back_to_slug(self):
        key, res = self.conn.fetch_dataset(CAT_COST_UUID, opener=self.fake,
                                           store=self.store)
        self.assertEqual(key, "hospital_provider_cost_report")
        self.assertEqual(len(res.rows), 2)

    def test_unknown_slug_without_catalog_raises(self):
        empty = CmsOpenDataStore(":memory:")
        with self.assertRaises(KeyError):
            self.conn.fetch_dataset("hospital_provider_cost_report",
                                    opener=self.fake, store=empty)
        empty.close()


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.fake = (FakeCmsOpenData()
                     .add_dataset(CAT_PHYS_UUID, phys_rows(5))
                     .add_dataset(CAT_COST_UUID, cost_rows()))
        self.store = CmsOpenDataStore(":memory:")
        self.conn = _connector()

    def tearDown(self):
        self.store.close()

    def test_refresh_catalog(self):
        out = self.conn.refresh(self.store, "catalog", opener=self.fake)
        self.assertEqual(out["upserted"], 3)
        self.assertEqual(out["table"], "cms_open_data_catalog")

    def test_refresh_curated_lands_in_canonical_table(self):
        self.conn.sync_catalog(self.store, opener=self.fake)
        out = self.conn.refresh(self.store, "mup_physician_by_provider",
                                opener=self.fake)
        self.assertEqual(out["fetched"], 5)
        self.assertEqual(out["upserted"], 5)
        self.assertEqual(out["table"], "cms_open_data_mup_physician_by_provider")
        self.assertEqual(
            self.store.count("cms_open_data_mup_physician_by_provider"), 5)
        # Idempotent on re-run.
        self.conn.refresh(self.store, "mup_physician_by_provider",
                          opener=self.fake)
        self.assertEqual(
            self.store.count("cms_open_data_mup_physician_by_provider"), 5)

    def test_refresh_generic_lands_in_rows_table(self):
        self.conn.sync_catalog(self.store, opener=self.fake)
        out = self.conn.refresh(self.store, "hospital_provider_cost_report",
                                opener=self.fake)
        self.assertEqual(out["table"], "cms_open_data_rows")
        self.assertEqual(out["upserted"], 2)
        self.assertEqual(
            self.store.count("cms_open_data_rows", "dataset_key = ?",
                             ("hospital_provider_cost_report",)), 2)


class StatsTests(unittest.TestCase):
    def test_stats_roundtrip(self):
        fake = FakeCmsOpenData().add_dataset(_PINNED_PHYS_UUID, phys_rows(5))
        doc = _connector().stats("mup_physician_by_provider", opener=fake)
        self.assertEqual(doc, {"found_rows": 5, "total_rows": 5})

    def test_stats_absent_returns_none(self):
        fake = FakeCmsOpenData()   # unknown uuid → 404 → []
        doc = _connector().stats("mup_physician_by_provider", opener=fake)
        self.assertIsNone(doc)


if __name__ == "__main__":
    unittest.main()
