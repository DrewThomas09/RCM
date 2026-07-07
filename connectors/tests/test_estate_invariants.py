"""Estate-wide declarative invariants: registry rows vs canonical tables.

The registry is the contract every surface trusts blindly (query slicing,
incremental ``{date_field}__gte`` filters, join planning, the RCM-MC
estate page). A row whose metadata names a column that does not exist in
its target table ships a landmine — the caller only finds out via
``QueryError`` at query time. This suite locks the invariants for all
connectors at once, so the 17th connector (or the next 15-dataset sweep)
is covered for free.

Also pins the README's estate-size claims to the live registry — the
counts drifted once (189 vs 204) when a dataset sweep skipped the doc.
"""
import os
import re
import unittest

from .._spi import CONNECTOR_NAMES, load_all

_README = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")


class RegistryTableInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapters = load_all()

    def test_target_table_exists_for_every_dataset(self):
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            tables = adapter.tables_mod.TABLES
            for row in adapter.registry_as_dicts():
                self.assertIn(row["target_table"], tables,
                              f"{row['dataset_id']}: unknown target_table")

    def test_join_keys_are_real_columns(self):
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            tables = adapter.tables_mod.TABLES
            for row in adapter.registry_as_dicts():
                cols = set(tables[row["target_table"]].columns)
                for jk in row.get("join_keys") or []:
                    self.assertIn(
                        jk, cols,
                        f"{row['dataset_id']}: join_key {jk!r} not a column "
                        f"of {row['target_table']}")

    def test_date_field_is_a_real_column_when_set(self):
        # Regression: openfda_drug_label advertised the raw-only
        # 'effective_time' and openfda_device_recall 'event_date_posted';
        # both made the documented incremental filter a guaranteed 400.
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            tables = adapter.tables_mod.TABLES
            for row in adapter.registry_as_dicts():
                df = row.get("date_field") or ""
                if not df:
                    continue
                cols = set(tables[row["target_table"]].columns)
                self.assertIn(
                    df, cols,
                    f"{row['dataset_id']}: date_field {df!r} not a column "
                    f"of {row['target_table']} — the advertised "
                    f"'{df}__gte=…' filter would 400")

    def test_source_filter_implies_a_source_endpoint_column(self):
        for name in CONNECTOR_NAMES:
            adapter = self.adapters[name]
            tables = adapter.tables_mod.TABLES
            for row in adapter.registry_as_dicts():
                if not row.get("source_filter"):
                    continue
                cols = set(tables[row["target_table"]].columns)
                self.assertIn(
                    "source_endpoint", cols,
                    f"{row['dataset_id']}: source_filter set but "
                    f"{row['target_table']} has no source_endpoint column "
                    f"— the slice pin cannot apply")

    def test_dataset_ids_globally_unique(self):
        seen = {}
        for name in CONNECTOR_NAMES:
            for did in self.adapters[name].dataset_ids():
                self.assertNotIn(
                    did, seen,
                    f"dataset id {did!r} registered by both {seen.get(did)} "
                    f"and {name} — /v1/query dispatch would be ambiguous")
                seen[did] = name

    def test_openfda_device_recall_advertises_the_canonical_date(self):
        rows = {r["dataset_id"]: r
                for r in self.adapters["openfda"].registry_as_dicts()}
        self.assertEqual(rows["openfda_device_recall"]["date_field"],
                         "report_date")
        # dim_drug_product carries no date column at all — honest empty.
        self.assertEqual(rows["openfda_drug_label"]["date_field"], "")


class LookupRouteUniquenessTests(unittest.TestCase):
    def test_lookup_templates_globally_unique(self):
        # The unified server's _route_lookup is first-match-wins; two
        # connectors registering the same template would silently shadow
        # each other with no failure anywhere. Guard it estate-wide.
        adapters = load_all()
        seen = {}
        for name in CONNECTOR_NAMES:
            store = adapters[name].open_store(":memory:")
            try:
                for template in adapters[name].lookup_handlers(store):
                    self.assertNotIn(
                        template, seen,
                        f"lookup template {template!r} registered by both "
                        f"{seen.get(template)} and {name}")
                    seen[template] = name
            finally:
                store.close()
        self.assertGreaterEqual(len(seen), 30)


class ReadmeDriftTests(unittest.TestCase):
    """The README is the estate contract doc — its counts must not drift."""

    @classmethod
    def setUpClass(cls):
        with open(_README, encoding="utf-8") as fh:
            cls.readme = fh.read()
        cls.adapters = load_all()

    def test_headline_totals_match_live_registry(self):
        m = re.search(r"\*\*(\d+) registered datasets across (\d+) "
                      r"connectors\*\*", self.readme)
        self.assertIsNotNone(m, "README headline totals line missing")
        n_datasets = sum(len(a.dataset_ids()) for a in self.adapters.values())
        self.assertEqual(int(m.group(1)), n_datasets,
                         "README dataset total drifted from the registry")
        self.assertEqual(int(m.group(2)), len(CONNECTOR_NAMES),
                         "README connector total drifted")

    def test_per_connector_table_counts_match(self):
        rows = re.findall(r"^\|[^|]+\| `connectors/(\w+)` \|.*\| (\d+) \|$",
                          self.readme, re.MULTILINE)
        counted = {name: int(n) for name, n in rows}
        self.assertEqual(set(counted), set(CONNECTOR_NAMES),
                         "README connector table rows drifted")
        for name in CONNECTOR_NAMES:
            self.assertEqual(
                counted[name], len(self.adapters[name].dataset_ids()),
                f"README dataset count for {name} drifted")

    def test_every_connector_ships_a_readme(self):
        root = os.path.dirname(_README)
        for name in CONNECTOR_NAMES:
            self.assertTrue(
                os.path.isfile(os.path.join(root, name, "README.md")),
                f"{name} has no README.md")


if __name__ == "__main__":
    unittest.main()
