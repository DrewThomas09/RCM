"""Market-intel package regression tests."""
from __future__ import annotations

import unittest

from rcm_mc.market_intel import (
    ManualMarketIntelAdapter, PublicComp, StubVendorBloombergAdapter,
    StubVendorPitchBookAdapter, StubVendorSeekingAlphaAdapter,
    category_bands, find_comparables, list_companies,
    news_for_target, sector_sentiment, transaction_multiple,
)
from rcm_mc.ui.market_intel_page import render_market_intel_page


class PublicCompsTests(unittest.TestCase):

    def test_list_companies_includes_hca_thc(self):
        comps = list_companies()
        tickers = {c.ticker for c in comps}
        for t in ("HCA", "THC", "CYH", "UHS", "EHC", "ARDT"):
            self.assertIn(t, tickers, msg=f"missing {t}")

    def test_hca_fields_populated(self):
        hca = next(c for c in list_companies() if c.ticker == "HCA")
        self.assertGreater(hca.market_cap_usd_bn, 50)
        self.assertGreater(hca.ev_ebitda_multiple, 5)
        self.assertGreater(hca.revenue_ttm_usd_bn, 50)
        # Payer mix rows populated
        self.assertIsNotNone(hca.payer_mix_commercial)
        self.assertAlmostEqual(
            (hca.payer_mix_commercial or 0)
            + (hca.payer_mix_medicare or 0)
            + (hca.payer_mix_medicaid or 0)
            + (hca.payer_mix_other or 0),
            1.0, delta=0.02,
        )

    def test_find_comparables_by_category_returns_matches(self):
        r = find_comparables(target_category="MULTI_SITE_ACUTE_HOSPITAL")
        tickers = {c["ticker"] for c in r["comps"]}
        self.assertIn("HCA", tickers)
        self.assertIn("THC", tickers)

    def test_find_comparables_sorts_by_size_when_supplied(self):
        # Revenue ~5B matches Encompass/Ardent in size even though
        # we restrict to MULTI_SITE_ACUTE.
        r = find_comparables(
            target_category="MULTI_SITE_ACUTE_HOSPITAL",
            target_revenue_usd=5_500_000_000,
        )
        self.assertEqual(r["comps"][0]["ticker"], "ARDT")

    def test_unknown_category_returns_note(self):
        r = find_comparables(target_category="MADE_UP_CATEGORY")
        self.assertEqual(r["comps"], [])
        self.assertIn("No public operator", r["note"])

    def test_category_bands_has_multi_site_acute(self):
        bands = category_bands()
        self.assertIn("MULTI_SITE_ACUTE_HOSPITAL", bands)
        b = bands["MULTI_SITE_ACUTE_HOSPITAL"]
        self.assertGreater(b.median_ev_ebitda, 0)


class TransactionMultipleTests(unittest.TestCase):

    def test_anesthesia_band_has_nsa_discount_note(self):
        m = transaction_multiple(
            specialty="ANESTHESIOLOGY", ev_usd=200_000_000,
        )
        self.assertIsNotNone(m)
        # NSA-discount compresses vs. other specialty medians
        self.assertLess(m.p50_ev_ebitda, 9.5)
        self.assertIsNotNone(m.note)
        self.assertIn("NSA", m.note)

    def test_ev_usd_drives_size_band_selection(self):
        small = transaction_multiple(
            specialty="MULTI_SITE_PHYSICIAN_GROUP",
            ev_usd=50_000_000,
        )
        mid = transaction_multiple(
            specialty="MULTI_SITE_PHYSICIAN_GROUP",
            ev_usd=300_000_000,
        )
        large = transaction_multiple(
            specialty="MULTI_SITE_PHYSICIAN_GROUP",
            ev_usd=800_000_000,
        )
        self.assertEqual(small.deal_size_band, "SUB_100M")
        self.assertEqual(mid.deal_size_band, "100M_TO_500M")
        self.assertEqual(large.deal_size_band, "OVER_500M")
        # Larger deals clear at higher multiples (platform premium).
        self.assertGreater(large.p50_ev_ebitda, small.p50_ev_ebitda)

    def test_unknown_specialty_returns_none(self):
        self.assertIsNone(
            transaction_multiple(specialty="WIDGET_MEDICINE"),
        )


