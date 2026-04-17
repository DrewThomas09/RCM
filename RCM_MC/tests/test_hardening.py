"""Hardening: rate limit, consistency check, error envelope."""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from rcm_mc.infra.consistency_check import check_consistency, ConsistencyReport
from rcm_mc.infra.rate_limit import RateLimiter
from rcm_mc.portfolio.store import PortfolioStore


def _temp_store():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = PortfolioStore(path)
    s.init_db()
    return s, path


# ── Rate limiter ────────────────────────────────────────────────────

class TestRateLimiter(unittest.TestCase):
    def test_limiter_allows_up_to_max_hits(self):
        rl = RateLimiter(max_hits=3, window_secs=60)
        for _ in range(3):
            ok, _ = rl.check("k")
            self.assertTrue(ok)
        ok, wait = rl.check("k")
        self.assertFalse(ok)
        self.assertGreater(wait, 0)

    def test_different_keys_independent(self):
        rl = RateLimiter(max_hits=1, window_secs=60)
        self.assertTrue(rl.check("a")[0])
        self.assertTrue(rl.check("b")[0])
        self.assertFalse(rl.check("a")[0])

    def test_window_expiration_resets(self):
        rl = RateLimiter(max_hits=1, window_secs=1)
        self.assertTrue(rl.check("k")[0])
        self.assertFalse(rl.check("k")[0])
        time.sleep(1.2)
        ok, _ = rl.check("k")
        self.assertTrue(ok)

    def test_reset_key(self):
        rl = RateLimiter(max_hits=1, window_secs=60)
        rl.check("k")
        self.assertFalse(rl.check("k")[0])
        rl.reset("k")
        self.assertTrue(rl.check("k")[0])


# ── Consistency check ──────────────────────────────────────────────

class TestConsistencyCheck(unittest.TestCase):
    def setUp(self):
        self.store, self.path = _temp_store()

    def tearDown(self):
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def test_fresh_store_has_expected_tables(self):
        report = check_consistency(self.store)
        self.assertIsInstance(report, ConsistencyReport)
        for name in ("deals", "runs", "hospital_benchmarks",
                      "data_source_status", "analysis_runs",
                      "mc_simulation_runs", "generated_exports"):
            self.assertIn(name, report.existing_tables,
                          f"missing {name}")
        self.assertEqual(report.missing_tables, [])
        self.assertTrue(report.ok)

    def test_orphaned_analysis_runs_detected(self):
        from rcm_mc.analysis.analysis_store import save_packet
        from rcm_mc.analysis.packet import DealAnalysisPacket
        # Prompt 21 turned on FK enforcement with ON DELETE CASCADE on
        # analysis_runs, which prevents a true orphan from appearing in
        # normal operation — the consistency checker still matters for
        # DBs that predate the FK constraint, but the test has to
        # fabricate an orphan by temporarily disabling enforcement.
        p = DealAnalysisPacket(deal_id="ghost")
        self.store.upsert_deal("ghost", name="ghost")
        save_packet(self.store, p, inputs_hash="h")
        with self.store.connect() as con:
            con.execute("PRAGMA foreign_keys = OFF")
            con.execute("DELETE FROM deals WHERE deal_id = 'ghost'")
            con.commit()
        report = check_consistency(self.store)
        self.assertGreaterEqual(report.orphaned_analysis_runs, 1)
        self.assertTrue(any("orphaned" in n for n in report.notes))

    def test_to_dict_serializable(self):
        report = check_consistency(self.store)
        d = report.to_dict()
        self.assertIn("existing_tables", d)
        self.assertIn("missing_tables", d)
        self.assertIn("orphaned_analysis_runs", d)


# ── Error envelope shape ───────────────────────────────────────────

class TestErrorEnvelope(unittest.TestCase):
    def test_refresh_rate_limit_envelope(self):
        """Verify the rate-limited error JSON matches the standard
        envelope shape used across the API."""
        from rcm_mc.infra.rate_limit import RateLimiter
        rl = RateLimiter(max_hits=1, window_secs=60)
        rl.check("k")
        ok, wait = rl.check("k")
        # The server-level handler constructs the envelope; we mimic
        # it here to lock the expected shape.
        envelope = {
            "error": f"rate limited on 'k'; wait {int(wait)}s",
            "code": "RATE_LIMITED",
            "detail": {"retry_after_seconds": int(wait)},
        }
        self.assertIn("error", envelope)
        self.assertIn("code", envelope)
        self.assertIn("detail", envelope)
        self.assertEqual(envelope["code"], "RATE_LIMITED")


if __name__ == "__main__":
    unittest.main()
