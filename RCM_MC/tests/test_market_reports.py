"""Market Reports subsystem — registry integrity + renderer + route smoke.

Real-path tests (no mocks of our own code). They pin:

  - every canonical subsector has a page (full report or honest scaffold),
    and the canonical slug set is exactly the industry-deep-dive registry;
  - the three flagships are complete, validated MarketReports whose live
    figures wire from the matching *_deep_dive();
  - the /market index lists every subsector under its care setting;
  - each flagship dossier renders every section, leaks no template tokens,
    keeps its tags balanced (html.parser, CDATA-aware), and labels every
    figure with an honesty basis/source chip;
  - a scaffold slug renders honestly (never a 404), including an unknown slug;
  - the route + nav/palette wiring is live over real HTTP.
"""
from __future__ import annotations

import html as _h
import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from html.parser import HTMLParser

from rcm_mc import market_reports as mr
from rcm_mc.market_reports import BASIS_LABELS, SOURCE_KINDS, CONNECTION_KINDS
from rcm_mc.ui.market_report_page import (
    render_market_index, render_market_report,
)

_FLAGSHIPS = ("dialysis", "home_health", "hospice")
_SECTION_HEADS = (
    "How it works", "Market size", "Reimbursement", "Regulatory",
    "Competition", "Unit economics", "Risks", "Diligence questions",
    "Insider lens", "Our data connections", "Sources",
)
# Container tags our renderer always opens+closes explicitly. HTMLParser puts
# <script>/<style> bodies in CDATA mode, so tag-looking text inside them is not
# counted — this is a real structural balance check, not a string count.
_TRACK = {"section", "table", "thead", "tbody", "ul", "ol", "tr"}


class _BalanceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in _TRACK:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in _TRACK:
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            elif tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            else:
                self.errors.append(("stray_close", tag))


def _assert_balanced(test: unittest.TestCase, html: str, label: str) -> None:
    p = _BalanceParser()
    p.feed(html)
    test.assertEqual(p.errors, [], f"{label}: unbalanced tags {p.errors[:5]}")
    test.assertEqual(p.stack, [], f"{label}: unclosed tags {p.stack[:5]}")


class RegistryIntegrityTests(unittest.TestCase):
    def setUp(self):
        mr.reset_for_tests()

    def test_canonical_slug_set_equals_deep_dive_registry(self):
        # The taxonomy is the TAM/SAM template key AND the deep-dive key —
        # they must line up 1:1 so every subsector has a live data connection.
        from rcm_mc.diligence.industry_deep_dive import DEEP_DIVES
        self.assertEqual(set(mr.canonical_slugs()), set(DEEP_DIVES))
        self.assertEqual(len(mr.canonical_slugs()), len(set(mr.canonical_slugs())))

    def test_every_canonical_slug_has_a_care_setting(self):
        for slug, name, setting in mr.CANONICAL_SUBSECTORS:
            self.assertIn(setting, mr.CARE_SETTINGS, f"{slug}: bad setting")
            self.assertTrue(name.strip(), f"{slug}: empty display name")

    def test_autoload_has_no_errors_and_registers_flagships(self):
        reports = mr.all_reports()
        self.assertEqual(mr.autoload_errors(), [],
                         f"autoload errors: {mr.autoload_errors()}")
        for slug in _FLAGSHIPS:
            self.assertIn(slug, reports, f"{slug} did not self-register")

    def test_flagships_are_full_validated_reports(self):
        for slug in _FLAGSHIPS:
            rep = mr.report_for(slug)
            self.assertIsNotNone(rep, f"{slug} report missing")
            rep.validate()  # raises on any contract violation
            self.assertEqual(rep.tam_headline.basis_label in BASIS_LABELS, True)
            self.assertGreaterEqual(len(rep.executive_summary), 3)
            self.assertTrue(rep.insider_lens, f"{slug}: empty insider lens")

    def test_flagship_live_figures_are_sourced_from_deep_dives(self):
        for slug in _FLAGSHIPS:
            rep = mr.report_for(slug)
            self.assertTrue(rep.live_figures,
                            f"{slug}: expected SOURCED live figures from dive")
            for lf in rep.live_figures:
                self.assertEqual(lf.basis, "SOURCED")
                self.assertTrue(lf.source_label.strip())

    def test_report_for_unknown_slug_is_none_not_error(self):
        self.assertIsNone(mr.report_for("no_such_subsector"))

    def test_every_canonical_slug_renders_a_page(self):
        # Registry integrity: every subsector has a page (full or scaffold),
        # never a crash and never a blank.
        for slug in mr.canonical_slugs():
            html = render_market_report(slug)
            self.assertGreater(len(html), 1000, f"{slug}: blank/short page")
            _assert_balanced(self, html, f"{slug}-page")


class HonestyContractTests(unittest.TestCase):
    """Every quantitative claim must carry a basis/source label."""

    def test_flagship_figures_all_carry_a_basis_or_source_label(self):
        for slug in _FLAGSHIPS:
            rep = mr.report_for(slug)
            self.assertIn(rep.tam_headline.basis_label, BASIS_LABELS)
            for seg in rep.market_size.segments:
                self.assertTrue(seg.source_label.strip(),
                                f"{slug}/{seg.name}: no source_label")
            for s in rep.sources:
                self.assertIn(s.kind, SOURCE_KINDS)
            for c in rep.connections:
                self.assertIn(c.kind, CONNECTION_KINDS)

    def test_rendered_flagship_uses_the_basis_chip_helper(self):
        # The label helper (ck-mr-chip) must appear at least once per segment,
        # once per live figure, and once for the TAM headline — i.e. no bare
        # figure ships without a chip.
        for slug in _FLAGSHIPS:
            rep = mr.report_for(slug)
            html = render_market_report(slug)
            self.assertIn("ck-mr-chip", html)
            expected_min = (len(rep.market_size.segments)
                            + len(rep.live_figures) + 1)
            self.assertGreaterEqual(html.count("ck-mr-chip "), expected_min,
                                    f"{slug}: too few basis chips")


