import unittest

from ..endpoints import get_endpoint
from ..lookup import lookup_industry_employment, lookup_labor_market
from ..normalize import normalize
from ..query import QueryError, aggregate, query
from ..tables import BlsQcewStore
from .fakes import (area_48453_2024q1_rows, area_48453_rows,
                    industry_622_rows)


def _seed(store: BlsQcewStore) -> None:
    """Both slices ingested (with the live cross-slice overlap) plus one
    older quarter — the shape lookups must cope with."""
    for key, raw in (("industry_area", industry_622_rows()),
                     ("area_industry", area_48453_rows()),
                     ("area_industry", area_48453_2024q1_rows())):
        rows = normalize(get_endpoint(key), raw).rows["qcew_industry_area"]
        store.upsert("qcew_industry_area", rows)


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = BlsQcewStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "bls_qcew_industry_area",
                    filters={"area_fips": "48303"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["month3_emplvl"], "9800")

    def test_slice_pinning_separates_the_shared_table(self):
        # 6 industry rows vs 6+1 area rows in one physical table.
        res_ind = query(self.store, "bls_qcew_industry_area")
        self.assertEqual(res_ind.total, 6)
        self.assertTrue(all(r["source_endpoint"] == "industry_area"
                            for r in res_ind.rows))
        res_area = query(self.store, "bls_qcew_area_industry")
        self.assertEqual(res_area.total, 7)
        self.assertTrue(all(r["source_endpoint"] == "area_industry"
                            for r in res_area.rows))

    def test_like_filter_healthcare_prefix(self):
        res = query(self.store, "bls_qcew_area_industry",
                    filters={"industry_code__like": "62%",
                             "year": "2025"})
        self.assertEqual(res.total, 4)          # 62, 622 x2, 6216 — not 23

    def test_in_filter(self):
        res = query(self.store, "bls_qcew_industry_area",
                    filters={"area_fips__in": ["48453", "48303"]})
        self.assertEqual(res.total, 3)

    def test_gte_and_sort(self):
        res = query(self.store, "bls_qcew_industry_area",
                    filters={"own_code": "5",
                             "avg_wkly_wage__gte": "1500"},
                    sort=["-avg_wkly_wage"])
        self.assertEqual([r["area_fips"] for r in res.rows],
                         ["US000", "48453", "48000", "48303"])

    def test_select_projects_columns(self):
        res = query(self.store, "bls_qcew_industry_area",
                    select=["area_fips", "month3_emplvl"], limit=1)
        self.assertEqual(set(res.rows[0].keys()),
                         {"area_fips", "month3_emplvl"})

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "bls_qcew_industry_area",
                        group_by=["own_code"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"own_code": "5", "count": 5})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "bls_qcew_industry_area",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "bls_qcew_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "bls_qcew_industry_area", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "bls_qcew_industry_area", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


class LookupTests(unittest.TestCase):
    def setUp(self):
        self.store = BlsQcewStore(":memory:")
        _seed(self.store)

    def tearDown(self):
        self.store.close()

    def test_labor_market_defaults_to_latest_quarter(self):
        out = lookup_labor_market(self.store, "48453")
        self.assertEqual((out["year"], out["qtr"]), ("2025", "4"))
        codes = {r["industry_code"] for r in out["industries"]}
        self.assertEqual(codes, {"62", "622", "6216"})   # never 10 or 23

    def test_labor_market_collapses_cross_slice_duplicates(self):
        # Travis 622 own 5/2 exist in BOTH slices; each must count once.
        out = lookup_labor_market(self.store, "48453")
        self.assertEqual(out["observations"], 4)   # 62, 622x2 owns, 6216
        row_622 = [r for r in out["industries"]
                   if r["industry_code"] == "622" and r["own_code"] == "5"]
        self.assertEqual(len(row_622), 1)
        self.assertEqual(row_622[0]["month3_emplvl"], "21500")
        self.assertEqual(row_622[0]["own_title"], "Private")

    def test_labor_market_orders_by_employment(self):
        out = lookup_labor_market(self.store, "48453")
        emps = [int(r["month3_emplvl"]) for r in out["industries"]]
        self.assertEqual(emps, sorted(emps, reverse=True))

    def test_labor_market_can_pin_an_earlier_quarter(self):
        out = lookup_labor_market(self.store, "48453",
                                  year="2024", qtr="1")
        self.assertEqual((out["year"], out["qtr"]), ("2024", "1"))
        self.assertEqual(out["observations"], 1)
        self.assertEqual(out["industries"][0]["month3_emplvl"], "20000")

    def test_labor_market_limit_is_clamped(self):
        out = lookup_labor_market(self.store, "48453", limit=1)
        self.assertEqual(len(out["industries"]), 1)
        self.assertEqual(out["observations"], 4)  # count is unaffected

    def test_labor_market_empty_area_says_fetch_first(self):
        out = lookup_labor_market(self.store, "06037")
        self.assertEqual(out["observations"], 0)
        self.assertIn("fetch", out["note"])

    def test_industry_employment_top_areas(self):
        out = lookup_industry_employment(self.store, "622")
        self.assertEqual((out["year"], out["qtr"]), ("2025", "4"))
        # Duplicated Travis observations collapse; 5 area x own groups:
        # US000/5, 48000/5, 48453/5, 48453/2, 48303/5, 48117/5.
        self.assertEqual(out["observations"], 6)
        self.assertEqual(out["top_areas"][0]["area_fips"], "US000")
        self.assertEqual(out["top_areas"][0]["month3_emplvl"], "5421400")
        own_map = {r["own_code"]: r["areas"] for r in out["by_ownership"]}
        self.assertEqual(own_map, {"2": 1, "5": 5})

    def test_industry_employment_unknown_industry(self):
        out = lookup_industry_employment(self.store, "99")
        self.assertEqual(out["observations"], 0)
        self.assertIn("fetch", out["note"])


if __name__ == "__main__":
    unittest.main()
