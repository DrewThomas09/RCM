"""tests for ``rcm_mc.portfolio.user_pins``.

PROMPTS.md Phase 4 / Prompt 48: per-user pin storage. UI integration
(Home pinned-strip + per-route pin button) follows piecewise.
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.user_pins import (
    is_pinned, list_pins, pin, unpin,
)


class PinCRUD(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_pin_then_is_pinned(self) -> None:
        pin(self.store, user_id="alice",
            route="/diligence/risk-workbench", label="Risk Workbench")
        self.assertTrue(is_pinned(
            self.store, user_id="alice",
            route="/diligence/risk-workbench",
        ))

    def test_repinning_idempotent(self) -> None:
        for _ in range(3):
            pin(self.store, user_id="alice",
                route="/library", label="Library")
        pins = list_pins(self.store, user_id="alice")
        self.assertEqual(len(pins), 1)

    def test_unpin(self) -> None:
        pin(self.store, user_id="alice",
            route="/library", label="Library")
        self.assertTrue(unpin(
            self.store, user_id="alice", route="/library",
        ))
        self.assertFalse(is_pinned(
            self.store, user_id="alice", route="/library",
        ))

    def test_unpin_missing_returns_false(self) -> None:
        self.assertFalse(unpin(
            self.store, user_id="alice", route="/never-pinned",
        ))


class Ordering(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_most_recent_pin_first(self) -> None:
        pin(self.store, user_id="alice",
            route="/library", label="Library")
        time.sleep(0.01)
        pin(self.store, user_id="alice",
            route="/alerts", label="Alerts")
        time.sleep(0.01)
        pin(self.store, user_id="alice",
            route="/portfolio", label="Portfolio")

        pins = list_pins(self.store, user_id="alice")
        self.assertEqual(
            [p["route"] for p in pins],
            ["/portfolio", "/alerts", "/library"],
        )

    def test_repin_moves_to_top(self) -> None:
        pin(self.store, user_id="alice",
            route="/library", label="Library")
        time.sleep(0.01)
        pin(self.store, user_id="alice",
            route="/alerts", label="Alerts")
        time.sleep(0.01)
        # Re-pin Library — should sort first now.
        pin(self.store, user_id="alice",
            route="/library", label="Library")

        pins = list_pins(self.store, user_id="alice")
        self.assertEqual(pins[0]["route"], "/library")


class PerUserScope(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_alice_pins_invisible_to_bob(self) -> None:
        pin(self.store, user_id="alice",
            route="/library", label="Library")
        self.assertFalse(is_pinned(
            self.store, user_id="bob", route="/library",
        ))
        bob_pins = list_pins(self.store, user_id="bob")
        self.assertEqual(bob_pins, [])


class InputValidation(unittest.TestCase):

    def setUp(self) -> None:
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        self.db = tf.name
        self.store = PortfolioStore(self.db)

    def tearDown(self) -> None:
        os.unlink(self.db)

    def test_empty_label_rejected(self) -> None:
        with self.assertRaises(ValueError):
            pin(self.store, user_id="alice",
                route="/library", label="")


if __name__ == "__main__":
    unittest.main()
