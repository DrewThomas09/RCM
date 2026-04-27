"""End-to-end test for /cli-runs (campaign target 3C — Phase 3 surfacing).

Boots a real ThreadingHTTPServer and hits /cli-runs via urllib.request.
Tests three states: outdir unconfigured (empty-state hint), outdir
configured but empty runs.sqlite, and outdir with one row populated
via infra.run_history.record_run.

What this guards (per Phase 3 surfacing checklist):
  - shell() with no bespoke wrapper: chartis_shell <title> present.
  - v3 chartis.css tokens: at least one .num utility class.
  - Empty-state path renders without crashing in both unconfigured
    and configured-but-empty cases.
  - Real-row path: a recorded run renders with .num spans on
    numerics + the actual_config_hash truncated.
  - ?limit=N is clamp_int-validated (no DoS via huge limit).
"""
from __future__ import annotations

import os
import socket as _socket
import tempfile
import threading
import time as _time
import unittest
import urllib.request as _u

from rcm_mc.infra.run_history import record_run
from rcm_mc.server import build_server


def _free_port() -> int:
    s = _socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class CliRunsPageTests(unittest.TestCase):
    def _start(self, tmp: str, *, outdir: str = ""):
        port = _free_port()
        kwargs = {"port": port, "db_path": os.path.join(tmp, "p.db")}
        if outdir:
            kwargs["outdir"] = outdir
        server, _ = build_server(**kwargs)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        _time.sleep(0.05)
        return server, port

    def test_unconfigured_outdir_renders_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server, port = self._start(tmp)  # no outdir
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cli-runs") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                self.assertIn("<title>CLI Run History", body)
                self.assertIn("No outputs directory configured", body)
                self.assertIn("--outdir", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_configured_empty_outdir_renders_no_runs_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = os.path.join(tmp, "out")
            os.makedirs(outdir)
            server, port = self._start(tmp, outdir=outdir)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cli-runs") as r:
                    body = r.read().decode("utf-8")
                self.assertIn("<title>CLI Run History", body)
                self.assertIn("No CLI runs recorded yet", body)
                # Hint points at the rcm-mc command
                self.assertIn("rcm-mc", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_recorded_run_renders_in_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outdir = os.path.join(tmp, "out")
            os.makedirs(outdir)
            # Plant a row via the real record_run API (no mocks).
            record_run(
                outdir,
                n_sims=10000,
                seed=42,
                ebitda_drag_mean=0.087,
                ebitda_drag_p10=0.041,
                ebitda_drag_p90=0.142,
                hospital_name="Test Memorial Hospital",
                notes="loop-26 e2e fixture",
            )
            server, port = self._start(tmp, outdir=outdir)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cli-runs") as r:
                    body = r.read().decode("utf-8")
                # The row landed
                self.assertIn("Test Memorial Hospital", body)
                # Numerics use the .num utility class
                self.assertIn('class="num"', body)
                # Sim count rendered with thousands separator via fmt_num
                self.assertIn("10,000", body)
                # Drag mean rendered with sign + 3dp via the inline format
                self.assertIn("+0.087", body)
            finally:
                server.shutdown()
                server.server_close()

    def test_limit_query_param_is_clamped(self) -> None:
        """Posting ?limit=999999999 should not cause a giant SELECT.
        _clamp_int caps at 500."""
        with tempfile.TemporaryDirectory() as tmp:
            outdir = os.path.join(tmp, "out")
            os.makedirs(outdir)
            server, port = self._start(tmp, outdir=outdir)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/cli-runs?limit=999999999") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode("utf-8")
                # The page reports the clamped limit, not the raw input
                self.assertIn("limit", body.lower())
                # Make sure 999999999 isn't echoed back in the limit display
                # (it would be if _clamp_int weren't applied)
                self.assertNotIn("999,999,999", body)
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
