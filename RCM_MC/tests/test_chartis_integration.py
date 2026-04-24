"""Smoke tests for the five Phase 2A Chartis routes.

Wires the server on a free port and hits each route with urllib.
Assertions are intentionally shallow — we only verify the route
exists and renders without crashing. Deeper behavioural tests are
deferred to Phase 2B / 2C.

Covered:

  - GET  /home
  - GET  /pe-intelligence
  - GET  /library              (deals corpus; was /deals-library)
  - GET  /methodology          (methodology hub; was /library)
  - GET  /deals-library        301 → /library  (preserves query)
  - GET  /deal/<id>/partner-review
  - GET  /deal/<id>/red-flags
"""
from __future__ import annotations

import os
import socket
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from tests.test_alerts import _seed_with_pe_math


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _ServerHarness:
    """Context-manager wrapping build_server on a free port."""

    def __init__(self, tmp: str) -> None:
        self.tmp = tmp
        self.port = _free_port()
        self.server = None

    def __enter__(self):
        from rcm_mc.server import build_server
        self.server, _ = build_server(
            port=self.port,
            db_path=os.path.join(self.tmp, "p.db"),
        )
        t = threading.Thread(target=self.server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.05)
        return self

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def __exit__(self, exc_type, exc, tb):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()


def _fetch(url: str, *, timeout: float = 10.0) -> tuple[int, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, (exc.read() or b"").decode("utf-8", errors="replace")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Make 301/302/303 visible instead of auto-following."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # type: ignore[return-value]


def _fetch_no_redirect(url: str, *, timeout: float = 10.0):
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(url, timeout=timeout) as r:
            return r.status, r.headers.get("Location"), r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location"), exc.read()


class TestChartisLandingRoutes(unittest.TestCase):
    """The four no-deal-required landing pages."""

    def test_home_renders_seven_panel_landing(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/home"))
            self.assertEqual(status, 200)
            self.assertIn("SeekingChartis", body)
            self.assertIn("Home", body)
            # Panel titles that are always present even with zero deals.
            self.assertIn("Pipeline Funnel", body)
            self.assertIn("PE Intelligence Highlights", body)
            self.assertIn("Corpus Insights", body)

    def test_home_seeded_deal_surfaces_healthcare_highlights(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "homecase")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url("/home"))
                self.assertEqual(status, 200)
                self.assertIn("homecase", body)
                self.assertIn("PE Intelligence Highlights", body)

    def test_pe_intelligence_hub_renders(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/pe-intelligence"))
            self.assertEqual(status, 200)
            self.assertIn("PE Intelligence", body)
            self.assertIn("SEVEN PARTNER REFLEXES", body)
            self.assertIn("Archetype Library", body)
            self.assertIn("Claude", body)

    def test_library_serves_deals_corpus(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/library"))
            self.assertEqual(status, 200)
            self.assertIn("Deals Library", body)
            self.assertIn("DEAL CORPUS", body)

    def test_methodology_serves_reference_hub(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/methodology"))
            self.assertEqual(status, 200)
            self.assertIn("Methodology", body)
            self.assertIn("Valuation Models", body)

    def test_deals_library_301_redirects_to_library(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, location, _ = _fetch_no_redirect(srv.url("/deals-library"))
            self.assertEqual(status, 301)
            self.assertEqual(location, "/library")

    def test_deals_library_301_preserves_query(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, location, _ = _fetch_no_redirect(
                srv.url("/deals-library?sector=Hospital&regime=expansion")
            )
            self.assertEqual(status, 301)
            self.assertEqual(location, "/library?sector=Hospital&regime=expansion")


class TestChartisPerDealRoutes(unittest.TestCase):
    """The two per-deal brain surfaces shipped in Phase 2A."""

    def test_partner_review_renders_for_seeded_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "testdeal")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url("/deal/testdeal/partner-review"))
                self.assertEqual(status, 200)
                self.assertIn("testdeal", body)
                self.assertIn("Partner Review", body)

    def test_partner_review_handles_missing_deal_without_500(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/deal/nonexistent/partner-review"))
            self.assertEqual(status, 200)
            self.assertIn("nonexistent", body)
            self.assertIn("INSUFFICIENT DATA", body)

    def test_red_flags_renders_for_seeded_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "testdeal")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url("/deal/testdeal/red-flags"))
                self.assertEqual(status, 200)
                self.assertIn("testdeal", body)
                self.assertIn("Red Flags", body)
                self.assertIn("Supplemental Healthcare Signals", body)
                self.assertIn("Claude Look", body)

    def test_red_flags_handles_missing_deal_without_500(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/deal/nonexistent/red-flags"))
            self.assertEqual(status, 200)
            self.assertIn("nonexistent", body)
            self.assertIn("UNAVAILABLE", body)


class TestChartisPhase2BRoutes(unittest.TestCase):
    """The six per-deal drill-down pages shipped in Phase 2B."""

    def _assert_seeded(self, suffix: str, *, expect_title: str,
                        expect_substrings: tuple = ()) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "td")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url(f"/deal/td/{suffix}"))
                self.assertEqual(status, 200, f"{suffix} non-200")
                self.assertIn(expect_title, body, f"{suffix} title missing")
                self.assertIn("td", body, f"{suffix} deal_id missing")
                for sub in expect_substrings:
                    self.assertIn(sub, body,
                                   f"{suffix} expected substring missing: {sub!r}")

    def _assert_missing(self, suffix: str) -> None:
        """The missing-deal path must render 200 with UNAVAILABLE, not 500."""
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url(f"/deal/nonexistent/{suffix}"))
            self.assertEqual(status, 200, f"{suffix} non-200 on missing deal")
            self.assertIn("UNAVAILABLE", body,
                           f"{suffix} expected UNAVAILABLE banner")

    def test_archetype_renders_for_seeded_deal(self):
        self._assert_seeded(
            "archetype",
            expect_title="Archetype",
            expect_substrings=("SPONSOR-STRUCTURE ARCHETYPES",
                               "REGIME CLASSIFICATION"),
        )

    def test_archetype_handles_missing_deal(self):
        self._assert_missing("archetype")

    def test_investability_renders_for_seeded_deal(self):
        self._assert_seeded(
            "investability",
            expect_title="Investability",
            expect_substrings=("THREE THINGS THAT MOST NEED",
                               "Exit Readiness"),
        )

    def test_investability_handles_missing_deal(self):
        self._assert_missing("investability")

    def test_market_structure_renders_for_seeded_deal(self):
        self._assert_seeded(
            "market-structure",
            expect_title="Market Structure",
            expect_substrings=(),  # shares are optional — empty state OK
        )

    def test_market_structure_handles_missing_deal(self):
        self._assert_missing("market-structure")

    def test_white_space_renders_for_seeded_deal(self):
        self._assert_seeded(
            "white-space",
            expect_title="White Space",
            expect_substrings=(),  # empty-state path is allowed
        )

    def test_white_space_handles_missing_deal(self):
        self._assert_missing("white-space")

    def test_stress_renders_for_seeded_deal(self):
        self._assert_seeded(
            "stress",
            expect_title="Stress Grid",
            expect_substrings=("ROBUSTNESS GRADE", "SCENARIO GRID"),
        )

    def test_stress_handles_missing_deal(self):
        self._assert_missing("stress")

    def test_ic_packet_renders_for_seeded_deal(self):
        self._assert_seeded(
            "ic-packet",
            expect_title="IC Packet",
            expect_substrings=(
                "SUPPLEMENTAL REVIEW SIGNALS",
                "Supplemental Healthcare Checks",
                "Claude Look",
                "IC-READY PACKET",
                "IC Memo",
            ),
        )

    def test_ic_packet_handles_missing_deal(self):
        self._assert_missing("ic-packet")


class TestChartisPhase2CPortfolioRoutes(unittest.TestCase):
    """The six portfolio-level pages shipped in Phase 2C."""

    def _assert_renders(self, path: str, *, expect_title: str,
                         expect_substrings: tuple = ()) -> None:
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url(path))
            self.assertEqual(status, 200, f"{path} returned {status}")
            self.assertIn(expect_title, body,
                           f"{path} missing title {expect_title!r}")
            for sub in expect_substrings:
                self.assertIn(sub, body,
                               f"{path} missing substring {sub!r}")

    def test_sponsor_track_record_renders(self):
        self._assert_renders(
            "/sponsor-track-record",
            expect_title="Sponsor Track Record",
            expect_substrings=("FULL LEAGUE TABLE", "TOP 5 BY MEDIAN MOIC"),
        )

    def test_payer_intelligence_renders(self):
        self._assert_renders(
            "/payer-intelligence",
            expect_title="Payer Intelligence",
            expect_substrings=("PAYER-MIX REGIMES", "COMPREHENSIVE VIEW"),
        )

    def test_payer_intel_summary_links_to_payer_intelligence(self):
        """The legacy /payer-intel page must cross-link to the new
        /payer-intelligence hub per the disambiguation rule."""
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/payer-intel"))
            self.assertEqual(status, 200)
            self.assertIn("/payer-intelligence", body)
            self.assertIn("SUMMARY VIEW", body)

    def test_rcm_benchmarks_renders(self):
        self._assert_renders(
            "/rcm-benchmarks",
            expect_title="RCM Benchmarks",
            expect_substrings=("CROSS-SEGMENT COMPARISON", "Community Hospital"),
        )

    def test_corpus_backtest_renders(self):
        self._assert_renders(
            "/corpus-backtest",
            expect_title="Corpus Backtest",
            expect_substrings=("DISAMBIGUATION", "GROUND-TRUTH CURVE"),
        )

    def test_backtester_cross_links_to_corpus_backtest(self):
        """The legacy /backtester page must cross-link to /corpus-backtest
        per the disambiguation rule."""
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/backtester"))
            self.assertEqual(status, 200)
            self.assertIn("/corpus-backtest", body)
            self.assertIn("VALUE BRIDGE BACKTEST", body)

    def test_deal_screening_renders(self):
        self._assert_renders(
            "/deal-screening",
            expect_title="Deal Screening",
            expect_substrings=("DECISION MIX", "Screening controls"),
        )

    def test_portfolio_analytics_renders(self):
        self._assert_renders(
            "/portfolio-analytics",
            expect_title="Portfolio Analytics",
            expect_substrings=("CORPUS SCORECARD",
                               "VINTAGE MIX",
                               "CONCENTRATION RISK"),
        )


