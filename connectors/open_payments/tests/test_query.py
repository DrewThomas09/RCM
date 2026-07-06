import unittest

from ..normalize import normalize_generic
from ..query import QueryError, aggregate, query
from ..tables import OpenPaymentsStore
from .fakes import general_payment_row


def _payment(record_id, state, amount, nature="Food and Beverage"):
    row = {c: v for c, v in general_payment_row(
        record_id, state=state, amount=amount, nature=nature).items()}
    row["source_endpoint"] = "general_payments_2024"
    return row


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenPaymentsStore(":memory:")
        self.store.upsert("op_general_payment", [
            _payment("1", "VT", "175.14"),
            _payment("2", "VT", "20.74", nature="Travel and Lodging"),
            _payment("3", "CA", "5000.00", nature="Consulting Fee"),
            # A drifted row tagged with a different endpoint must be
            # excluded by the registry's source_endpoint pinning.
            {**_payment("9", "VT", "1.00"),
             "source_endpoint": "somewhere_else"},
        ])

    def tearDown(self):
        self.store.close()

    def test_equality_filter(self):
        res = query(self.store, "open_payments_general_payments_2024",
                    filters={"recipient_state": "CA"})
        self.assertEqual(res.total, 1)
        self.assertEqual(res.rows[0]["record_id"], "3")

    def test_slice_pins_source_endpoint(self):
        res = query(self.store, "open_payments_general_payments_2024")
        self.assertEqual(res.total, 3)          # the drifted row is excluded
        self.assertNotIn("9", {r["record_id"] for r in res.rows})

    def test_like_and_in_filters(self):
        res = query(self.store, "open_payments_general_payments_2024",
                    filters={"nature_of_payment_or_transfer_of_value__like":
                             "%Travel%"})
        self.assertEqual(res.total, 1)
        res2 = query(self.store, "open_payments_general_payments_2024",
                     filters={"record_id__in": ["1", "3"]})
        self.assertEqual(res2.total, 2)

    def test_select_sort_and_offset(self):
        res = query(self.store, "open_payments_general_payments_2024",
                    select=["record_id", "recipient_state"],
                    sort=["-record_id"], limit=2, offset=1)
        self.assertEqual(list(res.rows[0].keys()),
                         ["record_id", "recipient_state"])
        self.assertEqual(res.rows[0]["record_id"], "2")

    def test_aggregate_group_by_count(self):
        res = aggregate(self.store, "open_payments_general_payments_2024",
                        group_by=["recipient_state"])
        top = res.as_dict()["rows"][0]
        self.assertEqual(top, {"recipient_state": "VT", "count": 2})

    def test_generic_rows_sliced_by_dataset_key(self):
        # fetched_rows has an empty source_filter: two on-demand datasets
        # share the table and are separated by an explicit dataset_key filter.
        self.store.upsert("open_payments_rows", normalize_generic(
            "uuid-a", [general_payment_row("1")]).rows["open_payments_rows"])
        self.store.upsert("open_payments_rows", normalize_generic(
            "uuid-b", [general_payment_row("2")]).rows["open_payments_rows"])
        everything = query(self.store, "open_payments_fetched_rows")
        self.assertEqual(everything.total, 2)
        sliced = query(self.store, "open_payments_fetched_rows",
                       filters={"dataset_key": "uuid-a"})
        self.assertEqual(sliced.total, 1)
        self.assertEqual(sliced.rows[0]["row_key"], "uuid-a:00000000")
        # row_json stays LIKE-searchable through the uniform grammar.
        by_content = query(self.store, "open_payments_fetched_rows",
                           filters={"row_json__like": '%"record_id": "2"%'})
        self.assertEqual(by_content.total, 1)

    def test_unknown_field_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "open_payments_general_payments_2024",
                  filters={"nope": "x"})

    def test_unknown_dataset_raises(self):
        with self.assertRaises(QueryError):
            query(self.store, "open_payments_does_not_exist")

    def test_limit_is_clamped(self):
        res = query(self.store, "open_payments_general_payments_2024",
                    limit=999999)
        self.assertEqual(res.limit, 1000)      # clamped to _MAX_LIMIT
        res2 = query(self.store, "open_payments_general_payments_2024",
                     limit=0)
        self.assertEqual(res2.limit, 1)        # clamped up to lower bound


if __name__ == "__main__":
    unittest.main()
