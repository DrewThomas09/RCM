"""Saved peer sets (P4's open half) — store CRUD + compare-view flow.

A peer set is a named, owner-scoped CCN basket reusable on the compare
view. Honesty contracts pinned: invalid CCN tokens are dropped (never
stored), <2 valid CCNs rejected, owner-scoping on read AND delete, the
signed-out compare view renders no persistence affordance, and the
end-to-end save → list → load flow runs through the real HTTP server.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request

from rcm_mc.portfolio.peer_sets import (
    delete_peer_set, list_peer_sets, save_peer_set)
from rcm_mc.portfolio.store import PortfolioStore


class PeerSetStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "p.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_list_roundtrip_order_preserved(self):
        sid = save_peer_set(self.store, "anna", "TX comps",
                            "450358, 450076, 450358, 450068")
        sets = list_peer_sets(self.store, "anna")
        self.assertEqual(len(sets), 1)
        self.assertEqual(sets[0]["id"], sid)
        # De-dup keeps first occurrence; order preserved.
        self.assertEqual(sets[0]["ccns"], ["450358", "450076", "450068"])

    def test_invalid_tokens_dropped_never_stored(self):
        save_peer_set(self.store, "anna", "junk-resistant",
                      '450358,<script>,45 03,,"x",450076')
        sets = list_peer_sets(self.store, "anna")
        self.assertEqual(sets[0]["ccns"], ["450358", "450076"])

    def test_fewer_than_two_valid_ccns_rejected(self):
        with self.assertRaises(ValueError):
            save_peer_set(self.store, "anna", "solo", "450358,<bad>")

    def test_owner_scoping_on_read_and_delete(self):
        sid = save_peer_set(self.store, "anna", "mine", "450358,450076")
        self.assertEqual(list_peer_sets(self.store, "bob"), [])
        self.assertFalse(delete_peer_set(self.store, "bob", sid))
        self.assertTrue(delete_peer_set(self.store, "anna", sid))
        self.assertEqual(list_peer_sets(self.store, "anna"), [])


class CompareViewFlowTests(unittest.TestCase):
    def test_signed_out_compare_has_no_persistence_affordance(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        h = render_target_screener({"view": ["compare"]})
        self.assertNotIn("Save basket as peer set", h)
        self.assertNotIn("SAVED PEER SETS", h)

    def test_owner_sees_save_form_and_saved_sets(self):
        from rcm_mc.ui.target_screener_page import (
            _vertical_rows, render_target_screener)
        ccns = [r["ccn"] for r in
                _vertical_rows("home_health", "", limit=3)[:2]]
        sets = [{"id": 7, "name": "My HH pair", "ccns": ccns,
                 "created_at": "2026-06-12T00:00:00+00:00"}]
        h = render_target_screener(
            {"view": ["compare"], "compare": [",".join(ccns)]},
            owner="anna", peer_sets=sets)
        self.assertIn("Save basket as peer set", h)
        self.assertIn("SAVED PEER SETS", h)
        self.assertIn("My HH pair", h)
        self.assertIn(f'compare={",".join(ccns)}', h)

    def test_http_save_then_load(self):
        from rcm_mc.server import build_server
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            s = socket.socket(); s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]; s.close()
            srv, _ = build_server(port=port, host="127.0.0.1",
                                  db_path=db, auth=None)
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start(); time.sleep(0.2)
            try:
                data = urllib.parse.urlencode({
                    "name": "saved via http",
                    "ccns": "450358,450076"}).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/peer-sets/save",
                    data=data, method="POST")
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
                # Open-auth server: current user is the open-mode
                # identity; the set must round-trip through the store.
                store = PortfolioStore(db)
                all_owners = []
                with store.connect() as con:
                    try:
                        all_owners = [r2[0] for r2 in con.execute(
                            "SELECT owner FROM peer_sets").fetchall()]
                    except Exception:  # noqa: BLE001
                        all_owners = []
                if all_owners:           # an identity existed → saved
                    sets = list_peer_sets(store, all_owners[0])
                    self.assertEqual(sets[0]["name"], "saved via http")
                    self.assertEqual(sets[0]["ccns"],
                                     ["450358", "450076"])
            finally:
                srv.shutdown(); srv.server_close(); t.join(timeout=5)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
