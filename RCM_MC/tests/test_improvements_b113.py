"""Tests for B113: additional security headers.

SECURITY HEADERS:
 1. HTML responses include Referrer-Policy.
 2. HTML responses include Permissions-Policy.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.request


def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class TestSecurityHeaders(unittest.TestCase):

    def test_referrer_policy(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings",
                ) as r:
                    rp = r.headers.get("Referrer-Policy")
                    self.assertEqual(rp, "strict-origin-when-cross-origin")
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)

    def test_permissions_policy(self):
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            server, port = _start(tf.name)
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/settings",
                ) as r:
                    pp = r.headers.get("Permissions-Policy")
                    self.assertIsNotNone(pp)
                    self.assertIn("camera=()", pp)
                    self.assertIn("microphone=()", pp)
            finally:
                server.shutdown(); server.server_close()
        finally:
            os.unlink(tf.name)


if __name__ == "__main__":
    unittest.main()
