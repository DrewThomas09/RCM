"""Regression tests for B154 bugs (ninth audit pass)."""
from __future__ import annotations

import os
import resource
import tempfile
import threading
import unittest

from rcm_mc.auth.auth import create_user, delete_user
from rcm_mc.deals.deal_notes import import_notes_csv
from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestProbeHandleCleanup(unittest.TestCase):
    """B154 #1: the UTF-8 probe must close its handle before opening
    a latin-1 fallback, or bulk imports leak file descriptors."""

    def test_many_latin1_imports_no_fd_growth(self):
        """Import 200 latin-1 CSVs in a row — fd count should stay stable."""
        # Use /proc approach via os.listdir; fall back to resource module
        try:
            import pathlib
            fd_dir = pathlib.Path(f"/proc/{os.getpid()}/fd")
            fd_dir.is_dir()  # probe
            have_fd_dir = fd_dir.is_dir()
        except Exception:  # noqa: BLE001
            have_fd_dir = False

        def fd_count():
            if have_fd_dir:
                return len(list(fd_dir.iterdir()))
            # macOS fallback: use lsof-free `resource` getrusage
            # doesn't expose count directly. Use the hard limit hack:
            # count by trying open+close until failure. We'll just
            # skip the assertion on non-/proc systems.
            return None

        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            path = os.path.join(tmp, "latin1.csv")
            with open(path, "wb") as f:
                f.write(b"deal_id,body,author\n")
                f.write(b"ccf,caf\xe9 notes,JD\n")
            initial = fd_count()
            for _ in range(200):
                summary = import_notes_csv(store, path)
                self.assertEqual(summary["rows_ingested"], 1)
            final = fd_count()
            if initial is not None and final is not None:
                # Some drift is OK (pandas, sqlite), but >100 fd growth
                # means a leak per import cycle.
                self.assertLess(final - initial, 50)


class TestDeleteUserTransaction(unittest.TestCase):
    """B154 #2: delete_user's check+delete must be atomic to defeat
    TOCTOU races where another thread assigns a deal between check
    and delete."""

    def test_no_dangling_owner_after_concurrent_assign(self):
        """
        One thread repeatedly assigns 'ccf' to 'at'.
        Another thread tries to delete 'at'.
        Either: (a) delete succeeds and no future assign points at 'at'
                    (b) delete fails because assign beat it.
        There must NEVER be a state where 'at' is deleted AND 'ccf' is
        owned by 'at' (dangling reference).
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            errors = []
            stop = threading.Event()

            def assigner():
                for _ in range(50):
                    if stop.is_set():
                        break
                    try:
                        assign_owner(store, deal_id="ccf", owner="at")
                    except Exception as exc:  # noqa: BLE001
                        errors.append(exc)

            def deleter():
                for _ in range(20):
                    try:
                        delete_user(store, "at")
                        break
                    except ValueError:
                        # Expected — another thread's assign blocks us
                        pass
                    except Exception as exc:  # noqa: BLE001
                        errors.append(exc)

            t_a = threading.Thread(target=assigner)
            t_d = threading.Thread(target=deleter)
            t_a.start(); t_d.start()
            t_a.join(timeout=5)
            stop.set()
            t_d.join(timeout=5)

            # Invariant: if user 'at' was deleted, no deal currently
            # points at them in deal_owner_history's latest row per deal.
            with store.connect() as con:
                user_exists = con.execute(
                    "SELECT COUNT(*) AS n FROM users WHERE username = 'at'",
                ).fetchone()["n"] > 0
                current_owner_of_ccf = con.execute(
                    """SELECT owner FROM deal_owner_history h1
                       WHERE id = (
                           SELECT MAX(id) FROM deal_owner_history h2
                           WHERE h2.deal_id = h1.deal_id
                       ) AND deal_id = 'ccf'"""
                ).fetchone()

            if not user_exists and current_owner_of_ccf is not None:
                self.assertNotEqual(
                    current_owner_of_ccf["owner"], "at",
                    "Dangling: user 'at' was deleted but still owns 'ccf'",
                )
            # Background errors should only be the expected ValueErrors
            self.assertEqual(errors, [])

    def test_normal_delete_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            self.assertTrue(delete_user(store, "at"))


if __name__ == "__main__":
    unittest.main()
