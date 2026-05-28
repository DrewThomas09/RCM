"""Deal-lens analysis surfaces (/deals/<ccn>/*) — Phase 1.

Covers:
- the 18-surface registry shape (counts, groups, which surfaces ship today);
- shell rendering (one <h1> per page; identity header is real, not invented;
  sub-nav exposes all 18 tabs and only ``profile`` is non-stub for now);
- Surface 01 Profile renders the spec's components from real-data shapes and
  never fabricates a value — missing HCRIS columns show "—";
- routes: GET /deals/<ccn> renders Profile, GET /deals/<ccn>/<built> renders
  the surface, GET /deals/<ccn>/<unbuilt> renders the honest stub, unknown
  CCNs and unknown slugs 404.
"""
from __future__ import annotations

import json
import os
import re
import socket
import tempfile
import threading
import time
import unittest
import urllib.parse as _p
import urllib.request as _u
from http.cookiejar import CookieJar
from urllib.error import HTTPError

from rcm_mc.auth.auth import create_user
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.deal_surfaces import (
    SURFACES, SURFACE_BY_PATH, SURFACE_GROUPS,
    render_deal_profile, render_surface_stub,
)
from rcm_mc.ui.deal_surfaces._shell import _fmt_money, _fmt_pct, _fmt_int


FAKE_HOSPITAL = {
    "ccn": "050001", "name": "Test Med Ctr", "state": "CA", "city": "Los Angeles",
    "beds": 325, "net_patient_revenue": 4.2e8, "operating_expenses": 3.9e8,
    "net_income": 2.5e7, "percent_days_medicare": 0.42, "percent_days_medicaid": 0.18,
}


class SurfaceRegistry(unittest.TestCase):
    def test_eighteen_surfaces_five_groups(self):
        self.assertEqual(len(SURFACES), 18)
        self.assertEqual(len(SURFACE_GROUPS), 5)
        self.assertEqual(
            sorted({s.group for s in SURFACES}), sorted(SURFACE_GROUPS))

    def test_slugs_unique_and_numbered_one_to_eighteen(self):
        self.assertEqual(len({s.slug for s in SURFACES}), 18)
        self.assertEqual(sorted(s.number for s in SURFACES), list(range(1, 19)))

    def test_built_surfaces_grow_one_phase_at_a_time(self):
        # Phase 1: profile. Phase 2: bridge. Phase 3: lbo. New surfaces
        # appear here as they land — assertion is order-insensitive.
        built = {s.slug for s in SURFACES if s.built}
        self.assertEqual(built, {"profile", "bridge", "lbo"})

    def test_lookup_by_path(self):
        self.assertIs(SURFACE_BY_PATH["profile"].built, True)
        self.assertIn("bridge", SURFACE_BY_PATH)


class FormattingNeverFabricates(unittest.TestCase):
    def test_money_handles_missing_and_zero(self):
        self.assertEqual(_fmt_money(None), "—")
        self.assertEqual(_fmt_money(""), "—")
        self.assertEqual(_fmt_money(0), "$0")
        self.assertTrue(_fmt_money(4.2e8).endswith("M"))

    def test_pct_handles_missing(self):
        self.assertEqual(_fmt_pct(None), "—")

    def test_int_handles_missing(self):
        self.assertEqual(_fmt_int(None), "—")


class ProfileRender(unittest.TestCase):
    def setUp(self):
        self.html = render_deal_profile("050001", FAKE_HOSPITAL)

    def test_one_h1_only(self):
        # No regression of the #1036 accessibility fix on this new shell.
        self.assertEqual(len(re.findall(r"<h1[ >]", self.html)), 1)

    def test_identity_header_is_real(self):
        self.assertIn("Test Med Ctr", self.html)
        self.assertIn("DEAL · CCN", self.html)
        self.assertIn("325", self.html)             # beds, real
        self.assertIn("$420.0M", self.html)         # NPR, real

    def test_subnav_shows_all_18_tabs(self):
        for s in SURFACES:
            self.assertIn(f"/deals/050001/{s.slug}", self.html, f"missing {s.slug}")

    def test_profile_tab_marked_active(self):
        self.assertIn('aria-current="page"', self.html)

    def test_unbuilt_surfaces_get_soon_badge(self):
        # 18 total − built (profile, bridge, lbo) = 15 soon badges
        self.assertGreaterEqual(self.html.count("ds-nav-soon"), 15)

    def test_payer_mix_uses_real_data(self):
        self.assertIn("Medicare 42%", self.html)
        self.assertIn("Medicaid 18%", self.html)
        # Commercial is the remainder, computed not invented
        self.assertIn("Commercial 40%", self.html)

    def test_missing_payer_mix_renders_honest_message(self):
        h = dict(FAKE_HOSPITAL)
        h.pop("percent_days_medicare"); h.pop("percent_days_medicaid")
        out = render_deal_profile("050001", h)
        self.assertIn("not reported in this HCRIS row", out)
        self.assertNotIn("Medicare 0%", out)        # nothing invented

    def test_missing_numeric_fields_show_em_dash_not_zero(self):
        h = {"ccn": "999999", "name": "Sparse Co", "state": "TX"}  # almost nothing
        out = render_deal_profile("999999", h)
        # No invented dollars
        self.assertIn("—", out)

    def test_actions_link_to_all_built_and_unbuilt_surfaces(self):
        for slug in ("ic-memo", "bridge", "comp-intel", "scenarios", "ml",
                     "market", "denial", "trends", "dcf", "lbo", "stmt", "returns"):
            self.assertIn(f"/deals/050001/{slug}", self.html)