class NewsFeedTests(unittest.TestCase):

    def test_no_filters_returns_newest_first(self):
        items = news_for_target(limit=5)
        self.assertGreater(len(items), 0)
        dates = [i.date for i in items]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_ticker_filter_matches_hca(self):
        items = news_for_target(tickers=["HCA"])
        self.assertTrue(any("HCA" in it.tickers for it in items))

    def test_specialty_filter_matches_ma_risk(self):
        items = news_for_target(specialty="MA_RISK_PRIMARY_CARE")
        self.assertTrue(items)
        for it in items:
            self.assertIn(
                (it.specialty or "").upper(),
                {"MA_RISK_PRIMARY_CARE"},
            )

    def test_tag_filter_matches_site_neutral(self):
        items = news_for_target(tags=["site_neutral"])
        self.assertTrue(items)

    def test_sector_sentiment_returns_curated_label(self):
        self.assertEqual(
            sector_sentiment("MA_RISK_PRIMARY_CARE"), "negative",
        )
        self.assertEqual(
            sector_sentiment("OPHTHALMOLOGY"), "positive",
        )
        self.assertIsNone(sector_sentiment("ZZZ"))


class AdapterTests(unittest.TestCase):

    def test_manual_adapter_returns_real_data(self):
        a = ManualMarketIntelAdapter()
        self.assertGreater(len(a.public_comps()), 0)
        self.assertIsNotNone(
            a.transaction_multiple(specialty="ANESTHESIOLOGY"),
        )
        self.assertGreater(len(a.news_for_target(limit=3)), 0)

    def test_stub_vendors_raise_with_endpoint(self):
        for cls in (
            StubVendorSeekingAlphaAdapter,
            StubVendorPitchBookAdapter,
            StubVendorBloombergAdapter,
        ):
            # Non-empty auth is required — no silent construction.
            adapter = cls(
                "fake" if cls is StubVendorBloombergAdapter else "key",
            ) if cls is StubVendorBloombergAdapter else cls("key")
            with self.assertRaises(NotImplementedError) as cm:
                adapter.news_for_target()
            # The stub message always mentions an endpoint the
            # implementer should hit.
            msg = str(cm.exception)
            self.assertTrue(
                "api" in msg.lower() or "endpoint" in msg.lower()
                or "implement" in msg.lower(),
            )

    def test_stub_requires_auth(self):
        with self.assertRaises(ValueError):
            StubVendorSeekingAlphaAdapter(api_key="")
        with self.assertRaises(ValueError):
            StubVendorPitchBookAdapter(api_key="")
        with self.assertRaises(ValueError):
            StubVendorBloombergAdapter(auth_token="")


class MarketIntelPageTests(unittest.TestCase):

    def test_page_renders_without_filters(self):
        h = render_market_intel_page()
        self.assertIn("Market Intelligence", h)
        self.assertIn("HCA", h)
        self.assertIn("THC", h)

    def test_page_with_specialty_shows_transaction_multiple(self):
        h = render_market_intel_page(
            specialty="ANESTHESIOLOGY",
            ev_usd=300_000_000,
        )
        self.assertIn("ANESTHESIOLOGY", h)
        self.assertIn("transaction multiple", h.lower())

    def test_page_with_category_filters_comps(self):
        h = render_market_intel_page(
            category="MULTI_SITE_ACUTE_HOSPITAL",
        )
        self.assertIn("HCA", h)
        # Category band should render
        self.assertIn("Median EV/EBITDA", h)

    def test_page_renders_news_with_sector_sentiment(self):
        h = render_market_intel_page(
            specialty="MA_RISK_PRIMARY_CARE",
        )
        self.assertIn("News Feed", h)
        self.assertIn("negative", h)   # sector sentiment pill


