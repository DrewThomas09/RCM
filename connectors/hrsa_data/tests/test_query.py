import unittest

from ..query import QueryError, aggregate, query
from ..tables import HrsaDataStore


def _hpsa(hpsa_id, name, state, score, source, discipline):
    key_disc = {"hpsa_primary_care": "primary_care",
                "hpsa_dental": "dental",
                "hpsa_mental_health": "mental_health"}[source]
    return {"hpsa_key": f"{hpsa_id}:{key_disc}:{state}001",
            "hpsa_id": hpsa_id, "hpsa_name": name,
            "hpsa_discipline_class": discipline, "hpsa_score": score,
            "common_state_abbreviation": state, "hpsa_status": "Designated",
            "source_endpoint": source}


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = HrsaDataStore(":memory:")
        self.store.upsert("hrsa_hpsa", [
            _hpsa("100", "Lubbock County", "TX", "18",
                  "hpsa_primary_care", "Primary Care"),
            _hpsa("101", "Deaf Smith County", "TX", "21",
                  "hpsa_primary_care", "Primary Care"),
            _hpsa("102", "Marshall Islands", "MH", "25",
                  "hpsa_primary_care", "Primary Care"),
            # A different file sharing the same table (must be sliced out).
            _hpsa("500", "Lubbock Dental", "TX", "26",
                  "hpsa_dental", "Dental Health"),
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "hrsa_data_hpsa_primary_care",
                    filters={"common_state_abbreviation": "MH"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["hpsa_id"], "102")

    def test_slice_excludes_other_discipline(self):
        # The dental row shares the table but must not appear for the
        # primary-care dataset.
        res = query(self.store, "hrsa_data_hpsa_primary_care")
        self.assertEqual(res.total, 3)
        self.assertTrue(all(r["hpsa_discipline_class"] == "Primary Care"
                            for r in res.rows))
        res_dh = query(self.store, "hrsa_data_hpsa_dental")
        self.assertEqual(res_dh.total, 1)
        self.assertEqual(res_dh.rows[0]["hpsa_id"], "500")

    def test_like_filter(self):
        res = query(self.store, "hrsa_data_hpsa_primary_care",
                    filters={"hpsa_name__like": "%County%"})
        self.assertEqual(res.total, 2)

    def test_in_filter(self):
        res = query(self.store, "hrsa_data_hpsa_primary_care",
                    filters={"hpsa_id__in": ["100", "102"]})
        self.assertEqual(res.total, 2)

    def test_gte_and_sort(self):
        res = query(self.store, "hrsa_data_hpsa_primary_care",
                    filters={"hpsa_score__gte": "20"},
                    sort=["-hpsa_score"])
        self.assertEqual([r["hpsa_id"] for r in res.rows], ["102", "101"])

    def test_select_projects_columns(self):
        res = query(self.store, "hrsa_data_hpsa_primary_care",
                    select=["hpsa_id", "hpsa_name"], limit=1)
        self.assertEqual(set(res.rows[0].keys()), {"hpsa_id", "hpsa_name"})

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "hrsa_data_hpsa_primary_care",
                        group_by=["common_state_abbreviation"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"common_state_abbreviation": "TX", "count": 2})

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "hrsa_data_hpsa_primary_care",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "hrsa_data_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "hrsa_data_hpsa_primary_care", limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "hrsa_data_hpsa_primary_care", limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
