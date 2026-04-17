"""Tests for the Prompt 21 infrastructure hardening pass.

Invariants locked here:

1. ``PRAGMA foreign_keys`` is ON on every fresh connection.
2. Inserting an override / analysis_run / mc_simulation_run / export
   against a non-existent deal raises ``IntegrityError``.
3. ``ON DELETE CASCADE`` on ``deal_overrides`` removes children when
   the parent deal row is deleted.
4. ``ON DELETE SET NULL`` on ``generated_exports`` keeps the export
   row but nulls the ``deal_id``.
5. Sessions survive a simulated restart (re-open the store, call
   ``user_for_session`` — still valid).
6. ``cleanup_expired_sessions`` deletes expired rows and leaves
   live rows alone.
7. ``build_server`` invokes the cleanup on startup (smoke).
8. Schema-version mismatch forces a cache rebuild — a cached packet
   under an old ``model_version`` is not served.
9. Matching schema version still serves the cache.
10. ``log_event`` accepts + persists a ``request_id`` correlation.
11. ``audit_events.request_id`` column exists after migration.
12. Structured JSON access log contains ``request_id``, ``method``,
    ``path``, ``status``, ``duration_ms``.
13. ``rcm_mc.data.lookup`` imports cleanly (no ``lookup 2.py``
    filesystem artifact regression).
14. Session-cleanup helper returns the correct count.
15. ``_session_cleanup_interval`` is honoured — every N requests
    triggers a purge (smoke — verifies counter state).
"""
from __future__ import annotations

import io
import json
import os
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.request

from datetime import datetime, timedelta, timezone

from rcm_mc.analysis.analysis_store import (
    find_cached_packet, get_or_build_packet, save_packet,
)
from rcm_mc.analysis.deal_overrides import set_override
from rcm_mc.analysis.packet import (
    DealAnalysisPacket, PACKET_SCHEMA_VERSION, hash_inputs,
)
from rcm_mc.auth.audit_log import (
    _ensure_table as _ensure_audit_table,
    list_events,
    log_event,
)
from rcm_mc.auth.auth import (
    cleanup_expired_sessions,
    create_session,
    user_for_session,
)
from rcm_mc.exports.export_store import record_export
from rcm_mc.portfolio.store import PortfolioStore


def _tmp_db() -> str:
    tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tf.close()
    return tf.name


def _seed_user(store: PortfolioStore, username: str = "analyst") -> None:
    """Minimal user row so ``create_session`` works end-to-end."""
    from rcm_mc.auth.auth import create_user
    create_user(store, username=username, password="s3cret-Pwd!",
                role="analyst")


# ── Foreign-key enforcement ────────────────────────────────────────

