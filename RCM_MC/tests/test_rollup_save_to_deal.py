"""Backlog #17 — persist a built roll-up scenario on a deal as a sourced note.

The POST recomputes the scenario server-side (form figures are never
trusted), requires an EXISTING deal (record_note would silently upsert a
junk deal otherwise), and the note states its filed-value basis + a link
back to the exact scenario. The save button only renders with an active
deal context — nothing honest to attach to otherwise.
"""
from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request as _u

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.server import build_server


def _meta_cookie() -> str:
    return "pedesk_active_deal_meta=" + urllib.parse.quote(json.dumps(
        {"id": "buh", "name": "Bigtown Health", "state": "TX",
         "ccn": "450076"}, separators=(",", ":")))


class _NoRedirect(_u.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class RollupSaveToDealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(cls.db)
        store.upsert_deal("buh", name="Bigtown Health",
                          profile={"state": "TX", "ccn": "450076"})
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]; s.close()
        cls.server, _ = build_server(port=cls.port, host="127.0.0.1",
                                     db_path=cls.db, auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.t.start(); time.sleep(0.2)
        cls.opener = _u.build_opener(_NoRedirect)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5); cls.tmp.cleanup()

    def _post(self, data: dict):
        req = _u.Request(
            f"http://127.0.0.1:{self.port}/api/rollup/save-to-deal",
            data=urllib.parse.urlencode(data).encode(), method="POST")
        try:
            resp = self.opener.open(req, timeout=30)
            return resp.status, resp.headers.get("Location", "")
        except _u.HTTPError as e:
            return e.code, e.headers.get("Location", "")

    def test_save_button_renders_only_with_active_deal(self):
        url = (f"http://127.0.0.1:{self.port}/pipeline/rollup"
               "?ccns=450076,450068")
        with _u.urlopen(url, timeout=30) as r:
            self.assertNotIn("Save scenario to", r.read().decode())
        req = _u.Request(url)
        req.add_header("Cookie", _meta_cookie())
        with _u.urlopen(req, timeout=30) as r:
            html = r.read().decode()
        self.assertIn("Save scenario to Bigtown Health", html)
        self.assertIn("/api/rollup/save-to-deal", html)

    def test_post_records_sourced_note_on_existing_deal(self):
        code, loc = self._post({"deal_id": "buh",
                                "ccns": "450076,450068,450358",
                                "ga_pct": "0.05"})
        self.assertIn(code, (302, 303))
        self.assertIn("saved_note=1", loc)
        from rcm_mc.deals.deal_notes import list_notes
        notes = list_notes(PortfolioStore(self.db), deal_id="buh")
        self.assertEqual(len(notes), 1)          # DataFrame, newest-first
        body = str(notes.iloc[0]["body"])
        self.assertIn("Roll-up scenario — 3 facilities", body)
        self.assertIn("CCN 450076", body)
        self.assertIn("filed HCRIS values", body)          # basis stated
        self.assertIn("ENTERED", body)                      # synergy labeled
        self.assertIn("/pipeline/rollup?ccns=450076", body)  # reopen link

    def test_unknown_deal_is_rejected_without_note(self):
        code, loc = self._post({"deal_id": "ghost-deal",
                                "ccns": "450076,450068"})
        self.assertIn(code, (302, 303))
        self.assertNotIn("saved_note=1", loc)
        # and crucially: no junk deal was upserted
        store = PortfolioStore(self.db)
        self.assertNotIn("ghost-deal",
                         set(store.list_deals().get("deal_id", [])))

    def test_fewer_than_two_ccns_rejected(self):
        code, loc = self._post({"deal_id": "buh", "ccns": "450076"})
        self.assertNotIn("saved_note=1", loc)


if __name__ == "__main__":
    unittest.main()
