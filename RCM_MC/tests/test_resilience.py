"""Resilience tests for the web deployment.

Covers operator-facing recovery hooks documented in DEPLOY.md §5:

  1. ``JobRegistry.mark_stale`` flips long-running jobs to ``failed``
     so the dashboard stops lying about jobs that no worker is
     watching anymore (typical: dyno restart mid-analysis).

  2. The mark_stale grace period is honored — a fresh job that just
     started running is NOT marked stale.

  3. Idempotency-coalesced submissions don't accumulate ghost rows
     across restarts (covered indirectly by data_refresh tests).
"""
from __future__ import annotations

import threading
import time
import unittest
from datetime import datetime, timedelta, timezone


class TestMarkStaleJobs(unittest.TestCase):
    def test_old_running_job_is_marked_failed(self):
        from rcm_mc.infra.job_queue import JobRegistry, Job

        reg = JobRegistry()
        # Plant a fake "running" job whose started_at is 2 hours ago
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        job_id = "stale-deadbeef"
        reg._jobs[job_id] = Job(
            job_id=job_id, status="running",
            created_at=old, kind="data_refresh",
            started_at=old,
        )
        reg._order.append(job_id)

        marked = reg.mark_stale(max_age_seconds=3600)
        self.assertIn(job_id, marked)

        job = reg.get(job_id)
        self.assertEqual(job.status, "failed")
        self.assertIsNotNone(job.finished_at)
        self.assertIn("mark_stale", (job.error or ""))
        reg.shutdown(timeout=1.0)

    def test_fresh_running_job_is_left_alone(self):
        from rcm_mc.infra.job_queue import JobRegistry, Job

        reg = JobRegistry()
        recent = datetime.now(timezone.utc).isoformat()
        job_id = "fresh-cafef00d"
        reg._jobs[job_id] = Job(
            job_id=job_id, status="running",
            created_at=recent, kind="data_refresh",
            started_at=recent,
        )
        reg._order.append(job_id)

        marked = reg.mark_stale(max_age_seconds=3600)
        self.assertEqual(marked, [])
        self.assertEqual(reg.get(job_id).status, "running")
        reg.shutdown(timeout=1.0)

    def test_done_jobs_are_not_touched(self):
        from rcm_mc.infra.job_queue import JobRegistry, Job

        reg = JobRegistry()
        old = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        job_id = "old-but-done"
        reg._jobs[job_id] = Job(
            job_id=job_id, status="done",
            created_at=old, kind="data_refresh",
            started_at=old, finished_at=old,
        )
        reg._order.append(job_id)

        marked = reg.mark_stale(max_age_seconds=60)
        self.assertEqual(marked, [],
                         msg="terminal jobs must never be re-failed")
        reg.shutdown(timeout=1.0)


if __name__ == "__main__":
    unittest.main()
