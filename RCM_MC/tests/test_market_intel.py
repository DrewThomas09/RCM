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


if __name__ == "__main__":
    unittest.main()
