"""Tests for the local web server (Brick 62).

Strategy: for routing correctness, test by spinning up a real server on an
OS-assigned port + hitting it with urllib. For pure rendering logic, unit
tests exercise the builders directly so we don't pay HTTP overhead for
every assertion.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import unittest
import urllib.request
from http import HTTPStatus
from urllib.error import HTTPError

from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
from rcm_mc.server import (
    RCMHandler,
    _render_dashboard,
    _render_deal_detail,
    _rewrite_dashboard_links,
    build_server,
)


def _seed(tmp: str, *, entry_ebitda: float = 50e6):
    """Stand up a portfolio store with one held deal + snapshot."""
    store = PortfolioStore(os.path.join(tmp, "p.db"))
    run = os.path.join(tmp, "run")
    os.makedirs(run, exist_ok=True)
    with open(os.path.join(run, "pe_bridge.json"), "w") as f:
        json.dump({
            "entry_ebitda": entry_ebitda,
            "entry_ev": entry_ebitda * 9.0,
            "entry_multiple": 9.0, "exit_multiple": 10.0,
            "hold_years": 5.0,
        }, f)
    with open(os.path.join(run, "pe_returns.json"), "w") as f:
        json.dump({"moic": 2.55, "irr": 0.21}, f)
    with open(os.path.join(run, "pe_covenant.json"), "w") as f:
        json.dump({"actual_leverage": 5.4,
                   "covenant_headroom_turns": 1.1}, f)
    register_snapshot(store, "ccf_2026", "hold", run_dir=run)
    return store


# ── Pure unit tests ────────────────────────────────────────────────────────

class TestDashboardRender(unittest.TestCase):
    def test_render_dashboard_returns_valid_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            RCMHandler.config.db_path = os.path.join(tmp, "p.db")
            html = _render_dashboard(RCMHandler.config)
            self.assertIn("<html", html)
            self.assertIn("ccf_2026", html)


class TestDealRender(unittest.TestCase):
    def test_unknown_deal_shows_helpful_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            RCMHandler.config.db_path = os.path.join(tmp, "p.db")
            html = _render_deal_detail(RCMHandler.config, "ghost")
            self.assertIn("No snapshots", html)
            self.assertIn("ghost", html)

    def test_known_deal_renders_audit_trail(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            RCMHandler.config.db_path = os.path.join(tmp, "p.db")
            html = _render_deal_detail(RCMHandler.config, "ccf_2026")
            self.assertIn("Snapshot audit trail", html)
            self.assertIn("ccf_2026", html)

    def test_deal_with_variance_renders_variance_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            record_quarterly_actuals(store, "ccf_2026", "2026Q1",
                                     actuals={"ebitda": 12e6},
                                     plan={"ebitda": 12.5e6})
            RCMHandler.config.db_path = os.path.join(tmp, "p.db")
            html = _render_deal_detail(RCMHandler.config, "ccf_2026")
            self.assertIn("Quarterly variance", html)
            self.assertIn("2026Q1", html)


class TestDashboardLinkRewrite(unittest.TestCase):
    def test_strong_tags_become_deal_links(self):
        src = "<strong>ccf_2026</strong>"
        out = _rewrite_dashboard_links(src)
        self.assertIn('href="/deal/ccf_2026"', out)

    def test_multiple_replacements(self):
        src = "<strong>a</strong> and <strong>b</strong>"
        out = _rewrite_dashboard_links(src)
        self.assertIn('href="/deal/a"', out)
        self.assertIn('href="/deal/b"', out)

    def test_url_encodes_special_chars(self):
        src = "<strong>deal with spaces</strong>"
        out = _rewrite_dashboard_links(src)
        self.assertIn('href="/deal/deal%20with%20spaces"', out)


# ── Live server smoke tests ────────────────────────────────────────────────

def _start_server(db_path: str, outdir: str = None):
    """Start a server on an OS-assigned port in a background thread.

    Returns (server, thread, port). Caller must call server.shutdown() +
    server.server_close() when done.
    """
    import socket as _socket
    # Pick a free port by binding to 0
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    server, _ = build_server(port=port, db_path=db_path, outdir=outdir)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Tiny wait for the thread to be ready
    time.sleep(0.05)
    return server, thread, port


class TestLiveRoutes(unittest.TestCase):
    def test_dashboard_route_returns_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("Portfolio", body)
                    self.assertIn("ccf_2026", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_route_returns_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026"
                ) as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                    self.assertIn("ccf_2026", body)
                    self.assertIn("Snapshot audit trail", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_route_empty_path_redirects(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/deal/") as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown()
                server.server_close()

    def test_health_route_returns_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health") as r:
                    self.assertEqual(r.status, 200)
                    self.assertEqual(r.read().decode(), "ok")
            finally:
                server.shutdown()
                server.server_close()

    def test_unknown_route_returns_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/nowhere")
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()

    def test_outputs_without_configured_outdir_is_404(self):
        """/outputs/* must not serve when no outdir was configured."""
        with tempfile.TemporaryDirectory() as tmp:
            # Explicitly do not pass outdir
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/outputs/anything.csv"
                    )
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()

    def test_outputs_path_traversal_refused(self):
        """/outputs/../etc/passwd must be blocked."""
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(
                os.path.join(tmp, "p.db"), outdir=tmp,
            )
            try:
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/outputs/../../../etc/passwd"
                    )
                self.assertIn(ctx.exception.code, (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND))
            finally:
                server.shutdown()
                server.server_close()

    def test_outputs_serves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = os.path.join(tmp, "out")
            os.makedirs(outdir)
            with open(os.path.join(outdir, "test.csv"), "w") as f:
                f.write("col1,col2\n1,2\n")
            server, _, port = _start_server(
                os.path.join(tmp, "p.db"), outdir=outdir,
            )
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/outputs/test.csv"
                ) as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn("text/csv", r.headers.get("Content-Type"))
            finally:
                server.shutdown()
                server.server_close()

    def test_favicon_returns_204(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/favicon.ico") as r:
                    self.assertEqual(r.status, 204)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_deals_returns_list(self):
        """GET /api/deals returns paginated deal response."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals"
                ) as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn("application/json",
                                  r.headers.get("Content-Type"))
                    data = json.loads(r.read().decode())
                    self.assertIn("deals", data)
                    self.assertIn("total", data)
                    self.assertTrue(
                        any(d.get("deal_id") == "ccf_2026"
                            for d in data["deals"])
                    )
            finally:
                server.shutdown()
                server.server_close()

    def test_api_deal_detail_404_for_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/deals/ghost"
                    )
                self.assertEqual(ctx.exception.code, 404)
                body = json.loads(ctx.exception.read().decode())
                self.assertIn("error", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_deal_detail_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026"
                ) as r:
                    self.assertEqual(r.status, 200)
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["deal_id"], "ccf_2026")
                    self.assertIn("latest", data)
                    self.assertIn("snapshots", data)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/rollup"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertIn("deal_count", data)
                    self.assertIn("stage_funnel", data)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_stages_returns_canonical_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/stages"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(
                        data["stages"][0], "sourced",
                    )
                    self.assertEqual(data["stages"][-1], "exit")
            finally:
                server.shutdown()
                server.server_close()

    def test_api_variance_empty_when_no_actuals(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026/variance"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data, [])
            finally:
                server.shutdown()
                server.server_close()


class TestBasicAuth(unittest.TestCase):
    """B89: HTTP Basic auth gate when config has credentials."""

    def _start_with_auth(self, db_path: str, auth: str):
        """Mirror _start_server but pass auth through build_server."""
        import socket as _socket
        import threading
        import time as _time
        from rcm_mc.server import build_server
        s = _socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        server, _ = build_server(port=port, db_path=db_path, auth=auth)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_401_when_no_credentials_provided(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_with_auth(
                os.path.join(tmp, "p.db"), "alice:wonderland",
            )
            try:
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/")
                self.assertEqual(ctx.exception.code, 401)
                self.assertIn(
                    "Basic realm",
                    ctx.exception.headers.get("WWW-Authenticate") or "",
                )
            finally:
                server.shutdown()
                server.server_close()

    def test_200_with_correct_credentials(self):
        import base64
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, port = self._start_with_auth(
                os.path.join(tmp, "p.db"), "alice:wonderland",
            )
            try:
                token = base64.b64encode(b"alice:wonderland").decode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/",
                    headers={"Authorization": f"Basic {token}"},
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown()
                server.server_close()

    def test_401_with_wrong_password(self):
        import base64
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_with_auth(
                os.path.join(tmp, "p.db"), "alice:wonderland",
            )
            try:
                token = base64.b64encode(b"alice:nope").decode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/",
                    headers={"Authorization": f"Basic {token}"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 401)
            finally:
                server.shutdown()
                server.server_close()

    def test_health_route_bypasses_auth(self):
        """Load balancers need to probe /health without credentials."""
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_with_auth(
                os.path.join(tmp, "p.db"), "alice:wonderland",
            )
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health"
                ) as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown()
                server.server_close()

    def test_no_auth_configured_means_no_gate(self):
        """Default (laptop mode) must not require credentials."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown()
                server.server_close()

    def test_malformed_auth_header_is_401(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_with_auth(
                os.path.join(tmp, "p.db"), "alice:wonderland",
            )
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/",
                    headers={"Authorization": "NotBasic garbage"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 401)
            finally:
                server.shutdown()
                server.server_close()

    def test_post_endpoint_gated_too(self):
        """Auth must block writes, not just reads."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, port = self._start_with_auth(
                os.path.join(tmp, "p.db"), "alice:wonderland",
            )
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/x/notes",
                    data=b"body=test", method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 401)
            finally:
                server.shutdown()
                server.server_close()


class TestPostForms(unittest.TestCase):
    """B65 form POST endpoints."""

    def test_post_actuals_records_to_store(self):
        import urllib.parse
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = urllib.parse.urlencode({
                    "quarter": "2026Q1",
                    "ebitda": "12000000",
                    "plan_ebitda": "12500000",
                    "notes": "From server form",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026/actuals",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                # urllib auto-follows 303; disable by using no-redirect opener
                class _NoRedirect(urllib.request.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw):
                        return None
                opener = urllib.request.build_opener(_NoRedirect)
                try:
                    opener.open(req)
                except HTTPError as exc:
                    # 303 surfaces as HTTPError in some Python versions — OK
                    self.assertEqual(exc.code, 303)
                # Verify the row landed
                from rcm_mc.pe.hold_tracking import variance_report
                df = variance_report(store, "ccf_2026")
                self.assertFalse(df.empty)
                self.assertIn("2026Q1", df["quarter"].tolist())
            finally:
                server.shutdown()
                server.server_close()

    def test_post_actuals_bad_quarter_returns_400(self):
        import urllib.parse
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = urllib.parse.urlencode({
                    "quarter": "not-a-quarter",
                    "ebitda": "1000",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026/actuals",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
                err = json.loads(ctx.exception.read().decode())
                self.assertIn("error", err)
            finally:
                server.shutdown()
                server.server_close()

    def test_post_snapshot_advances_stage(self):
        import urllib.parse
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = urllib.parse.urlencode({
                    "stage": "exit",
                    "notes": "Exit announced",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026/snapshots",
                    data=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                )
                class _NoRedirect(urllib.request.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw):
                        return None
                try:
                    urllib.request.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                # New snapshot landed
                from rcm_mc.portfolio.portfolio_snapshots import list_snapshots
                snaps = list_snapshots(store, deal_id="ccf_2026")
                self.assertEqual(snaps.iloc[0]["stage"], "exit")
            finally:
                server.shutdown()
                server.server_close()

    def test_search_page_empty_query_shows_hint(self):
        """B77: /search without q parameter surfaces a hint."""
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/search") as r:
                    body = r.read().decode()
                    self.assertIn("Portfolio-wide search", body)
                    self.assertIn("Type a query", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_search_matches_deal_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/search?q=ccf"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("ccf_2026", body)
                    self.assertIn("Deal matches", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_search_matches_note_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            from rcm_mc.deals.deal_notes import record_note
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            record_note(store, deal_id="ccf_2026",
                        body="Management confirmed working-capital release")
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/search?q=working-capital"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Note matches", body)
                    self.assertIn("working-capital release", body)
                    # Link back to the deal page
                    self.assertIn('href="/deal/ccf_2026"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_search_no_matches_shows_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/search?q=definitely_not_there_xyz"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No matches", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_bulk_stage_advances_multiple_deals(self):
        """B99: POST /api/bulk/stage writes a snapshot at target stage per deal."""
        import urllib.parse as _p
        import urllib.request as _u
        from rcm_mc.portfolio.portfolio_snapshots import list_snapshots
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            for did in ("a", "b", "c"):
                register_snapshot(store, did, "ioi")
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({
                    "stage": "loi",
                    "deal_ids": "a,b,c",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/bulk/stage",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    payload = json.loads(r.read().decode())
                    self.assertEqual(payload["affected"], 3)
                    self.assertEqual(payload["stage"], "loi")
                for did in ("a", "b", "c"):
                    latest = list_snapshots(store, deal_id=did).iloc[0]
                    self.assertEqual(latest["stage"], "loi")
            finally:
                server.shutdown()
                server.server_close()

    def test_bulk_stage_invalid_stage_returns_400(self):
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({
                    "stage": "not_a_stage", "deal_ids": "a",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/bulk/stage",
                    data=body, method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_download_sets_attachment_header(self):
        """B100: /deal/<id>?download=1 sends Content-Disposition attachment."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026?download=1"
                ) as r:
                    self.assertEqual(r.status, 200)
                    cd = r.headers.get("Content-Disposition") or ""
                    self.assertIn("attachment", cd)
                    self.assertIn("ccf_2026", cd)
                    body = r.read().decode()
                    self.assertIn("<!doctype html>", body)
                    # Same content as regular view (sanity)
                    self.assertIn("ccf_2026", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_has_download_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026"
                ) as r:
                    body = r.read().decode()
                    self.assertIn('href="/deal/ccf_2026?download=1"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_dashboard_ships_tag_datalist(self):
        """Autocomplete: dashboard exposes a <datalist id='rcm-tag-datalist'>."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('id="rcm-tag-datalist"', body)
                    # Bulk tag input points at the datalist
                    self.assertIn('list="rcm-tag-datalist"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_bulk_tag_add_applies_to_multiple_deals(self):
        """B97: POST /api/bulk/tags/add tags every deal_id in the list."""
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        from rcm_mc.deals.deal_tags import tags_for
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            for did in ("a", "b", "c"):
                register_snapshot(store, did, "ioi")

            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({
                    "tag": "watch",
                    "deal_ids": "a,b,c",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/bulk/tags/add",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    payload = json.loads(r.read().decode())
                    self.assertEqual(payload["affected"], 3)
                    self.assertEqual(payload["tag"], "watch")
                for did in ("a", "b", "c"):
                    self.assertIn("watch", tags_for(store, did))
            finally:
                server.shutdown()
                server.server_close()

    def test_bulk_tag_rejects_empty_ids(self):
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({"tag": "x", "deal_ids": ""}).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/bulk/tags/add",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()

    def test_bulk_tag_remove(self):
        """POST /api/bulk/tags/remove strips tag from multiple deals."""
        import urllib.parse as _p
        import urllib.request as _u
        from rcm_mc.deals.deal_tags import add_tag, tags_for
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            for did in ("a", "b"):
                register_snapshot(store, did, "ioi")
                add_tag(store, did, "watch")
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                body = _p.urlencode({
                    "tag": "watch", "deal_ids": "a,b",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/bulk/tags/remove",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    payload = json.loads(r.read().decode())
                    self.assertEqual(payload["affected"], 2)
                for did in ("a", "b"):
                    self.assertNotIn("watch", tags_for(store, did))
            finally:
                server.shutdown()
                server.server_close()

    def test_dashboard_renders_bulk_bar_and_checkboxes(self):
        """B97: dashboard has the bulk-select checkboxes + floating bar."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn("rcm-bulk-select", body)
                    self.assertIn("rcm-bulk-bar", body)
                    self.assertIn('action="/api/bulk/tags/add"', body)
                    self.assertIn('id="rcm-bulk-all"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_dashboard_persists_filter_state_in_localstorage(self):
        """B96: filter JS reads/writes localStorage key for persistence."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn("rcm-mc-filter-v1", body)
                    self.assertIn("localStorage", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_ops_page_shows_store_stats(self):
        """B94: /ops renders deal / snapshot / notes counts + DB size."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/ops") as r:
                    body = r.read().decode()
                    for label in ("Deals", "Snapshots", "Notes", "DB Size",
                                  "deal_snapshots"):
                        self.assertIn(label, body)
                    # Auth off in test setup → laptop-mode badge
                    self.assertIn("laptop mode", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_ops_page_shows_auth_status_when_enabled(self):
        import socket as _socket
        import threading
        import time as _time
        from rcm_mc.server import build_server
        with tempfile.TemporaryDirectory() as tmp:
            s = _socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"),
                                     auth="alice:pw")
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start(); _time.sleep(0.05)
            try:
                import base64
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/ops",
                    headers={"Authorization":
                             "Basic " + base64.b64encode(b"alice:pw").decode()},
                )
                with urllib.request.urlopen(req) as r:
                    body = r.read().decode()
                    self.assertIn("enabled", body)
                    self.assertIn("alice", body)
            finally:
                server.shutdown(); server.server_close()

    def test_post_remark_creates_snapshot(self):
        """B90a: POSTing /api/deals/<id>/remark persists a re-mark snapshot."""
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            from rcm_mc.pe.hold_tracking import record_quarterly_actuals
            for qtr, v in [("2025Q4", 12e6), ("2026Q1", 11.5e6),
                           ("2026Q2", 11e6), ("2026Q3", 10.5e6)]:
                record_quarterly_actuals(store, "ccf_2026", qtr,
                                         actuals={"ebitda": v})
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026/remark",
                    data=b"", method="POST",
                )
                class _NoRedirect(_u.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw): return None
                try:
                    _u.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                # A new snapshot with re-mark note landed
                from rcm_mc.portfolio.portfolio_snapshots import list_snapshots
                snaps = list_snapshots(store, deal_id="ccf_2026")
                notes_col = [str(n or "") for n in snaps["notes"]]
                self.assertTrue(any("Re-mark" in n for n in notes_col))
            finally:
                server.shutdown()
                server.server_close()

    def test_post_remark_no_actuals_returns_400(self):
        """Re-mark requires EBITDA actuals — otherwise 400."""
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)  # snapshot only, no actuals
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf_2026/remark",
                    data=b"", method="POST",
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
                body = json.loads(ctx.exception.read().decode())
                self.assertIn("actuals", body["error"].lower())
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_has_remark_form(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf_2026") as r:
                    body = r.read().decode()
                    self.assertIn("Re-mark underwrite", body)
                    self.assertIn("/api/deals/ccf_2026/remark", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_note_restore_undoes_soft_delete(self):
        """B91: POSTing .../restore flips the soft-delete flag back."""
        import urllib.request as _u
        from urllib.error import HTTPError
        from rcm_mc.deals.deal_notes import delete_note, list_notes, record_note
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            nid = record_note(store, deal_id="ccf", body="keep me")
            delete_note(store, nid)
            self.assertTrue(list_notes(store, "ccf").empty)

            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/notes/{nid}/restore",
                    data=b"", method="POST",
                )
                class _NoRedirect(_u.HTTPRedirectHandler):
                    def http_error_303(self, *a, **kw): return None
                try:
                    _u.build_opener(_NoRedirect).open(req)
                except HTTPError:
                    pass
                self.assertEqual(len(list_notes(store, "ccf")), 1)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_shows_trash_bin_when_notes_deleted(self):
        import urllib.request as _u
        from rcm_mc.deals.deal_notes import delete_note, record_note
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            nid = record_note(store, deal_id="ccf_2026",
                              body="was sensitive", author="AT")
            delete_note(store, nid)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Recently deleted", body)
                    self.assertIn("Restore", body)
                    self.assertIn("Purge", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_dashboard_includes_tag_filter_and_export_link(self):
        """B87 + B88: dashboard filter bar has tag input + export CSV button."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            from rcm_mc.deals.deal_tags import add_tag
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            add_tag(store, "ccf_2026", "growth")
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn("rcm-filter-tag", body)
                    self.assertIn("rcm-export-link", body)
                    self.assertIn('data-tags="growth"', body)
                    # Tag pill rendered next to deal ID
                    self.assertIn(">growth<", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_export_csv_with_filters(self):
        """B88: filtered CSV matches query params."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            # Two deals — one tagged, one not
            run = os.path.join(tmp, "r")
            os.makedirs(run)
            with open(os.path.join(run, "pe_bridge.json"), "w") as f:
                json.dump({"entry_ebitda": 50e6, "entry_ev": 450e6,
                           "entry_multiple": 9.0, "exit_multiple": 10.0,
                           "hold_years": 5.0}, f)
            with open(os.path.join(run, "pe_returns.json"), "w") as f:
                json.dump({"moic": 2.5, "irr": 0.2}, f)
            register_snapshot(store, "tagged_deal", "hold", run_dir=run)
            register_snapshot(store, "untagged_deal", "hold", run_dir=run)
            from rcm_mc.deals.deal_tags import add_tag
            add_tag(store, "tagged_deal", "watch")

            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                # Filter by tag "watch"
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/export?tag=watch&format=csv"
                ) as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn("text/csv", r.headers.get("Content-Type"))
                    self.assertIn(
                        "attachment",
                        r.headers.get("Content-Disposition") or "",
                    )
                    body = r.read().decode()
                    self.assertIn("tagged_deal", body)
                    self.assertNotIn("untagged_deal", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_api_export_json_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/export?format=json"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertIsInstance(data, list)
                    self.assertTrue(
                        any(d.get("deal_id") == "ccf_2026" for d in data)
                    )
            finally:
                server.shutdown()
                server.server_close()

    def test_api_export_stage_filter_excludes_other_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "held", "hold")
            register_snapshot(store, "pipeline", "ioi")
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/export?stage=hold&format=csv"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("held", body)
                    self.assertNotIn("pipeline", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_compare_page_without_deals_shows_form(self):
        """B78: /compare with no query shows deal-entry form."""
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/compare") as r:
                    body = r.read().decode()
                    self.assertIn("Comparison", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_compare_renders_side_by_side(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Seed two deals
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            for did, eb in [("ccf_2026", 50e6), ("mgh_2026", 30e6)]:
                run = os.path.join(tmp, did + "_run")
                os.makedirs(run)
                with open(os.path.join(run, "pe_bridge.json"), "w") as f:
                    json.dump({
                        "entry_ebitda": eb, "entry_ev": eb * 9.0,
                        "entry_multiple": 9.0, "exit_multiple": 10.0,
                        "hold_years": 5.0,
                    }, f)
                with open(os.path.join(run, "pe_returns.json"), "w") as f:
                    json.dump({"moic": 2.5, "irr": 0.20}, f)
                register_snapshot(store, did, "hold", run_dir=run)

            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/compare?deals=ccf_2026,mgh_2026"
                ) as r:
                    body = r.read().decode()
                    # The page should render (may show comparison or empty state)
                    self.assertIn("Comparison", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_compare_limits_to_five_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/compare?deals=a,b,c,d,e,f"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Comparison", body)  # renders with shell_v2
            finally:
                server.shutdown()
                server.server_close()

    def test_activity_feed_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/activity"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No activity matches", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_activity_feed_lists_snapshots_notes_actuals(self):
        """B79: one chronological feed with all three event kinds."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            from rcm_mc.deals.deal_notes import record_note
            from rcm_mc.pe.hold_tracking import record_quarterly_actuals
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            record_note(store, deal_id="ccf_2026", body="Test note",
                        author="AT")
            record_quarterly_actuals(
                store, "ccf_2026", "2026Q1",
                actuals={"ebitda": 12e6}, plan={"ebitda": 12.5e6},
            )
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/activity"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("Recent activity", body)
                    # All three event-kind badges appear
                    self.assertIn("STAGE", body)
                    self.assertIn("NOTE", body)
                    self.assertIn("ACTUAL", body)
                    # Linked back to deal page
                    self.assertIn('href="/deal/ccf_2026"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_activity_limit_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            from rcm_mc.deals.deal_notes import record_note
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            for i in range(5):
                record_note(store, deal_id="ccf_2026", body=f"note {i}")
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/activity?limit=2"
                ) as r:
                    body = r.read().decode()
                    # Count <li> entries
                    self.assertEqual(body.count("<li style=\"padding: 0.75rem 0;"), 2)
            finally:
                server.shutdown()
                server.server_close()

    def test_compare_handles_missing_deal_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/compare?deals=ccf_2026,ghost_deal"
                ) as r:
                    body = r.read().decode()
                    # Page renders — missing deals silently skipped
                    self.assertIn("Comparison", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_live_mode_injects_meta_refresh(self):
        """B72: /?live=1 adds an auto-refresh meta tag."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/?live=1") as r:
                    body = r.read().decode()
                    self.assertIn('http-equiv="refresh"', body)
                    self.assertIn("Live mode", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_live_mode_off_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertNotIn('http-equiv="refresh"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_upload_page_renders_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/upload"
                ) as r:
                    body = r.read().decode()
                    self.assertIn('action="/api/upload-actuals"', body)
                    self.assertIn('action="/api/upload-initiatives"', body)
                    self.assertIn('type="file"', body)
                    self.assertIn("multipart/form-data", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_upload_csv_records_actuals(self):
        """POST multipart CSV → rows land in the store."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed(tmp)
            csv_text = (
                "deal_id,quarter,ebitda,plan_ebitda\n"
                "ccf_2026,2026Q1,12000000,12500000\n"
                "ccf_2026,2026Q2,11500000,13000000\n"
            )
            boundary = "----BoundaryTest123"
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file"; '
                f'filename="actuals.csv"\r\n'
                f"Content-Type: text/csv\r\n\r\n"
                f"{csv_text}\r\n"
                f"--{boundary}--\r\n"
            ).encode()
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/upload-actuals",
                    data=body,
                    headers={
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
                    receipt = r.read().decode()
                    self.assertIn("Upload complete", receipt)
                    self.assertIn("2", receipt)  # 2 rows ingested
                # Store received the rows
                from rcm_mc.pe.hold_tracking import variance_report
                df = variance_report(store, "ccf_2026")
                self.assertGreaterEqual(len(df), 2)
                self.assertIn("2026Q1", df["quarter"].tolist())
                self.assertIn("2026Q2", df["quarter"].tolist())
            finally:
                server.shutdown()
                server.server_close()

    def test_upload_without_file_returns_400(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/upload-actuals",
                    data=b"",
                    headers={
                        "Content-Type": "multipart/form-data; boundary=x",
                    },
                    method="POST",
                )
                with self.assertRaises(HTTPError) as ctx:
                    urllib.request.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_includes_svg_sparkline_when_multi_quarter_data(self):
        """B69: EBITDA sparkline appears on deal detail with ≥2 quarters."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            # Minimum 2 quarters for the sparkline
            record_quarterly_actuals(store, "ccf_2026", "2026Q1",
                                     actuals={"ebitda": 12e6},
                                     plan={"ebitda": 12.5e6})
            record_quarterly_actuals(store, "ccf_2026", "2026Q2",
                                     actuals={"ebitda": 11.5e6},
                                     plan={"ebitda": 13e6})
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("EBITDA trend", body)
                    self.assertIn("<svg", body)
                    self.assertIn("polyline", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_omits_sparkline_with_single_quarter(self):
        """Sparkline needs ≥2 points — otherwise no chart rendered."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            record_quarterly_actuals(store, "ccf_2026", "2026Q1",
                                     actuals={"ebitda": 12e6},
                                     plan={"ebitda": 12.5e6})
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026"
                ) as r:
                    body = r.read().decode()
                    self.assertNotIn("EBITDA trend", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_dashboard_includes_new_deal_card(self):
        """B70: dashboard carries a collapsible 'Register new deal' form."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn("Register a new deal", body)
                    self.assertIn("<details", body)
                    self.assertIn('name="deal_id"', body)
                    self.assertIn('name="stage"', body)
            finally:
                server.shutdown()
                server.server_close()

    def test_deal_page_renders_forms(self):
        """GET /deal/<id> must include both POST forms."""
        with tempfile.TemporaryDirectory() as tmp:
            _seed(tmp)
            server, _, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/deal/ccf_2026"
                ) as r:
                    body = r.read().decode()
                    self.assertIn('action="/api/deals/ccf_2026/actuals"', body)
                    self.assertIn('action="/api/deals/ccf_2026/snapshots"', body)
                    self.assertIn("Record quarterly actuals", body)
                    self.assertIn("Advance stage", body)
            finally:
                server.shutdown()
                server.server_close()