class IndexRenderTests(unittest.TestCase):
    def setUp(self):
        self.html = render_market_index()

    def test_index_is_non_trivial_and_balanced(self):
        self.assertGreater(len(self.html), 5000)
        _assert_balanced(self, self.html, "index")

    def test_index_lists_every_subsector_and_care_setting(self):
        # Names/settings render HTML-escaped ("Dx & labs" -> "Dx &amp; labs",
        # "Women's Health" -> "Women&#x27;s Health"), so compare escaped forms.
        for slug, name, setting in mr.CANONICAL_SUBSECTORS:
            self.assertIn(_h.escape(name), self.html, f"{name} missing")
            self.assertIn(f"/market/{slug}", self.html, f"{slug} link missing")
        for setting in mr.CARE_SETTINGS:
            self.assertIn(_h.escape(setting), self.html,
                          f"{setting} header missing")

    def test_index_has_editorial_head_and_honesty_legend(self):
        self.assertIn("Healthcare subsector market reports", self.html)
        self.assertIn("<em>", self.html)          # italic-serif cadence
        self.assertIn("ck-mr-legend", self.html)   # honesty legend


class FlagshipRenderTests(unittest.TestCase):
    def test_each_flagship_renders_every_section(self):
        for slug in _FLAGSHIPS:
            html = render_market_report(slug)
            self.assertGreater(len(html), 5000, f"{slug}: trivial render")
            for head in _SECTION_HEADS:
                self.assertIn(head, html, f"{slug}: section {head!r} missing")

    def test_flagships_have_no_template_token_leaks(self):
        leak_markers = (
            "None", "{th.", "{rep", "{_esc", "{slug", "{c.", "{s.",
            "MarketReport(", "TamHeadline(", "HowItWorks(", "f'<",
        )
        for slug in _FLAGSHIPS:
            html = render_market_report(slug)
            for marker in leak_markers:
                self.assertNotIn(marker, html, f"{slug}: leaked {marker!r}")

    def test_flagship_tags_are_balanced(self):
        for slug in _FLAGSHIPS:
            _assert_balanced(self, render_market_report(slug), slug)

    def test_flagship_contains_real_domain_content(self):
        # Spot-check that the authored insider knowledge actually rendered.
        self.assertIn("DaVita", render_market_report("dialysis"))
        self.assertIn("PDGM", render_market_report("home_health"))
        self.assertIn("aggregate cap", render_market_report("hospice"))


class ScaffoldRenderTests(unittest.TestCase):
    def test_known_slug_without_report_renders_scaffold(self):
        # cardiology is canonical but has no authored report yet.
        html = render_market_report("cardiology")
        self.assertGreater(len(html), 2000)
        self.assertIn("authoring queue", html)
        self.assertIn("Cardiology", html)
        self.assertIn("/market", html)       # link back
        _assert_balanced(self, html, "cardiology-scaffold")

    def test_scaffold_offers_live_data_connections(self):
        html = render_market_report("cardiology")
        self.assertIn("/diligence/tam-sam?template=cardiology", html)

    def test_unknown_slug_is_scaffold_not_404(self):
        html = render_market_report("totally-made-up")
        self.assertGreater(len(html), 1000)
        self.assertIn("authoring queue", html)
        # The bogus slug must be escaped, never reflected raw as markup.
        self.assertNotIn("<totally", html)

    def test_hyphenated_slug_normalises(self):
        # /market/home-health should resolve to the home_health report.
        self.assertIn("PDGM", render_market_report("home-health"))


class WiringTests(unittest.TestCase):
    def test_route_resolves_to_research_section(self):
        from rcm_mc.ui._chartis_kit import _resolve_sub_section
        self.assertEqual(_resolve_sub_section("/market"), "research")
        self.assertEqual(_resolve_sub_section("/market/dialysis"), "research")

    def test_market_in_palette_and_sub_nav(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES, _SUB_NAV
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/market", routes)
        research = {e["href"] for e in _SUB_NAV["research"]}
        self.assertIn("/market", research)


class HttpRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls._tmp = tempfile.TemporaryDirectory()
        with closing(socket.socket()) as s:
            s.bind(("127.0.0.1", 0))
            cls._port = s.getsockname()[1]
        srv, _ = build_server(port=cls._port, host="127.0.0.1",
                              db_path=os.path.join(cls._tmp.name, "p.db"))
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _get(self, path):
        try:
            return urllib.request.urlopen(
                f"http://127.0.0.1:{self._port}{path}", timeout=15)
        except urllib.error.HTTPError as exc:
            return exc

    def test_index_serves_200(self):
        resp = self._get("/market")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Healthcare subsector market reports", body)
        self.assertIn("Dialysis", body)

    def test_flagship_serves_200(self):
        resp = self._get("/market/dialysis")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("DaVita", body)
        self.assertIn("Reimbursement", body)

    def test_scaffold_serves_200(self):
        resp = self._get("/market/cardiology")
        self.assertEqual(resp.status, 200)
        self.assertIn("authoring queue", resp.read().decode())


if __name__ == "__main__":
    unittest.main()
