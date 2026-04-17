"""Tests for per-deal rerun-sim shortcut (Brick 121)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
import urllib.parse as _p
import urllib.request as _u
from urllib.error import HTTPError

from rcm_mc.deals.deal_sim_inputs import (
    get_inputs, next_outdir, set_inputs,
)
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestSimInputsCore(unittest.TestCase):
    def test_get_returns_none_when_unset(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(get_inputs(_store(tmp), "ccf"))

    def test_set_then_get(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            set_inputs(
                store, deal_id="ccf",
                actual_path="/data/ccf/actual.yaml",
                benchmark_path="/data/ccf/benchmark.yaml",
                outdir_base="runs/ccf",
            )
            got = get_inputs(store, "ccf")
            self.assertEqual(got["actual_path"], "/data/ccf/actual.yaml")
            self.assertEqual(got["benchmark_path"], "/data/ccf/benchmark.yaml")
            self.assertEqual(got["outdir_base"], "runs/ccf")

    def test_set_upserts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            set_inputs(store, deal_id="ccf",
                       actual_path="/v1/a.yaml",
                       benchmark_path="/v1/b.yaml")
            set_inputs(store, deal_id="ccf",
                       actual_path="/v2/a.yaml",
                       benchmark_path="/v2/b.yaml")
            got = get_inputs(store, "ccf")
            self.assertEqual(got["actual_path"], "/v2/a.yaml")

    def test_empty_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                set_inputs(store, deal_id="ccf",
                           actual_path="", benchmark_path="/b.yaml")
            with self.assertRaises(ValueError):
                set_inputs(store, deal_id="ccf",
                           actual_path="/a.yaml", benchmark_path="")
            with self.assertRaises(ValueError):
                set_inputs(store, deal_id="",
                           actual_path="/a.yaml", benchmark_path="/b.yaml")

    def test_next_outdir_timestamped(self):
        a = next_outdir("ccf", "")
        b = next_outdir("ccf", "custom/base")
        self.assertTrue(a.startswith(os.path.join("runs", "ccf")))
        self.assertTrue(b.startswith(os.path.join("custom", "base")))


class TestRerunHttp(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.infra.job_queue import JobRegistry
        import rcm_mc.infra.job_queue as jq
        from rcm_mc.server import build_server

        def _fast_runner(params):
            import time as _time_mod
            _time_mod.sleep(0.01)
            return {"outdir": params["outdir"]}

        jq._DEFAULT_REGISTRY = JobRegistry(runner=_fast_runner)

        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def _stop(self, server):
        import rcm_mc.infra.job_queue as jq
        server.shutdown(); server.server_close()
        jq.reset_default_registry()

    def test_deal_page_shows_setup_form_when_unconfigured(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("Rerun simulation", body)
                    self.assertIn("not configured", body)
                    self.assertIn('action="/api/deals/ccf/sim-inputs"', body)
            finally:
                self._stop(server)

    def test_post_sim_inputs_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                body = _p.urlencode({
                    "actual_path": "/path/a.yaml",
                    "benchmark_path": "/path/b.yaml",
                    "outdir_base": "runs/ccf",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/sim-inputs",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                _u.urlopen(req)
                # Verify via API
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/deals/ccf/sim-inputs"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data["actual_path"], "/path/a.yaml")
            finally:
                self._stop(server)

    def test_rerun_button_appears_when_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            actual = os.path.join(tmp, "actual.yaml")
            bench = os.path.join(tmp, "benchmark.yaml")
            for p in (actual, bench):
                open(p, "w").close()
            set_inputs(store, deal_id="ccf",
                       actual_path=actual, benchmark_path=bench)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                    self.assertIn("Rerun simulation", body)
                    self.assertIn('action="/api/deals/ccf/rerun"', body)
                    self.assertNotIn("not configured", body)
            finally:
                self._stop(server)

    def test_rerun_queues_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            actual = os.path.join(tmp, "actual.yaml")
            bench = os.path.join(tmp, "benchmark.yaml")
            for p in (actual, bench):
                open(p, "w").close()
            set_inputs(store, deal_id="ccf",
                       actual_path=actual, benchmark_path=bench)
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/rerun",
                    data=b"", method="POST",
                    headers={"Accept": "application/json"},
                )
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 202)
                    data = json.loads(r.read().decode())
                    self.assertIn("job_id", data)
                    self.assertIn("outdir", data)
            finally:
                self._stop(server)

    def test_rerun_400_when_unconfigured(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/rerun",
                    data=b"", method="POST",
                    headers={"Accept": "application/json"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                self._stop(server)

    def test_rerun_400_when_path_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            # Point at paths that don't exist
            set_inputs(store, deal_id="ccf",
                       actual_path="/no/such.yaml",
                       benchmark_path="/no/such_b.yaml")
            server, port = self._start(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/deals/ccf/rerun",
                    data=b"", method="POST",
                    headers={"Accept": "application/json"},
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                self._stop(server)


if __name__ == "__main__":
    unittest.main()
