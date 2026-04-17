"""Tests for alert history + first-seen tracking (Brick 104)."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.alerts.alert_history import (
    age_hint, days_red, get_first_seen, list_history, record_sightings,
)
from rcm_mc.alerts.alerts import Alert, evaluate_active, evaluate_all
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestRecordSightings(unittest.TestCase):
    def test_first_sighting_sets_first_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = Alert(kind="covenant_tripped", severity="red", deal_id="ccf",
                      title="T", detail="D", triggered_at="2026-04-14T10:00:00")
            record_sightings(store, [a])
            df = list_history(store)
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["sightings_count"], 1)
            self.assertEqual(df.iloc[0]["first_seen_at"],
                             df.iloc[0]["last_seen_at"])

    def test_repeat_sighting_bumps_count_but_not_first_seen(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = Alert(kind="k", severity="red", deal_id="d", title="T",
                      detail="D", triggered_at="2026-01-01T00:00:00")
            record_sightings(store, [a])
            first = list_history(store).iloc[0]["first_seen_at"]
            time.sleep(0.01)
            record_sightings(store, [a])
            df = list_history(store)
            self.assertEqual(df.iloc[0]["sightings_count"], 2)
            self.assertEqual(df.iloc[0]["first_seen_at"], first)
            self.assertNotEqual(df.iloc[0]["last_seen_at"], first)

    def test_different_trigger_keys_are_separate_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a1 = Alert(kind="k", severity="red", deal_id="d", title="T",
                       detail="D", triggered_at="2026-01-01")
            a2 = Alert(kind="k", severity="red", deal_id="d", title="T",
                       detail="D", triggered_at="2026-02-01")
            record_sightings(store, [a1, a2])
            self.assertEqual(len(list_history(store)), 2)


class TestEvaluateActiveEnrichment(unittest.TestCase):
    def test_active_alerts_get_first_seen_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            active = evaluate_active(store)
            self.assertTrue(active)
            # Every active alert must have a first_seen_at after enrichment
            for a in active:
                self.assertIsNotNone(a.first_seen_at)

    def test_first_seen_stable_across_multiple_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            first_call = evaluate_active(store)
            time.sleep(0.01)
            second_call = evaluate_active(store)
            by_kind = {a.kind: a.first_seen_at for a in first_call}
            for a in second_call:
                self.assertEqual(a.first_seen_at, by_kind[a.kind])


class TestAgeHint(unittest.TestCase):
    def test_age_hint_minutes(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(minutes=5)).isoformat()
        self.assertEqual(age_hint(ts, now=now), "5m ago")

    def test_age_hint_hours(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(hours=3)).isoformat()
        self.assertEqual(age_hint(ts, now=now), "3h ago")

    def test_age_hint_days(self):
        now = datetime.now(timezone.utc)
        ts = (now - timedelta(days=14)).isoformat()
        self.assertEqual(age_hint(ts, now=now), "14d ago")

    def test_age_hint_empty_for_bad_input(self):
        self.assertEqual(age_hint(None), "")
        self.assertEqual(age_hint(""), "")
        self.assertEqual(age_hint("not-a-date"), "")


class TestDaysRed(unittest.TestCase):
    def test_days_red_filters_by_age(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = Alert(kind="k", severity="red", deal_id="d", title="T",
                      detail="D", triggered_at="x")
            record_sightings(store, [a])
            # Just recorded → 0 days old → filtered out by min_days=30
            self.assertTrue(days_red(store, min_days=30).empty)
            # min_days=0 → included
            self.assertEqual(len(days_red(store, min_days=0)), 1)

    def test_days_red_excludes_amber(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            a = Alert(kind="k", severity="amber", deal_id="d", title="T",
                      detail="D")
            record_sightings(store, [a])
            self.assertTrue(days_red(store, min_days=0).empty)


class TestHistoryHttp(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_api_alerts_history_returns_rows_after_visit(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                # Visit /api/alerts/active to trigger sighting recording
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active"
                ) as r:
                    r.read()
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/history"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(len(data) >= 1)
                    kinds = {row["kind"] for row in data}
                    self.assertIn("covenant_tripped", kinds)
            finally:
                server.shutdown(); server.server_close()

    def test_api_days_red_respects_min_days(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active"
                ) as r:
                    r.read()
                # Fresh alert, min_days=0 should include it
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/days_red?min_days=0"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertTrue(len(data) >= 1)
                # Same alert, min_days=30 should exclude
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/days_red?min_days=30"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertEqual(data, [])
            finally:
                server.shutdown(); server.server_close()

    def test_alerts_page_shows_age_hint(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn("seen ", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
