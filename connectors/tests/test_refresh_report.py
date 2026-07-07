"""Refresh report v2: env-prereq skips, JSON report, persistence.

Regressions pinned here:

* census_acs is documented as optional-without-CENSUS_API_KEY, but its
  steps used to count as FAILED StepResults — a keyless but otherwise
  perfect sweep exited 1 and read as a failure to cron/CI. Now those
  steps are recorded as skipped (ok, visible, non-fatal).
* the report was print-only; now it round-trips to JSON (``as_dict``)
  and persists to ``{db_dir}/_refresh_report.json`` so the estate page /
  a cron wrapper can see what the last refresh did.
* cms_coverage moved from UNPLANNED into the quick plan when it gained a
  ``fetch`` verb — refresh must now drive it root-style.
"""
import json
import os
import tempfile
import unittest

from .. import refresh as refresh_mod


class _FakeProc:
    def __init__(self, returncode=0, stdout="rows=5", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class _EnvGuard(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.get("CENSUS_API_KEY")

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("CENSUS_API_KEY", None)
        else:
            os.environ["CENSUS_API_KEY"] = self._saved


class EnvPrereqSkipTests(_EnvGuard):
    def test_keyless_census_steps_skip_not_fail(self):
        os.environ.pop("CENSUS_API_KEY", None)
        calls = []
        report = refresh_mod.refresh(
            "var/t", connectors=["census_acs"],
            runner=lambda argv, **kw: calls.append(argv) or _FakeProc())
        self.assertEqual(calls, [], "keyless census steps must not spawn")
        self.assertTrue(report.ok, "skips are non-fatal by design")
        self.assertTrue(all(s.skipped for s in report.steps))
        self.assertTrue(all(s.ok for s in report.steps))
        self.assertIn("CENSUS_API_KEY", report.steps[0].tail)
        self.assertIn("skip", report.summary())
        self.assertIn("skipped", report.summary())

    def test_with_key_census_steps_run_normally(self):
        os.environ["CENSUS_API_KEY"] = "test-key"
        calls = []
        report = refresh_mod.refresh(
            "var/t", connectors=["census_acs"],
            runner=lambda argv, **kw: calls.append(argv) or _FakeProc())
        self.assertEqual(len(calls), len(report.steps))
        self.assertGreater(len(calls), 0)
        self.assertFalse(any(s.skipped for s in report.steps))

    def test_other_connectors_unaffected_by_missing_key(self):
        os.environ.pop("CENSUS_API_KEY", None)
        calls = []
        report = refresh_mod.refresh(
            "var/t", connectors=["medicaid_data"],
            runner=lambda argv, **kw: calls.append(argv) or _FakeProc())
        self.assertTrue(report.ok)
        self.assertFalse(any(s.skipped for s in report.steps))
        self.assertGreater(len(calls), 0)


class JsonReportTests(unittest.TestCase):
    def _run(self, **kw):
        return refresh_mod.refresh(
            kw.pop("db_dir", "var/t"), connectors=["medicaid_data"],
            runner=lambda argv, **k: _FakeProc(), **kw)

    def test_as_dict_is_json_ready_and_complete(self):
        report = self._run()
        d = report.as_dict()
        blob = json.loads(json.dumps(d))  # round-trips
        self.assertEqual(blob["db_dir"], "var/t")
        self.assertTrue(blob["ok"])
        self.assertEqual(blob["n_steps"], len(report.steps))
        self.assertEqual(blob["n_failed"], 0)
        self.assertIn("finished_at", blob)
        self.assertIn("+00:00", blob["finished_at"])  # timezone-aware UTC
        step = blob["steps"][0]
        for key in ("connector", "argv", "ok", "skipped", "returncode",
                    "seconds", "tail"):
            self.assertIn(key, step)

    def test_injected_runner_does_not_write_report_by_default(self):
        target = "var/__test_refresh_report_no_write__"
        self.assertFalse(os.path.exists(target))
        self._run(db_dir=target)
        self.assertFalse(os.path.exists(target))

    def test_write_report_true_persists_json_next_to_the_dbs(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = refresh_mod.refresh(
                tmp, connectors=["medicaid_data"],
                runner=lambda argv, **k: _FakeProc(),
                write_report=True)
            path = os.path.join(tmp, "_refresh_report.json")
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding="utf-8") as fh:
                blob = json.load(fh)
            self.assertEqual(blob["n_steps"], len(report.steps))
            self.assertTrue(blob["ok"])


class CmsCoveragePlanTests(unittest.TestCase):
    def test_cms_coverage_is_planned_now_that_fetch_exists(self):
        self.assertNotIn("cms_coverage", refresh_mod.UNPLANNED)
        p = refresh_mod.plan(connectors=["cms_coverage"])
        verbs = [argv[0] for argv in p["cms_coverage"]]
        self.assertTrue(all(v == "fetch" for v in verbs))

    def test_refresh_drives_cms_coverage_root_style(self):
        calls = []
        report = refresh_mod.refresh(
            "var/t", connectors=["cms_coverage"],
            runner=lambda argv, **kw: calls.append(argv) or _FakeProc())
        self.assertTrue(report.ok)
        for argv in calls:
            self.assertEqual(argv[1:3], ["-m", "connectors.cms_coverage.cli"])
            # Root-style: storage flag precedes the verb.
            self.assertEqual(argv[3:5], ["--root", "var/t"])
            self.assertEqual(argv[5], "fetch")

    def test_manual_only_trio_still_unplanned(self):
        for name in ("openfda", "npi_registry", "icd10"):
            self.assertIn(name, refresh_mod.UNPLANNED)


if __name__ == "__main__":
    unittest.main()
