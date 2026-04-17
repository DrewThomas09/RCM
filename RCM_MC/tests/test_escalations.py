"""Tests for /escalations page (Brick 105)."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from rcm_mc.alerts.alert_history import record_sightings
from rcm_mc.alerts.alerts import Alert, evaluate_active
from rcm_mc.portfolio.store import PortfolioStore
from tests.test_alerts import _seed_with_pe_math


def _backdate_first_seen(store, *, kind, deal_id, trigger_key, days):
    """Force first_seen_at to N days ago so days_open is deterministic."""
    from datetime import datetime, timedelta, timezone
    ts = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with store.connect() as con:
        con.execute(
            "UPDATE alert_history SET first_seen_at = ? "
            "WHERE kind = ? AND deal_id = ? AND trigger_key = ?",
            (ts, kind, deal_id, trigger_key),
        )
        con.commit()


class TestEscalationsPage(unittest.TestCase):
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

    def test_escalations_empty_when_no_aged_reds(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Fresh covenant red — just recorded, should not hit 30-day threshold
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                # Force a sighting
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active"
                ) as r:
                    r.read()
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/escalations"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No red alerts open", body)
            finally:
                server.shutdown(); server.server_close()

    def test_escalations_shows_aged_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            # Record sighting & backdate to 45 days ago
            active = evaluate_active(store)
            covenant = next(a for a in active if a.kind == "covenant_tripped")
            from rcm_mc.alerts.alert_acks import trigger_key_for
            _backdate_first_seen(
                store, kind=covenant.kind, deal_id=covenant.deal_id,
                trigger_key=trigger_key_for(covenant), days=45,
            )
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/escalations"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("45d", body)
                    self.assertIn("ccf", body)
                    self.assertIn("Covenant TRIPPED", body)
            finally:
                server.shutdown(); server.server_close()

    def test_escalations_min_days_query_param(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            active = evaluate_active(store)
            covenant = next(a for a in active if a.kind == "covenant_tripped")
            from rcm_mc.alerts.alert_acks import trigger_key_for
            _backdate_first_seen(
                store, kind=covenant.kind, deal_id=covenant.deal_id,
                trigger_key=trigger_key_for(covenant), days=10,
            )
            server, port = self._start(tmp)
            try:
                # 10 days old, min_days=7 → included
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/escalations?min_days=7"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("10d", body)
                # min_days=30 → excluded
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/escalations?min_days=30"
                ) as r:
                    body = r.read().decode()
                    self.assertIn("No red alerts open", body)
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_escalations_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('href="/escalations"', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
