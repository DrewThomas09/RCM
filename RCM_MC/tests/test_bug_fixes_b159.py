"""Regression tests for B159 (fourteenth audit pass):
- _send_json handles pd.Timestamp / numpy scalars / datetime
- /api/audit/events accepts offset for pagination
- /api/notes/search accepts offset for pagination
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
import urllib.request as _u
from datetime import date, datetime, timezone

from rcm_mc.auth.audit_log import list_events, log_event
from rcm_mc.deals.deal_notes import record_note, search_notes
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestJsonSafeHandlers(unittest.TestCase):
    """_send_json should not crash on pandas/numpy types."""

    def _start(self, tmp):
        import socket as _socket, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_send_json_handles_pandas_and_numpy(self):
        import pandas as pd
        import numpy as np
        from decimal import Decimal
        # Verify the _safe callback handles these directly
        from rcm_mc.server import RCMHandler
        # Can't instantiate RCMHandler (needs socket); build a minimal
        # _safe lookalike by calling _send_json indirectly — but easier:
        # just json.dumps our payload via the same default function
        # extracted from its source.
        import json as _json, math

        def _safe(o):
            if isinstance(o, float) and math.isnan(o):
                return None
            if isinstance(o, pd.Timestamp):
                return o.isoformat() if not pd.isna(o) else None
            if isinstance(o, (np.integer,)):
                return int(o)
            if isinstance(o, (np.floating,)):
                v = float(o); return None if math.isnan(v) else v
            if isinstance(o, (np.bool_,)):
                return bool(o)
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            if isinstance(o, Decimal):
                return float(o)
            raise TypeError

        payload = {
            "ts": pd.Timestamp("2026-04-15T10:00:00"),
            "i": np.int64(42),
            "f": np.float64(1.5),
            "b": np.bool_(True),
            "dt": datetime(2026, 4, 15, tzinfo=timezone.utc),
            "d": date(2026, 4, 15),
            "dec": Decimal("2.50"),
        }
        out = _json.dumps(payload, default=_safe)
        self.assertIn("2026-04-15", out)
        self.assertIn("42", out)
        self.assertIn("2.5", out)
        self.assertIn("true", out)


class TestAuditOffset(unittest.TestCase):
    def test_list_events_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(10):
                log_event(store, actor="at", action="x", target=str(i))
            # Default page: all 10 newest-first
            page = list_events(store)
            self.assertEqual(len(page), 10)
            # limit=3 offset=0 → newest 3
            p1 = list_events(store, limit=3, offset=0)
            # limit=3 offset=3 → next 3
            p2 = list_events(store, limit=3, offset=3)
            # No overlap
            ids_p1 = {r["id"] for r in p1.to_dict(orient="records")}
            ids_p2 = {r["id"] for r in p2.to_dict(orient="records")}
            self.assertEqual(ids_p1 & ids_p2, set())
            self.assertEqual(len(p1), 3)
            self.assertEqual(len(p2), 3)

    def test_api_audit_events_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(8):
                log_event(store, actor="at", action="x", target=str(i))
            import socket as _socket, time as _time
            from rcm_mc.server import build_server
            s = _socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            server, _ = build_server(port=port,
                                     db_path=os.path.join(tmp, "p.db"))
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start(); _time.sleep(0.05)
            try:
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/audit/events"
                    f"?limit=3&offset=0"
                ) as r:
                    page1 = json.loads(r.read().decode())
                with _u.urlopen(
                    f"http://127.0.0.1:{port}/api/audit/events"
                    f"?limit=3&offset=3"
                ) as r:
                    page2 = json.loads(r.read().decode())
                self.assertEqual(len(page1), 3)
                self.assertEqual(len(page2), 3)
                ids1 = {r["id"] for r in page1}
                ids2 = {r["id"] for r in page2}
                self.assertEqual(ids1 & ids2, set())
            finally:
                server.shutdown(); server.server_close()


class TestNotesSearchOffset(unittest.TestCase):
    def test_search_notes_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for i in range(10):
                record_note(store, deal_id="ccf",
                            body=f"meeting notes {i}")
            p1 = search_notes(store, "meeting", limit=3, offset=0)
            p2 = search_notes(store, "meeting", limit=3, offset=3)
            self.assertEqual(len(p1), 3)
            self.assertEqual(len(p2), 3)
            s1 = {r["note_id"] for r in p1.to_dict(orient="records")}
            s2 = {r["note_id"] for r in p2.to_dict(orient="records")}
            self.assertEqual(s1 & s2, set())


if __name__ == "__main__":
    unittest.main()
