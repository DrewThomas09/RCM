import unittest

from ..query import QueryError, aggregate, query
from ..tables import OigLeieStore


def _excl(key, lastname, busname, npi, state, excldate, source="exclusions"):
    return {"exclusion_key": key, "lastname": lastname, "busname": busname,
            "npi": npi, "state": state, "excltype": "1128a1",
            "excldate": excldate, "source_endpoint": source}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = OigLeieStore(":memory:")
        self.store.upsert("oig_exclusions", [
            _excl("k1", "SMITH", "", "1234567893", "VA", "2023-01-15"),
            _excl("k2", "GARZA", "", "", "FL", "1997-06-20"),
            _excl("k3", "", "ACME HOME HEALTH, INC", "", "FL", "2020-03-19"),
            # A row that arrived via a monthly supplement — must still be
            # visible through the exclusions dataset (union view).
            _excl("k4", "OKAFOR", "", "1558362563", "OH", "2026-05-01",
                  source="supplement:2026-05"),
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "oig_leie_exclusions",
                    filters={"state": "FL"})
        self.assertEqual(res.total, 2)

    def test_union_view_includes_supplement_rows(self):
        # No source_filter pinning: a compliance screen of the
        # exclusions dataset must see rows added by the supplement.
        res = query(self.store, "oig_leie_exclusions")
        self.assertEqual(res.total, 4)
        res_supp = query(self.store, "oig_leie_supplement")
        self.assertEqual(res_supp.total, 4)   # same cumulative table

    def test_like_filter(self):
        res = query(self.store, "oig_leie_exclusions",
                    filters={"busname__like": "%HOME HEALTH%"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["exclusion_key"], "k3")

    def test_in_filter(self):
        res = query(self.store, "oig_leie_exclusions",
                    filters={"lastname__in": ["SMITH", "OKAFOR"]})
        self.assertEqual(res.total, 2)

    def test_gte_and_sort(self):
        res = query(self.store, "oig_leie_exclusions",
                    filters={"excldate__gte": "2020-01-01"},
                    sort=["-excldate"])
        self.assertEqual([r["exclusion_key"] for r in res.rows],
                         ["k4", "k1", "k3"])

    def test_isnull_matches_empty_npi(self):
        # The zero-NPI sentinel is normalized to '' — isnull treats ''
        # as null, so this is the "no NPI on record" slice.
        res = query(self.store, "oig_leie_exclusions",
                    filters={"npi__isnull": "1"})
        self.assertEqual(res.total, 2)

    def test_select_projects_columns(self):
        res = query(self.store, "oig_leie_exclusions",
                    select=["lastname", "npi"], limit=1)
        self.assertEqual(set(res.rows[0].keys()), {"lastname", "npi"})

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "oig_leie_exclusions",
                        group_by=["state"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"state": "FL", "count": 2})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "oig_leie_exclusions", filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "oig_leie_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "oig_leie_exclusions", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "oig_leie_exclusions", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound

    def test_reinstatements_dataset_targets_own_table(self):
        self.store.upsert("oig_reinstatements", [
            {"reinstatement_key": "r1", "lastname": "ACHU",
             "npi": "1234567893", "reindate": "2026-05-19",
             "source_endpoint": "reinstatements:2026-05"}])
        res = query(self.store, "oig_leie_reinstatements")
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["reinstatement_key"], "r1")


if __name__ == "__main__":
    unittest.main()
