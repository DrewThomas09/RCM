"""Quick-import entry-time range validation (PAGE_INVENTORY top fix).

The plausibility bounds existed only on DISPLAY: the form's HTML
min/max never bound a curl / JS-off submit, so an impossible 140%
denial rate landed silently as profile truth — and a comma-formatted
'180,000' was silently DROPPED by the float loop despite the form hint
promising commas are stripped. Both server-side behaviors are pinned
here, ungated (no v2-shell markers asserted).
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

from rcm_mc.portfolio.store import PortfolioStore


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class QuickImportValidationTests(unittest.TestCase):
    def test_quick_import_rejects_impossible_values_preserving_entries(self):
        # Entry-time range validation: HTML min/max never bound a curl /
        # JS-off submit, so a 140% denial rate landed silently as profile
        # truth. Physically impossible values now reject with the form
        # re-rendered and every typed value preserved; the deal is NOT
        # created.
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                data = urllib.parse.urlencode({
                    "deal_id": "bad_import",
                    "name": "Out Of Range Hospital",
                    "denial_rate": "140",        # impossible percentage
                    "days_in_ar": "48",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/quick-import",
                    data=data, method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    body = r.read().decode()
                self.assertIn("Out-of-range", body)
                self.assertIn("denial_rate = 140", body)
                # Typed values survive the bounce (prefill, no retyping).
                self.assertIn('value="bad_import"', body)
                self.assertIn('value="48"', body)
                store = PortfolioStore(tf.name)
                deals = store.list_deals()
                self.assertTrue(
                    deals.empty
                    or "bad_import" not in deals["deal_id"].values)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_quick_import_accepts_comma_formatted_numbers(self):
        # '180,000' used to ValueError inside the float loop and get
        # SILENTLY DROPPED (the form hint even promised "commas are
        # stripped on submit"). Commas now strip server-side.
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                data = urllib.parse.urlencode({
                    "deal_id": "comma_import",
                    "name": "Comma Hospital",
                    "claims_volume": "180,000",
                    "net_revenue": "386,000,000",
                }).encode()
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/quick-import",
                    data=data, method="POST",
                )
                with urllib.request.urlopen(req) as r:
                    self.assertEqual(r.status, 200)
                store = PortfolioStore(tf.name)
                deals = store.list_deals()   # flattens profile → columns
                row = deals[deals["deal_id"] == "comma_import"].iloc[0]
                self.assertEqual(float(row["claims_volume"]), 180000.0)
                self.assertEqual(float(row["net_revenue"]), 386000000.0)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)



if __name__ == "__main__":
    unittest.main()
