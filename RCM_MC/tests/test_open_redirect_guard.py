"""Open-redirect guard — _safe_local_path closes the /\\ protocol-relative
hole the //-only checks missed.

Browsers treat /\\evil.com as //evil.com (off-site). The deal-context
return= and pipeline return_to= guards checked // but not /\; one helper now
backs both. Legit single-slash local paths must still pass.
"""
from __future__ import annotations

import unittest

from rcm_mc.server import RCMHandler


class SafeLocalPathTests(unittest.TestCase):
    def test_rejects_protocol_relative_variants(self):
        f = RCMHandler._safe_local_path
        for evil in ("//evil.com", "/\\evil.com", "\\\\evil.com",
                     "https://evil.com", "//evil.com/x"):
            self.assertEqual(f(evil, "/portfolio"), "/portfolio", evil)

    def test_rejects_header_splitting(self):
        f = RCMHandler._safe_local_path
        self.assertEqual(f("/x\nLocation: //evil", "/p"), "/p")
        self.assertEqual(f("/x\r\nSet-Cookie: y", "/p"), "/p")

    def test_preserves_legit_local_paths(self):
        f = RCMHandler._safe_local_path
        for ok in ("/deal/ccf", "/pipeline/rollup?ccns=1,2",
                   "/target-screener?view=saved&diff=7", "/"):
            self.assertEqual(f(ok, "/portfolio"), ok, ok)

    def test_empty_falls_back(self):
        self.assertEqual(RCMHandler._safe_local_path("", "/home"), "/home")
        self.assertEqual(RCMHandler._safe_local_path(None, "/home"), "/home")


if __name__ == "__main__":
    unittest.main()
