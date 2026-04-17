"""Tests for the simulation job queue (Brick 95).

Uses a fast mock runner so tests finish in milliseconds rather than
kicking off real Monte Carlo simulations.
"""
from __future__ import annotations

import threading
import time
import unittest

from rcm_mc.infra.job_queue import JobRegistry


def _fast_runner(params):
    """Minimal runner: sleeps briefly then returns outdir."""
    time.sleep(0.02)
    return {"outdir": params["outdir"], "rows": 42}


def _failing_runner(params):
    raise RuntimeError("intentional test failure")


class TestJobLifecycle(unittest.TestCase):
    def test_submit_returns_job_id(self):
        reg = JobRegistry(runner=_fast_runner)
        try:
            jid = reg.submit_run(
                actual="/a", benchmark="/b", outdir="/o",
            )
            self.assertIsInstance(jid, str)
            self.assertGreater(len(jid), 4)
        finally:
            reg.shutdown(timeout=1.0)

    def test_job_transitions_to_done(self):
        reg = JobRegistry(runner=_fast_runner)
        try:
            jid = reg.submit_run(actual="/a", benchmark="/b", outdir="/o")
            final = reg.wait(jid, timeout=2.0)
            self.assertEqual(final.status, "done")
            self.assertIsNotNone(final.started_at)
            self.assertIsNotNone(final.finished_at)
            self.assertEqual(final.result["rows"], 42)
        finally:
            reg.shutdown(timeout=1.0)

    def test_failing_job_marked_failed_with_error(self):
        reg = JobRegistry(runner=_failing_runner)
        try:
            jid = reg.submit_run(actual="/a", benchmark="/b", outdir="/o")
            final = reg.wait(jid, timeout=2.0)
            self.assertEqual(final.status, "failed")
            self.assertIn("intentional test failure", final.error)
        finally:
            reg.shutdown(timeout=1.0)

    def test_get_unknown_returns_none(self):
        reg = JobRegistry(runner=_fast_runner)
        try:
            self.assertIsNone(reg.get("nope"))
        finally:
            reg.shutdown(timeout=1.0)

    def test_list_recent_newest_first(self):
        reg = JobRegistry(runner=_fast_runner)
        try:
            ids = []
            for _ in range(3):
                ids.append(reg.submit_run(
                    actual="/a", benchmark="/b", outdir="/o",
                ))
                time.sleep(0.05)
            # Wait all done
            for jid in ids:
                reg.wait(jid, timeout=2.0)
            recent = reg.list_recent(10)
            self.assertEqual([j.job_id for j in recent], list(reversed(ids)))
        finally:
            reg.shutdown(timeout=1.0)

    def test_output_tail_captures_prints(self):
        """Runner's stdout + stderr land on the job's output_tail field."""
        def _chatty_runner(params):
            print("step 1")
            print("step 2")
            return {"outdir": params["outdir"]}
        reg = JobRegistry(runner=_chatty_runner)
        try:
            jid = reg.submit_run(actual="/a", benchmark="/b", outdir="/o")
            final = reg.wait(jid, timeout=2.0)
            self.assertIn("step 1", final.output_tail)
            self.assertIn("step 2", final.output_tail)
        finally:
            reg.shutdown(timeout=1.0)

    def test_worker_is_single_threaded_fifo(self):
        """Jobs complete in submit order."""
        order_seen = []
        lock = threading.Lock()
        def _ordered_runner(params):
            with lock:
                order_seen.append(params["outdir"])
            return {"outdir": params["outdir"]}
        reg = JobRegistry(runner=_ordered_runner)
        try:
            ids = []
            for i in range(5):
                ids.append(reg.submit_run(
                    actual="/a", benchmark="/b", outdir=f"/o{i}",
                ))
            for jid in ids:
                reg.wait(jid, timeout=2.0)
            self.assertEqual(order_seen, [f"/o{i}" for i in range(5)])
        finally:
            reg.shutdown(timeout=1.0)


