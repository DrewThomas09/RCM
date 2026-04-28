"""Test tools/azure_smoke.py against a local server.

This proves the smoke-gate script works end-to-end before it's
ever pointed at a real Azure deploy. Boots an in-process server
on a random port with seeded credentials, runs the same checks
the script would run against ``rcm-mc.azurewebsites.net``, and
asserts every check passes.

Failure modes are also covered: bad credentials, missing chrome,
unreachable host. These ensure the script reliably *fails* when
the deploy is broken, not just passes when healthy.
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager

# tools/ is not a package; add it to sys.path so the smoke
# script can be imported by its module name.
_HERE = os.path.dirname(os.path.abspath(__file__))
_TOOLS = os.path.normpath(os.path.join(_HERE, "..", "tools"))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import azure_smoke  # noqa: E402


@contextmanager
def _running_server(seed_users=True):
    """Yield (base_url) for an in-process server with seeded users.

    Sets ``CHARTIS_UI_V2=1`` for the duration so the editorial chrome
    is active — matching the production Azure deploy env from
    ``deploy/azure-app-service.json``. Without it, ``/app`` redirects
    into the legacy dashboard chain and the smoke script's chrome
    assertions miss the navy topbar.
    """
    from rcm_mc.auth.auth import create_user
    from rcm_mc.portfolio.store import PortfolioStore

    prior = os.environ.get("CHARTIS_UI_V2")
    os.environ["CHARTIS_UI_V2"] = "1"

    # Force a fresh import so the module-level ``UI_V2_ENABLED`` flag
    # in _chartis_kit re-resolves against the env we just set.
    import importlib
    import sys
    for m in (
        "rcm_mc.ui._chartis_kit",
        "rcm_mc.server",
    ):
        if m in sys.modules:
            importlib.reload(sys.modules[m])

    from rcm_mc.server import build_server

    tmp = tempfile.mkdtemp(prefix="azure_smoke_test_")
    db_path = os.path.join(tmp, "p.db")

    store = PortfolioStore(db_path)
    if seed_users:
        # Match the smoke script's default credentials so the tests
        # can rely on the script's defaults working.
        create_user(
            store, "andrewthomas@chartis.com", "ChartisDemo1",
            display_name="Andrew Thomas", role="admin",
        )

    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        if prior is None:
            os.environ.pop("CHARTIS_UI_V2", None)
        else:
            os.environ["CHARTIS_UI_V2"] = prior


class HealthzCheckTests(unittest.TestCase):
    def test_healthz_passes_under_threshold(self):
        with _running_server() as base:
            result = azure_smoke.check_healthz(base, max_ms=2000)
            self.assertTrue(result.passed, result.detail)
            self.assertEqual(result.name, "healthz")
            self.assertGreater(result.duration_ms, 0)

    def test_healthz_fails_when_threshold_too_tight(self):
        # Pin the failure mode: a 0ms threshold will always fail
        # because no real network hop completes that fast.
        with _running_server() as base:
            result = azure_smoke.check_healthz(base, max_ms=0)
            self.assertFalse(result.passed)
            self.assertIn("exceeded", result.detail)

    def test_healthz_fails_unreachable_host(self):
        result = azure_smoke.check_healthz(
            "http://127.0.0.1:1",  # almost certainly closed
            max_ms=1000,
        )
        self.assertFalse(result.passed)
        self.assertIn("could not reach", result.detail)


class LoginRoundTripTests(unittest.TestCase):
    def test_login_success_returns_opener_with_session_cookie(self):
        with _running_server() as base:
            result, opener = azure_smoke.check_login_round_trip(
                base,
                username="andrewthomas@chartis.com",
                password="ChartisDemo1",
            )
            self.assertTrue(result.passed, result.detail)
            self.assertIsNotNone(opener)

    def test_login_failure_returns_no_opener(self):
        with _running_server() as base:
            result, opener = azure_smoke.check_login_round_trip(
                base,
                username="andrewthomas@chartis.com",
                password="WrongPassword!",
            )
            self.assertFalse(result.passed)
            self.assertIsNone(opener)


class AppChromeTests(unittest.TestCase):
    def test_app_chrome_present_after_login(self):
        with _running_server() as base:
            _, opener = azure_smoke.check_login_round_trip(
                base,
                username="andrewthomas@chartis.com",
                password="ChartisDemo1",
            )
            self.assertIsNotNone(opener)
            result = azure_smoke.check_app_chrome(base, opener=opener)
            self.assertTrue(result.passed, result.detail)
            self.assertIn("chrome markers", result.detail)


class FullSmokeRunTests(unittest.TestCase):
    def test_run_smoke_all_pass_against_healthy_server(self):
        with _running_server() as base:
            report = azure_smoke.run_smoke(
                base,
                username="andrewthomas@chartis.com",
                password="ChartisDemo1",
                max_healthz_ms=2000,
            )
            self.assertTrue(
                report.all_passed,
                "\n".join(
                    f"  [{c.name}] {c.detail}" for c in report.checks
                ),
            )
            # Three checks: healthz, login, app_chrome
            self.assertEqual(len(report.checks), 3)

    def test_run_smoke_fails_with_bad_password(self):
        with _running_server() as base:
            report = azure_smoke.run_smoke(
                base,
                username="andrewthomas@chartis.com",
                password="WrongPassword!",
                max_healthz_ms=2000,
            )
            self.assertFalse(report.all_passed)
            # Login fails; app_chrome reports skipped (also fails)
            login = next(c for c in report.checks if c.name == "login")
            chrome = next(c for c in report.checks if c.name == "app_chrome")
            self.assertFalse(login.passed)
            self.assertFalse(chrome.passed)
            self.assertIn("skipped", chrome.detail)


class CLIExitCodeTests(unittest.TestCase):
    def test_main_exit_zero_when_all_pass(self):
        with _running_server() as base:
            rc = azure_smoke.main([
                base,
                "--username", "andrewthomas@chartis.com",
                "--password", "ChartisDemo1",
                "--max-healthz-ms", "2000",
                "--json",
            ])
            self.assertEqual(rc, 0)

    def test_main_exit_nonzero_on_bad_password(self):
        with _running_server() as base:
            rc = azure_smoke.main([
                base,
                "--username", "andrewthomas@chartis.com",
                "--password", "wrong!",
                "--max-healthz-ms", "2000",
                "--json",
            ])
            self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
