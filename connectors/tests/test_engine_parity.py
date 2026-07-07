"""Behavioral parity harness across all 16 copy-pasted query engines.

Every connector ships its own ``query.py`` (a deliberate self-contained
design), which means a grammar fix applied to one package can silently
miss the other fifteen. This suite runs one fixed matrix of filter-grammar
cases against every connector's real engine + real SQLite store so any
future single-package drift fails loudly.

The matrix also pins two regressions fixed estate-wide:

* numeric range operators (``gt/gte/lt/lte/between``) must compare
  numerically over the all-TEXT storage — lexicographic compare made
  ``patient_age__gt=10`` match an age-9 row;
* ``field__in`` must accept the HTTP/CLI form (one comma-joined string),
  not just a Python list — the string form silently matched nothing.
"""
import unittest

from .._spi import CONNECTOR_NAMES, load_all

_META_COLS = {"source_endpoint", "ingested_at", "fetched_at", "company_key",
              "source"}


def _fixture_for(adapter):
    """(dataset_id, table, pk_col, filter_col, source_filter) per connector."""
    row = adapter.registry_as_dicts()[0]
    tdef = adapter.tables_mod.TABLES[row["target_table"]]
    filter_col = next(c for c in tdef.columns
                      if c != tdef.pk and c not in _META_COLS)
    return row["dataset_id"], row["target_table"], tdef.pk, filter_col, \
        row.get("source_filter") or ""


def _seed(adapter, store, table, pk, col, source_filter):
    """Three numeric-valued rows (9/10/40) plus one empty-valued row."""
    rows = []
    for key, val in (("k1", "9"), ("k2", "10"), ("k3", "40"), ("k4", "")):
        r = {pk: key, col: val}
        if source_filter:
            r["source_endpoint"] = source_filter
        rows.append(r)
    store.upsert(table, rows)


