"""Federated /search — the find-anything box (user-reported).

Typing "hospital" into the topbar search rendered nothing: /search only
scanned portfolio deals + notes. It now spans the HCRIS hospital universe
(hits open the full X-Ray profile), the tools catalogue, the public deals
corpus (hits open Deal Search scoped to the query), and the portfolio.
"""
from __future__ import annotations

import os
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request


class FederatedSearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls._tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls._tmp.name, "s.db")
        cls.server, _ = build_server(port=0, db_path=db, host="127.0.0.1")
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever,
                         daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._tmp.cleanup()

    def _search(self, q: str) -> str:
        url = (f"http://127.0.0.1:{self.port}/search?"
               + urllib.parse.urlencode({"q": q}))
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.read().decode()

    def test_hospital_query_returns_hospital_hits(self):
        # The user's exact repro: "hospital" must return hospital results,
        # each linking to the facility's full X-Ray profile.
        html = self._search("hospital")
        self.assertIn("<h2>Hospitals</h2>", html)
        self.assertIn("full X-Ray profile", html)
        self.assertIn("/diligence/hcris-xray?ccn=", html)

    def test_named_hospital_resolves(self):
        html = self._search("stanford")
        self.assertIn("/diligence/hcris-xray?ccn=", html)

    def test_tool_query_returns_tool_hits(self):
        html = self._search("bridge")
        self.assertIn("Tools", html)
        self.assertIn("/diligence/bridge-audit", html)

    def test_sponsor_query_hits_market_deals(self):
        html = self._search("kkr")
        self.assertIn("Market deals", html)
        self.assertIn("open in Deal Search", html)

    def test_gibberish_renders_honest_empty(self):
        html = self._search("zzqxv999")
        self.assertIn("No matches", html)

    def test_search_never_500s_on_hostile_input(self):
        for q in ("<script>", "%", "'; DROP TABLE--", "a" * 500):
            html = self._search(q)
            self.assertIn("<html", html)


if __name__ == "__main__":
    unittest.main()
