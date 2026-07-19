"""Tests for the Data Hub console (/data-hub) and its warm endpoint.

Covers:
  1. /data-hub renders 200 and shows the real estate + benchmark sections
  2. Nav wiring — /data-hub resolves to Research, is in the palette + sub-nav
  3. POST /api/data-hub/warm/<connector> is admin-gated (403 without admin)
  4. Admin + unknown/manual connector are rejected BEFORE any ingest runs
  5. Admin + valid connector enqueues a background job (subprocess mocked),
     which runs to done and reports the connector back
  6. Rate limiting — a second immediate warm of the same connector is 429

The warm subprocess (``python -m connectors.cli refresh``) is mocked so the
suite never touches the network; the job-queue + endpoint contract is what
we assert here.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from unittest import mock


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _estate_available() -> bool:
    try:
        from rcm_mc.data_public import connector_estate as ce
        return ce.estate_available()
    except Exception:  # noqa: BLE001
        return False


# ────────────────────────────────────────────────────────────────────
# 1 + 2. Page render + nav wiring (no auth needed)
# ────────────────────────────────────────────────────────────────────
class TestDataHubPage(unittest.TestCase):
    def test_render_contains_sections(self):
        from rcm_mc.ui.data_public.data_hub_page import render_data_hub
        with tempfile.TemporaryDirectory() as tmp:
            html = render_data_hub({}, db_path=os.path.join(tmp, "p.db"),
                                   can_warm=True)
        for needle in ("Data Hub", "Public-API estate",
                       "CMS benchmark", "Research tools", "/npi-cleaner"):
            self.assertIn(needle, html, f"missing {needle!r}")

    def test_admin_sees_warm_buttons_non_admin_sees_command(self):
        from rcm_mc.ui.data_public.data_hub_page import render_data_hub
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            admin_html = render_data_hub({}, db_path=db, can_warm=True)
            guest_html = render_data_hub({}, db_path=db, can_warm=False)
        if _estate_available():
            self.assertIn("dh-warm", admin_html)
            self.assertIn("Warm every connector", admin_html)
            # A non-admin never gets a warm button — only the copy command.
            self.assertNotIn('class="dh-warm"', guest_html)

    def test_nav_wiring(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _NAV_FLAGSHIPS, _SUB_NAV,
            _resolve_sub_section,
        )
        self.assertEqual(_resolve_sub_section("/data-hub"), "research")
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/data-hub", routes)
        self.assertIn("/data-hub", _NAV_FLAGSHIPS["research"])
        self.assertTrue(any(x["href"] == "/data-hub"
                            for x in _SUB_NAV["research"]))


# ────────────────────────────────────────────────────────────────────
# 3-6. Warm endpoint (needs a real server + admin session)
# ────────────────────────────────────────────────────────────────────
class TestWarmEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        from rcm_mc.auth.auth import create_user
        from rcm_mc.portfolio.store import PortfolioStore

        cls.tmp = tempfile.TemporaryDirectory()
        db_path = os.path.join(cls.tmp.name, "p.db")
        # Seed an admin (the gate lets through) + a plain user (the gate
        # rejects with 403 — role, not authentication, is the barrier).
        store = PortfolioStore(db_path)
        create_user(store, "boss", "supersecret1",
                    display_name="Boss", role="admin")
        create_user(store, "clerk", "supersecret1", display_name="Clerk")
        cls.port = _free_port()
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=db_path, auth=None)
        cls.thread = threading.Thread(target=cls.server.serve_forever,
                                      daemon=True)
        cls.thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def setUp(self):
        # The rate limiter is process-global; clear it so each test starts
        # with a fresh budget.
        from rcm_mc.server import _REFRESH_RATE_LIMITER
        _REFRESH_RATE_LIMITER.reset()

    def _base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _login(self, username: str):
        """Log in, return a Cookie header (session + csrf) and the csrf value."""
        body = urllib.parse.urlencode({
            "username": username, "password": "supersecret1",
        }).encode()
        req = urllib.request.Request(
            self._base() + "/api/login", data=body, method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            set_cookie = r.headers.get_all("Set-Cookie") or []
        jar = {}
        for hdr in set_cookie:
            first = hdr.split(";", 1)[0]
            k, _, v = first.partition("=")
            jar[k.strip()] = v
        cookie = "; ".join(f"{k}={v}" for k, v in jar.items())
        return cookie, jar.get("rcm_csrf", "")

    def _admin_cookies(self):
        return self._login("boss")

    def _get_job(self, job_id: str, cookie: str):
        req = urllib.request.Request(
            self._base() + f"/api/jobs/{job_id}",
            headers={"Cookie": cookie} if cookie else {})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode())

    def _post_warm(self, connector: str, *, cookie: str = "",
                   csrf: str = ""):
        headers = {"Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        if csrf:
            headers["X-CSRF-Token"] = csrf
        req = urllib.request.Request(
            self._base() + f"/api/data-hub/warm/{connector}",
            data=b"{}", method="POST", headers=headers)

        def _decode(raw: bytes):
            try:
                return json.loads(raw.decode())
            except (ValueError, UnicodeDecodeError):
                return {}

        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return r.status, _decode(r.read())
        except urllib.error.HTTPError as e:
            return e.code, _decode(e.read())

    def test_requires_authentication(self):
        # No session at all: the global auth gate rejects with 401 before
        # the handler runs (users exist, so anonymous POST is unauthorized).
        status, _ = self._post_warm("cms_coverage")
        self.assertIn(status, (401, 403))

    def test_non_admin_forbidden(self):
        # Authenticated but not admin: the handler's role gate returns 403.
        cookie, csrf = self._login("clerk")
        status, body = self._post_warm("cms_coverage", cookie=cookie,
                                       csrf=csrf)
        self.assertEqual(status, 403)
        self.assertEqual(body.get("code"), "FORBIDDEN")

    def test_unknown_connector_rejected(self):
        if not _estate_available():
            self.skipTest("estate not available on this deployment")
        cookie, csrf = self._admin_cookies()
        status, body = self._post_warm("not_a_real_connector",
                                       cookie=cookie, csrf=csrf)
        self.assertEqual(status, 400)
        self.assertEqual(body.get("code"), "UNKNOWN_CONNECTOR")

    def test_manual_ingest_connector_rejected(self):
        if not _estate_available():
            self.skipTest("estate not available on this deployment")
        cookie, csrf = self._admin_cookies()
        # openfda ingests manually (needs domain args) — the sweep skips it,
        # so warming it from the UI must be refused with the real command.
        status, body = self._post_warm("openfda", cookie=cookie, csrf=csrf)
        self.assertEqual(status, 400)
        self.assertEqual(body.get("code"), "MANUAL_INGEST")
        self.assertIn("command", body.get("detail", {}))

    def test_valid_connector_enqueues_job(self):
        if not _estate_available():
            self.skipTest("estate not available on this deployment")
        cookie, csrf = self._admin_cookies()
        fake = mock.Mock()
        fake.returncode = 0
        fake.stdout = json.dumps({"ok": True, "n_steps": 4, "n_failed": 0})
        fake.stderr = ""
        # Patch subprocess.run so the worker never touches the network.
        with mock.patch("subprocess.run", return_value=fake) as m:
            status, body = self._post_warm("cms_coverage",
                                           cookie=cookie, csrf=csrf)
            self.assertEqual(status, 202, body)
            job_id = body["job_id"]
            self.assertTrue(job_id)
            # Poll the job to completion while the mock is still active.
            deadline = time.time() + 8
            job = None
            while time.time() < deadline:
                job = self._get_job(job_id, cookie)
                if job.get("status") in ("done", "failed"):
                    break
                time.sleep(0.15)
            self.assertEqual(job.get("status"), "done", job)
            self.assertEqual(job["result"]["connector"], "cms_coverage")
            self.assertTrue(m.called)

    def test_rate_limited_on_second_warm(self):
        if not _estate_available():
            self.skipTest("estate not available on this deployment")
        cookie, csrf = self._admin_cookies()
        fake = mock.Mock()
        fake.returncode = 0
        fake.stdout = json.dumps({"ok": True})
        fake.stderr = ""
        with mock.patch("subprocess.run", return_value=fake):
            first = self._post_warm("provider_data", cookie=cookie, csrf=csrf)
            second = self._post_warm("provider_data", cookie=cookie, csrf=csrf)
        self.assertEqual(first[0], 202, first)
        self.assertEqual(second[0], 429, second)
        self.assertEqual(second[1].get("code"), "RATE_LIMITED")


class TestCmsDataBrowserReal(unittest.TestCase):
    """The CMS Data Browser must render REAL estate data, not synthetic."""

    def test_compute_is_estate_scoped(self):
        from rcm_mc.data_public.cms_data_browser import (
            compute_cms_data_browser, _CMS_CONNECTORS,
        )
        r = compute_cms_data_browser()
        if not _estate_available():
            self.assertFalse(r.available)
            return
        self.assertTrue(r.available)
        # Every catalog row belongs to a CMS connector, and counts are the
        # real ingested totals (>= 0), never fabricated.
        for d in r.datasets:
            self.assertIn(d.connector, _CMS_CONNECTORS)
            self.assertGreaterEqual(d.record_count, 0)
        # cached_datasets is exactly the count of rows actually on disk.
        self.assertEqual(
            r.cached_datasets,
            sum(1 for d in r.datasets if d.record_count > 0))

    def test_page_renders_real_sections(self):
        from rcm_mc.ui.data_public.cms_data_browser_page import (
            render_cms_data_browser,
        )
        html = render_cms_data_browser({})
        if _estate_available():
            for needle in ("CMS Public Data Browser", "CMS Connectors",
                           "Dataset Catalog", "/data-hub"):
                self.assertIn(needle, html, f"missing {needle!r}")
        else:
            # honest empty state, never a 500
            self.assertIn("/data-hub", html)


class TestNotReadyHidden(unittest.TestCase):
    """Synthetic 'not ready' pages are hidden from partner catalogs but
    stay reachable by URL."""

    def test_ma_star_is_hidden(self):
        from rcm_mc.ui._surface_visibility import (
            is_internal, curate_rows, NOT_READY_ROUTES,
        )
        self.assertIn("/ma-star", NOT_READY_ROUTES)
        self.assertTrue(is_internal("/ma-star"))
        kept = [r["route"] for r in curate_rows(
            [{"route": "/ma-star", "label": "MA Star"},
             {"route": "/data-hub", "label": "Data Hub"}])]
        self.assertEqual(kept, ["/data-hub"])

    def test_hidden_page_not_pinned_in_nav_or_palette(self):
        # A hidden route must not be pinned anywhere that requires it to
        # render as a card (else the nav/palette walk tests would fail).
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _NAV_FLAGSHIPS, _SUB_NAV,
        )
        self.assertNotIn("/ma-star",
                         {m["route"] for m in _DEFAULT_PALETTE_MODULES})
        self.assertNotIn("/ma-star",
                         {r for v in _NAV_FLAGSHIPS.values() for r in v})
        self.assertNotIn("/ma-star",
                         {x["href"] for v in _SUB_NAV.values() for x in v})

    def test_real_data_pages_stay_visible(self):
        from rcm_mc.ui._surface_visibility import is_internal
        for route in ("/data-hub", "/cms-data-browser", "/connector-estate"):
            self.assertFalse(is_internal(route), route)


if __name__ == "__main__":
    unittest.main()
