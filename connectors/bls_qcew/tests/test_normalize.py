import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, snake
from ..tables import TABLES
from .fakes import QCEW_HEADERS, area_48453_rows, industry_622_rows


class SnakeTests(unittest.TestCase):
    def test_identity_on_every_live_header(self):
        # QCEW headers are already snake_case; the documented rule must
        # be the identity on all 42 of them.
        for h in QCEW_HEADERS:
            self.assertEqual(snake(h), h)

    def test_table_columns_are_snake_fixed_points(self):
        # Every declared column must be stable under snake() — proof the
        # schema really is "live headers passed through the one rule".
        for tdef in TABLES.values():
            for col in tdef.columns:
                self.assertEqual(snake(col), col)

    def test_defensive_normalization_if_bls_ever_drifts(self):
        self.assertEqual(snake("  Area FIPS  "), "area_fips")
        self.assertEqual(snake("avg-wkly-wage"), "avg_wkly_wage")


class NormalizeTests(unittest.TestCase):
    def test_composes_slice_prefixed_key_and_strips_values(self):
        spec = get_endpoint("industry_area")
        res = normalize(spec, industry_622_rows())
        rows = res.rows["qcew_industry_area"]
        self.assertEqual(len(rows), 6)
        travis = rows[2]
        self.assertEqual(travis["qcew_key"],
                         "industry_area:48453:5:622:2025:4")
        self.assertEqual(travis["area_fips"], "48453")
        self.assertEqual(travis["avg_wkly_wage"], "1725")   # " 1725" stripped
        self.assertEqual(travis["source_endpoint"], "industry_area")
        self.assertEqual(res.unmapped, {})

    def test_all_42_columns_land(self):
        spec = get_endpoint("area_industry")
        rows = normalize(spec, area_48453_rows()).rows["qcew_industry_area"]
        # 42 published columns + qcew_key + source_endpoint.
        self.assertEqual(len(rows[0]), 44)
        self.assertEqual(rows[0]["month3_emplvl"], "939358")
        self.assertEqual(rows[0]["oty_month3_emplvl_pct_chg"], "2.7")

    def test_slices_cannot_collide_across_datasets(self):
        # The same raw observation through both specs → different keys,
        # the invariant that makes the shared table safe (the live
        # overlap: industry-622 and area-48453 both publish this row).
        rec = industry_622_rows()[2]
        ind = normalize(get_endpoint("industry_area"), [rec])
        area = normalize(get_endpoint("area_industry"), [rec])
        k1 = ind.rows["qcew_industry_area"][0]["qcew_key"]
        k2 = area.rows["qcew_industry_area"][0]["qcew_key"]
        self.assertNotEqual(k1, k2)
        # ... but the natural observation suffix is identical.
        self.assertEqual(k1.split(":", 1)[1], k2.split(":", 1)[1])

    def test_row_missing_area_fips_is_skipped(self):
        spec = get_endpoint("industry_area")
        res = normalize(spec, [{"area_fips": "  ", "own_code": "5"}])
        self.assertEqual(res.rows.get("qcew_industry_area", []), [])

    def test_unknown_column_is_audited_not_dropped_silently(self):
        spec = get_endpoint("industry_area")
        rec = dict(industry_622_rows()[0])
        rec["brand_new_bls_column"] = "x"
        res = normalize(spec, [rec])
        self.assertEqual(res.unmapped, {"brand_new_bls_column": 1})
        # The known columns still landed.
        self.assertEqual(len(res.rows["qcew_industry_area"]), 1)

    def test_disclosure_suppressed_row_is_kept(self):
        # Suppressed rows (disclosure_code N, zeroed measures) are real
        # observations — dropping them would misreport "no data" as
        # "never fetched".
        spec = get_endpoint("industry_area")
        rows = normalize(spec, industry_622_rows()).rows["qcew_industry_area"]
        suppressed = [r for r in rows if r["disclosure_code"] == "N"]
        self.assertEqual(len(suppressed), 1)
        self.assertEqual(suppressed[0]["area_fips"], "48117")


if __name__ == "__main__":
    unittest.main()
