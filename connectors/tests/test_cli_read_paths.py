"""Read verbs on the root-style CLIs must never create dirs or db files.

Regression: `python -m connectors.<name>.cli query <dataset>` on a
never-ingested root used to mkdir the storage dir (``./.openfda_data``
etc.) and write an empty schema db (+wal/shm) as a side effect of a
*read* — observed live as four stray dot-dirs at the repo root after one
smoke run. Read verbs now answer from an in-memory store when the db
file does not exist, and still read the real file when it does.
"""
import contextlib
import io
import os
import tempfile
import unittest

from ..cms_coverage import cli as cms_coverage_cli
from ..hrsa_data import cli as hrsa_cli
from ..icd10 import cli as icd10_cli
from ..npi_registry import cli as npi_cli
from ..openfda import cli as openfda_cli

# (cli module, sample read-verb argvs) per root-style connector. Every
# argv runs against a --root that does not exist and must leave zero
# filesystem trace while exiting 0 (an empty result is a valid answer).
_CASES = [
    (openfda_cli, [
        ["query", "openfda_drug_ndc", "--limit", "1"],
        ["lookup-drug", "0002-1200"],
        ["aggregate", "openfda_drug_event", "--group-by", "occurcountry"],
    ]),
    (cms_coverage_cli, [
        ["query", "cms_coverage_national_ncd", "--limit", "1"],
        ["lookup-contractor", "236"],
    ]),
    (npi_cli, [
        ["query", "npi_provider", "--limit", "1"],
        ["lookup-provider", "1234567893"],
    ]),
    (icd10_cli, [
        ["query", "icd10_cm", "--limit", "1"],
        ["lookup-code", "E11.65"],
        ["search", "cm", "diabetes"],
    ]),
    (hrsa_cli, [
        ["query", "hrsa_data_mua", "--limit", "1"],
        ["lookup-shortage-area", "MD"],
    ]),
]


def _run(cli_mod, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = cli_mod.main(argv)
    return rc, out.getvalue()


class ReadVerbsNeverCreateFilesTests(unittest.TestCase):
    def test_read_verbs_on_missing_root_leave_no_trace_and_exit_zero(self):
        for cli_mod, verb_argvs in _CASES:
            name = cli_mod.__name__
            with tempfile.TemporaryDirectory() as tmp:
                root = os.path.join(tmp, "never-ingested")
                for verb_argv in verb_argvs:
                    rc, out = _run(cli_mod, ["--root", root, *verb_argv])
                    self.assertEqual(rc, 0, f"{name} {verb_argv}: rc={rc}")
                    self.assertFalse(
                        os.path.exists(root),
                        f"{name} {verb_argv} created {root} on a read")
                self.assertEqual(os.listdir(tmp), ["never-ingested"]
                                 if os.path.exists(root) else [],
                                 f"{name} littered {tmp}")

    def test_query_still_reads_a_real_ingested_db(self):
        # The :memory: fallback must only apply when the file is absent —
        # an ingested root keeps answering with its real rows.
        from ..icd10.tables import Icd10Store
        with tempfile.TemporaryDirectory() as tmp:
            store = Icd10Store(os.path.join(tmp, "icd10.db"))
            store.upsert("dim_icd10_code", [
                {"code_key": "cm:E11.65", "code_type": "cm", "code": "E11.65",
                 "name": "Type 2 diabetes mellitus with hyperglycemia",
                 "source_endpoint": "cm"}])
            store.close()
            rc, out = _run(icd10_cli,
                           ["--root", tmp, "query", "icd10_cm",
                            "--filter", "code=E11.65"])
            self.assertEqual(rc, 0)
            self.assertIn("E11.65", out)
            self.assertIn('"total": 1', out)

    def test_ingest_verbs_still_create_the_root(self):
        # The write path keeps its mkdir — only reads went side-effect
        # free. cms_coverage's new fetch verb is the cheapest to prove
        # offline: an unknown dataset exits 2 but the root exists.
        import sys
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root = os.path.join(tmp, "fresh")
                rc = cms_coverage_cli.main(
                    ["--root", root, "fetch", "--dataset", "not_real"])
                self.assertEqual(rc, 2)
                self.assertTrue(os.path.isdir(root),
                                "ingest verbs must still create the root")
        finally:
            sys.stderr = old


if __name__ == "__main__":
    unittest.main()
