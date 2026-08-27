"""Cross-catalog keyword search: the estate's dataset-discovery surface.

The registered datasets are the *curated* slice — the ones someone
promoted to first-class typed tables. The synced catalogs are everything
the upstream publishers list (tens of thousands of rows across
data.cms.gov, the Provider Data Catalog, Open Payments,
data.medicaid.gov, Healthcare.gov, data.cdc.gov and healthdata.gov), and
each is already pullable through its connector's generic fetched-rows
slot. Until this surface existed you had to know a dataset's identifier
before you could pull it, which made the catalogs reachable in principle
and undiscoverable in practice.

Everything here is data-driven over :data:`CATALOG_SPECS`, so an eighth
catalog connector is covered for free — and a renamed upstream column
fails loudly here instead of silently returning zero hits forever.
"""
import json
import threading
import unittest
import urllib.error
import urllib.request

from .. import registry as estate
from .._spi import (
    CATALOG_CONNECTORS, CATALOG_ROW_FIELDS, CATALOG_SPECS, CONNECTOR_NAMES,
    load_all,
)
from ..api_server import make_server

# Two rows per catalog: one matching on TITLE, one matching only on
# DESCRIPTION (so a title-only implementation fails), plus a decoy.
_TITLE_HIT = "Medicare Advantage Enrollment"
_DESC_HIT = "Nursing Home Compare"
_DECOY = "Zzz Unrelated Dataset"


def _seed(adapter, store) -> None:
    spec = CATALOG_SPECS[adapter.name]
    store.upsert(spec["table"], [
        {spec["id"]: "cat-1", spec["title"]: _TITLE_HIT,
         spec["description"]: "monthly contract enrollment counts",
         spec["modified"]: "2026-01-15", spec["url"]: "https://x/1"},
        {spec["id"]: "cat-2", spec["title"]: _DESC_HIT,
         spec["description"]: "star ratings; medicare advantage crosswalk",
         spec["modified"]: "2026-02-20", spec["url"]: "https://x/2"},
        {spec["id"]: "cat-3", spec["title"]: _DECOY,
         spec["description"]: "nothing relevant here"},
    ])


class CatalogSpecIntegrityTests(unittest.TestCase):
    """The declared columns must be real columns of real tables."""

    @classmethod
    def setUpClass(cls):
        cls.adapters = load_all()

    def test_every_declared_catalog_column_exists(self):
        for name, spec in CATALOG_SPECS.items():
            self.assertIn(name, CONNECTOR_NAMES,
                          f"{name} is declared in CATALOG_SPECS but is not a "
                          f"registered connector")
            tables = self.adapters[name].tables_mod.TABLES
            self.assertIn(spec["table"], tables,
                          f"{name}: catalog table {spec['table']!r} missing")
            cols = set(tables[spec["table"]].columns)
            for field in ("id", "title", "description", "modified", "url"):
                self.assertIn(
                    spec[field], cols,
                    f"{name}: CATALOG_SPECS[{field!r}] = {spec[field]!r} is "
                    f"not a column of {spec['table']} — catalog search would "
                    f"raise or silently return nothing")

    def test_catalog_connectors_follow_registration_order(self):
        self.assertEqual(
            list(CATALOG_CONNECTORS),
            [n for n in CONNECTOR_NAMES if n in CATALOG_SPECS])

    def test_non_catalog_connectors_report_no_catalog(self):
        # The normal case: most connectors (openFDA, ICD-10, HCPCS, QPP,
        # RxNorm, NPI Registry, …) have no catalog and must be skipped
        # cleanly rather than raising anywhere in the fan-out.
        plain = [n for n in CONNECTOR_NAMES if n not in CATALOG_SPECS]
        self.assertTrue(plain, "expected some connectors without a catalog")
        for name in plain:
            adapter = self.adapters[name]
            self.assertFalse(adapter.has_catalog, name)
            store = adapter.open_store(":memory:")
            try:
                self.assertEqual(adapter.catalog_search(store, "medicare"), [],
                                 f"{name} must answer [] not raise")
            finally:
                store.close()


