"""Empty-state sweep — ?state=ZZ + empty-db walk (backlog #30).

Two honesty failure modes this guards:
  1. A state filter that matches NOTHING (ZZ is not a US state) must
     degrade to an explicit empty read — never a traceback, never a
     table of nan/None, never a silently-wrong unfiltered table.
  2. The same pages on an EMPTY database must render their empty state.

This is the mechanical half of the original "screenshot deck"
verification: the route walker's marker set (traceback / nan / None
leaks) plus an explicit emptiness-language check per page.
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.route_walker import walk  # noqa: E402

#: The state-filterable analytics pages a partner actually opens, each
#: walked with ?state=ZZ. Markers come from the walker (traceback,
#: nan/None leak); emptiness language is asserted separately where the
#: page filters its main table by state.
_STATE_ROUTES = [
    "/target-screener?state=ZZ",
    "/target-screener?state=ZZ&vertical=snf",
    "/market-data?state=ZZ",
    "/predictive-screener?state=ZZ",
    "/competitive-intel/450358?state=ZZ",
    "/ml-insights?state=ZZ",
    "/diligence/tam-sam?state=ZZ",
    "/diligence/cim-crosscheck?state=ZZ",
    "/pipeline/rollup?state=ZZ",
]

#: Phrases that count as an honest empty read. Any ONE suffices — pages
#: phrase emptiness differently ("No hospitals matched", "0 of 5,234",
#: "no facilities", an ck-empty block, …).
_EMPTY_MARKERS = (
    "No ", "no ", " 0 of ", "n=0", "ck-empty", "Nothing ", "nothing ",
    "not found", "empty",
)


class EmptyStateSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "empty.db"), auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever,
                                 daemon=True)
        cls.t.start()
        time.sleep(0.2)
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.t.join(timeout=5)
        cls.tmp.cleanup()

    def test_state_zz_pages_render_clean(self):
        rows = walk(self.base, _STATE_ROUTES)
        for r in rows:
            self.assertIn(r["status"], (200, 302, 303), r)
            self.assertEqual(r.get("traceback", 0), 0, r["route"])
            self.assertEqual(r.get("nan_leak", 0), 0, r["route"])
            self.assertEqual(r.get("none_leak", 0), 0, r["route"])

    def test_screener_zz_states_emptiness_not_unfiltered_table(self):
        import urllib.request
        with urllib.request.urlopen(
                f"{self.base}/target-screener?state=ZZ", timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        # The honest read: the results header counts ZERO matches (the
        # filter was applied, not silently dropped) and the page says so
        # in words. The cross-universe scale strip may still cite the
        # full universe sizes — that's context, not results.
        self.assertIn("0 Hospitals", body)
        self.assertTrue(any(m in body for m in _EMPTY_MARKERS),
                        "no emptiness language on /target-screener?state=ZZ")

    def test_empty_db_core_pages_render_clean(self):
        rows = walk(self.base, [
            "/portfolio", "/alerts", "/escalations", "/runs",
            "/scenarios", "/lp-update", "/my/nobody", "/notes",
        ])
        for r in rows:
            self.assertIn(r["status"], (200, 302, 303), r)
            self.assertEqual(r.get("traceback", 0), 0, r["route"])
            self.assertEqual(r.get("nan_leak", 0), 0, r["route"])
            self.assertEqual(r.get("none_leak", 0), 0, r["route"])


if __name__ == "__main__":
    unittest.main()
