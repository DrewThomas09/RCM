"""tests for ``entity_activity_rail`` (P60).

Surfaces the audit log diegetically on entity pages — readers
without admin role can still see who-did-what-and-when.
"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

from rcm_mc.ui._ui_kit import entity_activity_rail


def _seed_audit(db_path: str, entries: list[dict]) -> None:
    con = sqlite3.connect(db_path)
    con.execute(
        """CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            target TEXT NOT NULL DEFAULT '',
            detail_json TEXT NOT NULL DEFAULT '{}'
        )"""
    )
    for e in entries:
        con.execute(
            "INSERT INTO audit_events (at, actor, action, target) "
            "VALUES (?, ?, ?, ?)",
            (e["at"], e["actor"], e["action"], e["target"]),
        )
    con.commit()
    con.close()


class RailRendering(unittest.TestCase):

    def test_empty_table_renders_empty_state(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            html = entity_activity_rail(
                tf.name, entity_id="aurora",
            )
        self.assertIn("activity-rail", html)
        self.assertIn("No recent activity", html)

    def test_missing_table_does_not_crash(self) -> None:
        # Brand-new DB with no schema must not raise.
        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            html = entity_activity_rail(
                tf.name, entity_id="aurora",
            )
        self.assertIn("No recent activity", html)

    def test_rows_filtered_by_target(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            now = datetime.now(timezone.utc).isoformat()
            _seed_audit(tf.name, [
                {"at": now, "actor": "alice",
                 "action": "ack_alert", "target": "aurora"},
                {"at": now, "actor": "bob",
                 "action": "rerun_sim", "target": "meadowbrook"},
                {"at": now, "actor": "alice",
                 "action": "advance_stage", "target": "aurora"},
            ])
            html = entity_activity_rail(
                tf.name, entity_id="aurora",
            )
        # Two aurora rows present; meadowbrook row absent.
        self.assertEqual(html.count("ack_alert") + html.count("advance_stage"), 2)
        self.assertNotIn("rerun_sim", html)

    def test_full_audit_link_carries_target(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".db") as tf:
            now = datetime.now(timezone.utc).isoformat()
            _seed_audit(tf.name, [{
                "at": now, "actor": "alice",
                "action": "ack_alert", "target": "aurora",
            }])
            html = entity_activity_rail(
                tf.name, entity_id="aurora",
            )
        self.assertIn('href="/audit?target=aurora"', html)


if __name__ == "__main__":
    unittest.main()
