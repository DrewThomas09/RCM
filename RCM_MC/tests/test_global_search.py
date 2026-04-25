"""Tests for global search across hospitals/metrics/pages."""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
import json
import urllib.parse


def _free_port() -> int:
    with socket.socket(socket.AF_INET,
                       socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestScoring(unittest.TestCase):
    def test_exact_match_highest(self):
        from rcm_mc.ui.global_search import _score
        s_exact = _score(
            "denial rate", "Denial Rate",
            "", "metric")
        s_prefix = _score(
            "den", "Denial Rate", "", "metric")
        s_substring = _score(
            "rate", "Denial Rate", "", "metric")
        self.assertGreater(s_exact, s_prefix)
        self.assertGreater(s_prefix, s_substring)

    def test_sublabel_match_lower(self):
        from rcm_mc.ui.global_search import _score
        s_label = _score(
            "denial", "Denial Rate", "x", "metric")
        s_sub = _score(
            "denied", "Other", "denied claims",
            "metric")
        self.assertGreater(s_label, s_sub)

    def test_no_match_zero(self):
        from rcm_mc.ui.global_search import _score
        self.assertEqual(
            _score("zebra", "Denial Rate",
                   "claims", "metric"), 0)

    def test_empty_query_zero(self):
        from rcm_mc.ui.global_search import _score
        self.assertEqual(
            _score("", "Denial Rate", "", "metric"),
            0)

    def test_category_boost(self):
        """Deal category gets +20 boost over the same match
        on a page."""
        from rcm_mc.ui.global_search import _score
        s_deal = _score(
            "aurora", "Aurora", "", "deal")
        s_page = _score(
            "aurora", "Aurora", "", "page")
        self.assertGreater(s_deal, s_page)


class TestSearch(unittest.TestCase):
    def test_metrics_searchable(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.global_search import search
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            results = search(store, "denial")
            # Denial rate metric in the glossary
            metric_results = [
                r for r in results
                if r.category == "metric"]
            self.assertGreater(
                len(metric_results), 0)
            self.assertTrue(any(
                "Denial" in r.label
                for r in metric_results))
        finally:
            tmp.cleanup()

    def test_pages_searchable(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.global_search import search
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            results = search(store, "catalog")
            page_results = [
                r for r in results
                if r.category == "page"]
            self.assertGreater(len(page_results), 0)
            self.assertTrue(any(
                "/data/catalog" == r.url
                for r in page_results))
        finally:
            tmp.cleanup()

    def test_empty_query_returns_empty(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.global_search import search
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            self.assertEqual(search(store, ""), [])
            self.assertEqual(search(store, "   "), [])
        finally:
            tmp.cleanup()

    def test_results_sorted_by_score(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.global_search import search
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            results = search(store, "data")
            scores = [r.score for r in results]
            self.assertEqual(
                scores, sorted(scores, reverse=True))
        finally:
            tmp.cleanup()

    def test_limit_respected(self):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.ui.global_search import search
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            store = PortfolioStore(db)
            store.init_db()
            results = search(store, "rate", limit=2)
            self.assertLessEqual(len(results), 2)
        finally:
            tmp.cleanup()


class TestSearchResultDataclass(unittest.TestCase):
    def test_to_dict(self):
        from rcm_mc.ui.global_search import SearchResult
        r = SearchResult(
            label="X", sublabel="y", url="/x",
            category="page", score=42)
        d = r.to_dict()
        self.assertEqual(d["label"], "X")
        self.assertEqual(d["score"], 42)


class TestSearchBar(unittest.TestCase):
    def test_renders_input_and_dropdown(self):
        from rcm_mc.ui.global_search import (
            render_search_bar,
        )
        html = render_search_bar()
        self.assertIn(
            'id="global-search-input"', html)
        self.assertIn(
            'id="global-search-dropdown"', html)
        self.assertIn("<script>", html)
        # Search debounce
        self.assertIn("setTimeout", html)
        # Esc to clear
        self.assertIn('"Escape"', html)
        # API endpoint URL
        self.assertIn("/api/global-search", html)

    def test_inject_css_disabled(self):
        from rcm_mc.ui.global_search import (
            render_search_bar,
        )
        html = render_search_bar(inject_css=False)
        self.assertNotIn("<style>", html)
        # JS still emits
        self.assertIn("<script>", html)


class TestHTTPRoute(unittest.TestCase):
    def test_api_search_endpoint(self):
        from rcm_mc.server import build_server
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            port = _free_port()
            srv, _h = build_server(
                port=port, db_path=db,
                host="127.0.0.1")
            t = threading.Thread(
                target=srv.serve_forever, daemon=True)
            t.start()
            try:
                time.sleep(0.2)
                url = (f"http://127.0.0.1:{port}"
                       f"/api/global-search?q=denial")
                with urllib.request.urlopen(
                        url, timeout=10) as resp:
                    self.assertEqual(resp.status, 200)
                    body = json.loads(
                        resp.read().decode())
                    self.assertIn("results", body)
                    self.assertIsInstance(
                        body["results"], list)
                    # Should find the denial_rate metric
                    self.assertTrue(any(
                        "Denial" in r.get("label", "")
                        for r in body["results"]))
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()

    def test_api_search_empty_query(self):
        from rcm_mc.server import build_server
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            port = _free_port()
            srv, _h = build_server(
                port=port, db_path=db,
                host="127.0.0.1")
            t = threading.Thread(
                target=srv.serve_forever, daemon=True)
            t.start()
            try:
                time.sleep(0.2)
                url = (f"http://127.0.0.1:{port}"
                       "/api/global-search?q=")
                with urllib.request.urlopen(
                        url, timeout=10) as resp:
                    body = json.loads(
                        resp.read().decode())
                    self.assertEqual(body["results"], [])
            finally:
                srv.shutdown()
                srv.server_close()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
