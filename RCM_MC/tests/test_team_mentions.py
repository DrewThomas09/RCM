"""tests for ``rcm_mc.portfolio.team_mentions``."""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.team_mentions import (
    list_for_user, mark_read, mention, unread_for_user,
)


class MentionFlow(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_mention_increments_unread_count(self) -> None:
        self.assertEqual(unread_for_user(self.store, user_id="bob"), 0)
        mention(
            self.store,
            from_user_id="alice", to_user_id="bob",
            entity_type="deal", entity_id="aurora",
            share_url="/deal/aurora",
        )
        self.assertEqual(unread_for_user(self.store, user_id="bob"), 1)

    def test_self_mention_rejected(self) -> None:
        with self.assertRaises(ValueError):
            mention(
                self.store,
                from_user_id="alice", to_user_id="alice",
                entity_type="deal", entity_id="aurora",
                share_url="/deal/aurora",
            )

    def test_mark_read_clears_count(self) -> None:
        mention(
            self.store,
            from_user_id="alice", to_user_id="bob",
            entity_type="deal", entity_id="aurora",
            share_url="/deal/aurora",
        )
        cleared = mark_read(self.store, user_id="bob")
        self.assertEqual(cleared, 1)
        self.assertEqual(unread_for_user(self.store, user_id="bob"), 0)

    def test_mark_read_idempotent(self) -> None:
        mention(
            self.store,
            from_user_id="alice", to_user_id="bob",
            entity_type="deal", entity_id="aurora",
            share_url="/deal/aurora",
        )
        mark_read(self.store, user_id="bob")
        # Second call returns 0 (nothing to clear).
        self.assertEqual(mark_read(self.store, user_id="bob"), 0)

    def test_list_includes_metadata(self) -> None:
        mention(
            self.store,
            from_user_id="alice", to_user_id="bob",
            entity_type="deal", entity_id="aurora",
            share_url="/deal/aurora?tab=mc",
            message="check the MC variance — bigger than I expected",
        )
        items = list_for_user(self.store, user_id="bob")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["from_user_id"], "alice")
        self.assertIn("MC variance", items[0]["message"])

    def test_only_unread_filter(self) -> None:
        for _ in range(3):
            mention(
                self.store,
                from_user_id="alice", to_user_id="bob",
                entity_type="deal", entity_id="aurora",
                share_url="/deal/aurora",
            )
        mark_read(self.store, user_id="bob")  # clear all
        # Now add one new one.
        mention(
            self.store,
            from_user_id="alice", to_user_id="bob",
            entity_type="deal", entity_id="aurora",
            share_url="/deal/aurora",
        )
        unread = list_for_user(
            self.store, user_id="bob", only_unread=True,
        )
        self.assertEqual(len(unread), 1)


class ShareButtonHelper(unittest.TestCase):

    def test_renders_with_data_attributes(self) -> None:
        from rcm_mc.ui._ui_kit import share_button
        html = share_button(
            entity_type="deal", entity_id="aurora",
            share_url="/deal/aurora?tab=mc",
        )
        self.assertIn('data-share-entity-type="deal"', html)
        self.assertIn('data-share-entity-id="aurora"', html)
        self.assertIn('data-share-url="/deal/aurora?tab=mc"', html)
        self.assertIn("Share", html)


if __name__ == "__main__":
    unittest.main()