class PerConnectorCatalogSearchTests(unittest.TestCase):
    """Every catalog connector answers the same uniform shape."""

    @classmethod
    def setUpClass(cls):
        cls.adapters = load_all()

    def _seeded(self, name):
        adapter = self.adapters[name]
        store = adapter.open_store(":memory:")
        _seed(adapter, store)
        return adapter, store

    def test_matches_on_title_and_on_description(self):
        for name in CATALOG_CONNECTORS:
            adapter, store = self._seeded(name)
            try:
                hits = adapter.catalog_search(store, "medicare advantage")
                ids = {h["dataset_id"] for h in hits}
                self.assertIn("cat-1", ids, f"{name}: title match missing")
                self.assertIn("cat-2", ids,
                              f"{name}: description match missing — the "
                              f"search must cover description, not just title")
                self.assertNotIn("cat-3", ids, f"{name}: decoy matched")
            finally:
                store.close()

    def test_search_is_case_insensitive(self):
        for name in CATALOG_CONNECTORS:
            adapter, store = self._seeded(name)
            try:
                for term in ("MEDICARE ADVANTAGE", "medicare advantage",
                             "MeDiCaRe AdVaNtAgE"):
                    self.assertEqual(
                        len(adapter.catalog_search(store, term)), 2,
                        f"{name}: {term!r} did not match case-insensitively")
            finally:
                store.close()

    def test_uniform_row_shape_and_no_none_values(self):
        for name in CATALOG_CONNECTORS:
            adapter, store = self._seeded(name)
            try:
                for row in adapter.catalog_search(store, "medicare"):
                    self.assertEqual(tuple(row), CATALOG_ROW_FIELDS,
                                     f"{name}: row keys/order drifted")
                    self.assertEqual(row["connector"], name)
                    for k, v in row.items():
                        self.assertIsInstance(
                            v, str,
                            f"{name}: {k} is {type(v).__name__}, not str — "
                            f"absent values must be '' so merged rows are "
                            f"uniform")
            finally:
                store.close()

    def test_absent_columns_become_empty_string(self):
        # cat-3 is seeded without modified/url; it is the decoy, so search
        # for its own title to pull it back and check the blanks.
        for name in CATALOG_CONNECTORS:
            adapter, store = self._seeded(name)
            try:
                hits = adapter.catalog_search(store, "Zzz Unrelated")
                self.assertEqual(len(hits), 1, name)
                self.assertEqual(hits[0]["modified"], "", name)
                self.assertEqual(hits[0]["url"], "", name)
            finally:
                store.close()

    def test_limit_is_clamped_at_both_ends(self):
        for name in CATALOG_CONNECTORS:
            adapter, store = self._seeded(name)
            try:
                self.assertEqual(
                    len(adapter.catalog_search(store, "medicare", limit=1)), 1,
                    name)
                # Junk and out-of-range limits must not raise or return all.
                self.assertLessEqual(
                    len(adapter.catalog_search(store, "medicare",
                                               limit=10 ** 9)), 1000, name)
                self.assertGreaterEqual(
                    len(adapter.catalog_search(store, "medicare", limit=-5)),
                    1, name)
                self.assertEqual(
                    len(adapter.catalog_search(store, "medicare",
                                               limit="junk")), 2, name)
            finally:
                store.close()

    def test_blank_query_returns_nothing_rather_than_everything(self):
        for name in CATALOG_CONNECTORS:
            adapter, store = self._seeded(name)
            try:
                for term in ("", "   ", None):
                    self.assertEqual(adapter.catalog_search(store, term), [],
                                     f"{name}: blank query must not match all")
            finally:
                store.close()


