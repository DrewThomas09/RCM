"""Tests for B139: trend arrow in rollup health cells."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.deals.deal_tags import add_tag
from rcm_mc.deals.watchlist import star_deal
from tests.test_alerts import _seed_with_pe_math


def _backdate_history(store, deal_id, score, days_ago=1):
    from rcm_mc.deals.health_score import _ensure_history_table
    _ensure_history_table(store)
    d = (date.today() - timedelta(days=days_ago)).isoformat()
    band = "green" if score >= 80 else "amber" if score >= 50 else "red"
    with store.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO deal_health_history "
            "(deal_id, at_date, score, band) VALUES (?, ?, ?, ?)",
            (deal_id, d, int(score), band),
        )
        con.commit()


class TestRollupArrows(unittest.TestCase):
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

    def test_watchlist_shows_down_arrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)  # 60
            star_deal(store, "ccf")
            _backdate_history(store, "ccf", 100, days_ago=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/watchlist") as r:
                    body = r.read().decode()
                    self.assertIn('title="Δ -40', body)
            finally:
                server.shutdown(); server.server_close()

    def test_cohort_shows_up_arrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)  # 100
            add_tag(store, deal_id="ccf", tag="watch")
            _backdate_history(store, "ccf", 60, days_ago=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cohort/watch") as r:
                    body = r.read().decode()
                    self.assertIn('title="Δ +40', body)
                    self.assertIn("↑", body)
            finally:
                server.shutdown(); server.server_close()

    def test_owner_detail_arrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            _backdate_history(store, "ccf", 100, days_ago=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/owner/AT") as r:
                    body = r.read().decode()
                    self.assertIn('title="Δ -40', body)
            finally:
                server.shutdown(); server.server_close()

    def test_my_dashboard_arrow(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            assign_owner(store, deal_id="ccf", owner="AT")
            _backdate_history(store, "ccf", 100, days_ago=1)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn('title="Δ -40', body)
            finally:
                server.shutdown(); server.server_close()

    def test_no_arrow_on_first_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            star_deal(store, "ccf")
            # No backdated row → no prior day → flat → no arrow
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/watchlist") as r:
                    body = r.read().decode()
                    self.assertNotIn('title="Δ', body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
