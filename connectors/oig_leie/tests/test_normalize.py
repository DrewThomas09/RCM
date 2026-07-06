import unittest

from ..endpoints import get_endpoint
from ..normalize import clean_npi, iso_date, normalize, snake
from .fakes import supplement_rein_rows, updated_rows


class SnakeTests(unittest.TestCase):
    def test_live_headers_map_to_columns(self):
        self.assertEqual(snake("LASTNAME"), "lastname")
        self.assertEqual(snake("WVRSTATE"), "wvrstate")
        self.assertEqual(snake("EXCLTYPE"), "excltype")

    def test_prose_header_future_proofing(self):
        # OIG's headers are single tokens today; the rule still handles
        # prose so schema drift lands as a clean column name.
        self.assertEqual(snake("Waiver State/Code"), "waiver_state_code")


class ValueRuleTests(unittest.TestCase):
    def test_clean_npi_zero_sentinel_becomes_empty(self):
        self.assertEqual(clean_npi("0000000000"), "")
        self.assertEqual(clean_npi("  0000000000 "), "")
        self.assertEqual(clean_npi(""), "")
        self.assertEqual(clean_npi(None), "")

    def test_clean_npi_real_value_passes_through(self):
        self.assertEqual(clean_npi("1972902351"), "1972902351")

    def test_iso_date_yyyymmdd(self):
        self.assertEqual(iso_date("20200319"), "2020-03-19")

    def test_iso_date_null_sentinel_and_empty(self):
        self.assertEqual(iso_date("00000000"), "")
        self.assertEqual(iso_date(""), "")
        self.assertEqual(iso_date(None), "")

    def test_iso_date_unexpected_format_passes_through_visibly(self):
        # Drift must be visible in the data, not silently erased.
        self.assertEqual(iso_date("2020-03-19"), "2020-03-19")
        self.assertEqual(iso_date("3/19/2020"), "3/19/2020")


class NormalizeTests(unittest.TestCase):
    def test_full_file_rows_normalize_with_sentinels_cleaned(self):
        spec = get_endpoint("exclusions")
        res = normalize(spec, updated_rows())
        rows = res.rows["oig_exclusions"]
        self.assertEqual(len(rows), 4)
        self.assertEqual(res.unmapped, {})
        biz = rows[0]
        self.assertEqual(biz["busname"], "#1 MARKETING SERVICE, INC")
        self.assertEqual(biz["npi"], "")                # zero sentinel gone
        self.assertEqual(biz["excldate"], "2020-03-19") # ISO
        self.assertEqual(biz["reindate"], "")           # 00000000 → ''
        self.assertEqual(biz["source_endpoint"], "exclusions")
        ind = rows[2]
        self.assertEqual(ind["npi"], "1234567893")
        self.assertEqual(ind["dob"], "1970-12-05")

    def test_exclusion_key_composition_uses_normalized_values(self):
        spec = get_endpoint("exclusions")
        rows = normalize(spec, updated_rows()).rows["oig_exclusions"]
        # lastname:firstname:midname:busname:dob:excldate:npi:address
        self.assertEqual(
            rows[2]["exclusion_key"],
            "SMITH:JOHN:A::1970-12-05:2023-01-15:1234567893:"
            "12824 CANOVA DRIVE")
        # Zero-NPI business: npi part is empty, address disambiguates
        # multi-location entities.
        self.assertEqual(
            rows[0]["exclusion_key"],
            ":::#1 MARKETING SERVICE, INC::2020-03-19::"
            "239 BRIGHTON BEACH AVENUE")

    def test_key_is_identical_from_full_file_and_supplement(self):
        # The same record arriving via UPDATED.csv and via a monthly
        # supplement must upsert to the same key — that is what makes
        # the supplement an incremental add rather than a duplicate.
        rec = updated_rows()[2]
        full = normalize(get_endpoint("exclusions"), [rec])
        supp = normalize(get_endpoint("supplement"), [rec],
                         month_tag="2026-05")
        k_full = full.rows["oig_exclusions"][0]["exclusion_key"]
        k_supp = supp.rows["oig_exclusions"][0]["exclusion_key"]
        self.assertEqual(k_full, k_supp)

    def test_supplement_month_tag_lands_in_source_endpoint(self):
        spec = get_endpoint("supplement")
        rows = normalize(spec, updated_rows()[:1],
                         month_tag="2026-05").rows["oig_exclusions"]
        self.assertEqual(rows[0]["source_endpoint"], "supplement:2026-05")

    def test_reinstatement_key_appends_reindate(self):
        spec = get_endpoint("reinstatements")
        rows = normalize(spec, supplement_rein_rows(),
                         month_tag="2026-05").rows["oig_reinstatements"]
        self.assertTrue(rows[1]["reinstatement_key"].endswith(":2026-05-19"))
        self.assertEqual(rows[1]["source_endpoint"],
                         "reinstatements:2026-05")

    def test_blank_row_is_skipped(self):
        spec = get_endpoint("exclusions")
        blank = {h: "" for h in updated_rows()[0]}
        res = normalize(spec, [blank])
        self.assertEqual(res.rows.get("oig_exclusions", []), [])

    def test_undeclared_column_is_audited_not_dropped_silently(self):
        spec = get_endpoint("exclusions")
        rec = dict(updated_rows()[0], **{"NEWCOL": "x"})
        res = normalize(spec, [rec])
        self.assertEqual(res.unmapped, {"newcol": 1})
        # The declared columns still landed.
        self.assertEqual(len(res.rows["oig_exclusions"]), 1)

    def test_values_are_whitespace_stripped(self):
        spec = get_endpoint("exclusions")
        rec = dict(updated_rows()[2], **{"LASTNAME": " SMITH  "})
        row = normalize(spec, [rec]).rows["oig_exclusions"][0]
        self.assertEqual(row["lastname"], "SMITH")


if __name__ == "__main__":
    unittest.main()
