import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, snake
from ..tables import TABLES
from .fakes import hpsa_pc_rows, mua_rows, sites_rows


class SnakeTests(unittest.TestCase):
    def test_documented_examples(self):
        self.assertEqual(snake("MUA/P ID"), "mua_p_id")
        self.assertEqual(snake("% of Population Below 100% Poverty"),
                         "pct_of_population_below_100_pct_poverty")
        self.assertEqual(snake("U.S. - Mexico Border 100 Kilometer Indicator"),
                         "u_s_mexico_border_100_kilometer_indicator")
        self.assertEqual(snake("HPSA ID"), "hpsa_id")
        self.assertEqual(snake("  Padded Header  "), "padded_header")

    def test_table_columns_are_snake_fixed_points(self):
        # Every declared column must be stable under snake() — proof the
        # schema really is "live headers passed through the one rule".
        for tdef in TABLES.values():
            for col in tdef.columns:
                self.assertEqual(snake(col), col)


class NormalizeTests(unittest.TestCase):
    def test_hpsa_mapper_composes_key_and_strips_values(self):
        spec = get_endpoint("hpsa_primary_care")
        res = normalize(spec, hpsa_pc_rows())
        rows = res.rows["hrsa_hpsa"]
        self.assertEqual(len(rows), 3)
        row = rows[0]
        self.assertEqual(row["hpsa_key"], "1481234567:primary_care:48303")
        self.assertEqual(row["hpsa_name"], "Lubbock County")
        self.assertEqual(row["hpsa_discipline_class"], "Primary Care")
        self.assertEqual(row["pc_mcta_score"], "6")   # " 6" stripped
        self.assertEqual(row["source_endpoint"], "hpsa_primary_care")
        self.assertEqual(res.unmapped, {})

    def test_hpsa_disciplines_cannot_collide_across_files(self):
        # Same raw record through two discipline specs → different keys,
        # the invariant that makes the shared hrsa_hpsa table safe.
        rec = hpsa_pc_rows()[0]
        pc = normalize(get_endpoint("hpsa_primary_care"), [rec])
        mh = normalize(get_endpoint("hpsa_mental_health"), [rec])
        self.assertNotEqual(pc.rows["hrsa_hpsa"][0]["hpsa_key"],
                            mh.rows["hrsa_hpsa"][0]["hpsa_key"])

    def test_mua_mapper_distinguishes_reused_ids(self):
        spec = get_endpoint("mua")
        res = normalize(spec, mua_rows())
        rows = res.rows["hrsa_mua"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            rows[0]["mua_key"],
            "1512420473:Augusta-Staunton-Waynesboro MUP:51015::"
            "Not Applicable:Augusta")
        # Fixed-width padding in the source is stripped.
        self.assertEqual(rows[0]["county_description"], "County")
        # The Designated/Withdrawn pair sharing id + geography must get
        # distinct keys (service-area name disambiguates).
        self.assertNotEqual(rows[1]["mua_key"], rows[2]["mua_key"])
        self.assertEqual(rows[1]["mua_p_id"], rows[2]["mua_p_id"])

    def test_sites_mapper_keys_on_bphc_number(self):
        spec = get_endpoint("health_center_sites")
        res = normalize(spec, sites_rows())
        rows = res.rows["hrsa_health_center_sites"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["site_key"], "BPS-H80-041310")
        self.assertEqual(rows[0]["fqhc_site_npi_number"], "1234567893")
        self.assertEqual(rows[0]["grantee_organization_type_description"],
                         "Corporate Entity, Federal Tax Exempt")
        self.assertEqual(rows[0]["source_endpoint"], "health_center_sites")

    def test_row_missing_id_is_skipped(self):
        spec = get_endpoint("hpsa_primary_care")
        res = normalize(spec, [{"HPSA Name": "orphan", "HPSA ID": "  "}])
        self.assertEqual(res.rows.get("hrsa_hpsa", []), [])

    def test_unknown_column_is_audited_not_dropped_silently(self):
        spec = get_endpoint("mua")
        rec = dict(mua_rows()[0])
        rec["Brand New HRSA Column"] = "x"
        res = normalize(spec, [rec])
        self.assertEqual(res.unmapped, {"brand_new_hrsa_column": 1})
        # The known columns still landed.
        self.assertEqual(len(res.rows["hrsa_mua"]), 1)


if __name__ == "__main__":
    unittest.main()
