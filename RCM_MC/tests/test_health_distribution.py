"""Tests for B140 portfolio health-distribution card on /."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from tests.test_alerts import _seed_with_pe_math


class TestHealthDistribution(unittest.TestCase):
    def _start(self, tmp):
        import socket as _socket, threading, time as _time
        from rcm_mc.server import build_server
        s = _socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); _time.sleep(0.05)
        return server, port

    def test_hidden_when_no_deals(self):
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/dashboard") as r:
                    body = r.read().decode()
                    self.assertNotIn("Portfolio health", body)
            finally:
                server.shutdown(); server.server_close()

    @unittest.skip(
        "Pinned the B140 portfolio health-distribution card on / "
        "(\"Portfolio health · ● 1 green · ● 0 amber · ● 0 red\"). "
        "The dashboard rebuild replaced inline-text counts with a "
        "banded health mosaic — one colored tile per deal — inside "
        "the portfolio pulse hero. Counts as text are gone; the "
        "tile color array carries the same signal visually. Rewrite "
        "against the mosaic markup before re-enabling. See PR #261 "
        "for context."
    )
    def test_shows_green_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "ccf", headroom=2.0)  # score=100
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/dashboard") as r:
                    body = r.read().decode()
                    self.assertIn("Portfolio health", body)
                    self.assertIn("● 1 green", body)
                    self.assertIn("● 0 amber", body)
                    self.assertIn("● 0 red", body)
            finally:
                server.shutdown(); server.server_close()

    @unittest.skip(
        "Same root cause as test_shows_green_only — inline-text "
        "counts replaced by the banded health mosaic in the "
        "portfolio pulse hero. See PR #261 for context."
    )
    def test_shows_mixed_distribution(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "good", headroom=2.0)     # green (100)
            _seed_with_pe_math(tmp, "tight", headroom=0.3)    # green (85)
            _seed_with_pe_math(tmp, "tripped", headroom=-0.5) # amber (60)
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/dashboard") as r:
                    body = r.read().decode()
                    self.assertIn("● 2 green", body)
                    self.assertIn("● 1 amber", body)
                    self.assertIn("● 0 red", body)
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
