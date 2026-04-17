"""Regression test for B160: trigger_key strips whitespace."""
from __future__ import annotations

import unittest

from rcm_mc.alerts.alert_acks import trigger_key_for
from rcm_mc.alerts.alerts import Alert


class TestTriggerKeyStripping(unittest.TestCase):
    def test_whitespace_stripped_from_components(self):
        a1 = Alert(
            kind="covenant_tripped", severity="red", deal_id="ccf",
            title="t", detail="d",
            triggered_at="2026-04-15T10:00:00+00:00",
        )
        a2 = Alert(
            kind=" covenant_tripped ", severity="red", deal_id=" ccf ",
            title="t", detail="d",
            triggered_at=" 2026-04-15T10:00:00+00:00 ",
        )
        # Whitespace differences must not produce different keys
        self.assertEqual(trigger_key_for(a1), trigger_key_for(a2))

    def test_none_triggered_at_becomes_empty(self):
        a = Alert(kind="k", severity="red", deal_id="ccf",
                  title="t", detail="d", triggered_at=None)
        self.assertEqual(trigger_key_for(a), "k|ccf|")


if __name__ == "__main__":
    unittest.main()
