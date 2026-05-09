"""tests for ``rcm_mc.portfolio.last_views``."""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from rcm_mc.portfolio.last_views import mark_viewed, previous_view
from rcm_mc.portfolio.store import PortfolioStore


class FirstViewReturnsNone(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_previous_view_none_before_any_mark(self) -> None:
        self.assertIsNone(previous_view(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        ))

    def test_first_mark_returns_none(self) -> None:
        prev = mark_viewed(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        )
        self.assertIsNone(prev)


class SubsequentMarksReturnPrior(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_second_mark_returns_first_timestamp(self) -> None:
        first = mark_viewed(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        )
        self.assertIsNone(first)
        time.sleep(0.01)
        second = mark_viewed(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        )
        # Second call returns the first timestamp.
        self.assertIsNotNone(second)
        # And the stored value is now the second timestamp; running
        # mark again returns the second timestamp.
        time.sleep(0.01)
        third = mark_viewed(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        )
        self.assertIsNotNone(third)
        self.assertGreaterEqual(third, second)


class PerEntityScope(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_different_entities_tracked_independently(self) -> None:
        mark_viewed(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        )
        # Viewing a different deal_id does not "consume" aurora's
        # state; aurora's previous_view is still set.
        self.assertIsNotNone(previous_view(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        ))
        self.assertIsNone(previous_view(
            self.store, user_id="alice",
            entity_type="deal", entity_id="meadowbrook",
        ))

    def test_different_users_tracked_independently(self) -> None:
        mark_viewed(
            self.store, user_id="alice",
            entity_type="deal", entity_id="aurora",
        )
        # bob's view of aurora is independent.
        self.assertIsNone(previous_view(
            self.store, user_id="bob",
            entity_type="deal", entity_id="aurora",
        ))


class RecentDeals(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_empty_when_no_views(self) -> None:
        from rcm_mc.portfolio.last_views import recent_deals
        self.assertEqual(
            recent_deals(self.store, user_id="alice"),
            [],
        )

    def test_returns_newest_first(self) -> None:
        from rcm_mc.portfolio.last_views import recent_deals
        for deal in ("alpha", "bravo", "charlie"):
            mark_viewed(self.store, user_id="alice",
                        entity_type="deal", entity_id=deal)
            time.sleep(0.01)
        recents = recent_deals(self.store, user_id="alice")
        self.assertEqual(
            [r["deal_id"] for r in recents],
            ["charlie", "bravo", "alpha"],
        )

    def test_limit_respected(self) -> None:
        from rcm_mc.portfolio.last_views import recent_deals
        for deal in ("a", "b", "c", "d"):
            mark_viewed(self.store, user_id="alice",
                        entity_type="deal", entity_id=deal)
            time.sleep(0.005)
        recents = recent_deals(self.store, user_id="alice", limit=2)
        self.assertEqual(len(recents), 2)
        self.assertEqual(recents[0]["deal_id"], "d")

    def test_excludes_other_entity_types(self) -> None:
        # Marking a non-deal entity must not pollute the deal list.
        from rcm_mc.portfolio.last_views import recent_deals
        mark_viewed(self.store, user_id="alice",
                    entity_type="portfolio", entity_id="main")
        mark_viewed(self.store, user_id="alice",
                    entity_type="deal", entity_id="aurora")
        recents = recent_deals(self.store, user_id="alice")
        self.assertEqual(len(recents), 1)
        self.assertEqual(recents[0]["deal_id"], "aurora")

    def test_per_user_scope(self) -> None:
        from rcm_mc.portfolio.last_views import recent_deals
        mark_viewed(self.store, user_id="alice",
                    entity_type="deal", entity_id="aurora")
        self.assertEqual(
            recent_deals(self.store, user_id="bob"), [],
        )


if __name__ == "__main__":
    unittest.main()
