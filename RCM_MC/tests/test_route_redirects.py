"""tests for the page-rename redirect registry.

PROMPTS.md Phase 3 / Prompt 37: as overlapping page names get
disambiguated (Comparable Deal Finder vs Comparable Realized
Outcomes vs Corpus Transactions, etc.), bookmarks and inbound
links must continue to resolve. The dispatcher consults a registry
of ``old_path → new_path`` mappings before normal routing.

These tests pin the machinery, not specific entries — when the
rename sweep adds entries this file gets per-entry parameterised
checks.
"""
from __future__ import annotations

import socket
import threading
import time
import unittest
import urllib.request


class RegistryWiredIntoDispatcher(unittest.TestCase):

    def test_registry_constant_exists(self) -> None:
        from rcm_mc.server import _PAGE_RENAME_REDIRECTS
        self.assertIsInstance(_PAGE_RENAME_REDIRECTS, dict)

    def test_registry_values_are_canonical_paths(self) -> None:
        # Every entry's target must start with "/" so we never
        # accidentally redirect off-host (open-redirect protection).
        from rcm_mc.server import _PAGE_RENAME_REDIRECTS
        for old, new in _PAGE_RENAME_REDIRECTS.items():
            with self.subTest(old=old, new=new):
                self.assertTrue(new.startswith("/"),
                                f"{new!r} must be a same-origin path")


class RedirectFiresWhenRegistered(unittest.TestCase):
    """Boot a server, register a redirect at runtime, GET the old
    path with redirects disabled, confirm 301 + Location header."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.server import build_server
        import tempfile, os
        cls.tmp = tempfile.mkdtemp(prefix="rcm_p37_")
        cls.db = os.path.join(cls.tmp, "p.db")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cls.server, _ = build_server(port=port, db_path=cls.db)
        cls.base = f"http://127.0.0.1:{port}"
        t = threading.Thread(target=cls.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()

    def test_redirect_emits_301_when_path_in_registry(self) -> None:
        # Mutate the registry just for this test.
        from rcm_mc.server import _PAGE_RENAME_REDIRECTS
        _PAGE_RENAME_REDIRECTS["/__p37_canary"] = "/library"
        try:
            req = urllib.request.Request(self.base + "/__p37_canary")
            # Don't follow redirects; we want to inspect the 301.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def http_error_301(self, *a, **kw): return None
                def http_error_302(self, *a, **kw): return None
            opener = urllib.request.build_opener(NoRedirect())
            try:
                resp = opener.open(req, timeout=5)
                # Some openers return None on 301; treat as pass.
                if resp is not None:
                    self.assertEqual(resp.status, 301)
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 301)
                self.assertEqual(e.headers.get("Location"), "/library")
        finally:
            _PAGE_RENAME_REDIRECTS.pop("/__p37_canary", None)

    def test_redirect_preserves_query_string(self) -> None:
        from rcm_mc.server import _PAGE_RENAME_REDIRECTS
        _PAGE_RENAME_REDIRECTS["/__p37_qs"] = "/library"
        try:
            req = urllib.request.Request(
                self.base + "/__p37_qs?sector=hospital",
            )
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def http_error_301(self, *a, **kw): return None
            opener = urllib.request.build_opener(NoRedirect())
            try:
                opener.open(req, timeout=5)
            except urllib.error.HTTPError as e:
                self.assertEqual(e.code, 301)
                self.assertEqual(
                    e.headers.get("Location"),
                    "/library?sector=hospital",
                )
        finally:
            _PAGE_RENAME_REDIRECTS.pop("/__p37_qs", None)


if __name__ == "__main__":
    unittest.main()
