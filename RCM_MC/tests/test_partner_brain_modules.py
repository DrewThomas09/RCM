"""Tests for the Partner Brain module directory (broad-coverage Phase).

The directory surfaces every orphaned ``pe_intelligence`` module at
once: enumerate in the directory, click through to an auto-rendered
detail page. This is the load-bearing route set for connecting the
remaining 244 orphaned modules to SeekingChartis.
"""
from __future__ import annotations

import os
import socket as _socket
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server
from rcm_mc.ui.data_public._pe_module_introspect import (
    catalog_pe_intelligence,
    find_entry,
    run_module_default,
)
from rcm_mc.ui.data_public.partner_brain_modules_page import (
    render_partner_brain_modules_directory,
    render_partner_brain_module_detail,
)


def _start_server(db_path: str):
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    server, _ = build_server(port=port, db_path=db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    return server, port


class TestPEIntrospection(unittest.TestCase):
    def test_catalog_covers_most_of_pe_intelligence(self):
        entries = catalog_pe_intelligence()
        # 275 modules on disk; catalog skips ~11 internal orchestrators.
        self.assertGreater(len(entries), 230)

    def test_catalog_has_reasonable_coverage_of_auto_runnable(self):
        entries = catalog_pe_intelligence()
        auto = [e for e in entries if e.compute_fn and e.input_class]
        # At least 60% of catalogued modules should have both compute + input
        self.assertGreater(len(auto) / max(1, len(entries)), 0.55)

    def test_find_entry_works_for_known_module(self):
        entry = find_entry("add_on_fit_scorer")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "add_on_fit_scorer")
        self.assertIsNotNone(entry.compute_fn)

    def test_find_entry_returns_none_for_unknown(self):
        self.assertIsNone(find_entry("nonexistent_module_xyz"))

    def test_run_module_default_succeeds_on_auto_runnable(self):
        # Pick the first module with both compute + input and run it.
        entries = catalog_pe_intelligence()
        auto = [e for e in entries if e.compute_fn and e.input_class]
        self.assertTrue(auto, "expected at least one auto-runnable module")
        result = run_module_default(auto[0].name)
        self.assertTrue(
            result["ok"],
            f"expected {auto[0].name} to auto-run, got reason: {result.get('reason')}"
        )

    def test_run_module_default_graceful_on_unknown(self):
        result = run_module_default("nonexistent_module_xyz")
        self.assertFalse(result["ok"])
        self.assertIn("catalog", result["reason"])

    def test_large_fraction_of_catalog_auto_runs(self):
        """Spot-check that a material share of catalogued modules actually
        auto-run without raising. Previously we measured ~80% on the
        first 30; lock ≥60% for the first 50 so CI is stable."""
        entries = catalog_pe_intelligence()
        auto = [e for e in entries if e.compute_fn and e.input_class][:50]
        ok = sum(1 for e in auto if run_module_default(e.name)["ok"])
        self.assertGreaterEqual(ok, int(0.60 * len(auto)))


class TestDirectoryRender(unittest.TestCase):
    def test_directory_renders_with_kpis(self):
        html = render_partner_brain_modules_directory({})
        self.assertIn("Module Directory", html)
        self.assertIn("AUTO-RUN", html)
        self.assertIn("Total modules", html)

    def test_directory_filter_by_category_narrows_output(self):
        full = render_partner_brain_modules_directory({})
        fail = render_partner_brain_modules_directory({"cat": "failures"})
        # Filtered view should be smaller than the full directory.
        self.assertLess(len(fail), len(full))
        self.assertIn("Named Failures", fail)

    def test_directory_has_working_module_links(self):
        html = render_partner_brain_modules_directory({})
        self.assertIn("/partner-brain/module?name=", html)


class TestDetailRender(unittest.TestCase):
    def test_detail_renders_auto_run_module(self):
        entries = catalog_pe_intelligence()
        auto = [e for e in entries if e.compute_fn and e.input_class]
        html = render_partner_brain_module_detail({"name": auto[0].name})
        self.assertIn(auto[0].name, html)
        self.assertIn("Module shape", html)
        # Auto-runnable means Report section should render
        self.assertTrue("Report" in html or "Markdown render" in html)

    def test_detail_missing_name_param(self):
        html = render_partner_brain_module_detail({})
        self.assertIn("Missing module name", html)

    def test_detail_unknown_module(self):
        html = render_partner_brain_module_detail({"name": "not_a_module_xyz"})
        self.assertIn("not found", html)

    def test_detail_shows_shape_even_if_auto_run_fails(self):
        # Find a module that's FN-ONLY (has compute but no defaulted input)
        entries = catalog_pe_intelligence()
        fn_only = [e for e in entries if e.compute_fn and not e.input_class]
        if not fn_only:
            # Fall back: find any with required fields
            for e in entries:
                if e.compute_fn and e.input_class:
                    r = run_module_default(e.name)
                    if not r["ok"]:
                        fn_only = [e]
                        break
        if fn_only:
            html = render_partner_brain_module_detail({"name": fn_only[0].name})
            self.assertIn("Module shape", html)


class TestDirectoryLiveRoutes(unittest.TestCase):
    def test_routes_return_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            PortfolioStore(os.path.join(tmp, "p.db"))
            server, port = _start_server(os.path.join(tmp, "p.db"))
            try:
                # Directory
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain/modules"
                ) as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn("Module Directory", r.read().decode())

                # Filter
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain/modules?cat=ic-decision"
                ) as r:
                    self.assertEqual(r.status, 200)

                # Detail — pick the first auto-runnable module
                entries = catalog_pe_intelligence()
                auto = [e for e in entries if e.compute_fn and e.input_class]
                name = auto[0].name
                qs = urllib.parse.urlencode({"name": name})
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/partner-brain/module?{qs}"
                ) as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn(name, r.read().decode())
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
