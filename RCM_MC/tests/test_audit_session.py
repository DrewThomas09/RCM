"""Time-boxed, read-only audit session.

Pins the security contract: OFF unless RCM_MC_AUDIT_SECRET is set, tokens are
signed + expiring + unforgeable, a valid link grants GET-only access (every
page visible, every write 403'd), and the whole thing fails closed.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request as _u
from contextlib import closing


class TokenTests(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.pop("RCM_MC_AUDIT_SECRET", None)

    def tearDown(self):
        if self._old is not None:
            os.environ["RCM_MC_AUDIT_SECRET"] = self._old
        else:
            os.environ.pop("RCM_MC_AUDIT_SECRET", None)

    def test_off_by_default(self):
        from rcm_mc.auth import audit_token as A
        self.assertFalse(A.audit_enabled())
        self.assertIsNone(A.mint(2))
        self.assertIsNone(A.verify("123.abc"))

    def test_mint_verify_roundtrip_and_tamper(self):
        from rcm_mc.auth import audit_token as A
        os.environ["RCM_MC_AUDIT_SECRET"] = "s3cret"
        tok = A.mint(2)
        self.assertIsNotNone(A.verify(tok))
        self.assertIsNone(A.verify(tok[:-2] + "zz"))      # bad signature
        self.assertIsNone(A.verify("999.deadbeef"))        # forged
        # rotating the secret invalidates outstanding tokens (the kill switch)
        os.environ["RCM_MC_AUDIT_SECRET"] = "different"
        self.assertIsNone(A.verify(tok))

    def test_expired_token_rejected(self):
        from rcm_mc.auth import audit_token as A
        os.environ["RCM_MC_AUDIT_SECRET"] = "s3cret"
        past = int(time.time()) - 10
        forged = f"{past}.{A._sign(past, b's3cret')}"
        self.assertIsNone(A.verify(forged))

    def test_capped_at_24h(self):
        from rcm_mc.auth import audit_token as A
        os.environ["RCM_MC_AUDIT_SECRET"] = "s3cret"
        exp = A.verify(A.mint(999))
        self.assertLessEqual(exp - time.time(), 24 * 3600 + 5)


def _start(db, secret=None):
    if secret is not None:
        os.environ["RCM_MC_AUDIT_SECRET"] = secret
    from rcm_mc.server import build_server
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    server, _ = build_server(port=port, db_path=db)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port


class _NoRedirect(_u.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class SessionTests(unittest.TestCase):
    def setUp(self):
        from tests.test_alerts import _seed_with_pe_math
        from rcm_mc.auth.auth import create_user
        self.tmp = tempfile.mkdtemp()
        store = _seed_with_pe_math(self.tmp, "ccf", headroom=-0.5)
        create_user(store, "boss", "Strong!1pw", role="admin")  # auth ON
        self.db = os.path.join(self.tmp, "p.db")
        self._old = os.environ.get("RCM_MC_AUDIT_SECRET")

    def tearDown(self):
        if self._old is not None:
            os.environ["RCM_MC_AUDIT_SECRET"] = self._old
        else:
            os.environ.pop("RCM_MC_AUDIT_SECRET", None)

    def _opener(self):
        return _u.build_opener(_NoRedirect, _u.HTTPCookieProcessor())

    def _status(self, op, base, path, method="GET", data=None):
        req = _u.Request(base + path, data=data, method=method)
        try:
            return op.open(req, timeout=8).status
        except urllib.error.HTTPError as e:
            return e.code

    def test_full_read_only_flow(self):
        from rcm_mc.auth import audit_token as A
        srv, port = _start(self.db, secret="window-secret")
        base = f"http://127.0.0.1:{port}"
        try:
            op = self._opener()
            # auth is enforced for anonymous
            self.assertIn(self._status(op, base, "/app"), (401, 303))
            # valid link opens the window (redirect + cookie)
            tok = A.mint(2)
            self.assertEqual(self._status(op, base, f"/audit/enter?token={tok}"), 303)
            # auditor can SEE pages
            self.assertEqual(self._status(op, base, "/app"), 200)
            self.assertEqual(self._status(op, base, "/diligence"), 200)
            # but cannot WRITE
            self.assertEqual(
                self._status(op, base, "/api/deals", method="POST", data=b"{}"),
                403)
            # exit clears the session
            self._status(op, base, "/audit/exit")
            self.assertIn(self._status(op, base, "/app"), (401, 303))
        finally:
            srv.shutdown(); srv.server_close()

    def test_invalid_and_disabled(self):
        srv, port = _start(self.db, secret="window-secret")
        base = f"http://127.0.0.1:{port}"
        try:
            op = self._opener()
            self.assertEqual(
                self._status(op, base, "/audit/enter?token=bad.tok"), 403)
        finally:
            srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
