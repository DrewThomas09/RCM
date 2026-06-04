"""b170 — two value-plan features collided on one SQLite table name.

Two unrelated features both created a table literally named
``value_creation_plans`` with ``CREATE TABLE IF NOT EXISTS`` but
*incompatible* schemas:

* ``pe.value_tracker`` — post-close value tracking: TEXT ``plan_json`` +
  ``total_planned_uplift`` + ``ccn`` + ``hospital_name``. Backs
  ``/value-tracker/<deal>`` and ``ml.fund_learning``.
* ``pe.value_creation_plan`` — the versioned, zlib-compressed value-creation
  plan *document*: BLOB ``plan_json`` + ``created_by`` + ``version``. Backs the
  hold dashboard, exit package and playbook.

Because of ``IF NOT EXISTS``, whichever ran first created the table and the
other's schema was silently dropped. Concretely: opening a deal's hold
dashboard (``/hold/<deal>`` → ``value_creation_plan.load_latest_plan`` →
creates the BLOB-schema table) and then its value tracker raised
``sqlite3.OperationalError: no such column: total_planned_uplift``. The order
matters, so it only bit when the two surfaces were viewed in one session —
exactly the demo / real walk-through path.

Fix: the value-tracker feature now owns ``value_tracker_plans``; the
value-creation-plan document keeps ``value_creation_plans``. This test seeds
*both* code paths against one DB in both orders and asserts neither is broken.
"""
from __future__ import annotations

import os
import tempfile
import unittest


class TestValuePlanTablesDoNotCollide(unittest.TestCase):
    def setUp(self):
        from rcm_mc.portfolio.store import PortfolioStore
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        self.store = PortfolioStore(self.db)
        self.store.init_db()
        # value_creation_plans FKs to deals(deal_id) ON DELETE CASCADE, so the
        # deal must exist before either feature writes a plan for it.
        self.store.upsert_deal("dealx", name="Hospital X")

    def tearDown(self):
        self.tmp.cleanup()

    def _freeze_tracker_plan(self):
        """value_tracker side: freeze a bridge as the tracked plan."""
        from rcm_mc.pe.value_tracker import freeze_bridge_as_plan, get_plan
        with self.store.connect() as con:
            freeze_bridge_as_plan(
                con, "dealx", "123456", "Hospital X",
                {"total_ebitda_impact": 4_200_000.0, "levers": {}},
            )
            con.commit()
        with self.store.connect() as con:
            return get_plan(con, "dealx")

    def _save_creation_plan(self):
        """value_creation_plan side: save + load the document (BLOB)."""
        from rcm_mc.pe.value_creation_plan import (
            ValueCreationPlan, load_latest_plan, save_plan,
        )
        plan = ValueCreationPlan(deal_id="dealx", initiatives=[],
                                 created_by="tester")
        save_plan(self.store, plan)
        return load_latest_plan(self.store, "dealx")

    def test_creation_plan_then_tracker(self):
        # Order that used to break the tracker: BLOB-schema table created first.
        self.assertIsNotNone(self._save_creation_plan())
        tracked = self._freeze_tracker_plan()
        self.assertIsNotNone(tracked)
        self.assertAlmostEqual(tracked["total_planned"], 4_200_000.0, places=2)

    def test_tracker_then_creation_plan(self):
        # Reverse order: tracker table first, then the document save/load.
        tracked = self._freeze_tracker_plan()
        self.assertIsNotNone(tracked)
        loaded = self._save_creation_plan()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.deal_id, "dealx")

    def test_both_tables_exist_with_their_own_columns(self):
        # Touch both features, then assert each table carries the column its
        # owner needs — i.e. neither schema was clobbered by the other.
        self._save_creation_plan()
        self._freeze_tracker_plan()
        with self.store.connect() as con:
            tracker_cols = {r[1] for r in con.execute(
                "PRAGMA table_info(value_tracker_plans)").fetchall()}
            doc_cols = {r[1] for r in con.execute(
                "PRAGMA table_info(value_creation_plans)").fetchall()}
        self.assertIn("total_planned_uplift", tracker_cols)
        self.assertIn("version", doc_cols)
        # And the two are genuinely distinct tables.
        self.assertNotEqual(tracker_cols, doc_cols)


class TestHoldThenValueTrackerRoute(unittest.TestCase):
    """End-to-end reproduction over HTTP: GET /hold/<deal> then
    /value-tracker/<deal> in one server must not 404 the tracker."""

    @classmethod
    def setUpClass(cls):
        import socket
        import threading
        import time
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.demo.kkr_demo import seed_kkr_demo
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(cls.db)
        store.init_db()
        seed_kkr_demo(store, run_dir=os.path.join(cls.tmp.name, "runs"))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        cls.srv, _ = build_server(port=cls.port, db_path=cls.db,
                                  host="127.0.0.1")
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.th.start()
        time.sleep(0.3)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.tmp.cleanup()

    def _code(self, path):
        import urllib.error
        import urllib.request
        try:
            with urllib.request.urlopen(self.base + path, timeout=25) as r:
                return r.getcode()
        except urllib.error.HTTPError as e:
            return e.code

    def test_hold_then_value_tracker_both_200(self):
        self.assertEqual(self._code("/hold/cotiviti"), 200)
        # Used to 404 ("no such column: total_planned_uplift").
        self.assertEqual(self._code("/value-tracker/cotiviti"), 200)


if __name__ == "__main__":
    unittest.main()
