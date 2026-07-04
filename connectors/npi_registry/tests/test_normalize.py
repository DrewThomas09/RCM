import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from .fakes import INDIVIDUAL, ORGANIZATION


class NormalizeIndividualTests(unittest.TestCase):
    def test_individual_flattens_primary_address_and_taxonomy(self):
        spec = get_endpoint("provider_individual")
        res = normalize(spec, [dict(INDIVIDUAL)])
        prov = res.rows["dim_provider"][0]
        self.assertEqual(prov["npi"], "1234567893")
        self.assertEqual(prov["enumeration_type"], "NPI-1")
        self.assertEqual(prov["first_name"], "JANE")
        self.assertEqual(prov["last_name"], "DOE")
        self.assertEqual(prov["credential"], "MD")
        # Primary taxonomy flattened on.
        self.assertEqual(prov["primary_taxonomy_code"], "207RC0000X")
        self.assertEqual(prov["primary_taxonomy_desc"], "Cardiovascular Disease")
        self.assertEqual(prov["primary_license"], "12345")
        # Primary LOCATION address flattened on (not the MAILING one).
        self.assertEqual(prov["city"], "BALTIMORE")
        self.assertEqual(prov["state"], "MD")
        self.assertEqual(prov["postal_code"], "212011234")
        self.assertEqual(prov["telephone"], "410-555-1212")
        self.assertEqual(prov["source_endpoint"], "provider_individual")

    def test_individual_taxonomy_and_address_rows_with_keys(self):
        spec = get_endpoint("provider_individual")
        res = normalize(spec, [dict(INDIVIDUAL)])
        tax = {r["taxonomy_key"]: r for r in res.rows["fact_provider_taxonomy"]}
        self.assertIn("1234567893:207RC0000X", tax)
        self.assertEqual(tax["1234567893:207RC0000X"]["is_primary"], "1")
        self.assertEqual(tax["1234567893:207R00000X"]["is_primary"], "0")
        addr = {r["address_key"]: r for r in res.rows["fact_provider_address"]}
        self.assertIn("1234567893:LOCATION", addr)
        self.assertIn("1234567893:MAILING", addr)
        self.assertEqual(addr["1234567893:LOCATION"]["address_1"], "123 MAIN ST")


class NormalizeOrganizationTests(unittest.TestCase):
    def test_organization_maps_org_name_no_person_name(self):
        spec = get_endpoint("provider_organization")
        res = normalize(spec, [dict(ORGANIZATION)])
        prov = res.rows["dim_provider"][0]
        self.assertEqual(prov["npi"], "1245319599")
        self.assertEqual(prov["enumeration_type"], "NPI-2")
        self.assertEqual(prov["organization_name"], "GENERAL HOSPITAL")
        self.assertIsNone(prov["first_name"])
        self.assertEqual(prov["primary_taxonomy_code"], "282N00000X")
        self.assertEqual(prov["state"], "NY")
        # One taxonomy, one LOCATION address.
        self.assertEqual(len(res.rows["fact_provider_taxonomy"]), 1)
        self.assertEqual(res.rows["fact_provider_address"][0]["address_key"],
                         "1245319599:LOCATION")


if __name__ == "__main__":
    unittest.main()