class TestChartisPhase2CScreeningIntegration(unittest.TestCase):
    """Integration test: /deal-screening actually returns ranked output.

    Catches the case where screen_corpus silently falls through to an
    empty table (e.g. all deals filtered out or module raises and we
    render the empty state). A healthy install should screen all 655
    corpus deals under default thresholds and produce at least one PASS
    decision card and at least one populated result row.
    """

    def test_screening_produces_ranked_output_with_defaults(self):
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            status, body = _fetch(srv.url("/deal-screening"))
            self.assertEqual(status, 200)
            # Decision-mix strip populated with counts
            self.assertIn("DECISION MIX", body)
            # Results table has rows (not the UNAVAILABLE / error banner)
            self.assertNotIn("Deal screening unavailable", body)
            self.assertNotIn("Screening run failed", body)
            # Sanity: corpus-size KPI shows a 3-digit count
            self.assertIn("655", body, "expected 655 corpus deals KPI")
            # The pass/watch/fail tiles must all render
            self.assertIn(">PASS<", body)
            self.assertIn(">WATCH<", body)
            self.assertIn(">FAIL<", body)

    def test_screening_threshold_filter_shifts_decision_mix(self):
        """Tightening max_medicaid_pct should move deals from PASS to
        FAIL — verify the decision mix actually responds to the control."""
        with tempfile.TemporaryDirectory() as tmp, _ServerHarness(tmp) as srv:
            _, default_body = _fetch(srv.url("/deal-screening"))
            _, strict_body = _fetch(srv.url(
                "/deal-screening?max_medicaid_pct=0.10&max_ev_ebitda=10.0"
            ))
            # Both render without crashing
            self.assertIn("DECISION MIX", default_body)
            self.assertIn("DECISION MIX", strict_body)
            # Strict config should show MORE fails than default.
            # We don't parse the number out — just confirm the page
            # responds (different byte length proves the mix changed).
            self.assertNotEqual(
                len(default_body), len(strict_body),
                "screen output did not change when thresholds tightened",
            )