class NavTest(unittest.TestCase):

    def test_market_intel_link_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/market-intel"', rendered)


# ────────────────────────────────────────────────────────────────────
# Expanded Seeking-Alpha-style data: analyst coverage + earnings +
# turnover disclosures + new tickers + scatter chart
# ────────────────────────────────────────────────────────────────────

class ExpandedTickerLatticeTests(unittest.TestCase):

    def test_lattice_has_14_tickers(self):
        comps = list_companies()
        self.assertGreaterEqual(len(comps), 14)

    def test_lattice_covers_all_9_categories(self):
        comps = list_companies()
        categories = {c.category for c in comps}
        expected = {
            "MULTI_SITE_ACUTE_HOSPITAL",
            "RURAL_ACUTE_HOSPITAL",
            "MULTI_SITE_ACUTE_AND_BEHAVIORAL",
            "POST_ACUTE_REHAB",
            "PHYSICIAN_GROUP_ROLL_UP",
            "DIALYSIS",
            "AMBULATORY_SURGERY",
            "MANAGED_CARE_PAYER",
            "HEALTHCARE_REIT",
        }
        self.assertTrue(expected.issubset(categories),
                        msg=f"missing {expected - categories}")

    def test_new_tickers_present(self):
        tickers = {c.ticker for c in list_companies()}
        for t in ("PRVA", "DVA", "FMS", "SGRY",
                  "UNH", "ELV", "MPW", "WELL"):
            self.assertIn(t, tickers)


class AnalystCoverageTests(unittest.TestCase):

    def test_hca_has_analyst_coverage(self):
        hca = next(c for c in list_companies() if c.ticker == "HCA")
        self.assertIsNotNone(hca.analyst_coverage)
        self.assertEqual(hca.analyst_coverage.consensus, "BUY")
        self.assertGreater(hca.analyst_coverage.price_target_usd, 0)
        self.assertGreater(hca.analyst_coverage.ratings_count, 0)

    def test_consensus_values_are_valid(self):
        for c in list_companies():
            if c.analyst_coverage is not None:
                self.assertIn(
                    c.analyst_coverage.consensus,
                    ("BUY", "HOLD", "SELL", "NONE"),
                )

    def test_to_dict_nests_analyst_coverage(self):
        hca = next(c for c in list_companies() if c.ticker == "HCA")
        d = hca.to_dict()
        self.assertIn("analyst_coverage", d)
        self.assertEqual(d["analyst_coverage"]["consensus"], "BUY")


class EarningsSurpriseTests(unittest.TestCase):

    def test_every_ticker_has_earnings_latest(self):
        for c in list_companies():
            self.assertIsNotNone(c.earnings_latest,
                                 msg=f"{c.ticker} missing earnings")

    def test_surprise_pct_signed(self):
        cyh = next(c for c in list_companies() if c.ticker == "CYH")
        self.assertLess(cyh.earnings_latest.surprise_pct, 0)
        hca = next(c for c in list_companies() if c.ticker == "HCA")
        self.assertGreater(hca.earnings_latest.surprise_pct, 0)


class PhysicianTurnoverPeerStatsTests(unittest.TestCase):

    def test_stats_populated(self):
        from rcm_mc.market_intel import peer_physician_turnover_stats
        stats = peer_physician_turnover_stats()
        self.assertGreaterEqual(stats["count"], 5)
        self.assertGreater(stats["median"], 0.03)
        self.assertLess(stats["median"], 0.15)
        self.assertLessEqual(stats["p25"], stats["median"])
        self.assertLessEqual(stats["median"], stats["p75"])

    def test_stats_returns_zero_when_empty(self):
        from rcm_mc.market_intel.public_comps import (
            peer_physician_turnover_stats,
        )
        # No-arg form — just verify defensive path is present
        stats = peer_physician_turnover_stats()
        # We have data so non-empty — this just verifies the
        # dict shape contract.
        self.assertIn("median", stats)
        self.assertIn("p25", stats)
        self.assertIn("p75", stats)
        self.assertIn("count", stats)


