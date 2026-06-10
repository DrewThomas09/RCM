"""Deal-context slice 2 — the active-deal cookie pre-scopes diligence forms.

When a partner sets an active deal (P1, /deal-context sets
pedesk_active_deal_meta = {id,name,state,ccn}), the CIM Cross-Check and
Roll-Up forms should open pre-scoped to that deal's geography/CCN instead of
blank — but an explicit query param must always win, and the cookie must
never leak into export URLs.
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

from rcm_mc.server import build_server


def _meta_cookie(**kw) -> str:
    meta = {"id": "buh", "name": "Bigtown Health", "state": "TX",
            "ccn": "450076"}
    meta.update(kw)
    return "pedesk_active_deal_meta=" + urllib.parse.quote(
        json.dumps(meta, separators=(",", ":")))


class _PrefillServerBase(unittest.TestCase):
    """Fixture-only base — holds the shared open-mode server. Test classes
    subclass this so the parent's tests don't run twice."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        cls.port = s.getsockname()[1]; s.close()
        cls.server, _ = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=os.path.join(cls.tmp.name, "p.db"), auth=None)
        cls.t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.t.start(); time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close()
        cls.t.join(timeout=5); cls.tmp.cleanup()

    def _get(self, path, cookie=None):
        req = _u.Request(f"http://127.0.0.1:{self.port}{path}")
        if cookie:
            req.add_header("Cookie", cookie)
        with _u.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()


class DealContextPrefillTests(_PrefillServerBase):
    def test_cim_prefills_state_and_ccn_from_cookie(self):
        status, html = self._get("/diligence/cim-crosscheck",
                                  cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertIn("Pre-scoped to your active deal", html)
        self.assertIn("Bigtown Health", html)
        # state TX selected, ccn prefilled into the input value
        self.assertIn('value="TX" selected', html)
        self.assertIn('value="450076"', html)

    def test_cim_query_param_overrides_cookie(self):
        status, html = self._get(
            "/diligence/cim-crosscheck?state=CA", cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertIn('value="CA" selected', html)
        self.assertNotIn('value="TX" selected', html)

    def test_cim_no_cookie_no_prefill_note(self):
        status, html = self._get("/diligence/cim-crosscheck")
        self.assertEqual(status, 200)
        self.assertNotIn("Pre-scoped to your active deal", html)

    def test_rollup_seeds_ccn_basket_from_cookie(self):
        status, html = self._get("/pipeline/rollup", cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertIn("Seeded with your active deal", html)
        self.assertIn('value="450076"', html)

    def test_rollup_query_param_overrides_cookie(self):
        status, html = self._get(
            "/pipeline/rollup?ccns=330182,330304", cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertIn('value="330182,330304"', html)
        self.assertNotIn("Seeded with your active deal", html)

    def test_prefill_key_absent_from_export_urls(self):
        # _prefill_deal is internal — it must not ride into the memo/CSV
        # export links the results panel builds.
        status, html = self._get(
            "/diligence/cim-crosscheck?c_provider_count=400",
            cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertNotIn("_prefill_deal", html)

    def test_malformed_cookie_is_ignored(self):
        status, html = self._get(
            "/diligence/cim-crosscheck",
            cookie="pedesk_active_deal_meta=not%20json")
        self.assertEqual(status, 200)
        self.assertNotIn("Pre-scoped to your active deal", html)


class ScreenerStatePrefillTests(_PrefillServerBase):
    """Parity: a plain screener visit pre-scopes to the active deal's state
    (one-click-removable filter chip); explicit params and non-main views
    are never re-filtered."""

    def test_screener_main_prefills_state_chip(self):
        status, html = self._get("/target-screener", cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertIn('ts-fchip-val">TX<', html)     # active filter chip

    def test_screener_explicit_state_wins(self):
        status, html = self._get("/target-screener?state=CA",
                                 cookie=_meta_cookie())
        self.assertIn('ts-fchip-val">CA<', html)
        self.assertNotIn('ts-fchip-val">TX<', html)

    def test_saved_view_not_prefiltered(self):
        status, html = self._get("/target-screener?view=saved",
                                 cookie=_meta_cookie())
        self.assertEqual(status, 200)
        self.assertNotIn('ts-fchip-val">TX<', html)


if __name__ == "__main__":
    unittest.main()
