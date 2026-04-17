"""Regression test for B158: duplicate-deadline dedupe."""
from __future__ import annotations

import os
import tempfile
import threading
import unittest

from rcm_mc.deals.deal_deadlines import (
    add_deadline, complete_deadline, list_deadlines,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestDeadlineDedupe(unittest.TestCase):
    def test_duplicate_returns_same_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = add_deadline(store, deal_id="ccf", label="refi",
                             due_date="2030-01-01")
            b = add_deadline(store, deal_id="ccf", label="refi",
                             due_date="2030-01-01")
            self.assertEqual(a, b)
            self.assertEqual(len(list_deadlines(store)), 1)

    def test_different_date_creates_new_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = add_deadline(store, deal_id="ccf", label="refi",
                             due_date="2030-01-01")
            b = add_deadline(store, deal_id="ccf", label="refi",
                             due_date="2030-02-01")
            self.assertNotEqual(a, b)
            self.assertEqual(len(list_deadlines(store)), 2)

    def test_different_label_creates_new_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            add_deadline(store, deal_id="ccf", label="refi",
                         due_date="2030-01-01")
            add_deadline(store, deal_id="ccf", label="audit",
                         due_date="2030-01-01")
            self.assertEqual(len(list_deadlines(store)), 2)

    def test_completed_does_not_block_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            did = add_deadline(store, deal_id="ccf", label="refi",
                               due_date="2030-01-01")
            complete_deadline(store, did)
            # Completing and re-creating creates a NEW open row, since
            # dedupe only scans status='open'
            new_id = add_deadline(store, deal_id="ccf", label="refi",
                                  due_date="2030-01-01")
            self.assertNotEqual(did, new_id)
            all_rows = list_deadlines(store, include_completed=True)
            self.assertEqual(len(all_rows), 2)

    def test_concurrent_duplicates_do_not_both_insert(self):
        """Two threads POSTing identical deadlines → exactly one row."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            ids = []
            errors = []

            def submit():
                try:
                    ids.append(add_deadline(
                        store, deal_id="ccf", label="refi",
                        due_date="2030-01-01",
                    ))
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

            threads = [threading.Thread(target=submit) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(errors, [])
            # Exactly one open deadline row
            self.assertEqual(len(list_deadlines(store)), 1)


if __name__ == "__main__":
    unittest.main()
