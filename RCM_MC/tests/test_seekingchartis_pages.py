"""Tests for SeekingChartis new pages: news, market data, library.

NEWS:
 1. GET /news renders news page with articles.
 2. Category filter works.

MARKET DATA:
 3. GET /market-data/map renders heatmap page.
 4. Metric selector works.
 5. GET /market-data/state/AL renders state detail.

LIBRARY:
 6. GET /library renders reference library.
 7. Library has model documentation sections.

ROUTES:
 8. /seekingchartis alias works.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestNewsPage(unittest.TestCase):

    def test_news_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/news",
                ) as r:
                    body = r.read().decode()
                self.assertIn("News &amp; Research", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("cad-topbar", body)
                self.assertIn("CMS Finalizes", body)
                self.assertIn("Diligence Impact", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_news_category_filter(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/news?cat=regulatory",
                ) as r:
                    body = r.read().decode()
                self.assertIn("CMS Finalizes", body)
                self.assertIn("Medicaid Unwinding", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestMarketDataPage(unittest.TestCase):

    def test_market_data_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/market-data/map",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Market Data", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("cad-topbar", body)
                self.assertIn("State Market Heatmap", body)
                self.assertIn("HCRIS", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_metric_selector(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/market-data/map?metric=hhi",
                ) as r:
                    body = r.read().decode()
                self.assertIn("HHI (Concentration)", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_state_detail(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/market-data/state/AL",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Market: AL", body)
                self.assertIn("Hospitals", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_regression_section(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/market-data/map",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Regression", body)
                self.assertIn("R-Squared", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestLibraryPage(unittest.TestCase):

    def test_library_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/library",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Library", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("cad-topbar", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_library_has_sections(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/library",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Valuation Models", body)
                self.assertIn("Market Intelligence", body)
                self.assertIn("Quantitative Tools", body)
                self.assertIn("Data Sources", body)
                self.assertIn("DCF Model", body)
                self.assertIn("LBO Model", body)
                self.assertIn("Monte Carlo", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestSeekingChartisAlias(unittest.TestCase):

    def test_seekingchartis_route(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/seekingchartis",
                ) as r:
                    body = r.read().decode()
                self.assertIn("SeekingChartis", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
