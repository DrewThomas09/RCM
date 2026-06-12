"""Saved Charts — owner-scoped chart-config persistence + library page.

Mirrors the saved_screens contract (the chart IS its URL query string)
plus the chart-specific route allow-list, the save strips on the two
chart pages, and the /charts registration invariants.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.saved_charts import (
    ALLOWED_ROUTES, delete_chart, list_charts, save_chart,
)
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.saved_charts_page import (
    render_saved_charts_page, save_chart_form,
)


class SavedChartsStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "s.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_list_owner_scoped(self):
        save_chart(self.store, "alice", "Denials Pareto",
                   "/chart-builder", "type=pareto&data=A%09B")
        save_chart(self.store, "bob", "IC slide", "/exhibit", "t0=column")
        a = list_charts(self.store, "alice")
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["title"], "Denials Pareto")
        self.assertEqual(a[0]["route"], "/chart-builder")
        self.assertEqual(len(list_charts(self.store, "bob")), 1)

    def test_route_allow_list_enforced(self):
        for bad in ("/deal/1", "https://evil.example", "", "chart-builder"):
            with self.assertRaises(ValueError, msg=bad):
                save_chart(self.store, "alice", "x", bad, "a=1")
        self.assertEqual(ALLOWED_ROUTES,
                         ("/chart-builder", "/exhibit"))

    def test_leading_question_mark_stripped(self):
        save_chart(self.store, "alice", "t", "/chart-builder", "?type=pie")
        self.assertEqual(list_charts(self.store, "alice")[0]["query_params"],
                         "type=pie")

    def test_empty_owner_or_title_rejected(self):
        with self.assertRaises(ValueError):
            save_chart(self.store, "", "t", "/chart-builder", "a=1")
        with self.assertRaises(ValueError):
            save_chart(self.store, "alice", "  ", "/chart-builder", "a=1")

    def test_delete_is_owner_scoped(self):
        cid = save_chart(self.store, "alice", "mine", "/chart-builder",
                         "a=1")
        self.assertFalse(delete_chart(self.store, "bob", cid))
        self.assertEqual(len(list_charts(self.store, "alice")), 1)
        self.assertTrue(delete_chart(self.store, "alice", cid))
        self.assertEqual(list_charts(self.store, "alice"), [])

    def test_newest_first(self):
        save_chart(self.store, "a", "first", "/chart-builder", "x=1")
        save_chart(self.store, "a", "second", "/exhibit", "x=2")
        self.assertEqual([c["title"] for c in list_charts(self.store, "a")],
                         ["second", "first"])

    def test_qs_capped_not_rejected(self):
        save_chart(self.store, "a", "big", "/chart-builder", "d=" + "x" * 9000)
        qp = list_charts(self.store, "a")[0]["query_params"]
        self.assertLessEqual(len(qp), 8000)


class SavedChartsPageTests(unittest.TestCase):
    def test_signed_out_empty_state(self):
        h = render_saved_charts_page([], owner="")
        self.assertIn("Sign in", h)

    def test_empty_library_empty_state(self):
        h = render_saved_charts_page([], owner="alice")
        self.assertIn("No saved charts yet", h)

    def test_rows_render_open_and_delete(self):
        charts = [{"id": 7, "title": "Denials Pareto",
                   "route": "/chart-builder",
                   "query_params": "type=pareto&data=A%09B",
                   "created_at": "2026-06-12T01:00:00+00:00"}]
        h = render_saved_charts_page(charts, owner="alice")
        self.assertIn("Denials Pareto", h)
        self.assertIn("/chart-builder?type=pareto", h)
        self.assertIn("/api/charts/delete", h)
        self.assertIn('value="7"', h)
        self.assertIn("2026-06-12", h)

    def test_titles_escaped(self):
        charts = [{"id": 1, "title": "<script>x</script>",
                   "route": "/exhibit", "query_params": "",
                   "created_at": "2026-06-12"}]
        h = render_saved_charts_page(charts, owner="a")
        self.assertNotIn("<script>x</script>", h)
        self.assertIn("&lt;script&gt;", h)

    def test_save_strip_on_both_chart_pages(self):
        from rcm_mc.ui.chart_builder_page import render_chart_builder_page
        from rcm_mc.ui.exhibit_page import render_exhibit_page
        for h, route in ((render_chart_builder_page({}), "/chart-builder"),
                         (render_exhibit_page({}), "/exhibit")):
            self.assertIn("/api/charts/save", h, route)
            self.assertIn("Save to library", h, route)
            self.assertIn(f'value="{route}"', h, route)
            # The qs snapshot happens client-side at submit.
            self.assertIn("location.search", h, route)

    def test_form_targets_post_endpoints(self):
        f = save_chart_form("/chart-builder")
        self.assertIn('method="post"', f)
        self.assertIn('action="/api/charts/save"', f)

    def test_registered_in_palette_nav_and_guide(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_NAV, _SUB_SECTION_MAP)
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/charts", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/charts"), "research")
        self.assertIn("/charts",
                      [e["href"] for e in _SUB_NAV["research"]])
        self.assertIsNotNone(
            build_guide_context_packet("/charts").page_context)


class SavedChartsE2ETests(unittest.TestCase):
    """Real-HTTP save → list → delete, per the e2e house convention
    (login for a csrf token + session, POST the forms, read the page)."""

    @classmethod
    def setUpClass(cls):
        import json
        import socket
        import threading
        import time
        import urllib.parse as _p
        import urllib.request as _u
        from rcm_mc.auth.auth import create_user
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls.tmp.name, "p.db")
        create_user(PortfolioStore(db), "alice", "Str0ng!Pass",
                    role="admin")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=db)
        cls.t = threading.Thread(target=cls.server.serve_forever,
                                 daemon=True)
        cls.t.start()
        time.sleep(0.2)
        body = _p.urlencode({"username": "alice",
                             "password": "Str0ng!Pass"}).encode()
        req = _u.Request(
            f"http://127.0.0.1:{cls.port}/api/login", data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json"})
        with _u.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
        cls.token = data["token"]
        cls.csrf = data["csrf_token"]

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.t.join(timeout=5)
        cls.tmp.cleanup()

    def _post(self, path, fields):
        import urllib.parse as _p
        import urllib.request as _u

        class _NoRedirect(_u.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        body = _p.urlencode({**fields, "csrf_token": self.csrf}).encode()
        req = _u.Request(
            f"http://127.0.0.1:{self.port}{path}", data=body,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Cookie": f"rcm_session={self.token}"})
        try:
            _u.build_opener(_NoRedirect).open(req, timeout=10)
        except Exception:   # 303 redirect surfaces as HTTPError
            pass

    def _page(self):
        import urllib.request as _u
        req = _u.Request(f"http://127.0.0.1:{self.port}/charts")
        req.add_header("Cookie", f"rcm_session={self.token}")
        with _u.urlopen(req, timeout=10) as r:
            return r.read().decode()

    def test_save_list_delete_round_trip(self):
        self._post("/api/charts/save", {
            "title": "Denials Pareto", "route": "/chart-builder",
            "query_params": "type=pareto&title=Denials"})
        h = self._page()
        self.assertIn("Denials Pareto", h)
        self.assertIn("/chart-builder?type=pareto", h)
        rows = list_charts(PortfolioStore(
            os.path.join(self.tmp.name, "p.db")), "alice")
        self.assertEqual(len(rows), 1)
        self._post("/api/charts/delete", {"id": str(rows[0]["id"])})
        self.assertIn("No saved charts yet", self._page())

    def test_forged_route_dropped_silently(self):
        self._post("/api/charts/save", {
            "title": "evil", "route": "https://evil.example",
            "query_params": "x=1"})
        self.assertNotIn("evil", self._page())


if __name__ == "__main__":
    unittest.main()