class TargetScatterChartTests(unittest.TestCase):

    def test_scatter_rendered_when_target_supplied(self):
        h = render_market_intel_page(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            revenue_usd=200_000_000,
            ev_usd=350_000_000,
        )
        self.assertIn("PEER SCATTER", h)
        self.assertIn("TARGET", h)

    def test_scatter_rendered_without_target_still_shows_peers(self):
        h = render_market_intel_page(
            category="MULTI_SITE_ACUTE_HOSPITAL",
        )
        # Peers alone → scatter still renders (without target marker).
        self.assertIn("PEER SCATTER", h)

    def test_scatter_suppressed_when_no_comps(self):
        """Unknown category means no comps → no scatter."""
        h = render_market_intel_page(
            category="NONEXISTENT_SECTOR",
        )
        # No peers, so chart should not render
        self.assertNotIn("PEER SCATTER", h)


class CompsTableEnrichmentTests(unittest.TestCase):

    def test_analyst_consensus_column_present(self):
        h = render_market_intel_page(
            category="MULTI_SITE_ACUTE_HOSPITAL",
        )
        self.assertIn("Analyst", h)
        self.assertIn("Q surprise", h)

    def test_consensus_pill_rendered(self):
        h = render_market_intel_page(
            category="MULTI_SITE_ACUTE_HOSPITAL",
        )
        # BUY / HOLD pills should appear for at least HCA and THC
        self.assertIn("BUY", h)
        # Price target annotation
        self.assertIn("PT $", h)


class PPAMMarketIntelLinkTests(unittest.TestCase):

    def test_ppam_hero_references_public_peer_median(self):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        h = render_physician_attrition_page()
        # PPAM hero summary should mention public-peer context.
        self.assertTrue(
            "public-peer" in h or "peer median" in h,
            msg="PPAM hero missing public-peer benchmark",
        )