class CrossCatalogFanOutTests(unittest.TestCase):
    def setUp(self):
        self.adapters = load_all()
        self.stores = {}
        for name in CONNECTOR_NAMES:
            store = self.adapters[name].open_store(":memory:")
            if name in CATALOG_SPECS:
                _seed(self.adapters[name], store)
            self.stores[name] = store

    def tearDown(self):
        for store in self.stores.values():
            store.close()

    def test_fan_out_covers_every_catalog_connector(self):
        res = estate.catalog_search_all(self.stores, "medicare advantage",
                                        limit=1000)
        self.assertEqual(res["connectors_searched"], list(CATALOG_CONNECTORS))
        self.assertEqual(res["total_before_limit"], 2 * len(CATALOG_CONNECTORS))
        self.assertEqual(res["fields"], list(CATALOG_ROW_FIELDS))

    def test_results_are_grouped_in_connector_registration_order(self):
        res = estate.catalog_search_all(self.stores, "medicare advantage",
                                        limit=1000)
        seen = []
        for row in res["results"]:
            if not seen or seen[-1] != row["connector"]:
                seen.append(row["connector"])
        self.assertEqual(seen, list(CATALOG_CONNECTORS),
                         "merged rows must be deterministically ordered by "
                         "connector registration order")

    def test_overall_limit_and_per_connector_limit_are_independent(self):
        res = estate.catalog_search_all(self.stores, "medicare",
                                        per_connector_limit=1, limit=1000)
        self.assertEqual(res["total_before_limit"], len(CATALOG_CONNECTORS))
        capped = estate.catalog_search_all(self.stores, "medicare", limit=3)
        self.assertEqual(capped["count"], 3)
        self.assertEqual(len(capped["results"]), 3)
        # total_before_limit reports what the fan-out actually found, so a
        # truncated answer is visibly truncated rather than looking complete.
        self.assertGreater(capped["total_before_limit"], 3)

    def test_connector_filter_narrows_the_fan_out(self):
        one = CATALOG_CONNECTORS[0]
        res = estate.catalog_search_all(self.stores, "medicare",
                                        connectors=[one])
        self.assertEqual(res["connectors_searched"], [one])
        self.assertTrue(all(r["connector"] == one for r in res["results"]))

    def test_unknown_connector_filter_is_ignored_not_fatal(self):
        res = estate.catalog_search_all(self.stores, "medicare",
                                        connectors=["not_a_connector"])
        self.assertEqual(res["connectors_searched"], [])
        self.assertEqual(res["results"], [])

    def test_missing_store_is_skipped_so_a_partial_estate_still_answers(self):
        partial = {k: v for k, v in self.stores.items()
                   if k != CATALOG_CONNECTORS[0]}
        res = estate.catalog_search_all(partial, "medicare advantage",
                                        limit=1000)
        self.assertNotIn(CATALOG_CONNECTORS[0], res["connectors_searched"])
        self.assertTrue(res["results"])

    def test_blank_query_searches_nothing(self):
        res = estate.catalog_search_all(self.stores, "   ")
        self.assertEqual(res["count"], 0)
        self.assertEqual(res["connectors_searched"], [])

    def test_catalog_connectors_helper_is_exported(self):
        self.assertEqual(estate.catalog_connectors(), list(CATALOG_CONNECTORS))


class CatalogSearchHttpTests(unittest.TestCase):
    """Real socket against the unified estate server."""

    def setUp(self):
        self.adapters = load_all()
        self.stores = {}
        for name in CONNECTOR_NAMES:
            store = self.adapters[name].open_store(":memory:")
            if name in CATALOG_SPECS:
                _seed(self.adapters[name], store)
            self.stores[name] = store
        self.server, self.port = make_server(self.stores)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        for store in self.stores.values():
            store.close()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def test_search_across_every_catalog(self):
        status, body = self._get(
            "/v1/catalog/search?q=medicare%20advantage&limit=1000")
        self.assertEqual(status, 200)
        self.assertEqual(body["connectors_searched"], list(CATALOG_CONNECTORS))
        self.assertEqual(body["total_before_limit"],
                         2 * len(CATALOG_CONNECTORS))

    def test_connector_filter_accepts_comma_joined_and_repeated(self):
        a, b = CATALOG_CONNECTORS[0], CATALOG_CONNECTORS[1]
        _, comma = self._get(
            f"/v1/catalog/search?q=medicare&connector={a},{b}")
        self.assertEqual(comma["connectors_searched"], [a, b])
        _, repeated = self._get(
            f"/v1/catalog/search?q=medicare&connector={a}&connector={b}")
        # parse_qs keeps both; the route flattens them the same way.
        self.assertIn(a, repeated["connectors_searched"])

    def test_limit_is_honoured_over_http(self):
        _, body = self._get("/v1/catalog/search?q=medicare&limit=2")
        self.assertEqual(body["count"], 2)

    def test_missing_q_is_a_400_not_an_empty_200(self):
        # Answering "0 results" to a malformed query is how a caller
        # concludes the catalogs are empty when they are not.
        for path in ("/v1/catalog/search", "/v1/catalog/search?q=",
                     "/v1/catalog/search?q=%20%20"):
            with self.assertRaises(urllib.error.HTTPError, msg=path) as ctx:
                self._get(path)
            self.assertEqual(ctx.exception.code, 400, path)

    def test_junk_limit_does_not_500(self):
        status, body = self._get("/v1/catalog/search?q=medicare&limit=abc")
        self.assertEqual(status, 200)
        self.assertTrue(body["results"])


if __name__ == "__main__":
    unittest.main()
