"""Regression tests for B151 bugs (sixth audit pass)."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.auth.auth import create_user, delete_user
from rcm_mc.deals.deal_deadlines import add_deadline
from rcm_mc.deals.deal_notes import import_notes_csv, record_note
from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestDeleteUserGuards(unittest.TestCase):
    def test_cannot_delete_user_with_current_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            assign_owner(store, deal_id="ccf", owner="at")
            with self.assertRaises(ValueError) as ctx:
                delete_user(store, "at")
            self.assertIn("currently owns", str(ctx.exception))

    def test_cannot_delete_user_with_open_deadlines(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            add_deadline(store, deal_id="ccf", label="x",
                         due_date="2030-01-01", owner="at")
            with self.assertRaises(ValueError) as ctx:
                delete_user(store, "at")
            self.assertIn("open deadline", str(ctx.exception))

    def test_can_delete_user_with_no_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            self.assertTrue(delete_user(store, "at"))

    def test_can_delete_user_after_reassignment(self):
        """Reassign deal, then delete works."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            create_user(store, "at", "supersecret1")
            create_user(store, "sb", "supersecret1")
            assign_owner(store, deal_id="ccf", owner="at")
            # Reassign to sb
            assign_owner(store, deal_id="ccf", owner="sb")
            # Now AT owns 0 current deals
            self.assertTrue(delete_user(store, "at"))


class TestCsvEncodingFallback(unittest.TestCase):
    def test_latin1_csv_ingests_without_crash(self):
        """A CP1252/latin-1 CSV (Windows Excel default) should import
        cleanly rather than 500 on UnicodeDecodeError."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            path = os.path.join(tmp, "latin1.csv")
            # Non-ASCII byte that's valid latin-1 but not UTF-8:
            # \xe9 = 'é' in latin-1
            with open(path, "wb") as f:
                f.write(b"deal_id,body,author\n")
                f.write(b"ccf,caf\xe9 meeting notes,JD\n")
            summary = import_notes_csv(store, path)
            self.assertEqual(summary["rows_ingested"], 1)


class TestNoteSizeCaps(unittest.TestCase):
    def test_huge_body_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError) as ctx:
                record_note(store, deal_id="ccf", body="x" * 100_000)
            self.assertIn("too long", str(ctx.exception))

    def test_long_deal_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                record_note(store, deal_id="a" * 200, body="text")

    def test_normal_body_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            nid = record_note(store, deal_id="ccf",
                              body="normal-length note")
            self.assertIsInstance(nid, int)


if __name__ == "__main__":
    unittest.main()