class TestHttpIntegration(unittest.TestCase):
    def _start_server(self, tmp: str, *, runner=None):
        """Spin up the real server wired to an isolated JobRegistry."""
        import socket as _socket
        import threading as _th
        import time as _time
        from rcm_mc.server import build_server
        import rcm_mc.infra.job_queue as jq

        # Swap in a non-default runner so tests don't kick off real sims
        jq._DEFAULT_REGISTRY = JobRegistry(runner=runner or _fast_runner)

        s = _socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        import os
        server, _ = build_server(port=port, db_path=os.path.join(tmp, "p.db"))
        t = _th.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def _stop(self, server):
        import rcm_mc.infra.job_queue as jq
        server.shutdown()
        server.server_close()
        jq.reset_default_registry()

    def test_post_jobs_run_accepts_and_returns_job_id(self):
        import json as _json
        import tempfile
        import urllib.parse as _p
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            import os
            actual = os.path.join(tmp, "actual.yaml")
            benchmark = os.path.join(tmp, "benchmark.yaml")
            for path in (actual, benchmark):
                open(path, "w").close()

            server, port = self._start_server(tmp)
            try:
                body = _p.urlencode({
                    "actual": actual, "benchmark": benchmark,
                    "outdir": os.path.join(tmp, "out"),
                    "n_sims": "100", "seed": "1",
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/jobs/run",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                )
                with _u.urlopen(req) as r:
                    self.assertEqual(r.status, 202)
                    data = _json.loads(r.read().decode())
                    self.assertIn("job_id", data)
                    jid = data["job_id"]

                # Poll the status endpoint until done
                for _ in range(100):
                    with _u.urlopen(
                        f"http://127.0.0.1:{port}/api/jobs/{jid}"
                    ) as r:
                        st = _json.loads(r.read().decode())
                    if st["status"] in ("done", "failed"):
                        break
                    import time as _time
                    _time.sleep(0.03)
                self.assertEqual(st["status"], "done")
            finally:
                self._stop(server)

    def test_post_jobs_run_missing_params_returns_400(self):
        import tempfile
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_server(tmp)
            try:
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/jobs/run",
                    data=b"", method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                self._stop(server)

    def test_post_jobs_run_nonexistent_actual_returns_400(self):
        import tempfile
        import urllib.parse as _p
        import urllib.request as _u
        from urllib.error import HTTPError
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_server(tmp)
            try:
                import os
                body = _p.urlencode({
                    "actual": "/nonexistent/actual.yaml",
                    "benchmark": "/nonexistent/benchmark.yaml",
                    "outdir": os.path.join(tmp, "o"),
                }).encode()
                req = _u.Request(
                    f"http://127.0.0.1:{port}/api/jobs/run",
                    data=body, method="POST",
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with self.assertRaises(HTTPError) as ctx:
                    _u.urlopen(req)
                self.assertEqual(ctx.exception.code, 400)
            finally:
                self._stop(server)

    def test_jobs_index_page_renders(self):
        import tempfile
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_server(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/jobs") as r:
                    body = r.read().decode()
                    self.assertIn("Queue a simulation run", body)
                    self.assertIn('action="/api/jobs/run"', body)
                    self.assertIn("Recent jobs", body)
            finally:
                self._stop(server)

    def test_job_detail_for_unknown_id_shows_message(self):
        import tempfile
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start_server(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/jobs/ghost") as r:
                    body = r.read().decode()
                    self.assertIn("No job", body)
                    self.assertIn("ghost", body)
            finally:
                self._stop(server)

    def test_job_detail_shows_status_and_params(self):
        import tempfile
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            import os
            actual = os.path.join(tmp, "a.yaml")
            benchmark = os.path.join(tmp, "b.yaml")
            for p in (actual, benchmark): open(p, "w").close()

            server, port = self._start_server(tmp)
            try:
                import rcm_mc.infra.job_queue as jq
                jid = jq.get_default_registry().submit_run(
                    actual=actual, benchmark=benchmark,
                    outdir=os.path.join(tmp, "o"),
                )
                # Wait for completion
                jq.get_default_registry().wait(jid, timeout=2.0)
                with _u.urlopen(f"http://127.0.0.1:{port}/jobs/{jid}") as r:
                    body = r.read().decode()
                    self.assertIn(jid, body)
                    self.assertIn("DONE", body)
                    self.assertIn("Parameters", body)
            finally:
                self._stop(server)
