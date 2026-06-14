import json
import unittest

from .. import market_map as mm
from ..crosswalk import resolve_ndc_rxcui
from ..query import QueryError, aggregate
from ..rxnorm_adapter import RxNormResolver, make_resolver
from ..tables import OpenFdaStore


class AggregateTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC", "device_class": "2",
             "decision_date": "2019-01-01", "source_endpoint": "device_510k"},
            {"device_key": "K:2", "product_code": "ABC", "device_class": "2",
             "decision_date": "2020-01-01", "source_endpoint": "device_510k"},
            {"device_key": "K:3", "product_code": "XYZ", "device_class": "3",
             "decision_date": "2020-06-01", "source_endpoint": "device_510k"}])

    def tearDown(self):
        self.store.close()

    def test_aggregate_counts_by_group(self):
        res = aggregate(self.store, "openfda_device_510k",
                        group_by=["product_code"])
        counts = {r["product_code"]: r["count"] for r in res.rows}
        self.assertEqual(counts, {"ABC": 2, "XYZ": 1})

    def test_aggregate_rejects_bad_group_field(self):
        with self.assertRaises(QueryError):
            aggregate(self.store, "openfda_device_510k", group_by=["nope"])

    def test_aggregate_requires_group_by(self):
        with self.assertRaises(QueryError):
            aggregate(self.store, "openfda_device_510k", group_by=[])


class MarketMapTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenFdaStore(":memory:")
        self.store.upsert("dim_device", [
            {"device_key": "K:1", "product_code": "ABC", "decision_date": "2019-01-01",
             "company_key": "co_a", "source_endpoint": "device_510k"},
            {"device_key": "K:2", "product_code": "ABC", "decision_date": "2020-01-01",
             "company_key": "co_b", "source_endpoint": "device_510k"},
            {"device_key": "CLASS:ABC", "product_code": "ABC",
             "source_endpoint": "device_classification"}])  # no date → excluded
        self.store.upsert("dim_device_udi", [
            {"public_device_record_key": "U1", "product_code": "ABC"},
            {"public_device_record_key": "U2", "product_code": "ABC"}])
        self.store.upsert("fact_device_adverse_event", [
            {"report_number": "E1", "product_code": "ABC"},
            {"report_number": "E2", "product_code": "ABC"},
            {"report_number": "E3", "product_code": "ABC"}])
        self.store.upsert("fact_drug_adverse_event", [
            {"safetyreportid": "1", "ndc": "0002-1200"}])
        self.store.upsert("fact_drug_recall", [
            {"recall_number": "R1", "ndc": "0002-1200"}])

    def tearDown(self):
        self.store.close()

    def test_clearance_timeline_excludes_undated(self):
        rows = mm.clearance_timeline_by_product_code(self.store)
        years = {r["year"]: r["clearances"] for r in rows
                 if r["product_code"] == "ABC"}
        self.assertEqual(years, {"2019": 1, "2020": 1})

    def test_competitive_entry_counts_distinct_applicants(self):
        rows = mm.competitive_entry_by_product_code(self.store)
        abc = next(r for r in rows if r["product_code"] == "ABC")
        self.assertEqual(abc["distinct_applicants"], 2)
        self.assertEqual(abc["first_decision"], "2019-01-01")

    def test_maude_intensity_normalizes_by_udi(self):
        rows = mm.maude_safety_intensity(self.store)
        abc = next(r for r in rows if r["product_code"] == "ABC")
        self.assertEqual(abc["maude_events"], 3)
        self.assertEqual(abc["udi_units"], 2)
        self.assertEqual(abc["events_per_udi"], 1.5)

    def test_drug_risk_weights_recalls(self):
        rows = mm.drug_risk_by_ndc(self.store)
        ndc = next(r for r in rows if r["ndc"] == "0002-1200")
        self.assertEqual(ndc["faers_events"], 1)
        self.assertEqual(ndc["recalls"], 1)
        self.assertEqual(ndc["risk_signal"], 1 + 5 * 1)


class RxNormResolverTests(unittest.TestCase):
    def test_resolves_via_fake_rxnav_and_caches(self):
        calls = []

        def fake_opener(url, timeout):
            calls.append(url)
            return json.dumps({"idGroup": {"rxnormId": ["1234"]}}).encode()

        r = RxNormResolver(opener=fake_opener, min_interval_s=0.0)
        self.assertEqual(r("0002-1200"), "1234")
        self.assertEqual(r("0002-1200"), "1234")  # cached
        self.assertEqual(len(calls), 1)            # only one live call

    def test_unresolved_returns_none_gracefully(self):
        def fake_opener(url, timeout):
            return json.dumps({"idGroup": {}}).encode()

        r = RxNormResolver(opener=fake_opener, min_interval_s=0.0)
        self.assertIsNone(r("9999-9999"))

    def test_network_error_is_swallowed(self):
        def boom(url, timeout):
            raise OSError("network down")

        r = RxNormResolver(opener=boom, min_interval_s=0.0)
        self.assertIsNone(r("0002-1200"))

    def test_resolver_wires_into_crosswalk(self):
        store = OpenFdaStore(":memory:")
        store.upsert("dim_drug_product", [
            {"ndc": "0002-1200", "source_endpoint": "drug_ndc"}])

        def fake_opener(url, timeout):
            return json.dumps({"idGroup": {"rxnormId": ["555"]}}).encode()

        stats = resolve_ndc_rxcui(store, ["0002-1200"],
                                  resolver=make_resolver(opener=fake_opener))
        self.assertEqual(stats["resolved"], 1)
        row = store.fetchall(
            "SELECT rxcui FROM dim_drug_product WHERE ndc='0002-1200'")[0]
        self.assertEqual(row["rxcui"], "555")
        store.close()


if __name__ == "__main__":
    unittest.main()
