import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, normalize_generic
from ..query import QueryError, aggregate, query
from ..registry import by_dataset_id
from ..tables import MedicaidDataStore
from .fakes import nadac_row, sdud_row


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = MedicaidDataStore(":memory:")
        # nadac_2026 slice: 3 rows; nadac_2025 slice: 1 row — SAME table.
        rows_26 = normalize(get_endpoint("nadac_2026"), [
            nadac_row(ndc="00000000001", as_of="2026-01-07",
                      per_unit="0.10000"),
            nadac_row(ndc="00000000002", as_of="2026-01-07",
                      per_unit="0.50000"),
            nadac_row(ndc="00000000001", as_of="2026-01-14",
                      per_unit="0.20000"),
        ]).rows["medicaid_nadac"]
        rows_25 = normalize(get_endpoint("nadac_2025"), [
            nadac_row(ndc="00000000001", effective="2024-12-18",
                      as_of="2025-01-01", per_unit="0.09000"),
        ]).rows["medicaid_nadac"]
        self.store.upsert("medicaid_nadac", rows_26 + rows_25)
        sdud = normalize(get_endpoint("sdud_2025"), [
            sdud_row(state="AK"), sdud_row(state="AL", ndc="99999999999"),
        ]).rows["medicaid_sdud"]
        self.store.upsert("medicaid_sdud", sdud)

    def tearDown(self):
        self.store.close()

    # ── the shared-table + source_filter pattern (assignment-critical) ──
    def test_year_slice_pinning_on_shared_table(self):
        res26 = query(self.store, "medicaid_data_nadac_2026")
        self.assertEqual(res26.total, 3)
        self.assertTrue(all(r["source_endpoint"] == "nadac_2026"
                            for r in res26.rows))
        res25 = query(self.store, "medicaid_data_nadac_2025")
        self.assertEqual(res25.total, 1)
        self.assertEqual(res25.rows[0]["nadac_per_unit"], "0.09000")

    def test_registry_source_filter_drives_the_slice(self):
        reg = by_dataset_id()
        self.assertEqual(reg["medicaid_data_nadac_2026"].source_filter,
                         "nadac_2026")
        self.assertEqual(reg["medicaid_data_nadac_2025"].target_table,
                         reg["medicaid_data_nadac_2026"].target_table)
        # Generic rows must NOT pin (empty source_filter) — the table
        # multiplexes arbitrary dataset_keys.
        self.assertEqual(reg["medicaid_data_fetched_rows"].source_filter, "")

    def test_equality_filter(self):
        res = query(self.store, "medicaid_data_nadac_2026",
                    filters={"ndc": "00000000002"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["nadac_per_unit"], "0.50000")

    def test_like_and_sort_and_select(self):
        res = query(self.store, "medicaid_data_nadac_2026",
                    filters={"ndc_description__like": "%DECONGEST%"},
                    select=["ndc", "as_of_date"], sort=["-as_of_date"])
        self.assertEqual(res.total, 3)
        self.assertEqual(list(res.rows[0].keys()), ["ndc", "as_of_date"])
        self.assertEqual(res.rows[0]["as_of_date"], "2026-01-14")

    def test_in_filter(self):
        res = query(self.store, "medicaid_data_nadac_2026",
                    filters={"ndc__in": ["00000000001", "00000000002"]})
        self.assertEqual(res.total, 3)

    def test_between_filter(self):
        res = query(self.store, "medicaid_data_nadac_2026",
                    filters={"as_of_date__between": "2026-01-01,2026-01-08"})
        self.assertEqual(res.total, 2)

    def test_generic_rows_query_by_dataset_key(self):
        rows = normalize_generic("uuid-1", [{"a": 1}]).rows["medicaid_data_rows"]
        rows += normalize_generic("uuid-2", [{"b": 2}]).rows["medicaid_data_rows"]
        self.store.upsert("medicaid_data_rows", rows)
        res = query(self.store, "medicaid_data_fetched_rows",
                    filters={"dataset_key": "uuid-1"})
        self.assertEqual(res.total, 1)
        self.assertIn('"a": 1', res.rows[0]["row_json"])

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "medicaid_data_sdud_2025",
                        group_by=["state"])
        rows = res.as_dict()["rows"]
        self.assertEqual({(r["state"], r["count"]) for r in rows},
                         {("AK", 1), ("AL", 1)})

    def test_aggregate_respects_slice(self):
        # Aggregating the 2025 NADAC dataset must not see 2026 rows.
        res = aggregate(self.store, "medicaid_data_nadac_2025",
                        group_by=["as_of_date"])
        self.assertEqual(res.rows, [{"as_of_date": "2025-01-01", "count": 1}])

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "medicaid_data_nadac_2026",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "medicaid_data_does_not_exist")

    def test_unknown_group_by_raises(self):
        with self.assertRaises(QueryError):
            aggregate(self.store, "medicaid_data_nadac_2026",
                      group_by=["nope"])

    def test_limit_is_clamped(self):
        res = query(self.store, "medicaid_data_nadac_2026", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "medicaid_data_nadac_2026", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
