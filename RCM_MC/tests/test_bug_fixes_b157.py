"""Regression test for B157: no literal newlines in HTML `title=` attrs."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.request as _u

from tests.test_alerts import _seed_with_pe_math


class TestTitleNoNewline(unittest.TestCase):
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

    def test_deal_page_health_title_is_single_line(self):
        """The health KPI-card `title` attribute must not contain
        raw newlines — they render inconsistently across browsers
        and break attribute parsing in edge cases.

        B161 strengthened: assert the actual bug-fix properties
        (no newlines, no carriage returns, tooltip is a single line)
        rather than the cosmetic separator choice. Also verify the
        tooltip still carries the component information partners rely
        on — a regression that dropped it entirely would otherwise
        pass a simple "no newline" check."""
        with tempfile.TemporaryDirectory() as tmp:
            # Seed a deal that will yield multiple health components
            # (covenant TRIPPED + variance miss = ≥2 deductions)
            from rcm_mc.pe.hold_tracking import record_quarterly_actuals
            store = _seed_with_pe_math(tmp, "ccf", headroom=-0.5)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 5e6}, plan={"ebitda": 12e6},
            )
            server, port = self._start(tmp)
            try:
                with _u.urlopen(f"http://127.0.0.1:{port}/deal/ccf") as r:
                    body = r.read().decode()
                import re
                m = re.search(
                    r'kpi-card" title="([^"]*)"', body,
                )
                self.assertIsNotNone(m)
                title_val = m.group(1)
                # Core bug-fix properties
                self.assertNotIn("\n", title_val)
                self.assertNotIn("\r", title_val)
                # Single-line: no invisible vertical whitespace at all
                self.assertEqual(len(title_val.splitlines()), 1)
                # Partner-visible content is preserved: at least the
                # covenant deduction must still show up in the tooltip
                self.assertIn("Covenant TRIPPED", title_val)
                # And multiple deductions should appear separately —
                # verify BOTH deductions are present, not just one
                # (guards against a regression that concatenated them
                # without a separator at all).
                self.assertIn("EBITDA miss", title_val)
                # Whatever separator is chosen, the two labels must
                # not be directly adjacent with no boundary.
                self.assertNotRegex(
                    title_val, r"TRIPPED\s*EBITDA miss",
                    "components must be separated, not concatenated",
                )
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
