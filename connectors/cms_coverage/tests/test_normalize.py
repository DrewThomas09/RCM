import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize


class NormalizeTests(unittest.TestCase):
    def test_national_document_mapper(self):
        rec = {"document_id": 169, "document_version": 2,
               "document_display_id": "240.2", "document_type": "NCD",
               "title": "Home Use of Oxygen", "chapter": "240", "is_lab": 0,
               "last_updated": "12/02/2024", "last_updated_sort": "20241202131453",
               "url": "/data/ncd?ncdid=169&ncdver=2"}
        res = normalize(get_endpoint("national_ncd"), [rec])
        rows = res.rows["dim_coverage_document"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["document_key"], "NCD:169:2")
        self.assertEqual(row["coverage_level"], "national")
        self.assertEqual(row["title"], "Home Use of Oxygen")
        self.assertIsNone(row["contractor_id"])
        self.assertEqual(row["source_endpoint"], "national_ncd")

    def test_local_document_mapper_carries_contractor(self):
        rec = {"document_id": 39044, "document_version": 5,
               "document_display_id": "L39044", "document_type": "LCD",
               "title": "MolDX", "chapter": "", "is_lab": 1,
               "contractor_id": 236, "contractor_name": "CGS Administrators, LLC",
               "last_updated": "01/15/2025", "last_updated_sort": "20250115090000",
               "url": "/data/lcd?lcdid=39044"}
        res = normalize(get_endpoint("local_lcd"), [rec])
        row = res.rows["dim_coverage_document"][0]
        self.assertEqual(row["document_key"], "LCD:39044:5")
        self.assertEqual(row["coverage_level"], "local")
        self.assertEqual(row["contractor_id"], 236)
        self.assertEqual(row["contractor_name"], "CGS Administrators, LLC")
        self.assertEqual(row["source_endpoint"], "local_lcd")

    def test_contractor_mapper(self):
        rec = {"contractor_id": 236, "contractor_version": 2,
               "contractor_name": "CGS Administrators, LLC",
               "contract_type_id": 11, "contract_subtype_id": 3,
               "contract_number": "15004"}
        res = normalize(get_endpoint("contractors"), [rec])
        row = res.rows["dim_medicare_contractor"][0]
        self.assertEqual(row["contractor_key"], "236:2")
        self.assertEqual(row["contractor_name"], "CGS Administrators, LLC")
        self.assertEqual(row["contract_number"], "15004")
        self.assertEqual(row["source_endpoint"], "contractors")

    def test_row_missing_id_is_skipped(self):
        res = normalize(get_endpoint("national_ncd"), [{"title": "orphan"}])
        self.assertEqual(res.rows.get("dim_coverage_document", []), [])


if __name__ == "__main__":
    unittest.main()
