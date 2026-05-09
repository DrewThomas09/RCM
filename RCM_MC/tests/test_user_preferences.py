"""tests for ``rcm_mc.portfolio.user_preferences``."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.user_preferences import (
    delete_pref, get_pref, list_prefs, set_pref,
)


class GetSetRoundTrip(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_get_returns_default_when_unset(self) -> None:
        self.assertIsNone(get_pref(
            self.store, user_id="alice",
            route="/library", key="sort",
        ))
        self.assertEqual(
            get_pref(
                self.store, user_id="alice",
                route="/library", key="sort", default="moic_desc",
            ),
            "moic_desc",
        )

    def test_set_then_get(self) -> None:
        set_pref(
            self.store, user_id="alice",
            route="/library", key="sort", value="irr_desc",
        )
        self.assertEqual(
            get_pref(self.store, user_id="alice",
                     route="/library", key="sort"),
            "irr_desc",
        )

    def test_set_is_upsert(self) -> None:
        for v in ("moic_desc", "irr_desc", "vintage_desc"):
            set_pref(
                self.store, user_id="alice",
                route="/library", key="sort", value=v,
            )
        # Final value wins; no duplicate rows.
        self.assertEqual(
            get_pref(self.store, user_id="alice",
                     route="/library", key="sort"),
            "vintage_desc",
        )
        prefs = list_prefs(self.store, user_id="alice")
        self.assertEqual(len(prefs), 1)


class PerScopeIsolation(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_different_routes_independent(self) -> None:
        set_pref(self.store, user_id="alice",
                 route="/library", key="sort", value="moic")
        set_pref(self.store, user_id="alice",
                 route="/screener", key="sort", value="state")
        self.assertEqual(get_pref(
            self.store, user_id="alice",
            route="/library", key="sort"), "moic")
        self.assertEqual(get_pref(
            self.store, user_id="alice",
            route="/screener", key="sort"), "state")

    def test_different_users_independent(self) -> None:
        set_pref(self.store, user_id="alice",
                 route="/library", key="sort", value="moic")
        self.assertIsNone(get_pref(
            self.store, user_id="bob",
            route="/library", key="sort"))


class DeleteAndList(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_delete(self) -> None:
        set_pref(self.store, user_id="alice",
                 route="/library", key="sort", value="moic")
        self.assertTrue(delete_pref(
            self.store, user_id="alice",
            route="/library", key="sort"))
        self.assertIsNone(get_pref(
            self.store, user_id="alice",
            route="/library", key="sort"))

    def test_list_route_filter(self) -> None:
        set_pref(self.store, user_id="alice",
                 route="/library", key="sort", value="moic")
        set_pref(self.store, user_id="alice",
                 route="/screener", key="sort", value="state")
        only_lib = list_prefs(
            self.store, user_id="alice", route="/library",
        )
        self.assertEqual([p["route"] for p in only_lib], ["/library"])


class InputValidation(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_empty_key_rejected(self) -> None:
        with self.assertRaises(ValueError):
            set_pref(self.store, user_id="alice",
                     route="/library", key="", value="x")


if __name__ == "__main__":
    unittest.main()
