"""End-to-end tests for the /excel-templates library page and the
per-slug .xlsx download route (real HTTP server, no mocks)."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing

from rcm_mc.exports.model_templates import TEMPLATES

_XLSX_MIME = ("application/vnd.openxmlformats-officedocument."
              "spreadsheetml.sheet")


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ExcelTemplatesPageTests(unittest.TestCase):
    def test_page_lists_every_template_with_download_link(self):
        import html as _html
        from rcm_mc.ui.excel_templates_page import render_excel_templates
        html = render_excel_templates()
        for spec in TEMPLATES:
            self.assertIn(_html.escape(spec.title), html)
            self.assertIn(f"/excel-templates/{spec.slug}.xlsx", html)

    def test_registered_in_palette_and_nav(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_NAV, _SUB_SECTION_MAP,
        )
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/excel-templates", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/excel-templates"), "research")
        research_hrefs = {e["href"] for e in _SUB_NAV["research"]}
        self.assertIn("/excel-templates", research_hrefs)


class ExcelTemplatesHttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1", db_path=cls.db, auth=None,
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

    def _open(self, path: str):
        return urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10)

    def test_library_page_serves(self):
        with self._open("/excel-templates") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("Excel Model Templates", resp.read().decode())

    def test_every_template_downloads_with_xlsx_mime(self):
        for spec in TEMPLATES:
            with self._open(f"/excel-templates/{spec.slug}.xlsx") as resp:
                self.assertEqual(resp.status, 200, spec.slug)
                self.assertEqual(
                    resp.headers["Content-Type"], _XLSX_MIME, spec.slug)
                self.assertIn(f'filename="{spec.slug}.xlsx"',
                              resp.headers["Content-Disposition"])
                body = resp.read()
                # OOXML zips start with the PK local-file-header magic.
                self.assertEqual(body[:2], b"PK", spec.slug)
                self.assertEqual(
                    int(resp.headers["Content-Length"]), len(body))

    def test_unknown_template_404s(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._open("/excel-templates/not-a-template.xlsx")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
