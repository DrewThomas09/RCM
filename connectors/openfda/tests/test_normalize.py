import unittest

from ..endpoints import get_endpoint
from ..normalize import company_key, ndc11, normalize


class CompanyKeyTests(unittest.TestCase):
    def test_variants_collapse_to_one_key(self):
        a = company_key("Acme Pharma, Inc.")
        b = company_key("ACME PHARMACEUTICALS LLC")
        self.assertEqual(a, b)
        self.assertEqual(a, "co_acme")

    def test_empty_is_none(self):
        self.assertIsNone(company_key(""))
        self.assertIsNone(company_key(None))


class Ndc11Tests(unittest.TestCase):
    def test_two_segment_pads(self):
        self.assertEqual(ndc11("0002-1200"), "000021200")

    def test_garbage_returns_digits_or_none(self):
        self.assertIsNone(ndc11(""))
        self.assertEqual(ndc11("abc123"), "123")


class NormalizeDrugTests(unittest.TestCase):
    def test_drug_ndc_maps_and_rolls_up_company(self):
        spec = get_endpoint("drug_ndc")
        rec = {"product_ndc": "0002-1200", "brand_name": "FOO",
               "generic_name": "foo sodium", "labeler_name": "Acme Inc",
               "dosage_form": "TABLET", "route": ["ORAL"],
               "marketing_category": "NDA", "application_number": "NDA001",
               "weird_new_field": 7}
        res = normalize(spec, [rec])
        row = res.rows["dim_drug_product"][0]
        self.assertEqual(row["ndc"], "0002-1200")
        self.assertEqual(row["route"], "ORAL")
        self.assertEqual(row["company_key"], "co_acme")
        self.assertIn("0002-1200", res.ndcs)
        # unmapped audit catches the unknown field
        self.assertIn("weird_new_field", res.unmapped)

    def test_drug_event_extracts_primary_drug_ndc(self):
        spec = get_endpoint("drug_event")
        rec = {"safetyreportid": "99", "receivedate": "20200101", "serious": "1",
               "patient": {"patientsex": "1",
                           "drug": [{"medicinalproduct": "FOO",
                                     "openfda": {"product_ndc": ["0002-1200"]}}],
                           "reaction": [{"reactionmeddrapt": "Nausea"}]}}
        res = normalize(spec, [rec])
        row = res.rows["fact_drug_adverse_event"][0]
        self.assertEqual(row["safetyreportid"], "99")
        self.assertEqual(row["ndc"], "0002-1200")
        self.assertEqual(row["reaction_pt"], "Nausea")


class NormalizeDeviceTests(unittest.TestCase):
    def test_510k_maps_with_decision_date(self):
        spec = get_endpoint("device_510k")
        rec = {"k_number": "K123", "product_code": "ABC",
               "device_name": "Widget", "applicant": "DeviceCo Inc",
               "decision_date": "2019-05-01", "decision_description": "SESE",
               "openfda": {"device_class": ["2"], "regulation_number": ["888.1"]}}
        res = normalize(spec, [rec])
        row = res.rows["dim_device"][0]
        self.assertEqual(row["device_key"], "K:K123")
        self.assertEqual(row["product_code"], "ABC")
        self.assertEqual(row["device_class"], "2")
        self.assertEqual(row["decision_date"], "2019-05-01")
        self.assertIn("ABC", res.product_codes)

    def test_device_event_and_recall_distinct_keys(self):
        ev = normalize(get_endpoint("device_event"), [
            {"report_number": "R1", "date_received": "20200101",
             "device": [{"device_report_product_code": "ABC",
                         "manufacturer_d_name": "DeviceCo"}]}])
        self.assertEqual(ev.rows["fact_device_adverse_event"][0]["product_code"], "ABC")

        enf = normalize(get_endpoint("device_enforcement"), [
            {"recall_number": "Z-1", "report_date": "20200101",
             "product_code": "ABC", "recalling_firm": "DeviceCo"}])
        self.assertTrue(enf.rows["fact_device_recall"][0]["recall_id"].startswith("ENF:"))


if __name__ == "__main__":
    unittest.main()
