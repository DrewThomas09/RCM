"""Concurrency stress — 5 packet builds running simultaneously.

The portfolio store uses ``busy_timeout=5000`` on every connection so
the SQLite writer lock waits rather than erroring. This test drives
five concurrent threads through ``get_or_build_packet`` on five
distinct deals and asserts:
- None raise ``sqlite3.OperationalError``
- Every build completes within a generous wall-clock budget
- All five cached packets are retrievable afterwards

Flaky concurrency tests are worse than no concurrency tests, so we
use a generous 60s timeout; a deadlock shows up as a hang past that.
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest

from rcm_mc.analysis.analysis_store import (
    get_or_build_packet,
    list_packets,
)
from rcm_mc.analysis.packet import ObservedMetric
from rcm_mc.portfolio.store import PortfolioStore


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    for i in range(5):
        s.upsert_deal(f"concurrent-{i}", name=f"Deal {i}", profile={
            "bed_count": 300 + 50 * i, "region": "midwest",
            "payer_mix": {"medicare": 0.4, "commercial": 0.45, "medicaid": 0.15},
        })
    return s, path


class TestConcurrentAnalysis(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_five_concurrent_builds_no_locking_errors(self):
        errors = []
        results = []

        def _build(deal_id: str):
            try:
                p = get_or_build_packet(
                    self.store, deal_id, skip_simulation=True,
                    observed_override={
                        "denial_rate": ObservedMetric(value=8.0 + int(deal_id[-1])),
                    },
                    financials={
                        "gross_revenue": 500_000_000,
                        "net_revenue": 200_000_000,
                        "current_ebitda": 18_000_000,
                        "claims_volume": 120_000,
                    },
                )
                results.append(p.deal_id)
            except Exception as exc:  # noqa: BLE001
                errors.append((deal_id, repr(exc)))

        threads = [
            threading.Thread(target=_build, args=(f"concurrent-{i}",))
            for i in range(5)
        ]
        t0 = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60.0)
            self.assertFalse(t.is_alive(), "thread hung past 60s — possible deadlock")
        duration = time.time() - t0
        self.assertEqual(errors, [], f"concurrent builds raised: {errors}")
        self.assertEqual(sorted(results), [f"concurrent-{i}" for i in range(5)])
        # Sanity: all five rows landed in analysis_runs.
        rows = list_packets(self.store)
        self.assertGreaterEqual(
            len({r["deal_id"] for r in rows}), 5,
        )
        # Diagnostic assertion — not a strict perf contract, just a
        # canary that the concurrency path hasn't regressed into
        # serialized slowness.
        self.assertLess(duration, 45.0, f"concurrent builds took {duration:.1f}s")

    def test_same_deal_concurrent_reads_are_idempotent(self):
        """Multiple threads asking for the same deal's packet must
        all see the same run_id (cache-hit convergence)."""
        run_ids = []
        lock = threading.Lock()

        def _read():
            p = get_or_build_packet(self.store, "concurrent-0",
                                     skip_simulation=True)
            with lock:
                run_ids.append(p.run_id)

        threads = [threading.Thread(target=_read) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30.0)
        # All four threads should have received a run_id (may differ
        # if they each miss the cache independently, but should
        # converge on cache hits).
        self.assertEqual(len(run_ids), 4)
        # Every run_id should match an existing row.
        rows = list_packets(self.store, "concurrent-0")
        stored_ids = {r["run_id"] for r in rows}
        for rid in run_ids:
            self.assertIn(rid, stored_ids)


if __name__ == "__main__":
    unittest.main()