class EngineParityTests(unittest.TestCase):
    """One grammar matrix, asserted identically for every connector."""

    @classmethod
    def setUpClass(cls):
        cls.adapters = load_all()

    def _each(self):
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            dataset, table, pk, col, sf = _fixture_for(adapter)
            store = adapter.open_store(":memory:")
            try:
                _seed(adapter, store, table, pk, col, sf)
                yield name, adapter, store, dataset, pk, col
            finally:
                store.close()

    def _keys(self, res, pk):
        return {r[pk] for r in res.rows}

    def test_numeric_gt_orders_numerically_not_lexicographically(self):
        # Lexicographically '9' > '10', so gt=9 returned nothing and gt=10
        # returned the age-9 row before the estate-wide CAST fix.
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.query(store, dataset, filters={f"{col}__gt": "9"})
            self.assertEqual(self._keys(res, pk), {"k2", "k3"},
                             f"{name}: {col}__gt=9 mis-ranked")
            res = adapter.query(store, dataset, filters={f"{col}__gt": 10})
            self.assertEqual(self._keys(res, pk), {"k3"},
                             f"{name}: {col}__gt=10 mis-ranked")

    def test_numeric_gte_lt_lte(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.query(store, dataset, filters={f"{col}__gte": "10"})
            self.assertEqual(self._keys(res, pk), {"k2", "k3"}, name)
            # notnull keeps the empty-string row (CAST('')=0.0) out of the
            # numeric window — the realistic pairing for lt/lte filters.
            res = adapter.query(store, dataset, filters={
                f"{col}__lt": "10", f"{col}__notnull": 1})
            self.assertEqual(self._keys(res, pk), {"k1"}, name)
            res = adapter.query(store, dataset, filters={
                f"{col}__lte": 10, f"{col}__notnull": 1})
            self.assertEqual(self._keys(res, pk), {"k1", "k2"}, name)

    def test_numeric_between_comma_string_and_list(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.query(store, dataset,
                                filters={f"{col}__between": "9,11"})
            self.assertEqual(self._keys(res, pk), {"k1", "k2"},
                             f"{name}: between 9,11")
            res = adapter.query(store, dataset,
                                filters={f"{col}__between": ["9", "40"]})
            self.assertEqual(self._keys(res, pk), {"k1", "k2", "k3"}, name)

    def test_in_accepts_comma_joined_string_and_list(self):
        # The HTTP/CLI surfaces can only send one string per key; before the
        # fix `x__in=9,40` became IN ('9,40') and matched nothing.
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.query(store, dataset, filters={f"{col}__in": "9,40"})
            self.assertEqual(self._keys(res, pk), {"k1", "k3"},
                             f"{name}: comma-string __in matched nothing")
            res = adapter.query(store, dataset,
                                filters={f"{col}__in": ["9", "40"]})
            self.assertEqual(self._keys(res, pk), {"k1", "k3"}, name)
            res = adapter.query(store, dataset, filters={f"{col}__in": "9"})
            self.assertEqual(self._keys(res, pk), {"k1"}, name)

    def test_isnull_notnull_treat_empty_string_as_absent(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.query(store, dataset, filters={f"{col}__isnull": 1})
            self.assertEqual(self._keys(res, pk), {"k4"}, name)
            res = adapter.query(store, dataset, filters={f"{col}__notnull": 1})
            self.assertEqual(self._keys(res, pk), {"k1", "k2", "k3"}, name)

    def test_unknown_filter_field_raises_query_error(self):
        for name, adapter, store, dataset, pk, col in self._each():
            with self.assertRaises(adapter.QueryError, msg=name):
                adapter.query(store, dataset,
                              filters={"definitely_not_a_column": "x"})

    def test_limit_clamped_and_sort_accepted(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.query(store, dataset, limit=999_999)
            self.assertLessEqual(res.limit, 1000, name)
            res = adapter.query(store, dataset, limit=-3)
            self.assertGreaterEqual(res.limit, 1, name)
            res = adapter.query(store, dataset, sort=[f"-{col}"])
            self.assertEqual(len(res.rows), 4, name)

    def test_aggregate_counts_by_group(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.aggregate(store, dataset, group_by=[col])
            counts = {r[col]: r["count"] for r in res.rows}
            self.assertEqual(counts.get("9"), 1, name)
            self.assertEqual(len(res.rows), 4, name)

    def test_aggregate_metrics_sum_avg_min_max_over_cast(self):
        # ``metrics`` rides the same all-TEXT storage as the numeric range
        # operators: values CAST to REAL ('' reads as 0.0), aliased
        # ``{func}_{field}``, requested as "func:field" strings or
        # (func, field) pairs — identically in all 16 engines.
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.aggregate(
                store, dataset, group_by=[pk],
                metrics=[f"sum:{col}", f"avg:{col}", ("min", col),
                         f"MAX:{col}"])
            d = res.as_dict()
            self.assertEqual(d["metrics"],
                             [f"sum:{col}", f"avg:{col}", f"min:{col}",
                              f"max:{col}"], name)
            by_pk = {r[pk]: r for r in d["rows"]}
            for func in ("sum", "avg", "min", "max"):
                self.assertEqual(by_pk["k3"][f"{func}_{col}"], 40.0, name)
            self.assertEqual(by_pk["k1"][f"sum_{col}"], 9.0, name)
            # Documented CAST trade-off: the empty-string row reads 0.0.
            self.assertEqual(by_pk["k4"][f"sum_{col}"], 0.0, name)
            for r in d["rows"]:
                self.assertEqual(r["count"], 1, name)

    def test_aggregate_metrics_roll_up_within_groups(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.aggregate(store, dataset, group_by=[col],
                                    filters={f"{col}__in": "9,10,40"},
                                    metrics=[f"sum:{col}"])
            got = {r[col]: r[f"sum_{col}"] for r in res.rows}
            self.assertEqual(got, {"9": 9.0, "10": 10.0, "40": 40.0}, name)

    def test_aggregate_without_metrics_shape_unchanged(self):
        for name, adapter, store, dataset, pk, col in self._each():
            res = adapter.aggregate(store, dataset, group_by=[col])
            d = res.as_dict()
            self.assertEqual(d["metrics"], [], name)
            for r in d["rows"]:
                self.assertEqual(set(r), {col, "count"}, name)

    def test_aggregate_metric_validation_raises_query_error(self):
        for name, adapter, store, dataset, pk, col in self._each():
            with self.assertRaises(adapter.QueryError, msg=name):
                adapter.aggregate(store, dataset, group_by=[col],
                                  metrics=[f"median:{col}"])
            with self.assertRaises(adapter.QueryError, msg=name):
                adapter.aggregate(store, dataset, group_by=[col],
                                  metrics=["sum:definitely_not_a_column"])
            with self.assertRaises(adapter.QueryError, msg=name):
                adapter.aggregate(store, dataset, group_by=[col],
                                  metrics=["sum"])  # no field part

    def test_every_registered_dataset_queries_cleanly_when_empty(self):
        # The declarative long tail: a misspelled target_table or bad
        # source_filter in any registry row would break here without a
        # single fixture — query() must return an empty-but-valid result
        # for all 200+ datasets.
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            store = adapter.open_store(":memory:")
            try:
                for dataset_id in adapter.dataset_ids():
                    res = adapter.query(store, dataset_id, limit=1)
                    self.assertEqual(res.total, 0, f"{name}:{dataset_id}")
                    self.assertEqual(res.rows, [], f"{name}:{dataset_id}")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