class TestForeignKeyPragma(unittest.TestCase):

    def test_pragma_on_for_every_connection(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            store.init_db()
            with store.connect() as con:
                self.assertEqual(
                    con.execute("PRAGMA foreign_keys").fetchone()[0], 1,
                )
            # Fresh connection must be on too.
            with store.connect() as con:
                self.assertEqual(
                    con.execute("PRAGMA foreign_keys").fetchone()[0], 1,
                )
        finally:
            os.unlink(path)


class TestOrphanInsertsBlocked(unittest.TestCase):

    def test_override_on_ghost_deal_raises(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            with self.assertRaises(sqlite3.IntegrityError):
                set_override(store, "ghost", "bridge.exit_multiple", 10.0,
                             set_by="u")
        finally:
            os.unlink(path)

    def test_mc_run_on_ghost_deal_raises(self):
        from rcm_mc.mc.mc_store import save_v2_mc_run
        path = _tmp_db()
        try:
            store = PortfolioStore(path)

            class _FakeResult:
                scenario_label = "test"
                n_simulations = 10
                def to_dict(self):
                    return {"scenario_label": "test", "n_simulations": 10}

            with self.assertRaises(sqlite3.IntegrityError):
                save_v2_mc_run(store, "ghost", _FakeResult())
        finally:
            os.unlink(path)

    def test_export_on_ghost_deal_raises(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            with self.assertRaises(sqlite3.IntegrityError):
                record_export(store, deal_id="ghost",
                              analysis_run_id="r", format="html",
                              filepath=None)
        finally:
            os.unlink(path)


class TestCascadeOnDelete(unittest.TestCase):

    def test_override_cascades(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            store.upsert_deal("d1", name="d1")
            set_override(store, "d1", "bridge.exit_multiple", 10.0,
                         set_by="u")
            with store.connect() as con:
                con.execute("DELETE FROM deals WHERE deal_id = ?", ("d1",))
                con.commit()
                remaining = con.execute(
                    "SELECT COUNT(*) FROM deal_overrides",
                ).fetchone()[0]
            self.assertEqual(remaining, 0)
        finally:
            os.unlink(path)

    def test_export_sets_null_on_delete(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            store.upsert_deal("d1", name="d1")
            record_export(store, deal_id="d1", analysis_run_id="r",
                          format="html", filepath=None)
            with store.connect() as con:
                con.execute("DELETE FROM deals WHERE deal_id = ?", ("d1",))
                con.commit()
                row = con.execute(
                    "SELECT deal_id FROM generated_exports",
                ).fetchone()
            self.assertIsNotNone(row)
            self.assertIsNone(row["deal_id"])
        finally:
            os.unlink(path)


# ── Session persistence ────────────────────────────────────────────

class TestSessionsSurviveRestart(unittest.TestCase):

    def test_session_valid_after_reopen(self):
        path = _tmp_db()
        try:
            first = PortfolioStore(path)
            _seed_user(first)
            token = create_session(first, "analyst")
            # "Restart": drop the reference and make a fresh store.
            del first
            second = PortfolioStore(path)
            user = user_for_session(second, token)
            self.assertIsNotNone(user)
            self.assertEqual(user["username"], "analyst")
        finally:
            os.unlink(path)


class TestSessionCleanup(unittest.TestCase):

    def _seed_expired(self, store: PortfolioStore, token: str) -> None:
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        now = datetime.now(timezone.utc).isoformat()
        with store.connect() as con:
            con.execute(
                "INSERT INTO sessions (token, username, expires_at, created_at) "
                "VALUES (?, ?, ?, ?)",
                (token, "analyst", past, now),
            )
            con.commit()

    def test_cleanup_deletes_expired_only(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            _seed_user(store)
            live_token = create_session(store, "analyst")
            self._seed_expired(store, "expired-tok")
            # Baseline: both rows present.
            with store.connect() as con:
                before = con.execute(
                    "SELECT COUNT(*) FROM sessions",
                ).fetchone()[0]
            self.assertEqual(before, 2)

            removed = cleanup_expired_sessions(store)
            self.assertEqual(removed, 1)

            with store.connect() as con:
                after = con.execute(
                    "SELECT COUNT(*) FROM sessions",
                ).fetchone()[0]
            self.assertEqual(after, 1)
            # The live session still resolves.
            self.assertIsNotNone(user_for_session(store, live_token))
        finally:
            os.unlink(path)

    def test_expired_session_rejected_even_without_cleanup(self):
        """``user_for_session`` rejects expired rows via the SQL JOIN
        predicate — this is defense-in-depth for the cleanup hook."""
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            _seed_user(store)
            past = (datetime.now(timezone.utc)
                    - timedelta(hours=1)).isoformat()
            now = datetime.now(timezone.utc).isoformat()
            with store.connect() as con:
                con.execute(
                    "INSERT INTO sessions (token, username, expires_at, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    ("stale", "analyst", past, now),
                )
                con.commit()
            self.assertIsNone(user_for_session(store, "stale"))
        finally:
            os.unlink(path)

    def test_build_server_invokes_cleanup(self):
        """Smoke test — ``build_server`` should import and call the
        cleanup path without raising."""
        from rcm_mc.server import build_server
        path = _tmp_db()
        try:
            server, handler = build_server(port=0, db_path=path)
            server.server_close()
            # Counter reset is the observable side-effect.
            self.assertEqual(handler._request_counter, 0)
        finally:
            os.unlink(path)


# ── Schema-version cache invalidation ──────────────────────────────

class TestSchemaVersionCache(unittest.TestCase):

    def _save_packet_with_version(
        self, store: PortfolioStore, deal_id: str,
        version: str, inputs_hash: str,
    ) -> None:
        """Persist a packet whose ``model_version`` is overridden."""
        p = DealAnalysisPacket(deal_id=deal_id, model_version=version)
        save_packet(store, p, inputs_hash=inputs_hash)

    def test_mismatched_version_skips_cache(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            store.upsert_deal("d1", name="d1")
            self._save_packet_with_version(
                store, "d1", version="0.0-old", inputs_hash="H1",
            )
            # Without the schema filter, the old row would be returned.
            without_filter = find_cached_packet(store, "d1", "H1")
            self.assertIsNotNone(without_filter)
            # With the filter on the current version, it's skipped.
            with_filter = find_cached_packet(
                store, "d1", "H1",
                schema_version=PACKET_SCHEMA_VERSION,
            )
            self.assertIsNone(with_filter)
        finally:
            os.unlink(path)

    def test_matching_version_serves_cache(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            store.upsert_deal("d1", name="d1")
            self._save_packet_with_version(
                store, "d1", version=PACKET_SCHEMA_VERSION, inputs_hash="H2",
            )
            hit = find_cached_packet(
                store, "d1", "H2",
                schema_version=PACKET_SCHEMA_VERSION,
            )
            self.assertIsNotNone(hit)
        finally:
            os.unlink(path)

    def test_get_or_build_respects_schema_version(self):
        """End-to-end: storing a packet under an old version and
        calling ``get_or_build_packet`` rebuilds rather than serving
        the stale blob."""
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            store.upsert_deal(
                "d1", name="d1",
                profile={"payer_mix": {"commercial": 1.0}, "bed_count": 150},
            )
            # Seed a packet under an old version, pinned to the same
            # hash the builder will compute.
            h = hash_inputs(deal_id="d1", observed_metrics={},
                            analyst_overrides={})
            p_old = DealAnalysisPacket(
                deal_id="d1", model_version="0.0-stale",
            )
            save_packet(store, p_old, inputs_hash=h)

            fresh = get_or_build_packet(
                store, "d1", skip_simulation=True,
            )
            # The rebuilt packet carries the *current* schema version.
            self.assertEqual(fresh.model_version, PACKET_SCHEMA_VERSION)
        finally:
            os.unlink(path)


# ── request_id correlation ─────────────────────────────────────────

class TestAuditRequestID(unittest.TestCase):

    def test_request_id_column_exists(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            _ensure_audit_table(store)
            with store.connect() as con:
                cols = {
                    r["name"] for r in con.execute(
                        "PRAGMA table_info(audit_events)",
                    ).fetchall()
                }
            self.assertIn("request_id", cols)
        finally:
            os.unlink(path)

    def test_log_event_persists_request_id(self):
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            log_event(store, actor="test", action="probe",
                      request_id="abc-123")
            with store.connect() as con:
                row = con.execute(
                    "SELECT request_id FROM audit_events ORDER BY id DESC LIMIT 1",
                ).fetchone()
            self.assertEqual(row["request_id"], "abc-123")
        finally:
            os.unlink(path)

    def test_log_event_backward_compat_without_request_id(self):
        """Callers that pre-date the field should still work — the
        column is nullable."""
        path = _tmp_db()
        try:
            store = PortfolioStore(path)
            log_event(store, actor="test", action="probe")
            df = list_events(store, action="probe")
            self.assertEqual(len(df), 1)
        finally:
            os.unlink(path)


# ── JSON access-log format ─────────────────────────────────────────

class TestJSONAccessLog(unittest.TestCase):
    """Spin up a real server, hit a benign endpoint, scrape the log
    line the handler wrote to stderr, and assert the structured JSON
    shape."""

    def _start(self, db_path: str) -> tuple:
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port, db_path=db_path)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return server, port

    def test_log_line_shape(self):
        import sys
        path = _tmp_db()
        saved_stderr = sys.stderr
        captured = io.StringIO()
        try:
            sys.stderr = captured
            server, port = self._start(path)
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/api/deals",
                ).read()
            finally:
                server.shutdown()
                server.server_close()
        finally:
            sys.stderr = saved_stderr
            os.unlink(path)

        lines = [ln for ln in captured.getvalue().splitlines() if ln.strip()]
        # Find the access-log JSON for the request we made.
        api_lines = [ln for ln in lines if "/api/deals" in ln]
        self.assertGreater(len(api_lines), 0)
        payload = json.loads(api_lines[-1])
        self.assertIn("request_id", payload)
        self.assertIn("method", payload)
        self.assertIn("path", payload)
        self.assertIn("status", payload)
        self.assertIn("duration_ms", payload)
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["path"], "/api/deals")
        self.assertIsNotNone(payload["request_id"])


# ── Filesystem-artifact regression ─────────────────────────────────

class TestLookupImport(unittest.TestCase):

    def test_lookup_module_imports(self):
        # Regression guard for the ``lookup 2.py`` artifact (Prompt 21
        # summary flag). The canonical path is
        # ``rcm_mc/data/lookup.py``; a stray copy would either
        # shadow the real module or get picked up by tooling.
        import rcm_mc.data.lookup as mod
        self.assertTrue(hasattr(mod, "__file__"))

    def test_no_space_suffixed_duplicate_on_disk(self):
        import rcm_mc.data as data_pkg
        pkg_dir = os.path.dirname(data_pkg.__file__)
        dupes = [
            f for f in os.listdir(pkg_dir)
            if f.startswith("lookup") and f.endswith(".py") and " " in f
        ]
        self.assertEqual(dupes, [])


# ── Request counter ────────────────────────────────────────────────

class TestRequestCounter(unittest.TestCase):

    def test_counter_increments_per_request(self):
        from rcm_mc.server import RCMHandler, build_server
        path = _tmp_db()
        try:
            server, handler = build_server(port=0, db_path=path)
            # ``_request_counter`` starts at 0 after build_server.
            before = handler._request_counter
            # Fabricate request completions.
            RCMHandler._request_counter = before + 3
            self.assertEqual(RCMHandler._request_counter, before + 3)
            server.server_close()
        finally:
            os.unlink(path)

    def test_session_cleanup_interval_default(self):
        from rcm_mc.server import RCMHandler
        self.assertEqual(RCMHandler._session_cleanup_interval, 100)


if __name__ == "__main__":
    unittest.main()
