"""Tests for B122: rerun CLI + /alerts owner filter."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.request as _u
from contextlib import redirect_stderr, redirect_stdout

from rcm_mc import portfolio_cmd
from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.deals.deal_sim_inputs import get_inputs, set_inputs
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _db(tmp: str) -> str:
    return os.path.join(tmp, "p.db")


def _capture(fn, *argv):
    buf_out, buf_err = io.StringIO(), io.StringIO()
    with redirect_stdout(buf_out), redirect_stderr(buf_err):
        rc = fn(list(argv))
    return rc, buf_out.getvalue(), buf_err.getvalue()


class TestSimInputsCli(unittest.TestCase):
    def test_show_empty_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, out, _ = _capture(
                portfolio_cmd.main,
                "--db", _db(tmp),
                "sim-inputs", "show", "--deal-id", "ccf",
            )
            self.assertEqual(rc, 1)
            self.assertIn("no sim inputs", out)

    def test_set_then_show(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc, _, _ = _capture(
                portfolio_cmd.main,
                "--db", _db(tmp),
                "sim-inputs", "set",
                "--deal-id", "ccf",
                "--actual", "/p/a.yaml",
                "--benchmark", "/p/b.yaml",
                "--outdir-base", "runs/ccf",
            )
            self.assertEqual(rc, 0)
            rc, out, _ = _capture(
                portfolio_cmd.main,
                "--db", _db(tmp),
                "sim-inputs", "show", "--deal-id", "ccf",
            )
            self.assertEqual(rc, 0)
            data = json.loads(out)
            self.assertEqual(data["actual_path"], "/p/a.yaml")
            self.assertEqual(data["outdir_base"], "runs/ccf")


class TestRerunCli(unittest.TestCase):
    def _install_fast_runner(self):
        from rcm_mc.infra.job_queue import JobRegistry
        import rcm_mc.infra.job_queue as jq
        def _fast(params):
            import time; time.sleep(0.01)
            return {"outdir": params["outdir"]}
        jq._DEFAULT_REGISTRY = JobRegistry(runner=_fast)

    def _reset(self):
        import rcm_mc.infra.job_queue as jq
        jq.reset_default_registry()

    def test_rerun_errors_without_stored_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._install_fast_runner()
            try:
                rc, _, err = _capture(
                    portfolio_cmd.main,
                    "--db", _db(tmp),
                    "rerun", "--deal-id", "ccf",
                )
                self.assertEqual(rc, 1)
                self.assertIn("no stored sim inputs", err)
            finally:
                self._reset()

    def test_rerun_errors_when_actual_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(_db(tmp))
            set_inputs(store, deal_id="ccf",
                       actual_path="/no/such.yaml",
                       benchmark_path="/no/such_b.yaml")
            self._install_fast_runner()
            try:
                rc, _, err = _capture(
                    portfolio_cmd.main,
                    "--db", _db(tmp),
                    "rerun", "--deal-id", "ccf",
                )
                self.assertEqual(rc, 1)
                self.assertIn("does not exist", err)
            finally:
                self._reset()

    def test_rerun_queues_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(_db(tmp))
            actual = os.path.join(tmp, "actual.yaml")
            bench = os.path.join(tmp, "benchmark.yaml")
            for p in (actual, bench):
                open(p, "w").close()
            set_inputs(store, deal_id="ccf",
                       actual_path=actual, benchmark_path=bench)
            self._install_fast_runner()
            try:
                rc, out, _ = _capture(
                    portfolio_cmd.main,
                    "--db", _db(tmp),
                    "rerun", "--deal-id", "ccf",
                )
                self.assertEqual(rc, 0)
                data = json.loads(out)
                self.assertIn("job_id", data)
                self.assertEqual(data["deal_id"], "ccf")
            finally:
                self._reset()


class TestAlertsOwnerFilter(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_alerts_owner_filter_scopes_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            _seed_with_pe_math(tmp, "other", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/alerts?owner=AT"
                ) as r:
                    body = r.read().decode()
                    self.assertIn(">ccf<", body)
                    self.assertNotIn(">other<", body)
                    self.assertIn("owner = AT", body)
            finally:
                server.shutdown(); server.server_close()

    def test_alerts_owner_filter_empty_when_unassigned(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/alerts?owner=AT"
                ) as r:
                    body = r.read().decode()
                    # No deals assigned to AT → empty state
                    self.assertIn("No 'AT' alerts", body)
            finally:
                server.shutdown(); server.server_close()

    def test_alerts_page_renders_owner_filter_form(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn('name="owner"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
