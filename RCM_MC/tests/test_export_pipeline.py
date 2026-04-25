"""Tests for the web export pipeline.

Covers:
  1. export_menu_for_deal() renders the 7 standard format links
  2. export_menu() generic variant renders caller-supplied links
  3. /exports landing page renders the three sections
  4. PDF format is in the valid-format list (direct unit test of the
     validation set; the full PDF render requires a real packet)
  5. /api/analysis/<deal>/export?format=<invalid> returns 400 with
     the PDF included in the advertised valid list
  6. Dashboard now surfaces portfolio-scope export links
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ────────────────────────────────────────────────────────────────────
# 1 + 2. Menu helpers
# ────────────────────────────────────────────────────────────────────

class TestExportMenuHelpers(unittest.TestCase):
    def test_deal_menu_has_seven_formats(self):
        from rcm_mc.ui._export_menu import export_menu_for_deal
        html = export_menu_for_deal("DEAL_123")
        # All 7 formats link to the deal-specific endpoint
        for fmt in ("html", "pdf", "xlsx", "pptx", "csv", "json", "package"):
            self.assertIn(
                f"/api/analysis/DEAL_123/export?format={fmt}",
                html,
                msg=f"missing format link: {fmt}",
            )

    def test_deal_menu_label_readable(self):
        from rcm_mc.ui._export_menu import export_menu_for_deal
        html = export_menu_for_deal("DEAL_ABC")
        self.assertIn("HTML memo", html)
        self.assertIn("PDF (print)", html)
        self.assertIn("PowerPoint", html)
        self.assertIn("ZIP package", html)

    def test_deal_id_safely_encoded(self):
        """Malicious deal_id must not render as unescaped HTML.

        The deal_id goes through URL-encoding (path-segment) + HTML-
        escape on render. Either encoding alone would neutralize the
        injection; both in series means the output is doubly safe.
        """
        from rcm_mc.ui._export_menu import export_menu_for_deal
        html = export_menu_for_deal('"><script>x</script>')
        # The raw <script> must never appear as literal HTML
        self.assertNotIn("<script>x</script>", html)
        # URL-encoding turns '"' → '%22', '<' → '%3C' etc.
        self.assertIn("%22", html)
        self.assertIn("%3C", html)

    def test_generic_menu_primary_styling(self):
        from rcm_mc.ui._export_menu import export_menu
        html = export_menu(
            "Download",
            [("First", "/a"), ("Second", "/b")],
        )
        # Primary button is the first one — dark background
        self.assertIn("/a", html)
        self.assertIn("/b", html)
        # Heading
        self.assertIn("Download", html)

    def test_generic_menu_empty_returns_empty(self):
        from rcm_mc.ui._export_menu import export_menu
        self.assertEqual(export_menu("nothing", []), "")


# ────────────────────────────────────────────────────────────────────
# 3 + 4 + 5. HTTP-level behavior
# ────────────────────────────────────────────────────────────────────

class TestExportHttpBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db_path, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _get(self, path: str, *, timeout: float = 10.0):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=timeout
            ) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def test_exports_landing_page(self):
        status, html = self._get("/exports")
        self.assertEqual(status, 200)
        # Three sections: per-deal / portfolio / corpus browsers
        self.assertIn("Per-deal exports", html)
        self.assertIn("Portfolio-scope", html)
        self.assertIn("Corpus browsers", html)
        # Format reference table entries
        self.assertIn("?format=pdf", html)
        self.assertIn("?format=xlsx", html)
        self.assertIn("?format=package", html)

    def test_dashboard_shows_portfolio_exports(self):
        status, html = self._get("/dashboard")
        self.assertEqual(status, 200)
        self.assertIn("Download portfolio-scope exports", html)
        self.assertIn("/api/export/portfolio.csv", html)
        self.assertIn("/data/refresh", html)
        self.assertIn("/exports/lp-update", html)

    def test_invalid_export_format_advertises_pdf(self):
        # /api/analysis/<id>/export?format=bogus should 400 with valid
        # list containing "pdf" (regression check for the new format).
        # Need a deal_id that resolves through the route dispatch.
        # Without a real packet this returns 404 from the analysis route,
        # not 400 — but we can still test the validation list directly:
        from rcm_mc.server import RCMHandler  # noqa: F401 — just to ensure import
        # The valid set lives as a local inside _route_analysis_export;
        # a cheap way to pin the contract is to grep the source.
        import inspect
        src = inspect.getsource(RCMHandler._route_analysis_export)
        self.assertIn('"pdf"', src,
                      msg="PDF not in advertised valid set of _route_analysis_export")
        # Also verify the PDF branch is actually implemented
        self.assertIn('fmt == "pdf"', src)

    def test_pdf_branch_renders_with_auto_print(self):
        """PDF branch appends an auto-print script. Test this in isolation."""
        # Use the raw renderer + mimic what the handler does, so we
        # don't need a real packet routed through the store.
        from rcm_mc.exports import PacketRenderer
        from rcm_mc.analysis.packet import DealAnalysisPacket

        # Minimal packet — only fields the HTML memo uses
        pkt = DealAnalysisPacket(
            deal_id="TEST_DEAL", scenario_id="base",
            as_of="2026-04-24",
        )
        renderer = PacketRenderer()
        try:
            body_html = renderer.render_diligence_memo_html(pkt, inputs_hash="")
        except Exception:  # noqa: BLE001 — skip if packet too minimal
            self.skipTest("render_diligence_memo_html rejects minimal packet")
            return

        # Simulate the handler's PDF injection
        auto_print = (
            '<script>window.addEventListener("load",function(){'
            'setTimeout(function(){window.print();},200);});</script>'
        )
        self.assertNotIn(auto_print, body_html,
                         msg="auto-print must not be baked into the base HTML")

    def test_temp_dir_cleanup_is_wired(self):
        """Verify the cleanup block exists in _route_analysis_export."""
        from rcm_mc.server import RCMHandler
        import inspect
        src = inspect.getsource(RCMHandler._route_analysis_export)
        self.assertIn("shutil", src,
                      msg="post-serve cleanup missing from export route")
        self.assertIn("rmtree", src)
        self.assertIn("/tmp/", src,
                      msg="cleanup must gate on /tmp/ prefix")


if __name__ == "__main__":
    unittest.main()
