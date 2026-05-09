"""tests for ``freshness_rail`` + ``_relative_time``."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.ui._ui_kit import _relative_time, freshness_rail


def _iso(delta: timedelta) -> str:
    return (datetime.now(timezone.utc) + delta).isoformat()


class RelativeTime(unittest.TestCase):

    def test_just_now(self) -> None:
        self.assertEqual(_relative_time(_iso(-timedelta(seconds=10))), "just now")

    def test_minutes(self) -> None:
        out = _relative_time(_iso(-timedelta(minutes=14)))
        self.assertTrue(out.endswith("m ago"))
        self.assertIn("14", out)

    def test_hours(self) -> None:
        out = _relative_time(_iso(-timedelta(hours=2)))
        self.assertEqual(out, "2h ago")

    def test_days(self) -> None:
        out = _relative_time(_iso(-timedelta(days=5)))
        self.assertEqual(out, "5d ago")

    def test_invalid_ts_returns_input(self) -> None:
        self.assertEqual(_relative_time("not a date"), "not a date")

    def test_empty_returns_empty(self) -> None:
        self.assertEqual(_relative_time(""), "")


class FreshnessRailRendering(unittest.TestCase):

    def test_all_fields(self) -> None:
        html = freshness_rail(
            packet_generated_at=_iso(-timedelta(minutes=14)),
            hcris_as_of="2024-Q3",
            last_rebuilt_at=_iso(-timedelta(hours=2)),
            rebuild_href="/api/analysis/aurora/rebuild",
        )
        self.assertIn("Packet:", html)
        self.assertIn("HCRIS:", html)
        self.assertIn("Rebuilt:", html)
        self.assertIn("/api/analysis/aurora/rebuild", html)

    def test_omitted_fields_drop(self) -> None:
        html = freshness_rail(packet_generated_at=_iso(-timedelta(minutes=5)))
        self.assertIn("Packet:", html)
        self.assertNotIn("HCRIS:", html)
        self.assertNotIn("Rebuilt:", html)
        self.assertNotIn("Rebuild", html)  # no button

    def test_no_fields_returns_empty(self) -> None:
        self.assertEqual(freshness_rail(), "")


if __name__ == "__main__":
    unittest.main()
