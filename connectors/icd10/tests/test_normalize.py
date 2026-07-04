import unittest

from ..endpoints import get_endpoint
from ..normalize import category_of, chapter_of, normalize


class DerivationTests(unittest.TestCase):
    def test_chapter_is_first_char(self):
        self.assertEqual(chapter_of("E11.65"), "E")
        self.assertEqual(chapter_of("0DTJ4ZZ"), "0")
        self.assertEqual(chapter_of(""), "")

    def test_category_is_three_chars_before_dot(self):
        self.assertEqual(category_of("E11.65"), "E11")
        self.assertEqual(category_of("E11"), "E11")
        self.assertEqual(category_of("0DTJ4ZZ"), "0DT")


class NormalizeCmTests(unittest.TestCase):
    def test_cm_row_composes_key_and_derives(self):
        spec = get_endpoint("cm")
        rec = {"code": "E11.65", "code_type": "cm",
               "name": "Type 2 diabetes mellitus with hyperglycemia",
               "weird_extra": "drift"}
        res = normalize(spec, [rec])
        row = res.rows["dim_icd10_code"][0]
        self.assertEqual(row["code_key"], "cm:E11.65")
        self.assertEqual(row["code_type"], "cm")
        self.assertEqual(row["chapter"], "E")
        self.assertEqual(row["category"], "E11")
        self.assertEqual(row["long_name"], "")     # absent → blank
        self.assertEqual(row["billable"], "")
        self.assertEqual(row["source_endpoint"], "cm")
        self.assertIn("E11.65", res.codes)
        self.assertIn("weird_extra", res.unmapped)

    def test_missing_code_is_skipped(self):
        spec = get_endpoint("cm")
        res = normalize(spec, [{"name": "no code here"}])
        self.assertEqual(res.rows.get("dim_icd10_code", []), [])


class NormalizePcsTests(unittest.TestCase):
    def test_pcs_row_composes_key_and_derives(self):
        spec = get_endpoint("pcs")
        rec = {"code": "0DTJ4ZZ", "code_type": "pcs",
               "name": "Resection of Appendix, Percutaneous Endoscopic Approach",
               "long_name": "Resection of Appendix, Percutaneous Endoscopic Approach"}
        res = normalize(spec, [rec])
        row = res.rows["dim_icd10_code"][0]
        self.assertEqual(row["code_key"], "pcs:0DTJ4ZZ")
        self.assertEqual(row["code_type"], "pcs")
        self.assertEqual(row["chapter"], "0")
        self.assertEqual(row["category"], "0DT")
        self.assertTrue(row["long_name"].startswith("Resection of Appendix"))
        self.assertEqual(row["source_endpoint"], "pcs")

    def test_cm_and_pcs_keys_do_not_collide(self):
        cm = normalize(get_endpoint("cm"),
                       [{"code": "0DT", "name": "x"}]).rows["dim_icd10_code"][0]
        pcs = normalize(get_endpoint("pcs"),
                        [{"code": "0DT", "name": "y"}]).rows["dim_icd10_code"][0]
        self.assertNotEqual(cm["code_key"], pcs["code_key"])
        self.assertEqual(cm["code_key"], "cm:0DT")
        self.assertEqual(pcs["code_key"], "pcs:0DT")


if __name__ == "__main__":
    unittest.main()
