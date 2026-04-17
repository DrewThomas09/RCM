"""Tests for portfolio alert evaluators (Brick 101)."""
from __future__ import annotations

import json
import os
import tempfile
import time
import unittest

from rcm_mc.alerts.alerts import active_count, evaluate_all
from rcm_mc.deals.deal_notes import record_note  # noqa — exercises shared imports
from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import register_snapshot


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


def _seed_with_pe_math(tmp: str, deal_id: str, *,
                       headroom: float = 1.1, concerning: int = 0):
    """Seed a deal with full PE artifacts so covenant evaluator fires."""
    run = os.path.join(tmp, deal_id + "_run")
    os.makedirs(run, exist_ok=True)
    with open(os.path.join(run, "pe_bridge.json"), "w") as f:
        json.dump({"entry_ebitda": 50e6, "entry_ev": 450e6,
                   "entry_multiple": 9.0, "exit_multiple": 10.0,
                   "hold_years": 5.0}, f)
    with open(os.path.join(run, "pe_returns.json"), "w") as f:
        json.dump({"moic": 2.5, "irr": 0.20}, f)
    with open(os.path.join(run, "pe_covenant.json"), "w") as f:
        json.dump({"actual_leverage": 5.4,
                   "covenant_headroom_turns": headroom}, f)
    if concerning:
        import pandas as _pd
        _pd.DataFrame({"severity": ["concerning"] * concerning + ["neutral"]}).to_csv(
            os.path.join(run, "trend_signals.csv"), index=False,
        )
    store = _store(tmp)
    register_snapshot(store, deal_id, "hold", run_dir=run)
    return store


class TestEvaluators(unittest.TestCase):
    def test_empty_portfolio_no_alerts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(evaluate_all(_store(tmp)), [])

    def test_covenant_tripped_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            alerts = evaluate_all(store)
            tripped = [a for a in alerts if a.kind == "covenant_tripped"]
            self.assertEqual(len(tripped), 1)
            self.assertEqual(tripped[0].severity, "red")
            self.assertEqual(tripped[0].deal_id, "ccf")

    def test_covenant_tight_amber(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=0.3)
            alerts = evaluate_all(store)
            tight = [a for a in alerts if a.kind == "covenant_tight"]
            self.assertEqual(len(tight), 1)
            self.assertEqual(tight[0].severity, "amber")

    def test_covenant_safe_no_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=2.0)
            alerts = evaluate_all(store)
            self.assertFalse(any(a.kind.startswith("covenant_") for a in alerts))

    def test_variance_miss_red(self):
        """EBITDA missing plan by 15%+ → red."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 8e6},
                                     plan={"ebitda": 12e6})
            alerts = evaluate_all(store)
            misses = [a for a in alerts if a.kind == "variance_miss_red"]
            self.assertEqual(len(misses), 1)
            self.assertIn("variance", misses[0].title.lower())

    def test_variance_miss_amber_for_5_to_10pct_miss(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 11.4e6},
                                     plan={"ebitda": 12e6})
            alerts = evaluate_all(store)
            ambers = [a for a in alerts if a.kind == "variance_miss_amber"]
            self.assertEqual(len(ambers), 1)

    def test_variance_on_track_no_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf")
            record_quarterly_actuals(store, "ccf", "2026Q1",
                                     actuals={"ebitda": 12e6},
                                     plan={"ebitda": 12e6})
            alerts = evaluate_all(store)
            self.assertFalse(any(a.kind.startswith("variance_miss") for a in alerts))

    def test_concerning_cluster(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", concerning=4)
            alerts = evaluate_all(store)
            clusters = [a for a in alerts if a.kind == "concerning_cluster"]
            self.assertEqual(len(clusters), 1)
            self.assertEqual(clusters[0].severity, "amber")

    def test_concerning_below_threshold_no_alert(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", concerning=2)
            self.assertFalse(any(
                a.kind == "concerning_cluster" for a in evaluate_all(store)
            ))

    def test_stage_regress(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            register_snapshot(store, "ccf", "loi")
            time.sleep(0.05)
            register_snapshot(store, "ccf", "ioi")  # backward
            alerts = evaluate_all(store)
            regress = [a for a in alerts if a.kind == "stage_regress"]
            self.assertEqual(len(regress), 1)
            self.assertEqual(regress[0].severity, "amber")

    def test_no_regress_for_canonical_forward_motion(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for stage in ("ioi", "loi", "spa", "closed", "hold"):
                register_snapshot(store, "ccf", stage)
                time.sleep(0.05)
            self.assertFalse(any(a.kind == "stage_regress"
                                 for a in evaluate_all(store)))

    def test_active_count_excludes_info(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_with_pe_math(tmp, "ccf", headroom=0.3)
            self.assertEqual(active_count(store), 1)


class TestAlertsHttp(unittest.TestCase):
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

    def test_alerts_page_empty_state(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn("No active alerts", body)
            finally:
                server.shutdown(); server.server_close()

    def test_alerts_page_with_tripped_covenant(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/alerts") as r:
                    body = r.read().decode()
                    self.assertIn("RED", body)
                    self.assertIn("Covenant TRIPPED", body)
                    self.assertIn('href="/deal/ccf"', body)
            finally:
                server.shutdown(); server.server_close()

    def test_api_alerts_active_returns_list(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/alerts/active"
                ) as r:
                    data = json.loads(r.read().decode())
                    self.assertIsInstance(data, list)
                    self.assertEqual(data[0]["severity"], "red")
                    self.assertEqual(data[0]["deal_id"], "ccf")
            finally:
                server.shutdown(); server.server_close()

    def test_dashboard_has_alerts_badge_skeleton(self):
        import urllib.request as _u
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/") as r:
                    body = r.read().decode()
                    self.assertIn('id="rcm-alert-badge"', body)
                    self.assertIn("/api/alerts/active", body)
            finally:
                server.shutdown(); server.server_close()
