"""Sub-nav integrity — every tab on the desk must open.

The top-nav sections and their sub-nav rails are the desk's primary
navigation; a tab that 404s or 500s is the most visible kind of
breakage a partner can hit. This walks every href in _CORPUS_NAV and
_SUB_NAV against a real server (the e2e pattern from CLAUDE.md) so a
nav entry can't be added — or a route renamed — without the tab
staying openable.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SubNavIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.port = _free_port()
        from rcm_mc.server import build_server
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "t.db"), auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _status(self, path: str) -> int:
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=15,
            ) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code

    def test_every_top_nav_tab_opens(self):
        from rcm_mc.ui._chartis_kit import _CORPUS_NAV
        bad = []
        for entry in _CORPUS_NAV:
            status = self._status(entry["href"])
            if status != 200:
                bad.append((entry["label"], entry["href"], status))
        self.assertEqual(bad, [],
                         f"Top-nav tabs that don't open: {bad}")

    def test_every_sub_nav_link_opens(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        bad = []
        for section, entries in _SUB_NAV.items():
            for entry in entries:
                status = self._status(entry["href"])
                if status != 200:
                    bad.append((section, entry["label"],
                                entry["href"], status))
        self.assertEqual(bad, [],
                         f"Sub-nav links that don't open: {bad}")


if __name__ == "__main__":
    unittest.main()
