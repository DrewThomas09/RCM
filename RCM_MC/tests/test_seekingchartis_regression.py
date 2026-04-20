"""Tests for SeekingChartis regression page and migrated pages.

REGRESSION:
 1. GET /portfolio/regression renders with HCRIS data.
 2. Metric selector works.
 3. Portfolio source works (empty portfolio).

MIGRATED PAGES:
 4. /runs renders with shell_v2.
 5. /calibration renders with shell_v2.
 6. /scenarios renders with shell_v2.
 7. /source renders with shell_v2.
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


class TestRegressionPage(unittest.TestCase):

    def test_regression_renders(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio/regression",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Regression Analysis", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("R&sup2;", body)
                self.assertIn("Coefficients", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_regression_with_target(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio/regression?target=beds",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Regression Analysis", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_regression_portfolio_source(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/portfolio/regression?source=portfolio",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Regression Analysis", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


class TestMigratedPages(unittest.TestCase):

    def test_runs_has_shell_v2(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/runs",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Run History", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("ck-topbar", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_calibration_has_shell_v2(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/calibration",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Calibration", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("ck-topbar", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_scenarios_has_shell_v2(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/scenarios",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Scenario Explorer", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("ck-topbar", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_source_has_shell_v2(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/source",
                ) as r:
                    body = r.read().decode()
                self.assertIn("Deal Sourcing", body)
                self.assertIn("SeekingChartis", body)
                self.assertIn("ck-topbar", body)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