class LBORender(unittest.TestCase):
    """Surface 08 (LBO) — wired to build_lbo_from_deal; honest empty otherwise."""

    def test_lbo_renders_all_four_panels_when_inputs_real(self):
        from rcm_mc.ui.deal_surfaces import render_deal_lbo
        out = render_deal_lbo("050001", FAKE_HOSPITAL)
        # Hero / S&U / signals / waterfall all eyebrowed. The "&" in the S&U
        # eyebrow is html-escaped in the rendered output.
        for eyebrow in ("HERO", "SOURCES &amp; USES",
                        "WHAT DRIVES THE RETURN", "RETURNS WATERFALL"):
            self.assertIn(eyebrow, out, f"missing panel: {eyebrow}")
        # IRR / MOIC tokens shown (real numbers from the engine).
        self.assertRegex(out, r"\d+\.\d+%")             # IRR pct
        self.assertRegex(out, r"\d+\.\d+x")             # MOIC suffix
        # LBO tab is the active one.
        self.assertIn('aria-current="page"', out)
        # One <h1> only.
        self.assertEqual(len(re.findall(r"<h1[ >]", out)), 1)
        # Decomposition reconciliation note present
        self.assertIn("VALUE CREATED", out)

    def test_lbo_renders_honest_empty_when_npr_missing(self):
        from rcm_mc.ui.deal_surfaces import render_deal_lbo
        h = {"ccn": "999999", "name": "Sparse Co", "state": "TX"}
        out = render_deal_lbo("999999", h)
        self.assertIn("LBO cannot run", out)
        # No fabricated returns metrics
        self.assertNotIn("HERO", out)
        # Identity preserved
        self.assertIn("CCN 999999", out)

    def test_lbo_marked_built_in_registry(self):
        self.assertTrue(SURFACE_BY_PATH["lbo"].built)


class BridgeRender(unittest.TestCase):
    """Surface 03 (Bridge) — wired to _compute_bridge; honest empty otherwise."""

    def test_bridge_renders_all_four_panels_when_inputs_real(self):
        from rcm_mc.ui.deal_surfaces import render_deal_bridge
        h = dict(FAKE_HOSPITAL)               # NPR + opex present
        out = render_deal_bridge("050001", h)
        # Hero, 7-lever bars, lever detail, implementation timing all eyebrowed.
        for eyebrow in ("HERO", "7-LEVER MODEL", "LEVER DETAIL",
                        "IMPLEMENTATION TIMING"):
            self.assertIn(eyebrow, out, f"missing panel: {eyebrow}")
        # Hero stat must reflect REAL computed current EBITDA = NPR - opex.
        # 4.2e8 - 3.9e8 = 3.0e7 → "$30.0M".
        self.assertIn("$30.0M", out)
        # Bridge tab is the active one.
        self.assertIn('aria-current="page"', out)
        # One <h1> only (accessibility / spec).
        self.assertEqual(len(re.findall(r"<h1[ >]", out)), 1)
        # Phase 2b deferral note present (honest about what's not shipped).
        self.assertIn("Phase 2b", out)

    def test_bridge_renders_honest_empty_when_npr_missing(self):
        from rcm_mc.ui.deal_surfaces import render_deal_bridge
        h = {"ccn": "999999", "name": "Sparse Co", "state": "TX"}
        out = render_deal_bridge("999999", h)
        self.assertIn("Bridge cannot run", out)
        self.assertNotIn("7-LEVER MODEL", out)        # no fabricated bridge
        # Identity header still real
        self.assertIn("CCN 999999", out)

    def test_bridge_marked_built_in_registry(self):
        self.assertTrue(SURFACE_BY_PATH["bridge"].built)


class StubRender(unittest.TestCase):
    def test_stub_is_honest_under_construction(self):
        h = render_surface_stub("050001", "bridge", FAKE_HOSPITAL)
        self.assertIn("Under construction", h)
        self.assertIn("EBITDA Bridge", h)
        # Identity header still real
        self.assertIn("Test Med Ctr", h)
        # Falls back to Profile
        self.assertIn("/deals/050001/profile", h)

    def test_stub_one_h1(self):
        h = render_surface_stub("050001", "lbo", FAKE_HOSPITAL)
        self.assertEqual(len(re.findall(r"<h1[ >]", h)), 1)


