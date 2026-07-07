"""End-to-end ingest path: fake opener → fetch → normalize → store → query.

Regression for the estate gap where cms_coverage shipped ``fetch()`` and
``normalize()`` but no wiring between them — its nine registered datasets
could never be populated by any documented command. These tests drive the
new :mod:`connectors.cms_coverage.pipeline` (and the CLI ``fetch`` verb's
plumbing) against the same in-memory fake server the connector tests use;
no socket, no live API.
"""
import unittest

from ..connector import CmsCoverageConnector
from ..endpoints import get_endpoint
from ..pipeline import ingest, ingest_endpoint, resolve_endpoint
from ..query import query
from ..tables import CmsCoverageStore
from ..transport import CmsCoverageTransport
from .fakes import FakeCmsCoverage

_NCD_PATH = "/v1/reports/national-coverage-ncd"
_LCD_PATH = "/v1/reports/local-coverage-lcd"
_CONTRACTORS_PATH = "/v1/metadata/contractors"


def _connector():
    return CmsCoverageConnector(
        CmsCoverageTransport(min_interval_s=0.0), page_limit=2)


def _national(n):
    return [{"document_id": 100 + i, "document_version": 1,
             "document_type": "NCD", "title": f"Doc {i}",
             "chapter": "240", "last_updated_sort": f"2024010{i}"}
            for i in range(n)]


class ResolveEndpointTests(unittest.TestCase):
    def test_accepts_key_and_full_dataset_id(self):
        self.assertEqual(resolve_endpoint("national_ncd").key, "national_ncd")
        self.assertEqual(resolve_endpoint("cms_coverage_national_ncd").key,
                         "national_ncd")

    def test_unknown_endpoint_raises_with_choices(self):
        with self.assertRaises(KeyError) as ctx:
            resolve_endpoint("nope")
        self.assertIn("national_ncd", str(ctx.exception))


class IngestEndpointTests(unittest.TestCase):
    def test_paged_endpoint_lands_in_canonical_table_and_is_queryable(self):
        fake = FakeCmsCoverage(page_size=2).add(_NCD_PATH, _national(5))
        store = CmsCoverageStore(":memory:")
        res = ingest_endpoint(store, get_endpoint("national_ncd"),
                              connector=_connector(), opener=fake)
        self.assertEqual(res.rows_fetched, 5)
        self.assertEqual(res.rows_written, 5)
        self.assertTrue(res.exhausted)
        self.assertEqual(res.pages, 3)  # 2 + 2 + 1
        # The registered dataset is now actually queryable — the whole
        # point of the gap fix.
        out = query(store, "cms_coverage_national_ncd",
                    filters={"chapter": "240"})
        self.assertEqual(out.total, 5)
        self.assertEqual(out.rows[0]["coverage_level"], "national")
        store.close()

    def test_max_pages_caps_the_pull_without_failing(self):
        fake = FakeCmsCoverage(page_size=2).add(_NCD_PATH, _national(6))
        store = CmsCoverageStore(":memory:")
        res = ingest_endpoint(store, get_endpoint("national_ncd"),
                              connector=_connector(), opener=fake,
                              max_pages=2)
        self.assertEqual(res.pages, 2)
        self.assertEqual(res.rows_written, 4)
        self.assertFalse(res.exhausted)
        store.close()

    def test_reingest_is_idempotent(self):
        recs = _national(3)
        store = CmsCoverageStore(":memory:")
        for _ in range(2):
            fake = FakeCmsCoverage(page_size=2).add(_NCD_PATH, recs)
            ingest_endpoint(store, get_endpoint("national_ncd"),
                            connector=_connector(), opener=fake)
        self.assertEqual(store.count("dim_coverage_document"), 3)
        store.close()

    def test_contractor_dimension_single_shot(self):
        fake = FakeCmsCoverage().add(_CONTRACTORS_PATH, [
            {"contractor_id": 236, "contractor_version": 2,
             "contractor_name": "Noridian", "contract_type_id": 1},
        ])
        store = CmsCoverageStore(":memory:")
        res = ingest_endpoint(store, get_endpoint("contractors"),
                              connector=_connector(), opener=fake)
        self.assertEqual(res.rows_written, 1)
        self.assertTrue(res.exhausted)
        out = query(store, "cms_coverage_contractors")
        self.assertEqual(out.total, 1)
        self.assertEqual(out.rows[0]["contractor_id"], "236")
        store.close()


class IngestAllTests(unittest.TestCase):
    def test_dataset_arg_limits_to_one_endpoint(self):
        fake = FakeCmsCoverage(page_size=2).add(_NCD_PATH, _national(2))
        store = CmsCoverageStore(":memory:")
        results = ingest(store, dataset="cms_coverage_national_ncd",
                         connector=_connector(), opener=fake)
        self.assertEqual([r.endpoint for r in results], ["national_ncd"])
        store.close()

    def test_no_dataset_sweeps_every_registered_endpoint(self):
        fake = FakeCmsCoverage(page_size=2)
        fake.add(_NCD_PATH, _national(2))
        fake.add(_LCD_PATH, [{"document_id": 7, "document_version": 1,
                              "document_type": "LCD", "title": "L",
                              "contractor_id": 236}])
        fake.add(_CONTRACTORS_PATH, [{"contractor_id": 236,
                                      "contractor_version": 1,
                                      "contractor_name": "Noridian"}])
        store = CmsCoverageStore(":memory:")
        results = ingest(store, connector=_connector(), opener=fake)
        self.assertEqual(len(results), 9)  # all registered endpoints ran
        written = {r.endpoint: r.rows_written for r in results}
        self.assertEqual(written["national_ncd"], 2)
        self.assertEqual(written["local_lcd"], 1)
        self.assertEqual(written["contractors"], 1)
        # Endpoints with no canned records land zero rows, not errors.
        self.assertEqual(written["national_nca"], 0)
        # Slices are separable through the uniform query surface.
        self.assertEqual(query(store, "cms_coverage_local_lcd").total, 1)
        self.assertEqual(query(store, "cms_coverage_national_ncd").total, 2)
        store.close()


class CliFetchVerbTests(unittest.TestCase):
    def test_fetch_verb_is_wired_with_dataset_and_max_pages_flags(self):
        # The argparse wiring (verb exists, flags parse, handler bound) —
        # the network-side behavior is covered above through the same
        # ingest() the verb calls.
        from .. import cli as cms_cli
        parser = cms_cli.build_parser()
        args = parser.parse_args(["--root", "/tmp/x", "fetch",
                                  "--dataset", "national_ncd",
                                  "--max-pages", "2"])
        self.assertIs(args.func, cms_cli.cmd_fetch)
        self.assertEqual(args.dataset, "national_ncd")
        self.assertEqual(args.max_pages, 2)

    def test_fetch_verb_rejects_unknown_dataset_gracefully(self):
        import io
        import sys as _sys
        import tempfile

        from .. import cli as cms_cli
        err = io.StringIO()
        old = _sys.stderr
        _sys.stderr = err
        try:
            with tempfile.TemporaryDirectory() as tmp:
                rc = cms_cli.main(["--root", tmp, "fetch",
                                   "--dataset", "not_real"])
        finally:
            _sys.stderr = old
        self.assertEqual(rc, 2)
        self.assertIn("unknown cms_coverage endpoint", err.getvalue())


if __name__ == "__main__":
    unittest.main()