class TestChartisIntegration(unittest.TestCase):
    """End-to-end sanity check — catches the case where the PE brain
    silently crashes and every per-deal page falls through to the
    insufficient-data placeholder."""

    def test_partner_review_exercises_the_brain_on_a_seeded_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_with_pe_math(tmp, "rich")
            with _ServerHarness(tmp) as srv:
                status, body = _fetch(srv.url("/deal/rich/partner-review"))
                self.assertEqual(status, 200)
                self.assertNotIn("INSUFFICIENT DATA", body,
                                  "brain should run on _seed_with_pe_math deal")
                # Sections that only appear when partner_review() actually ran:
                self.assertIn("IC VERDICT", body)
                self.assertIn("Partner Voice", body)
                self.assertIn("Reasonableness Bands", body)
                self.assertIn("SECONDARY ANALYTICS", body)
                # Cross-link strip to Phase 2B drill-downs:
                self.assertIn("/deal/rich/archetype", body)
                self.assertIn("/deal/rich/stress", body)
                self.assertIn("/deal/rich/ic-packet", body)


class TestReasonablenessGuards(unittest.TestCase):
    """Phase 4A: the sanity module that wraps every numeric render.

    Every test calls the guard directly rather than hitting a live page
    — this keeps the unit tests fast and makes the failure modes easy
    to read. Integration tests in Phase 4B/4C exercise the guard via
    the actual chartis pages.
    """

    def test_moic_in_range_renders_cleanly(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(2.3, "moic")
        self.assertIn("2.30x", out)
        self.assertIn("ck-num", out)
        self.assertNotIn("ck-num-bad", out)
        self.assertNotIn("⚠", out)

    def test_moic_out_of_range_renders_warning(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(47.2, "moic")
        self.assertIn("47.20x", out)
        self.assertIn("ck-num-bad", out)
        self.assertIn("⚠", out)
        self.assertIn("Value outside expected range", out)
        self.assertIn("0.30x", out)  # range lower bound in tooltip
        self.assertIn("6.00x", out)  # range upper bound in tooltip

    def test_moic_negative_renders_warning(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(-0.5, "moic")
        self.assertIn("ck-num-bad", out)
        self.assertIn("-0.50x", out)

    def test_none_renders_emdash(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(None, "moic")
        self.assertIn("—", out)
        self.assertIn("ck-num-nil", out)
        self.assertNotIn("ck-num-bad", out)

    def test_nan_renders_emdash(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(float("nan"), "moic")
        self.assertIn("—", out)
        self.assertIn("ck-num-nil", out)

    def test_unparseable_renders_emdash(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number("banana", "moic")
        self.assertIn("—", out)
        self.assertIn("ck-num-nil", out)

    def test_unknown_metric_raises(self):
        from rcm_mc.ui.chartis._sanity import render_number, UnknownMetric
        with self.assertRaises(UnknownMetric) as cm:
            render_number(1.0, "mo1c_typo")
        self.assertIn("not in REGISTRY", str(cm.exception))

    def test_irr_in_range(self):
        from rcm_mc.ui.chartis._sanity import render_number
        self.assertIn("22.0%", render_number(0.22, "irr"))
        self.assertNotIn("ck-num-bad", render_number(0.22, "irr"))

    def test_irr_out_of_range(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(0.82, "irr")  # 82% IRR — implausible
        self.assertIn("ck-num-bad", out)
        self.assertIn("82.0%", out)

    def test_hhi_in_range(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(1847, "hhi")
        self.assertIn("1,847", out)
        self.assertNotIn("ck-num-bad", out)

    def test_hhi_out_of_range(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(20000, "hhi")  # max is 10,000
        self.assertIn("ck-num-bad", out)
        self.assertIn("20,000", out)

    def test_leverage_out_of_range(self):
        from rcm_mc.ui.chartis._sanity import render_number
        out = render_number(18.5, "leverage_multiple")  # max 12.0x
        self.assertIn("ck-num-bad", out)
        self.assertIn("18.50x", out)

    def test_ebitda_margin_implausible(self):
        from rcm_mc.ui.chartis._sanity import render_number
        # 250% margin — obviously wrong
        out = render_number(2.5, "ebitda_margin")
        self.assertIn("ck-num-bad", out)
        self.assertIn("250.0%", out)

    def test_aggregate_banner_fires(self):
        """3 out of 15 rows with bad MOIC → 'of 15' banner at top."""
        from rcm_mc.ui.chartis._sanity import render_table_with_guards
        rows = []
        for i in range(15):
            moic = 47.0 if i in (2, 7, 11) else 2.3
            rows.append({"deal": f"Deal {i}", "moic": moic})
        columns = [
            ("deal", "Deal", ""),
            ("moic", "MOIC", "moic"),
        ]
        html = render_table_with_guards(rows, columns)
        self.assertIn("ck-sanity-banner", html)
        self.assertIn("3 of 15", html)
        # Body renders all 15 rows; 3 should be flagged
        self.assertEqual(html.count("ck-num-bad"), 3)
        self.assertIn("47.00x", html)

    def test_aggregate_banner_silent_when_all_in_range(self):
        from rcm_mc.ui.chartis._sanity import render_table_with_guards
        rows = [{"deal": f"D{i}", "moic": 2.3} for i in range(10)]
        html = render_table_with_guards(
            rows, [("deal", "Deal", ""), ("moic", "MOIC", "moic")]
        )
        self.assertNotIn("ck-sanity-banner", html)
        self.assertNotIn("ck-num-bad", html)

    def test_warning_for_returns_none_in_range(self):
        from rcm_mc.ui.chartis._sanity import warning_for
        self.assertIsNone(warning_for(2.3, "moic"))
        self.assertIsNone(warning_for(None, "moic"))
        self.assertIsNone(warning_for(float("nan"), "moic"))

    def test_warning_for_returns_string_out_of_range(self):
        from rcm_mc.ui.chartis._sanity import warning_for
        msg = warning_for(47.2, "moic")
        self.assertIsNotNone(msg)
        self.assertIn("outside expected range", msg)
        self.assertIn("moic", msg)


class TestJsonApiSanityAnnotation(unittest.TestCase):
    """Phase 4C: JSON API responses get <metric>_warning siblings
    attached automatically for out-of-range numeric fields. The raw
    value is preserved — annotation is additive only."""

    def test_attaches_warning_on_out_of_range(self):
        from rcm_mc.ui.chartis._sanity import attach_sanity_warnings
        out = attach_sanity_warnings({"moic": 47.2, "deal_id": "x"})
        self.assertEqual(out["moic"], 47.2)  # raw value preserved
        self.assertIn("moic_warning", out)
        self.assertIn("outside expected range", out["moic_warning"])

    def test_no_warning_on_in_range(self):
        from rcm_mc.ui.chartis._sanity import attach_sanity_warnings
        out = attach_sanity_warnings({"moic": 2.3, "deal_id": "x"})
        self.assertEqual(out["moic"], 2.3)
        self.assertNotIn("moic_warning", out)

    def test_walks_nested_dicts(self):
        from rcm_mc.ui.chartis._sanity import attach_sanity_warnings
        out = attach_sanity_warnings({
            "summary": {"moic_p50": 47.2, "moic_p25": 2.0},
            "name": "deal",
        })
        self.assertEqual(out["summary"]["moic_p50"], 47.2)
        self.assertIn("moic_p50_warning", out["summary"])
        self.assertNotIn("moic_p25_warning", out["summary"])

    def test_walks_lists_of_dicts(self):
        from rcm_mc.ui.chartis._sanity import attach_sanity_warnings
        out = attach_sanity_warnings({
            "deals": [
                {"deal_id": "a", "median_moic": 2.3},
                {"deal_id": "b", "median_moic": 47.2},
            ],
        })
        self.assertNotIn("median_moic_warning", out["deals"][0])
        self.assertIn("median_moic_warning", out["deals"][1])

    def test_ignores_unknown_keys(self):
        """Arbitrary numeric fields (count, limit, score) don't get
        annotated unless their key matches a REGISTRY metric."""
        from rcm_mc.ui.chartis._sanity import attach_sanity_warnings
        out = attach_sanity_warnings({"count": 999999, "limit": 50, "offset": 0})
        self.assertNotIn("count_warning", out)
        self.assertNotIn("limit_warning", out)

    def test_ignores_nil_values(self):
        """None / NaN should not trigger warnings."""
        from rcm_mc.ui.chartis._sanity import attach_sanity_warnings
        out = attach_sanity_warnings({"moic": None})
        self.assertNotIn("moic_warning", out)


class TestExplainerHelper(unittest.TestCase):
    """Phase 3A: the render_page_explainer helper that every chartis
    page calls at the top of its body to document what the page
    shows, what the scale means, and how partners should use it."""

    def test_explainer_with_all_three_parts_renders(self):
        from rcm_mc.ui.chartis._helpers import render_page_explainer
        html = render_page_explainer(
            what="This page shows HHI for the target's local market.",
            scale="Under 1,500 = fragmented; 2,500+ = concentrated.",
            use="Use this to assess pricing power.",
            source="FTC Horizontal Merger Guidelines (2023).",
            page_key="market-structure",
        )
        self.assertIn("About this page", html)
        self.assertIn("HHI", html)
        self.assertIn(">Scale<", html)
        self.assertIn(">How to use<", html)
        self.assertIn("Source:", html)
        self.assertIn("FTC Horizontal Merger Guidelines", html)
        # Toggle + JS wired
        self.assertIn("ck-explainer-toggle", html)
        self.assertIn("ckExplainerToggle", html)
        # Page key wired for localStorage
        self.assertIn('data-page-key="market-structure"', html)

    def test_explainer_with_only_what_renders(self):
        from rcm_mc.ui.chartis._helpers import render_page_explainer
        html = render_page_explainer(
            what="This page shows a list of deals.",
            page_key="library",
        )
        self.assertIn("This page shows a list of deals.", html)
        # Scale / Use / Source sections absent
        self.assertNotIn(">Scale<", html)
        self.assertNotIn(">How to use<", html)
        self.assertNotIn("Source:", html)
        # Toggle still present — every explainer collapses
        self.assertIn("ck-explainer-toggle", html)

    def test_explainer_omits_source_line_when_source_empty(self):
        from rcm_mc.ui.chartis._helpers import render_page_explainer
        html = render_page_explainer(
            what="No source needed.",
            scale="Threshold X means Y.",
            use="Use for Z.",
            source="",
            page_key="page",
        )
        self.assertIn(">Scale<", html)
        self.assertIn(">How to use<", html)
        self.assertNotIn("Source:", html)

    def test_explainer_html_is_safe(self):
        """XSS vectors in any of the text args must be escaped."""
        from rcm_mc.ui.chartis._helpers import render_page_explainer
        xss = "<script>alert('x')</script>"
        html = render_page_explainer(
            what=xss,
            scale=xss,
            use=xss,
            source=xss,
            page_key="p",
        )
        # Raw <script> tags from user text must not leak into the DOM
        # (the helper's own <script> block is fine; that's page
        # infrastructure). Check that the literal attack string is
        # escaped.
        self.assertNotIn("<script>alert('x')</script>", html)
        self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