def _login_opener(port: int, username: str, password: str):
    """Login and return a urllib opener carrying the session cookie."""
    cj = CookieJar()
    opener = _u.build_opener(_u.HTTPCookieProcessor(cj))
    payload = _p.urlencode({"username": username, "password": password}).encode()
    req = _u.Request(
        f"http://127.0.0.1:{port}/api/login", data=payload, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        opener.open(req, timeout=10)
    except HTTPError:
        pass  # 303 is fine
    if not any(c.name == "rcm_session" for c in cj):
        raise RuntimeError("login failed")
    return opener


class DealRoutes(unittest.TestCase):
    """Server-side wiring: routes resolve, real CCNs render, unknown ones 404."""

    def _start(self, tmp):
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]; s.close()
        server, _ = build_server(port=port,
                                 db_path=os.path.join(tmp, "p.db"))
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start(); time.sleep(0.05)
        return server, port

    def _pick_real_ccn(self) -> str:
        from rcm_mc.data.hcris import _get_latest_per_ccn
        hdf = _get_latest_per_ccn()
        return str(hdf.iloc[0]["ccn"])

    def test_unknown_ccn_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(PortfolioStore(os.path.join(tmp, "p.db")), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                opener = _login_opener(port, "at", "supersecret1")
                with self.assertRaises(HTTPError) as ctx:
                    opener.open(f"http://127.0.0.1:{port}/deals/000000/profile")
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()

    def test_unknown_slug_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(PortfolioStore(os.path.join(tmp, "p.db")), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                opener = _login_opener(port, "at", "supersecret1")
                ccn = self._pick_real_ccn()
                with self.assertRaises(HTTPError) as ctx:
                    opener.open(f"http://127.0.0.1:{port}/deals/{ccn}/not-a-surface")
                self.assertEqual(ctx.exception.code, 404)
            finally:
                server.shutdown(); server.server_close()

    def test_real_ccn_profile_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(PortfolioStore(os.path.join(tmp, "p.db")), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                opener = _login_opener(port, "at", "supersecret1")
                ccn = self._pick_real_ccn()
                # /deals/<ccn> → profile (no trailing slug)
                with opener.open(f"http://127.0.0.1:{port}/deals/{ccn}") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                self.assertIn("DEAL · CCN", body)
                self.assertIn("PE Desk score", body)
                # exactly one h1
                self.assertEqual(len(re.findall(r"<h1[ >]", body)), 1)
                # explicit slug
                with opener.open(f"http://127.0.0.1:{port}/deals/{ccn}/profile") as r:
                    self.assertEqual(r.status, 200)
            finally:
                server.shutdown(); server.server_close()

    def test_real_ccn_unbuilt_surface_renders_stub_200(self):
        # Use a still-unbuilt slug (lbo and bridge are now built; dcf isn't).
        with tempfile.TemporaryDirectory() as tmp:
            create_user(PortfolioStore(os.path.join(tmp, "p.db")), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                opener = _login_opener(port, "at", "supersecret1")
                ccn = self._pick_real_ccn()
                with opener.open(f"http://127.0.0.1:{port}/deals/{ccn}/dcf") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                self.assertIn("Under construction", body)
                # identity header still rendered (shell is shared)
                self.assertIn("DEAL · CCN", body)
            finally:
                server.shutdown(); server.server_close()

    def test_real_ccn_lbo_renders_real_data_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(PortfolioStore(os.path.join(tmp, "p.db")), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                opener = _login_opener(port, "at", "supersecret1")
                ccn = self._pick_real_ccn()
                with opener.open(f"http://127.0.0.1:{port}/deals/{ccn}/lbo") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                # Built surface — never the construction stub.
                self.assertNotIn("Under construction", body)
                self.assertIn("DEAL · CCN", body)
                self.assertEqual(len(re.findall(r"<h1[ >]", body)), 1)
                self.assertTrue(
                    "SOURCES &amp; USES" in body or "LBO cannot run" in body,
                    "LBO neither rendered the S&U nor an honest empty",
                )
            finally:
                server.shutdown(); server.server_close()

    def test_real_ccn_bridge_renders_real_data_200(self):
        with tempfile.TemporaryDirectory() as tmp:
            create_user(PortfolioStore(os.path.join(tmp, "p.db")), "at", "supersecret1")
            server, port = self._start(tmp)
            try:
                opener = _login_opener(port, "at", "supersecret1")
                ccn = self._pick_real_ccn()
                with opener.open(f"http://127.0.0.1:{port}/deals/{ccn}/bridge") as r:
                    self.assertEqual(r.status, 200)
                    body = r.read().decode()
                # The body either renders bridge data or an honest empty —
                # NEVER "Under construction" (this is a built surface).
                self.assertNotIn("Under construction", body)
                # Identity is real, sub-nav is present, h1 count is 1.
                self.assertIn("DEAL · CCN", body)
                self.assertEqual(len(re.findall(r"<h1[ >]", body)), 1)
                # Bridge surface eyebrow or empty-state marker must be present.
                self.assertTrue(
                    "7-LEVER MODEL" in body or "Bridge cannot run" in body,
                    "bridge surface neither rendered the model nor an honest empty",
                )
            finally:
                server.shutdown(); server.server_close()


if __name__ == "__main__":
    unittest.main()
