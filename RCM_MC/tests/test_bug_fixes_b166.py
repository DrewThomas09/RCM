"""b166 — close the multi-h1 set: 5 diligence pages + /library.

The 2026-05-29 audit walk found seven partner-facing pages rendering
with TWO `<h1>`s — direct violation of the CLAUDE.md One-H1 invariant:

  /library, /deals-library      (same renderer)
  /diligence/checklist
  /diligence/ic-packet
  /diligence/management
  /diligence/physician-eu
  /diligence/risk-workbench

Two distinct causes were unified by separate fixes:

1. `ck_editorial_head` is the "Universal strict Tier-1 5-block head"
   and emits an `<h1>`. Pages that also rendered a `ck_page_title`
   on top of it ended up with two h1s. Five diligence pages did this.
   Helper now accepts ``as_subhead: bool = False`` — when True, the
   heading renders as `<h2>` instead of `<h1>`. The five offenders
   pass ``as_subhead=True`` so the editorial deck slots under the
   page title as a section head (h2) without losing its editorial
   styling.

2. `deals_library_page` built a local ``page_title = ck_page_title(
   "Deals Library", ...)`` and threaded it into the ``prelude_html``
   of ``render_insights_page``. But `render_insights_page` already
   builds its OWN `<h1>` from its ``title=`` arg (the 5-block
   editorial intro). The two h1s rendered identically — same text,
   same eyebrow. Local builder removed; the KPI strip alone rides
   in the prelude.

Coverage here:

- ``ck_editorial_head`` helper: ``as_subhead=False`` preserves h1
  (53 callers unaffected); ``as_subhead=True`` switches to h2.
- End-to-end HTTP: each of the 6 routes (library + 5 diligence)
  returns exactly one `<h1>`.
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestEditorialHeadSubheadKwarg(unittest.TestCase):
    """Helper-level coverage of the new `as_subhead` kwarg."""

    def test_default_emits_h1(self):
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(
            eyebrow="SECTION",
            title="Headline",
            show_legend=False,
        )
        self.assertIn(">Headline</h1>", html)
        self.assertNotIn(">Headline</h2>", html)

    def test_as_subhead_true_emits_h2(self):
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(
            eyebrow="SECTION",
            title="Sub deck",
            show_legend=False,
            as_subhead=True,
        )
        self.assertIn(">Sub deck</h2>", html)
        self.assertNotIn(">Sub deck</h1>", html)

    def test_other_53_callers_unaffected(self):
        """Sanity guard: the default is preserved so the 48+ existing
        ck_editorial_head callers (not in the 5-diligence cluster)
        keep their h1 contract."""
        from rcm_mc.ui._chartis_kit import ck_editorial_head
        html = ck_editorial_head(eyebrow="X", title="Y")
        self.assertEqual(html.count("<h1"), 1)
        self.assertEqual(html.count("<h2"), 0)


class TestMultiH1RoutesNowSingleton(unittest.TestCase):
    """End-to-end walk: each of the 6 audit-flagged multi-h1 routes
    now renders with exactly ONE `<h1>` over real HTTP."""

    @classmethod
    def setUpClass(cls):
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.server import build_server
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db = os.path.join(cls.tmp.name, "t.db")
        PortfolioStore(cls.db)
        cls.port = _free_port()
        cls.server, _h = build_server(
            port=cls.port, host="127.0.0.1",
            db_path=cls.db, auth=None,
        )
        cls.thread = threading.Thread(
            target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.tmp.cleanup()

    def _h1_count(self, path: str) -> int:
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.port}{path}", timeout=10,
        ) as resp:
            self.assertEqual(resp.status, 200,
                             msg=f"{path} → {resp.status}")
            return resp.read().decode().count("<h1")

    def test_library_has_exactly_one_h1(self):
        self.assertEqual(self._h1_count("/library"), 1)

    def test_diligence_checklist_has_exactly_one_h1(self):
        self.assertEqual(self._h1_count("/diligence/checklist"), 1)

    def test_diligence_ic_packet_has_exactly_one_h1(self):
        self.assertEqual(self._h1_count("/diligence/ic-packet"), 1)

    def test_diligence_management_has_exactly_one_h1(self):
        self.assertEqual(self._h1_count("/diligence/management"), 1)

    def test_diligence_physician_eu_has_exactly_one_h1(self):
        self.assertEqual(self._h1_count("/diligence/physician-eu"), 1)

    def test_diligence_risk_workbench_has_exactly_one_h1(self):
        self.assertEqual(
            self._h1_count("/diligence/risk-workbench"), 1)


if __name__ == "__main__":
    unittest.main()