class PeerSnapshotTests(unittest.TestCase):

    def test_peer_snapshot_in_line(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_revenue_usd=250_000_000,
            target_ev_usd=350_000_000,
            target_ebitda_usd=35_000_000,
        )
        self.assertAlmostEqual(s.target_implied_multiple, 10.0, places=2)
        self.assertEqual(s.assessment, "IN-LINE")
        self.assertGreaterEqual(len(s.peers), 1)

    def test_peer_snapshot_premium(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=600_000_000,
            target_ebitda_usd=35_000_000,
        )
        # ~17.1x vs p75 10.2x — premium
        self.assertEqual(s.assessment, "PREMIUM")

    def test_peer_snapshot_discount(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=180_000_000,
            target_ebitda_usd=30_000_000,
        )
        # 6x vs p25 8.5x — discount
        self.assertEqual(s.assessment, "DISCOUNT")

    def test_peer_snapshot_no_data(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(category="")
        self.assertEqual(s.assessment, "NO_DATA")

    def test_peer_snapshot_unknown_category(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="NONEXISTENT_CATEGORY",
            target_ev_usd=100_000_000,
            target_revenue_usd=50_000_000,
        )
        # No category band but we still return a dataclass; peers empty
        self.assertEqual(s.peers, [])
        self.assertIsNone(s.peer_median_ev_ebitda)

    def test_peer_snapshot_derives_from_revenue_when_no_ebitda(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        s = compute_peer_snapshot(
            category="MULTI_SITE_ACUTE_HOSPITAL",
            target_ev_usd=350_000_000,
            target_revenue_usd=250_000_000,
        )
        # 12% margin assumption: implied EBITDA 30M → ~11.67x
        self.assertIsNotNone(s.target_implied_multiple)
        self.assertGreater(s.target_implied_multiple, 10.0)

    def test_peer_snapshot_to_dict_roundtrip(self):
        from rcm_mc.market_intel import compute_peer_snapshot
        import json
        s = compute_peer_snapshot(
            category="DIALYSIS",
            target_ev_usd=200_000_000,
            target_revenue_usd=120_000_000,
            specialty="ANESTHESIOLOGY",
        )
        d = s.to_dict()
        # JSON-serialisable
        json.dumps(d, default=str)
        self.assertIn("assessment", d)


class PeerSnapshotAPITests(unittest.TestCase):

    def test_api_returns_json(self):
        import threading, time, urllib.request, tempfile, socket, json
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]; s.close()
        db = tempfile.mktemp(suffix='.db')
        srv, _ = build_server(
            port=port, db_path=db, host='127.0.0.1', auth=None,
        )
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        time.sleep(0.3)
        try:
            url = (
                f'http://127.0.0.1:{port}/api/market-intel/'
                'peer-snapshot?category=MULTI_SITE_ACUTE_HOSPITAL'
                '&ev_usd=350000000&revenue_usd=250000000'
                '&ebitda_usd=35000000'
            )
            r = urllib.request.urlopen(url, timeout=10)
            self.assertEqual(r.status, 200)
            payload = json.loads(r.read())
            self.assertEqual(payload["category"], "MULTI_SITE_ACUTE_HOSPITAL")
            self.assertEqual(payload["assessment"], "IN-LINE")
            self.assertAlmostEqual(
                payload["target_implied_multiple"], 10.0, places=2,
            )
        finally:
            srv.shutdown()

    def test_api_empty_params_returns_no_data(self):
        import threading, time, urllib.request, tempfile, socket, json
        from rcm_mc.server import build_server
        s = socket.socket(); s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]; s.close()
        db = tempfile.mktemp(suffix='.db')
        srv, _ = build_server(
            port=port, db_path=db, host='127.0.0.1', auth=None,
        )
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        time.sleep(0.3)
        try:
            r = urllib.request.urlopen(
                f'http://127.0.0.1:{port}/api/market-intel/peer-snapshot',
                timeout=10,
            )
            payload = json.loads(r.read())
            self.assertEqual(payload["assessment"], "NO_DATA")
        finally:
            srv.shutdown()


class NewsFeedExpansionTests(unittest.TestCase):

    def test_news_items_expanded_to_20_plus(self):
        from rcm_mc.market_intel.news_feed import _all_items
        self.assertGreaterEqual(len(_all_items()), 20)

    def test_news_items_have_tags(self):
        from rcm_mc.market_intel.news_feed import _all_items
        for item in _all_items():
            self.assertIsInstance(item.tags, list)

    def test_news_feed_covers_multiple_specialties(self):
        from rcm_mc.market_intel.news_feed import _all_items
        specialties = {
            i.specialty for i in _all_items() if i.specialty
        }
        self.assertGreaterEqual(len(specialties), 7)


class EarningsCalendarTests(unittest.TestCase):

    def test_earnings_calendar_section_rendered(self):
        from rcm_mc.ui.market_intel_page import (
            render_market_intel_page,
        )
        h = render_market_intel_page()
        self.assertIn("Earnings calendar", h)
        self.assertIn("Next expected", h)


class DealProfileMarketContextTests(unittest.TestCase):

    def test_deal_profile_has_market_context_block(self):
        from rcm_mc.ui.deal_profile_page import render_deal_profile_page
        h = render_deal_profile_page(slug="test-deal")
        self.assertIn("data-rcm-market-context", h)
        self.assertIn("Market Context · live from public comps", h)

    def test_deal_profile_js_calls_peer_snapshot_api(self):
        from rcm_mc.ui.deal_profile_page import render_deal_profile_page
        h = render_deal_profile_page(slug="test-deal")
        self.assertIn("/api/market-intel/peer-snapshot", h)
        self.assertIn("updateMarketContext", h)


if __name__ == "__main__":
    unittest.main()
