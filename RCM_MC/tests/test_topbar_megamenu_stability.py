"""Regression — topbar scroll + mega-menu hover stability.

Covers the fix/topbar-megamenu-stability hardening:
  - the topbar has exactly ONE positioning mode (sticky top:0), with no
    competing position:fixed or transform that would jitter on scroll;
  - the mega-menu JS implements hover-intent open + grace-period close, keeps
    at most one panel open, and closes on Escape / outside-click / focus-out;
  - the topbar still exposes Guide / Search / avatar controls;
  - /login renders no topbar element.
"""
import re
import unittest

from rcm_mc.ui._chartis_kit import chartis_shell, _NAV_MENU_JS
from rcm_mc.ui.chartis.login_page import render_login_page


def _app_shell() -> str:
    return chartis_shell("<p>body</p>", "App", active_nav="/app")


class TestTopbarPositioning(unittest.TestCase):
    def test_topbar_is_sticky_top_zero(self):
        html = _app_shell()
        self.assertIn("position:sticky; top:0", html)

    def test_topbar_has_single_positioning_mode(self):
        """The .ck-topbar rule must not declare position:fixed nor a transform
        — either would conflict with sticky and cause scroll jitter."""
        html = _app_shell()
        # Isolate the .ck-topbar { ... } declaration block.
        m = re.search(r"\.ck-topbar\s*\{[^}]*\}", html)
        self.assertIsNotNone(m, "no .ck-topbar rule found")
        block = m.group(0)
        self.assertIn("position:sticky", block)
        self.assertNotIn("position:fixed", block)
        self.assertNotIn("transform:", block)


class TestTopbarRowDoesNotWrap(unittest.TestCase):
    """Regression: at narrower-than-fullscreen widths the nav links wrapped to
    a row above the wordmark and were clipped by the fixed-height bar. The row
    must stay single-line (nowrap) and shrink gracefully."""

    def test_inner_row_is_nowrap(self):
        html = _app_shell()
        m = re.search(r"\.ck-topbar-inner\s*\{[^}]*\}", html)
        self.assertIsNotNone(m)
        block = m.group(0)
        self.assertIn("flex-wrap:nowrap", block)
        # min-height (not a hard height) so a grown child cannot clip the top.
        # Compact bar (2026-05-27: shrunk from 76 → 58px per "too massive").
        self.assertIn("min-height:58px", block)

    def test_nav_can_shrink(self):
        html = _app_shell()
        m = re.search(r"\.ck-nav\s*\{[^}]*\}", html)
        self.assertIsNotNone(m)
        self.assertIn("min-width:0", m.group(0))

    def test_responsive_padding_steps_present(self):
        # Nav-link padding tightens below fullscreen so 7 links + wordmark +
        # right rail fit without wrapping.
        html = _app_shell()
        self.assertIn("@media (max-width:1480px)", html)
        self.assertIn("@media (max-width:1320px)", html)


class TestMegaMenuHardening(unittest.TestCase):
    def test_hover_intent_open_delay(self):
        self.assertIn("OPEN_DELAY", _NAV_MENU_JS)
        self.assertRegex(_NAV_MENU_JS, r"OPEN_DELAY\s*=\s*\d+")

    def test_grace_period_close(self):
        self.assertIn("CLOSE_DELAY", _NAV_MENU_JS)
        # Close happens on a timer, not instantly.
        self.assertIn("setTimeout(closeAll", _NAV_MENU_JS)
        m = re.search(r"CLOSE_DELAY\s*=\s*(\d+)", _NAV_MENU_JS)
        self.assertIsNotNone(m)
        self.assertGreaterEqual(int(m.group(1)), 150)

    def test_reentering_cancels_close(self):
        self.assertIn("cancelClose", _NAV_MENU_JS)

    def test_one_menu_open_max(self):
        # openOnly removes is-open from every other group.
        self.assertIn("function openOnly", _NAV_MENU_JS)
        self.assertIn("x.classList.remove('is-open')", _NAV_MENU_JS)

    def test_escape_closes(self):
        self.assertIn("'Escape'", _NAV_MENU_JS)
        self.assertIn("closeAll", _NAV_MENU_JS)

    def test_outside_click_closes(self):
        self.assertIn("pointerdown", _NAV_MENU_JS)
        self.assertIn(".ck-nav-group", _NAV_MENU_JS)

    def test_focus_out_closes(self):
        self.assertIn("focusout", _NAV_MENU_JS)

    def test_coarse_pointer_tap_toggle(self):
        # Touch/trackpad (hover:none) gets tap-to-open instead of navigate.
        self.assertIn("hover: none", _NAV_MENU_JS)
        self.assertIn("preventDefault", _NAV_MENU_JS)

    def test_hover_bridge_present(self):
        self.assertIn(".ck-nav-menu::before", _app_shell())


