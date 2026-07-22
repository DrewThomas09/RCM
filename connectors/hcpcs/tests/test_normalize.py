import unittest

from ..endpoints import get_endpoint
from ..normalize import category_of, normalize, section_of


class DerivationTests(unittest.TestCase):
    def test_section_is_first_char(self):
        self.assertEqual(section_of("J9271"), "J")
        self.assertEqual(section_of("E0601"), "E")
        self.assertEqual(section_of(""), "")

    def test_category_is_three_chars(self):
        self.assertEqual(category_of("J9271"), "J92")
        self.assertEqual(category_of("E0601"), "E06")
        self.assertEqual(category_of("A0"), "A0")


class NormalizeLvl2Tests(unittest.TestCase):
    def test_row_composes_key_and_derives(self):
        spec = get_endpoint("lvl2")
        rec = {"code": "J9271", "code_type": "lvl2",
               "display": "Injection, pembrolizumab, 1 mg",
               "short_desc": "Pembrolizumab",
               "weird_extra": "drift"}
        res = normalize(spec, [rec])
        row = res.rows["dim_hcpcs_code"][0]
        self.assertEqual(row["code_key"], "lvl2:J9271")
        self.assertEqual(row["code_type"], "lvl2")
        self.assertEqual(row["section"], "J")
        self.assertEqual(row["category"], "J92")
        self.assertEqual(row["long_desc"], "")     # absent → blank
        self.assertEqual(row["obsolete"], "")
        self.assertEqual(row["source_endpoint"], "lvl2")
        self.assertIn("J9271", res.codes)
        self.assertIn("weird_extra", res.unmapped)

    def test_code_is_upper_cased(self):
        spec = get_endpoint("lvl2")
        res = normalize(spec, [{"code": "e0601", "display": "CPAP device"}])
        row = res.rows["dim_hcpcs_code"][0]
        self.assertEqual(row["code"], "E0601")
        self.assertEqual(row["code_key"], "lvl2:E0601")
        self.assertEqual(row["section"], "E")

    def test_missing_code_is_skipped(self):
        spec = get_endpoint("lvl2")
        res = normalize(spec, [{"display": "no code here"}])
        self.assertEqual(res.rows.get("dim_hcpcs_code", []), [])


if __name__ == "__main__":
    unittest.main()
