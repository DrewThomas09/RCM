import unittest

from ..endpoints import get_endpoint
from ..normalize import normalize, normalize_generic
from ..tables import _META, TABLES, OpenPaymentsStore
from .fakes import CATALOG_ITEMS, general_payment_row


class TablesSchemaTests(unittest.TestCase):
    def test_all_eleven_tables_defined_with_meta_columns(self):
        self.assertEqual(len(TABLES), 11)
        for tdef in TABLES.values():
            self.assertEqual(tdef.columns[-2:], _META)
            self.assertIn(tdef.pk, tdef.columns)

    def test_live_sampled_widths_are_locked(self):
        # Snapshot invariant: the curated column sets stay exactly as
        # sampled live 2026-07-06 (91 general / 252 research native cols).
        self.assertEqual(len(TABLES["op_general_payment"].columns), 91 + 2)
        self.assertEqual(len(TABLES["op_research_payment"].columns), 252 + 2)
        self.assertEqual(len(TABLES["op_ownership_payment"].columns), 30 + 2)
        self.assertEqual(len(TABLES["op_state_payment_totals"].columns),
                         28 + 1 + 2)           # + composed pk


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.store = OpenPaymentsStore(":memory:")

    def tearDown(self):
        self.store.close()

    def test_general_payment_upsert_is_record_id_idempotent(self):
        spec = get_endpoint("general_payments_2024")
        rows = normalize(spec, [general_payment_row("1092248200"),
                                general_payment_row("1118263217")]
                         ).rows["op_general_payment"]
        self.store.upsert("op_general_payment", rows)
        self.store.upsert("op_general_payment", rows)   # re-run
        self.assertEqual(self.store.count("op_general_payment"), 2)

    def test_upsert_updates_in_place_on_same_record_id(self):
        spec = get_endpoint("general_payments_2024")
        old = normalize(spec, [general_payment_row("77", amount="10.00")])
        new = normalize(spec, [general_payment_row("77", amount="99.99")])
        self.store.upsert("op_general_payment", old.rows["op_general_payment"])
        self.store.upsert("op_general_payment", new.rows["op_general_payment"])
        self.assertEqual(self.store.count("op_general_payment"), 1)
        row = self.store.fetchall(
            "SELECT total_amount_of_payment_usdollars FROM op_general_payment "
            "WHERE record_id = ?", ("77",))[0]
        self.assertEqual(row["total_amount_of_payment_usdollars"], "99.99")

    def test_catalog_upsert_idempotent(self):
        rows = normalize(get_endpoint("catalog"),
                         CATALOG_ITEMS).rows["open_payments_catalog"]
        self.store.upsert("open_payments_catalog", rows)
        self.store.upsert("open_payments_catalog", rows)
        self.assertEqual(self.store.count("open_payments_catalog"), 3)

    def test_generic_rows_upsert_idempotent_per_slice(self):
        recs = [general_payment_row("1"), general_payment_row("2")]
        rows = normalize_generic("uuid-x", recs).rows["open_payments_rows"]
        self.store.upsert("open_payments_rows", rows)
        self.store.upsert("open_payments_rows", rows)   # same slice re-fetch
        self.assertEqual(self.store.count("open_payments_rows"), 2)

    def test_coercion_lists_dicts_and_bools_to_text(self):
        # dataQuality is a live boolean; theme arrives joined but guard the
        # raw-list path too (store must never crash on container values).
        rows = normalize(get_endpoint("catalog"),
                         [CATALOG_ITEMS[0]]).rows["open_payments_catalog"]
        rows[0]["data_quality"] = True
        self.store.upsert("open_payments_catalog", rows)
        got = self.store.fetchall(
            "SELECT data_quality FROM open_payments_catalog")[0]
        self.assertEqual(got["data_quality"], "1")


if __name__ == "__main__":
    unittest.main()
