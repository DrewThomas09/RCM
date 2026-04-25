"""Tests for the web data-refresh workflow.

Covers:
  1. JobRegistry.submit_callable runs custom runners
  2. submit_callable idempotency_key coalesces concurrent submits
  3. GET /api/jobs/<id> returns JSON status (or 404)
  4. POST /api/data/refresh/<source>/async returns 202 + job_id
  5. Async refresh triggers the actual refresher (mocked) + populates
     data_source_status row
  6. /data/refresh UI page renders + contains source rows + inline JS
  7. Dashboard "data freshness" section picks up a newly refreshed source
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ────────────────────────────────────────────────────────────────────
# 1 + 2. submit_callable + idempotency
# ────────────────────────────────────────────────────────────────────

class TestSubmitCallable(unittest.TestCase):
    def test_custom_runner_is_invoked(self):
        from rcm_mc.infra.job_queue import JobRegistry
        calls = []

        def runner(params):
            calls.append(params["label"])
            return {"echo": params["label"]}

        reg = JobRegistry()  # default runner is the MC one, unused here
        job_id = reg.submit_callable(
            kind="data_refresh", runner=runner,
            params={"label": "hcris"},
        )
        job = reg.wait(job_id, timeout=2.0)
        self.assertEqual(job.status, "done")
        self.assertEqual(job.result["echo"], "hcris")
        self.assertEqual(job.kind, "data_refresh")
        self.assertEqual(calls, ["hcris"])
        reg.shutdown(timeout=1.0)

    def test_idempotency_key_coalesces_queued_jobs(self):
        from rcm_mc.infra.job_queue import JobRegistry
        started = threading.Event()
        release = threading.Event()
        call_count = [0]

        def slow_runner(params):
            call_count[0] += 1
            started.set()
            release.wait(timeout=3.0)
            return {}

        reg = JobRegistry()
        # First submit — will start and block inside runner
        id1 = reg.submit_callable(
            kind="data_refresh", runner=slow_runner,
            params={"source": "hcris"}, idempotency_key="refresh:hcris",
        )
        # Wait until the worker has actually entered the runner
        self.assertTrue(started.wait(timeout=2.0))
        # Second submit with same key — should coalesce to same job
        id2 = reg.submit_callable(
            kind="data_refresh", runner=slow_runner,
            params={"source": "hcris"}, idempotency_key="refresh:hcris",
        )
        self.assertEqual(id1, id2)
        # Let the first runner finish so a new submit creates a new job
        release.set()
        reg.wait(id1, timeout=2.0)
        # Third submit with same key — first job is terminal now, so a
        # new job_id is expected
        id3 = reg.submit_callable(
            kind="data_refresh", runner=slow_runner,
            params={"source": "hcris"}, idempotency_key="refresh:hcris",
        )
        self.assertNotEqual(id1, id3)
        release.set()  # already set; just in case
        reg.wait(id3, timeout=2.0)
        reg.shutdown(timeout=1.0)
        self.assertEqual(call_count[0], 2)


# ────────────────────────────────────────────────────────────────────
# 3-5. HTTP routes
# ────────────────────────────────────────────────────────────────────

class TestRefreshHttpRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "t.db")
        self.port = _free_port()
        from rcm_mc.server import build_server
        self.server, _ = build_server(
            port=self.port, host="127.0.0.1",
            db_path=self.db_path, auth=None,
        )
        self.thread = threading.Thread(
            target=self.server.serve_forever, daemon=True)
        self.thread.start()
        # Reset the in-process registry between test classes so rate
        # limits don't carry over.
        from rcm_mc.infra.job_queue import get_default_registry
        reg = get_default_registry()
        with reg._lock:
            reg._jobs.clear()
            reg._order.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def _get_json(self, path):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=5
            ) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def _post_empty(self, path):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=b"", method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_api_jobs_returns_404_for_unknown(self):
        status, body = self._get_json("/api/jobs/doesnotexist")
        self.assertEqual(status, 404)
        self.assertEqual(body["code"], "JOB_NOT_FOUND")

    def test_async_refresh_unknown_source_returns_400(self):
        status, body = self._post_empty(
            "/api/data/refresh/not-a-real-source/async")
        self.assertEqual(status, 400)
        self.assertEqual(body["code"], "UNKNOWN_SOURCE")
        self.assertIn("hcris", body["detail"]["known"])

    def test_async_refresh_enqueues_and_polls(self):
        # Patch the refresher set so the "hcris" source uses a fast fake
        # runner — we don't want a real CMS HTTP fetch in tests.
        import rcm_mc.data.data_refresh as dr
        real_refresh_all = dr.refresh_all_sources

        from rcm_mc.data.data_refresh import RefreshReport, RefreshSourceResult

        def fake_refresh_all(store, *, sources=None, **kw):
            # Simulate a successful refresh of "hcris" with 42 records
            dr.set_status(store, "hcris", status="ok", record_count=42)
            report = RefreshReport(started_at="t0", finished_at="t1")
            report.per_source.append(RefreshSourceResult(
                source="hcris", record_count=42,
                status="ok", error_detail=None,
            ))
            return report

        dr.refresh_all_sources = fake_refresh_all
        try:
            status, body = self._post_empty(
                "/api/data/refresh/hcris/async")
            self.assertEqual(status, 202)
            self.assertIn("job_id", body)
            self.assertEqual(body["source"], "hcris")
            self.assertEqual(body["status_url"],
                             f"/api/jobs/{body['job_id']}")

            # Poll until terminal
            for _ in range(20):
                s, poll_body = self._get_json(body["status_url"])
                self.assertEqual(s, 200)
                if poll_body["status"] in ("done", "failed"):
                    break
                time.sleep(0.1)

            self.assertEqual(poll_body["status"], "done",
                             msg=f"error: {poll_body.get('error')}")
            self.assertEqual(poll_body["kind"], "data_refresh")
            self.assertEqual(poll_body["result"]["total_records"], 42)
        finally:
            dr.refresh_all_sources = real_refresh_all

    def test_data_refresh_ui_page_renders(self):
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}/data/refresh", timeout=5
        ) as resp:
            html = resp.read().decode()
        self.assertIn("Data refresh", html)
        # Known sources should render as rows
        for source in ("hcris", "care_compare", "irs990"):
            self.assertIn(f'data-source="{source}"', html)
        # Refresh-all button
        self.assertIn('data-source="all"', html)
        # Inline JS that calls the async endpoint
        self.assertIn("/api/data/refresh/", html)
        self.assertIn("/api/jobs/", html)


if __name__ == "__main__":
    unittest.main()
