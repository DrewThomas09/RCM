"""Wave-35 visual: my-dashboard deadline timeline.

The dashboard listed overdue and upcoming deadlines as two lists;
how the fortnight clusters — three things due the same Thursday —
was invisible. Pins the lollipop timeline: TODAY line, overdue red
left, upcoming navy right, caption counts, and the empty state.
"""
from __future__ import annotations

import unittest
from datetime import date, datetime, timedelta, timezone

import pandas as pd

from rcm_mc.ui.my_dashboard_page import _deadline_timeline_svg


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _df(rows):
    return pd.DataFrame(rows)


class DeadlineTimelineTests(unittest.TestCase):
    def test_renders_overdue_and_upcoming_markers(self):
        od = _df([{
            "deal_id": "d1", "label": "QoE call",
            "due_date": (_today() - timedelta(days=5)).isoformat(),
        }])
        up = _df([{
            "deal_id": "d2", "label": "LOI deadline",
            "due_date": (_today() + timedelta(days=3)).isoformat(),
        }])
        svg = _deadline_timeline_svg(od, up)
        self.assertIn("<svg", svg)
        self.assertIn("ck-deadline-timeline", svg)
        self.assertIn("TODAY", svg)
        self.assertIn("d1 · QoE call", svg)
        self.assertIn("d2 · LOI deadline", svg)
        self.assertIn("#b5321e", svg)   # overdue red
        self.assertIn("#0b2341", svg)   # upcoming navy
        self.assertIn("1 OVERDUE", svg)
        self.assertIn("1 DUE IN THE NEXT 14 DAYS", svg)

    def test_overdue_marker_left_of_today(self):
        od = _df([{
            "deal_id": "d1", "label": "Late",
            "due_date": (_today() - timedelta(days=7)).isoformat(),
        }])
        up = _df([{
            "deal_id": "d2", "label": "Soon",
            "due_date": (_today() + timedelta(days=7)).isoformat(),
        }])
        svg = _deadline_timeline_svg(od, up)
        import re
        circles = [float(m) for m in
                   re.findall(r'<circle cx="([\d.]+)"', svg)]
        today_x = float(re.search(
            r'<line x1="([\d.]+)" y1="\d+" x2="\1" '
            r'y2="\d+" stroke="#0b2341"', svg).group(1))
        self.assertLess(circles[0], today_x)   # overdue left
        self.assertGreater(circles[1], today_x)  # upcoming right

    def test_bad_dates_skipped(self):
        od = _df([{"deal_id": "d1", "label": "Bad", "due_date": "garbage"}])
        up = _df([{
            "deal_id": "d2", "label": "Good",
            "due_date": (_today() + timedelta(days=2)).isoformat(),
        }])
        svg = _deadline_timeline_svg(od, up)
        self.assertNotIn("Bad", svg)
        self.assertIn("Good", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(
            _deadline_timeline_svg(pd.DataFrame(), pd.DataFrame()), "")
        self.assertEqual(_deadline_timeline_svg(None, None), "")


if __name__ == "__main__":
    unittest.main()
