import unittest

from ..lookup import lookup_device, lookup_drug
from ..query import QueryError, query
from ..tables import OpenFdaStore


class StoreUpsertTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_upsert_is_idempotent_and_updates(self):
        self.store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "proprietary_name": "OLD",
             "source_endpoint": "drug_ndc"}])
        self.store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "proprietary_name": "NEW",
             "source_endpoint": "drug_ndc"}])
        self.assertEqual(self.store.count("dim_drug_product"), 1)
        row = self.store.fetchall("SELECT proprietary_name FROM dim_drug_product")[0]
        self.assertEqual(row["proprietary_name"], "NEW")


class QueryEngineTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")
        # Two endpoints share dim_device; the dataset slice must separate them.
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC", "device_class": "2",
             "decision_date": "2019-01-01", "source_endpoint": "device_510k"},
            {"device_key": "K:2", "product_code": "ABC", "device_class": "2",
             "decision_date": "2020-01-01", "source_endpoint": "device_510k"},
            {"device_key": "CLASS:ABC", "product_code": "ABC", "device_class": "2",
             "source_endpoint": "device_classification"}])

    def tearDown(self):
        self.store.close()

    def test_dataset_slice_filters_by_source_endpoint(self):
        res = query(self.store, "openfda_device_510k")
        self.assertEqual(res.total, 2)
        self.assertTrue(all(r["source_endpoint"] == "device_510k" for r in res.rows))

    def test_filter_select_sort_paginate(self):
        res = query(self.store, "openfda_device_510k",
                    filters={"product_code": "ABC"},
                    select=["device_key", "decision_date"],
                    sort=["-decision_date"], limit=1, offset=0)
        self.assertEqual(res.limit, 1)
        self.assertEqual(res.total, 2)
        self.assertEqual(res.rows[0]["decision_date"], "2020-01-01")
        self.assertNotIn("product_code", res.rows[0])  # not selected

    def test_unknown_field_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "openfda_device_510k",
                  filters={"evil; DROP TABLE": "x"})

    def test_unknown_dataset_is_rejected(self):
        with self.assertRaises(QueryError):
            query(self.store, "openfda_not_a_dataset")

    def test_notnull_and_isnull_operators(self):
        # One 510k row has a decision_date, the classification slice has none;
        # within the 510k slice all three rows have decision_date... add a null.
        self.store.upsert("dim_device", [
            {"device_key": "K:3", "product_code": "ABC", "device_class": "2",
             "source_endpoint": "device_510k"}])  # no decision_date
        has = query(self.store, "openfda_device_510k",
                    filters={"decision_date__notnull": "1"})
        self.assertEqual(has.total, 2)
        missing = query(self.store, "openfda_device_510k",
                        filters={"decision_date__isnull": "1"})
        self.assertEqual(missing.total, 1)
        self.assertEqual(missing.rows[0]["device_key"], "K:3")

    def test_between_operator(self):
        res = query(self.store, "openfda_device_510k",
                    filters={"decision_date__between": "2018-06-01,2019-12-31"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["decision_date"], "2019-01-01")

    def test_between_rejects_bad_arity(self):
        with self.assertRaises(QueryError):
            query(self.store, "openfda_device_510k",
                  filters={"decision_date__between": "2019-01-01"})


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_lookup_drug_fans_out(self):
        self.store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "proprietary_name": "FOO", "rxcui": "1234",
             "application_number": "NDA001", "source_endpoint": "drug_ndc"}])
        self.store.upsert("fact_drug_adverse_event", [
            {"safetyreportid": "9", "ndc": "0002-1200", "receivedate": "20200101"}])
        self.store.upsert("fact_drug_recall", [
            {"recall_number": "R1", "ndc": "0002-1200", "report_date": "20200101"}])
        self.store.upsert("dim_drug_approval", [
            {"application_number": "NDA001", "sponsor_name": "Acme"}])
        out = lookup_drug(self.store, "0002-1200")
        self.assertEqual(out["rxcui"], "1234")
        self.assertTrue(out["rxcui_resolved"])
        self.assertEqual(out["adverse_events"]["count"], 1)
        self.assertEqual(out["recalls"]["count"], 1)
        self.assertEqual(out["approval"][0]["sponsor_name"], "Acme")

    def test_lookup_device_timeline_and_norm_counts(self):
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC", "decision_date": "2019-01-01",
             "decision_type": "SESE", "source_endpoint": "device_510k"},
            {"device_key": "K:2", "product_code": "ABC", "decision_date": "2021-01-01",
             "decision_type": "SESE", "source_endpoint": "device_510k"}])
        self.store.upsert("xwalk_device_product_code", [
            {"product_code": "ABC", "device_name": "Widget", "clearance_count": "2"}])
        self.store.upsert("dim_device_udi", [
            {"public_device_record_key": "U1", "product_code": "ABC"},
            {"public_device_record_key": "U2", "product_code": "ABC"}])
        self.store.upsert("fact_device_adverse_event", [
            {"report_number": "E1", "product_code": "ABC", "date_received": "20200101"}])
        out = lookup_device(self.store, "abc")  # case-insensitive
        self.assertEqual(out["clearance_count"], 2)
        self.assertEqual(out["clearance_timeline"][0]["decision_date"], "2019-01-01")
        self.assertEqual(out["udi"]["count"], 2)
        # MAUDE per UDI unit: 1 event / 2 udi = 0.5
        self.assertEqual(out["adverse_events"]["per_udi_unit"], 0.5)


if __name__ == "__main__":
    unittest.main()
