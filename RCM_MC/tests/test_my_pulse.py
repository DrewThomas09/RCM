"""Tests for B141 per-user pulse + health mix on /my/<owner>."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u
from datetime import date, timedelta

from rcm_mc.deals.deal_deadlines import add_deadline
from rcm_mc.deals.deal_owners import assign_owner
from tests.test_alerts import _seed_with_pe_math


class TestMyPulse(unittest.TestCase):
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

    def test_clean_owner_renders_pulse_with_zero_alerts(self):
        # Cycle 15 editorial port: pulse strip is ALWAYS rendered (5
        # KPI blocks) because "0 red" is a signal worth surfacing —
        # an analyst seeing a row of zeros confirms there's nothing
        # outstanding rather than wondering if the page didn't load.
        # Legacy behavior of hiding the pulse on a clean owner is
        # intentionally dropped.
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "clean", headroom=2.0)
            assign_owner(store, deal_id="clean", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    # Pulse strip + health-mix card both present
                    self.assertIn("ck-pulse-grid", body)
                    self.assertIn(">Red Alerts</div>", body)
                    self.assertIn("Your health mix", body)
                    # AT has 1 green deal — health-mix legend reflects it
                    self.assertIn("● 1 green", body)
            finally:
                server.shutdown(); server.server_close()

    def test_pulse_counts_scoped_to_owner(self):
        # Editorial port: legacy "1 red" inline phrase replaced by a
        # "Red Alerts" KPI block carrying the count. Other owners'
        # deals must NOT contribute to the count — scoping is the
        # load-bearing assertion this test pins.
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "atdeal", headroom=-0.5)
            _seed_with_pe_math(tmp, "other", headroom=-0.5)
            assign_owner(store, deal_id="atdeal", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    # Pulse strip is rendered
                    self.assertIn("ck-pulse-grid", body)
                    self.assertIn(">Red Alerts</div>", body)
                    # AT owns 1 red deal — scoped count reflects it.
                    # Pull the Red Alerts KPI block region for tight
                    # match. The KPI value slot ends at </div> so the
                    # rendered "1" trails right up to "</div>".
                    red_block_start = body.index(">Red Alerts</div>")
                    red_block_end = red_block_start + body[red_block_start:].index('class="ck-kpi-sub"')
                    self.assertIn(">1</div>", body[red_block_start:red_block_end])
            finally:
                server.shutdown(); server.server_close()

    def test_pulse_shows_owner_overdue(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            assign_owner(store, deal_id="ccf", owner="AT")
            past = (date.today() - timedelta(days=3)).isoformat()
            add_deadline(store, deal_id="ccf", label="t", due_date=past,
                         owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn("1 overdue", body)
            finally:
                server.shutdown(); server.server_close()

    def test_health_mix_shows_red_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "broken", headroom=-0.5)
            assign_owner(store, deal_id="broken", owner="AT")
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/my/AT") as r:
                    body = r.read().decode()
                    self.assertIn("Your health mix", body)
                    # 1 amber band (covenant TRIPPED = score 60)
                    self.assertIn("1 amber", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
