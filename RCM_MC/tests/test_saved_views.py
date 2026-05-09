"""tests for ``rcm_mc.portfolio.saved_views``.

PROMPTS.md Phase 4 / Prompt 47: storage layer for partner-defined
named filter snapshots. The UI integration (Save/Load chrome on
list pages) follows piecewise; this file pins the storage contract.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.saved_views import (
    delete_view, get_view, list_views, save_view,
)
from rcm_mc.portfolio.store import PortfolioStore


class SavedViewCRUD(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db_path = tf.name
        self.store = PortfolioStore(self.db_path)

    def tearDown(self) -> None:
        os.unlink(self.db_path)

    def test_save_and_get_round_trip(self) -> None:
        save_view(
            self.store,
            user_id="alice",
            route="/library",
            name="Florida hospitals",
            query_string="state=FL&sector=hospital",
        )
        view = get_view(
            self.store,
            user_id="alice",
            route="/library",
            name="Florida hospitals",
        )
        self.assertIsNotNone(view)
        self.assertEqual(view["query_string"], "state=FL&sector=hospital")

    def test_save_is_upsert(self) -> None:
        # Saving the same name twice updates the query string rather
        # than creating a duplicate row.
        for qs in ("state=FL", "state=CA"):
            save_view(
                self.store,
                user_id="alice",
                route="/library",
                name="My view",
                query_string=qs,
            )
        view = get_view(
            self.store, user_id="alice",
            route="/library", name="My view",
        )
        self.assertEqual(view["query_string"], "state=CA")

    def test_list_views_returns_user_scope(self) -> None:
        save_view(self.store, user_id="alice", route="/library",
                  name="A", query_string="a=1")
        save_view(self.store, user_id="alice", route="/library",
                  name="B", query_string="b=1")
        save_view(self.store, user_id="bob",  route="/library",
                  name="A", query_string="x=1")

        alice_views = list_views(self.store, user_id="alice")
        self.assertEqual({v["name"] for v in alice_views}, {"A", "B"})
        bob_views = list_views(self.store, user_id="bob")
        self.assertEqual({v["name"] for v in bob_views}, {"A"})

    def test_list_views_route_filter(self) -> None:
        save_view(self.store, user_id="alice", route="/library",
                  name="A", query_string="a=1")
        save_view(self.store, user_id="alice", route="/screen",
                  name="B", query_string="b=1")
        only_library = list_views(
            self.store, user_id="alice", route="/library",
        )
        self.assertEqual([v["name"] for v in only_library], ["A"])

    def test_delete_view(self) -> None:
        save_view(self.store, user_id="alice", route="/library",
                  name="X", query_string="z=1")
        removed = delete_view(
            self.store, user_id="alice",
            route="/library", name="X",
        )
        self.assertTrue(removed)
        self.assertIsNone(get_view(
            self.store, user_id="alice",
            route="/library", name="X",
        ))

    def test_delete_missing_returns_false(self) -> None:
        removed = delete_view(
            self.store, user_id="alice",
            route="/library", name="never-saved",
        )
        self.assertFalse(removed)


class InputValidation(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db_path = tf.name
        self.store = PortfolioStore(self.db_path)

    def tearDown(self) -> None:
        os.unlink(self.db_path)

    def test_empty_name_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_view(
                self.store, user_id="alice",
                route="/library", name="   ",
                query_string="x=1",
            )

    def test_empty_user_rejected(self) -> None:
        with self.assertRaises(ValueError):
            save_view(
                self.store, user_id="",
                route="/library", name="X",
                query_string="x=1",
            )


if __name__ == "__main__":
    unittest.main()
