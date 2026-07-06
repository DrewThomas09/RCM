"""The estate refresh driver: plan shape, argv construction, failure isolation."""
import unittest

from .. import refresh as refresh_mod
from .._spi import CONNECTOR_NAMES


class PlanTests(unittest.TestCase):
    def test_plan_covers_every_planned_connector(self):
        p = refresh_mod.plan()
        expected = [n for n in CONNECTOR_NAMES if n not in refresh_mod.UNPLANNED]
        self.assertEqual(list(p), expected)
        for steps in p.values():
            self.assertTrue(steps)

    def test_unplanned_connectors_are_documented_not_silent(self):
        # The manual-only trio must be declared so the CLI help / README can
        # say so — a connector missing from BOTH lists would be dropped
        # silently.
        for name in CONNECTOR_NAMES:
            self.assertTrue(
                name in refresh_mod._QUICK_PLAN or name in refresh_mod.UNPLANNED,
                f"{name} is neither planned nor declared manual-only")

    def test_full_widens_but_never_removes_a_connector(self):
        quick = refresh_mod.plan(quick=True)
        full = refresh_mod.plan(quick=False)
        self.assertEqual(set(quick), set(full))

    def test_unknown_connector_raises(self):
        with self.assertRaises(KeyError):
            refresh_mod.plan(connectors=["nope"])

    def test_plan_returns_copies(self):
        refresh_mod.plan()["cms_open_data"][0].append("mutated")
        self.assertNotIn("mutated", refresh_mod.plan()["cms_open_data"][0])


class ArgvTests(unittest.TestCase):
    def test_db_style_and_root_style_storage_flags(self):
        self.assertEqual(refresh_mod._storage_argv("cms_open_data", "var/x"),
                         ["--db", "var/x/cms_open_data.db"])
        # --root connectors write {root}/{name}.db themselves, so root IS the
        # db dir — that keeps every db at {db_dir}/{name}.db for open_stores.
        self.assertEqual(refresh_mod._storage_argv("hrsa_data", "var/x/"),
                         ["--root", "var/x"])


class _FakeProc:
    def __init__(self, returncode=0, stdout="rows=5", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class RefreshRunTests(unittest.TestCase):
    def test_refresh_builds_module_cli_argv_and_reports(self):
        calls = []

        def runner(argv, **kw):
            calls.append(argv)
            return _FakeProc()

        report = refresh_mod.refresh(
            "var/t", connectors=["medicaid_data"], runner=runner)
        self.assertTrue(report.ok)
        self.assertEqual(len(calls), 4)  # discover + 3 fetches
        head = calls[0][:5]
        self.assertEqual(head[1:5], [
            "-m", "connectors.medicaid_data.cli", "--db", "var/t/medicaid_data.db"])

    def test_subcommand_db_style_places_storage_after_the_verb(self):
        # cms_open_data and open_payments declare --db per-subcommand;
        # putting it before the verb makes argparse reject the invocation
        # (the exact failure the first live sweep hit).
        calls = []

        def runner(argv, **kw):
            calls.append(argv)
            return _FakeProc()

        refresh_mod.refresh("var/t", connectors=["open_payments"], runner=runner)
        for argv in calls:
            verb_at = 3  # [python, -m, module, verb, ...]
            self.assertNotEqual(argv[verb_at], "--db")
            self.assertEqual(argv[-2:], ["--db", "var/t/open_payments.db"])

    def test_a_failing_step_is_recorded_and_the_sweep_continues(self):
        def runner(argv, **kw):
            if "discover" in argv:
                return _FakeProc(returncode=2, stderr="boom")
            return _FakeProc()

        report = refresh_mod.refresh(
            "var/t", connectors=["medicaid_data"], runner=runner)
        self.assertFalse(report.ok)
        self.assertFalse(report.steps[0].ok)
        self.assertIn("boom", report.steps[0].tail)
        # Later steps still ran.
        self.assertTrue(all(s.ok for s in report.steps[1:]))
        self.assertIn("FAIL", report.summary())

    def test_runner_exception_is_isolated(self):
        def runner(argv, **kw):
            raise OSError("spawn failed")

        report = refresh_mod.refresh(
            "var/t", connectors=["cdc_data"], runner=runner)
        self.assertFalse(report.ok)
        self.assertTrue(all(not s.ok and s.returncode == -1
                            for s in report.steps))


if __name__ == "__main__":
    unittest.main()
