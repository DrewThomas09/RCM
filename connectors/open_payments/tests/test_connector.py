import unittest

from ..connector import MAX_PAGES_CAP, OpenPaymentsConnector, conditions_params
from ..normalize import normalize_generic
from ..tables import OpenPaymentsStore
from ..transport import OpenPaymentsTransport
from .fakes import (GENERAL_UUID, OLD_YEAR_UUID, FakeOpenPayments,
                    general_payment_row)


def _connector(**kw):
    return OpenPaymentsConnector(
        OpenPaymentsTransport(min_interval_s=0.0), **kw)


def _general(n, **kw):
    return [general_payment_row(str(1000 + i), **kw) for i in range(n)]


class ConnectorTests(unittest.TestCase):
    def test_discover_returns_normalized_catalog_rows(self):
        fake = FakeOpenPayments()
        rows = _connector().discover(opener=fake)
        self.assertEqual(len(rows), 3)          # fixture catalog size
        by_id = {r["identifier"]: r for r in rows}
        general = by_id[GENERAL_UUID]
        self.assertEqual(general["title"], "2024 General Payment Data")
        self.assertEqual(general["theme"], "General Payments")
        self.assertEqual(
            general["api_url"],
            f"https://openpaymentsdata.cms.gov/api/1/datastore/query/{GENERAL_UUID}/0")
        self.assertEqual(general["contact_email"], "openpayments@cms.hhs.gov")
        self.assertEqual(general["source_endpoint"], "catalog")

    def test_fetch_absorbs_limit_offset_paging(self):
        fake = FakeOpenPayments().add(GENERAL_UUID, _general(5))
        res = _connector(page_size=2, max_pages=10).fetch(
            "general_payments_2024", opener=fake)
        self.assertEqual(len(res.rows), 5)      # every record, no duplicates
        self.assertEqual(res.pages, 3)          # 2 + 2 + 1
        self.assertFalse(res.truncated)
        self.assertEqual({r["record_id"] for r in res.rows},
                         {"1000", "1001", "1002", "1003", "1004"})
        self.assertEqual(res.total, 5)

    def test_fetch_stops_at_max_pages_and_reports_truncated(self):
        # The scale guardrail: a 15M-row file must never be drained by
        # accident — the page budget stops the loop and flags it.
        fake = FakeOpenPayments().add(GENERAL_UUID, _general(10))
        res = _connector(page_size=2).fetch(
            "general_payments_2024", opener=fake, max_pages=2)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(res.pages, 2)
        self.assertTrue(res.truncated)

    def test_filters_become_server_side_conditions(self):
        recs = _general(3, state="VT") + _general(2, state="CA")
        # Distinct record ids across the two groups.
        for i, r in enumerate(recs):
            r["record_id"] = str(2000 + i)
        fake = FakeOpenPayments().add(GENERAL_UUID, recs)
        res = _connector().fetch("general_payments_2024",
                                 {"recipient_state": "VT"}, opener=fake)
        self.assertEqual(len(res.rows), 3)
        self.assertTrue(all(r["recipient_state"] == "VT" for r in res.rows))
        self.assertEqual(res.total, 3)          # count reflects the slice
        self.assertIn("conditions%5B0%5D%5Bproperty%5D=recipient_state",
                      fake.calls[0])

    def test_count_only_requested_on_first_page(self):
        fake = FakeOpenPayments().add(GENERAL_UUID, _general(5))
        _connector(page_size=2, max_pages=10).fetch(
            "general_payments_2024", opener=fake)
        self.assertNotIn("count=false", fake.calls[0])
        self.assertIn("count=false", fake.calls[1])
        self.assertIn("schema=false", fake.calls[0])

    def test_fetch_dataset_pulls_arbitrary_uuid(self):
        fake = FakeOpenPayments().add(OLD_YEAR_UUID, _general(3))
        res = _connector().fetch_dataset(OLD_YEAR_UUID, opener=fake)
        self.assertEqual(len(res.rows), 3)
        self.assertEqual(res.endpoint, OLD_YEAR_UUID)

    def test_fetch_generic_slot_directly_is_an_error(self):
        with self.assertRaises(ValueError):
            _connector().fetch("fetched_rows")

    def test_page_size_clamped_to_server_cap(self):
        fake = FakeOpenPayments().add(GENERAL_UUID, _general(1))
        res = _connector().fetch("general_payments_2024", opener=fake,
                                 page_size=9999)
        self.assertEqual(len(res.rows), 1)      # no 400: limit clamped ≤ 500
        self.assertIn("limit=500", fake.calls[0])

    def test_max_pages_clamped_to_hard_cap(self):
        conn = _connector(max_pages=10_000)
        self.assertEqual(conn.max_pages, MAX_PAGES_CAP)

    def test_refresh_fetches_normalizes_and_upserts(self):
        fake = FakeOpenPayments().add(GENERAL_UUID, _general(3))
        store = OpenPaymentsStore(":memory:")
        try:
            counts = _connector().refresh(store, "general_payments_2024",
                                          opener=fake)
            self.assertEqual(counts["fetched"], 3)
            self.assertEqual(counts["upserted"], 3)
            self.assertEqual(counts["table"], "op_general_payment")
            self.assertEqual(store.count("op_general_payment"), 3)

            catalog_counts = _connector().refresh(store, "catalog",
                                                  opener=FakeOpenPayments())
            self.assertEqual(catalog_counts["upserted"], 3)
            self.assertEqual(store.count("open_payments_catalog"), 3)
        finally:
            store.close()

    def test_refresh_generic_lands_in_rows_table(self):
        fake = FakeOpenPayments().add(OLD_YEAR_UUID, _general(2))
        store = OpenPaymentsStore(":memory:")
        try:
            counts = _connector().refresh(store, "fetched_rows",
                                          dataset_key=OLD_YEAR_UUID,
                                          opener=fake)
            self.assertEqual(counts["upserted"], 2)
            self.assertEqual(
                store.count("open_payments_rows", "dataset_key = ?",
                            (OLD_YEAR_UUID,)), 2)
        finally:
            store.close()

    def test_refresh_generic_unfiltered_keys_unchanged(self):
        # The unfiltered full-crawl key shape is a compatibility contract.
        fake = FakeOpenPayments().add(OLD_YEAR_UUID, _general(2))
        store = OpenPaymentsStore(":memory:")
        try:
            _connector().refresh(store, "fetched_rows",
                                 dataset_key=OLD_YEAR_UUID, opener=fake)
            keys = {r["row_key"] for r in store.fetchall(
                "SELECT row_key FROM open_payments_rows")}
            self.assertEqual(keys, {f"{OLD_YEAR_UUID}:00000000",
                                    f"{OLD_YEAR_UUID}:00000001"})
        finally:
            store.close()

    def test_refresh_generic_different_filters_coexist(self):
        # Regression: row_idx is positional within the FILTERED result
        # set, so refreshes of the same dataset with different filters
        # used to silently overwrite each other at row_key {key}:00000000.
        recs = _general(2, state="VT") + _general(2, state="CA")
        for i, r in enumerate(recs):
            r["record_id"] = str(3000 + i)
        fake = FakeOpenPayments().add(OLD_YEAR_UUID, recs)
        store = OpenPaymentsStore(":memory:")
        try:
            conn = _connector()
            conn.refresh(store, "fetched_rows", {"recipient_state": "VT"},
                         dataset_key=OLD_YEAR_UUID, opener=fake)
            conn.refresh(store, "fetched_rows", {"recipient_state": "CA"},
                         dataset_key=OLD_YEAR_UUID, opener=fake)
            keys = {r["row_key"] for r in store.fetchall(
                "SELECT row_key FROM open_payments_rows")}
            self.assertEqual(len(keys), 4)          # nothing overwritten
            # Re-running one filtered refresh upserts in place.
            conn.refresh(store, "fetched_rows", {"recipient_state": "CA"},
                         dataset_key=OLD_YEAR_UUID, opener=fake)
            self.assertEqual(store.count("open_payments_rows"), 4)
        finally:
            store.close()

    def test_fetch_dataset_reports_start_offset_for_stable_keys(self):
        # Regression: a fetch resumed mid-dataset must key rows by the
        # absolute datastore offset, never re-key them as 0..N.
        fake = FakeOpenPayments().add(OLD_YEAR_UUID, _general(5))
        res = _connector().fetch_dataset(OLD_YEAR_UUID, params={"offset": 3},
                                         opener=fake)
        self.assertEqual(res.start_offset, 3)
        norm = normalize_generic(OLD_YEAR_UUID, res.rows,
                                 row_offset=res.start_offset)
        keys = [r["row_key"] for r in norm.rows["open_payments_rows"]]
        self.assertEqual(keys, [f"{OLD_YEAR_UUID}:00000003",
                                f"{OLD_YEAR_UUID}:00000004"])

    def test_refresh_generic_without_dataset_key_is_an_error(self):
        store = OpenPaymentsStore(":memory:")
        try:
            with self.assertRaises(ValueError):
                _connector().refresh(store, "fetched_rows")
        finally:
            store.close()


class ConditionsParamsTests(unittest.TestCase):
    def test_equality_and_ops(self):
        params = conditions_params({
            "recipient_state": "VT",
            "total_amount_of_payment_usdollars__gt": "500",
        })
        # Sorted key order → recipient_state gets index 0.
        self.assertEqual(params["conditions[0][property]"], "recipient_state")
        self.assertEqual(params["conditions[0][operator]"], "=")
        self.assertEqual(params["conditions[1][property]"],
                         "total_amount_of_payment_usdollars")
        self.assertEqual(params["conditions[1][operator]"], ">")

    def test_like_operator_and_reserved_keys_skipped(self):
        params = conditions_params({
            "applicable_manufacturer_or_applicable_gpo_making_payment_name__like":
                "%MERCK%",
            "_internal": "skipped",
        })
        self.assertEqual(len(params), 3)        # one triplet only
        self.assertEqual(params["conditions[0][operator]"], "like")
        self.assertEqual(params["conditions[0][value]"], "%MERCK%")


if __name__ == "__main__":
    unittest.main()