class TestNavLinksAreLive(unittest.TestCase):
    """Every route reachable from the topbar — nav targets, mega-menu leaves,
    'All X tools' catalogs, and section landings — must render a live 200. A
    nav link that 404s or redirects is a broken click (this caught the Pipeline
    'Manual' leaf → /new-deal/manual, a form-POST target that 303'd)."""

    def test_every_nav_reachable_route_returns_200(self):
        import os, socket, tempfile, threading, time
        import urllib.error as _ue
        import urllib.request as _u
        from rcm_mc.server import build_server
        from rcm_mc.ui._chartis_kit import (
            _CORPUS_NAV, _SECTION_FEATURE, _ranked_subnav_items,
        )
        routes = set()
        for it in _CORPUS_NAV:
            routes.add(it["href"])
        for sect in ("source", "pipeline", "diligence", "library",
                     "research", "portfolio"):
            routes.add(f"/best/{sect}")
            top, _ = _ranked_subnav_items(sect)
            for t in top:
                routes.add(t["href"])
        for f in _SECTION_FEATURE.values():
            if f.get("href"):
                routes.add(f["href"])

        class _NoRedirect(_u.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        opener = _u.build_opener(_NoRedirect)
        sk = socket.socket(); sk.bind(("127.0.0.1", 0))
        port = sk.getsockname()[1]; sk.close()
        server, _ = build_server(
            port=port, db_path=os.path.join(tempfile.mkdtemp(), "p.db"))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        time.sleep(0.3)
        bad = {}
        try:
            for r in sorted(routes):
                try:
                    code = opener.open(
                        _u.Request(f"http://127.0.0.1:{port}{r}"), timeout=20
                    ).status
                    if code != 200:
                        bad[r] = code
                except _ue.HTTPError as e:
                    bad[r] = e.code
                except Exception as e:  # noqa: BLE001
                    bad[r] = f"ERR:{type(e).__name__}"
        finally:
            server.shutdown(); server.server_close()
        self.assertEqual(bad, {}, f"nav links that don't render 200: {bad}")


class TestTopbarControlsAndLogin(unittest.TestCase):
    def test_guide_search_avatar_triggers_exist(self):
        html = _app_shell()
        self.assertIn("ck-guide-trigger", html)        # Guide
        self.assertIn("ck-topbar-right", html)         # right-rail controls
        self.assertIn("ck-palette", html)              # Search / Cmd+K

    def test_login_has_no_topbar_element(self):
        html = render_login_page()
        self.assertNotIn('class="ck-topbar"', html)


if __name__ == "__main__":
    unittest.main()


class TestMegaMenuTextWraps(unittest.TestCase):
    """Regression: the Source feature blurb overflowed its 236px column into
    the destination items. Grid items need min-width:0 (default min-width:auto
    lets content overflow the track) + overflow-wrap on the text."""

    def test_grid_items_have_min_width_zero(self):
        html = _app_shell()
        for rule in (".ck-mega-feat {", ".ck-mega-items {", ".ck-mega-item {",
                     ".ck-mega-it-body {"):
            m = re.search(re.escape(rule) + r"[^}]*}", html)
            self.assertIsNotNone(m, rule)
            self.assertIn("min-width:0", m.group(0), rule)

    def test_feature_and_item_text_wrap(self):
        html = _app_shell()
        for rule in (".ck-mega-feat-blurb {", ".ck-mega-it-desc {",
                     ".ck-mega-it-label {", ".ck-mega-feat-title {"):
            m = re.search(re.escape(rule) + r"[^}]*}", html)
            self.assertIsNotNone(m, rule)
            # `overflow-wrap:anywhere` is the (stronger) intended value — it
            # breaks even an unbroken token, which `break-word` will not. Accept
            # either so the assertion tracks the wrapping intent, not the exact
            # keyword.
            block = m.group(0)
            self.assertTrue(
                "overflow-wrap:anywhere" in block
                or "overflow-wrap:break-word" in block,
                rule,
            )


if __name__ == "__main__":
    unittest.main()
