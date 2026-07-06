import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from ..tables import TABLES, BlsQcewStore
from .fakes import area_48453_rows, industry_622_rows


class TablesTests(unittest.TestCase):
    def setUp(self):
        self.store = BlsQcewStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_schema_declares_all_live_columns_plus_meta(self):
        # 1 pk + 42 live columns + 2 meta = 45. Guard against accidental
        # edits to the snapshotted column list.
        tdef = TABLES["qcew_industry_area"]
        self.assertEqual(len(tdef.columns), 45)
        self.assertEqual(tdef.columns[-2:], ("source_endpoint",
                                             "ingested_at"))
        self.assertEqual(tdef.columns[0], tdef.pk)
        self.assertEqual(tdef.pk, "qcew_key")

    def test_upsert_is_idempotent(self):
        spec = get_endpoint("industry_area")
        rows = normalize(spec, industry_622_rows()).rows["qcew_industry_area"]
        self.store.upsert("qcew_industry_area", rows)
        self.store.upsert("qcew_industry_area", rows)   # re-run
        self.assertEqual(self.store.count("qcew_industry_area"), 6)

    def test_upsert_updates_in_place_on_same_key(self):
        # A revised quarter (QCEW revises each quarter once) must replace
        # values, not duplicate the observation.
        spec = get_endpoint("industry_area")
        first = industry_622_rows()[2]
        self.store.upsert("qcew_industry_area",
                          normalize(spec, [first]).rows["qcew_industry_area"])
        revised = dict(first, month3_emplvl="21650", avg_wkly_wage="1740")
        self.store.upsert("qcew_industry_area",
                          normalize(spec, [revised]).rows["qcew_industry_area"])
        self.assertEqual(self.store.count("qcew_industry_area"), 1)
        row = self.store.fetchall(
            "SELECT month3_emplvl, avg_wkly_wage FROM qcew_industry_area "
            "WHERE qcew_key = ?",
            ("industry_area:48453:5:622:2025:4",))[0]
        self.assertEqual(row["month3_emplvl"], "21650")
        self.assertEqual(row["avg_wkly_wage"], "1740")

    def test_slices_share_table_without_colliding(self):
        rec = industry_622_rows()[2]
        for key in ("industry_area", "area_industry"):
            spec = get_endpoint(key)
            self.store.upsert(
                "qcew_industry_area",
                normalize(spec, [rec]).rows["qcew_industry_area"])
        self.assertEqual(self.store.count("qcew_industry_area"), 2)
        # Each slice keeps its own provenance tag.
        tags = {r["source_endpoint"] for r in self.store.fetchall(
            "SELECT source_endpoint FROM qcew_industry_area")}
        self.assertEqual(tags, {"industry_area", "area_industry"})

    def test_missing_columns_are_null(self):
        spec = get_endpoint("area_industry")
        row = normalize(spec, area_48453_rows()[:1]).rows["qcew_industry_area"][0]
        row.pop("oty_avg_wkly_wage_pct_chg", None)
        self.store.upsert("qcew_industry_area", [row])
        got = self.store.fetchall(
            "SELECT oty_avg_wkly_wage_pct_chg FROM qcew_industry_area")[0]
        self.assertIsNone(got["oty_avg_wkly_wage_pct_chg"])

    def test_ingested_at_is_set(self):
        spec = get_endpoint("industry_area")
        rows = normalize(spec, industry_622_rows()).rows["qcew_industry_area"]
        self.store.upsert("qcew_industry_area", rows)
        row = self.store.fetchall(
            "SELECT ingested_at FROM qcew_industry_area LIMIT 1")[0]
        self.assertRegex(row["ingested_at"],
                         r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")


if __name__ == "__main__":
    unittest.main()
