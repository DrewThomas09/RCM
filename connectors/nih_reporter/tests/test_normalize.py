import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize
from .fakes import project_record, publication_record


class NormalizeTests(unittest.TestCase):
    def test_project_mapper_flattens_nested_fields(self):
        res = normalize(get_endpoint("projects"), [project_record()])
        rows = res.rows["nih_projects"]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["appl_id"], 11184227)
        self.assertEqual(row["project_num"], "5R37GM070977-24")
        self.assertEqual(row["core_project_num"], "R37GM070977")
        self.assertEqual(row["fiscal_year"], 2025)
        # organization.* flattened to scalar columns
        self.assertEqual(row["org_name"],
                         "UNIVERSITY OF TX MD ANDERSON CAN CTR")
        self.assertEqual(row["org_city"], "HOUSTON")
        self.assertEqual(row["org_state"], "TX")
        self.assertEqual(row["org_uei"], "S3GMKS8ELA16")
        # agency_ic_admin → abbreviation
        self.assertEqual(row["agency_ic_admin"], "NIGMS")
        self.assertEqual(row["agency_ic_admin_name"],
                         "National Institute of General Medical Sciences")
        # person lists joined; RePORTER's double-space padding normalised
        self.assertEqual(row["pi_names"], "Alejandro Aballay")
        self.assertEqual(row["pi_profile_ids"], "7604113")
        self.assertEqual(row["program_officer_names"], "XIAOLI ZHAO")
        self.assertEqual(row["contact_pi_name"], "ABALLAY, ALEJANDRO")
        # money + geo
        self.assertEqual(row["award_amount"], 408750)
        self.assertEqual(row["direct_cost_amt"], 250000)
        self.assertEqual(row["org_latitude"], 29.706319)
        self.assertEqual(row["organization_type"], "HOSPITALS")
        self.assertEqual(row["full_study_section"], "NSS")
        self.assertIs(row["is_active"], True)
        self.assertEqual(row["source_endpoint"], "projects")

    def test_project_known_blobs_do_not_flag_drift(self):
        # abstract_text/terms/... are deliberately dropped, not "drift".
        res = normalize(get_endpoint("projects"), [project_record()])
        self.assertEqual(res.unmapped, {})

    def test_project_new_field_flags_drift(self):
        rec = project_record()
        rec["brand_new_field"] = "surprise"
        res = normalize(get_endpoint("projects"), [rec])
        self.assertEqual(res.unmapped, {"brand_new_field": 1})

    def test_project_missing_nested_objects_is_safe(self):
        res = normalize(get_endpoint("projects"), [
            {"appl_id": 42, "project_title": "Bare"}])
        row = res.rows["nih_projects"][0]
        self.assertEqual(row["appl_id"], 42)
        self.assertIsNone(row["org_name"])
        self.assertIsNone(row["pi_names"])
        self.assertIsNone(row["award_amount"])

    def test_project_missing_id_is_skipped(self):
        res = normalize(get_endpoint("projects"), [{"project_title": "orphan"}])
        self.assertEqual(res.rows.get("nih_projects", []), [])

    def test_publication_mapper_composes_link_key(self):
        res = normalize(get_endpoint("publications"), [publication_record()])
        row = res.rows["nih_publications"][0]
        self.assertEqual(row["pub_key"], "23959030:10247478")
        self.assertEqual(row["pmid"], 23959030)
        self.assertEqual(row["appl_id"], 10247478)
        self.assertEqual(row["core_project_num"], "R37GM070977")
        self.assertEqual(row["source_endpoint"], "publications")

    def test_publication_missing_pmid_is_skipped(self):
        res = normalize(get_endpoint("publications"),
                        [{"coreproject": "R01X", "applid": 1}])
        self.assertEqual(res.rows.get("nih_publications", []), [])


if __name__ == "__main__":
    unittest.main()
