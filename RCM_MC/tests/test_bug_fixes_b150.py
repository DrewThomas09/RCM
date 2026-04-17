"""Regression tests for B150 bugs (fifth audit pass).

Covers:
- Password length cap prevents scrypt DoS
- Decimal-based weighted aggregation is stable
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.auth.auth import change_password, create_user, verify_password
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestPasswordCap(unittest.TestCase):
    def test_create_user_rejects_long_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                create_user(store, "at", "A" * 257)

    def test_create_user_accepts_256_char_password(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # Exactly 256 should be allowed (boundary)
            create_user(store, "at", "A" * 256)
            self.assertTrue(verify_password(store, "at", "A" * 256))

    def test_change_password_rejects_long(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            with self.assertRaises(ValueError):
                change_password(store, "at", "B" * 300)

    def test_verify_password_rejects_long_quickly(self):
        """A 10 MB password must return False immediately, not hash."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            huge = "x" * (10 * 1024 * 1024)
            t0 = time.monotonic()
            result = verify_password(store, "at", huge)
            elapsed = time.monotonic() - t0
            self.assertFalse(result)
            # Pre-fix would hash 10 MB → 2+ seconds. Post-fix is
            # microseconds (just a length check). 0.5s is generous.
            self.assertLess(elapsed, 0.5)


class TestDecimalPrecision(unittest.TestCase):
    def test_portfolio_rollup_with_many_deals_is_stable(self):
        """Weighted aggregation over many deals should give the
        mathematically correct value to reasonable precision."""
        from rcm_mc.portfolio.portfolio_snapshots import portfolio_rollup
        from tests.test_alerts import _seed_with_pe_math
        with tempfile.TemporaryDirectory() as tmp:
            # Seed 20 identical deals — weighted MOIC must equal the
            # per-deal MOIC exactly (2.5) since all weights are equal.
            store = None
            for i in range(20):
                store = _seed_with_pe_math(tmp, f"d{i}", headroom=2.0)
            rollup = portfolio_rollup(store)
            # With 20 identical deals, the weighted avg is exactly 2.5
            self.assertAlmostEqual(
                rollup["weighted_moic"], 2.5, places=10,
            )
            self.assertAlmostEqual(
                rollup["weighted_irr"], 0.20, places=10,
            )

    def test_cohort_rollup_precision(self):
        from rcm_mc.analysis.cohorts import cohort_rollup
        from rcm_mc.deals.deal_tags import add_tag
        from tests.test_alerts import _seed_with_pe_math
        with tempfile.TemporaryDirectory() as tmp:
            store = None
            for i in range(15):
                store = _seed_with_pe_math(tmp, f"d{i}", headroom=2.0)
                add_tag(store, deal_id=f"d{i}", tag="cohort")
            df = cohort_rollup(store)
            row = df[df["tag"] == "cohort"].iloc[0]
            self.assertAlmostEqual(row["weighted_moic"], 2.5, places=10)


if __name__ == "__main__":
    unittest.main()
