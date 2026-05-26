"""Saved Target-Screener screens — owner-scoped persistence store."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.saved_screens import (
    delete_screen, list_screens, save_screen,
)
from rcm_mc.portfolio.store import PortfolioStore


class SavedScreensTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "s.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_list_owner_scoped(self):
        save_screen(self.store, "alice", "TX SNFs",
                    "view=main&vertical=snf&state=TX")
        save_screen(self.store, "bob", "CA dialysis",
                    "view=main&vertical=dialysis&state=CA")
        a = list_screens(self.store, "alice")
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["title"], "TX SNFs")
        self.assertIn("vertical=snf", a[0]["query_params"])
        self.assertEqual(len(list_screens(self.store, "bob")), 1)

    def test_newest_first(self):
        save_screen(self.store, "a", "first", "view=main")
        save_screen(self.store, "a", "second", "view=compare")
        titles = [s["title"] for s in list_screens(self.store, "a")]
        self.assertEqual(titles[0], "second")

    def test_leading_question_mark_stripped(self):
        save_screen(self.store, "a", "t", "?view=missed&vertical=irf")
        self.assertEqual(list_screens(self.store, "a")[0]["query_params"],
                         "view=missed&vertical=irf")

    def test_empty_owner_or_title_rejected(self):
        with self.assertRaises(ValueError):
            save_screen(self.store, "", "t", "view=main")
        with self.assertRaises(ValueError):
            save_screen(self.store, "a", "  ", "view=main")

    def test_delete_is_owner_scoped(self):
        sid = save_screen(self.store, "alice", "x", "view=main")
        # bob cannot delete alice's screen
        self.assertFalse(delete_screen(self.store, "bob", sid))
        self.assertEqual(len(list_screens(self.store, "alice")), 1)
        # alice can
        self.assertTrue(delete_screen(self.store, "alice", sid))
        self.assertEqual(len(list_screens(self.store, "alice")), 0)

    def test_list_empty_owner_safe(self):
        self.assertEqual(list_screens(self.store, ""), [])

    def test_idempotent_table_creation(self):
        # Saving twice must not raise on the second _ensure_table call.
        save_screen(self.store, "a", "one", "view=main")
        save_screen(self.store, "a", "two", "view=saved")
        self.assertEqual(len(list_screens(self.store, "a")), 2)


if __name__ == "__main__":
    unittest.main()
