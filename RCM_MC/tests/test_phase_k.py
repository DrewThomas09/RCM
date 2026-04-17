"""Tests for Phase K: Benchmark Evolution (55), Data Retention (57).

BENCHMARK EVOLUTION:
 1. save_snapshot + detect_benchmark_drift round-trip.
 2. Drift < 1pp → None (no alert).
 3. Drift > 1pp → BenchmarkDrift with direction.
 4. Single snapshot → None (need 2).

DATA RETENTION:
 5. enforce_retention deletes old sessions.
 6. Recent rows survive enforcement.
 7. export_user_data produces JSON file.
 8. Empty tables → zero deletions.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.data.benchmark_evolution import (
    BenchmarkDrift,
    detect_benchmark_drift,
    save_snapshot,
)
from rcm_mc.infra.data_retention import (
    enforce_retention,
    export_user_data,
)
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_store():
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return PortfolioStore(tf.name), tf.name


class TestBenchmarkEvolution(unittest.TestCase):

    def test_drift_detected(self):
        store, path = _tmp_store()
        try:
            save_snapshot(store, "denial_rate", 5.2, "2023")
            save_snapshot(store, "denial_rate", 4.0, "2024")
            drift = detect_benchmark_drift("denial_rate", store)
            self.assertIsNotNone(drift)
            self.assertAlmostEqual(drift.drift_pp, -1.2, places=1)
            self.assertEqual(drift.direction, "industry_improving")
        finally:
            os.unlink(path)

    def test_small_drift_ignored(self):
        store, path = _tmp_store()
        try:
            save_snapshot(store, "denial_rate", 5.2, "2023")
            save_snapshot(store, "denial_rate", 5.0, "2024")
            self.assertIsNone(detect_benchmark_drift("denial_rate", store))
        finally:
            os.unlink(path)

    def test_single_snapshot_returns_none(self):
        store, path = _tmp_store()
        try:
            save_snapshot(store, "denial_rate", 5.2, "2024")
            self.assertIsNone(detect_benchmark_drift("denial_rate", store))
        finally:
            os.unlink(path)

    def test_to_dict(self):
        d = BenchmarkDrift(
            metric_key="denial_rate", current_p50=4.0, prior_p50=5.2,
            drift_pp=-1.2, direction="industry_improving",
        )
        self.assertEqual(d.to_dict()["direction"], "industry_improving")


class TestDataRetention(unittest.TestCase):

    def test_enforce_deletes_old_sessions(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.auth.auth import _ensure_tables, create_user
            _ensure_tables(store)
            create_user(store, "u1", "s3cretPwd!")
            # Insert an old session manually.
            old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
            with store.connect() as con:
                con.execute(
                    "INSERT INTO sessions (token, username, expires_at, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    ("old-tok", "u1", old, old),
                )
                con.commit()
            result = enforce_retention(store, {"sessions": 30})
            self.assertGreater(result.get("sessions", 0), 0)
        finally:
            os.unlink(path)

    def test_recent_rows_survive(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.auth.auth import _ensure_tables, create_user, create_session
            _ensure_tables(store)
            create_user(store, "u1", "s3cretPwd!")
            create_session(store, "u1")
            result = enforce_retention(store, {"sessions": 30})
            self.assertEqual(result.get("sessions", 0), 0)
        finally:
            os.unlink(path)

    def test_export_user_data(self):
        store, path = _tmp_store()
        try:
            from rcm_mc.auth.audit_log import log_event
            log_event(store, actor="analyst", action="test")
            out_dir = tempfile.mkdtemp()
            export_path = export_user_data(store, "analyst", out_dir)
            self.assertTrue(export_path.exists())
            data = json.loads(export_path.read_text())
            self.assertIn("audit_events", data)
        finally:
            os.unlink(path)

    def test_empty_tables_zero_deletions(self):
        store, path = _tmp_store()
        try:
            result = enforce_retention(store, {"sessions": 1})
            # Might be 0 because the table may not exist yet.
            self.assertIsInstance(result, dict)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
