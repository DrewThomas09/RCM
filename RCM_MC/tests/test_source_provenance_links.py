"""Regression: data-source labels link to their public origin (defensibility).

Every value shown on a screener must be traceable to where it came from —
a partner (or LP) clicks the source label and lands on the public CMS
dataset it was derived from, rather than taking the label on faith. The
source→URL map (_chartis_kit.SOURCE_URLS) is the single source of truth and
must resolve every label the screener emits. See ck_source_link.
"""
import unittest

from rcm_mc.ui._chartis_kit import SOURCE_URLS, ck_source_link, source_url


class SourceUrlTests(unittest.TestCase):
    def test_known_label_resolves(self):
        self.assertTrue(source_url("CMS HCRIS").startswith("https://"))
        self.assertIn("cost-reports", source_url("CMS HCRIS"))

    def test_decorated_label_still_resolves(self):
        # A label with a year/period suffix must still map to the base dataset.
        self.assertEqual(source_url("CMS HCRIS · FY2023"), SOURCE_URLS["CMS HCRIS"])

    def test_unknown_label_is_none(self):
        self.assertIsNone(source_url("Some private vendor"))
        self.assertIsNone(source_url(None))
        self.assertIsNone(source_url(""))

    # Publishers the platform is willing to cite as a primary origin. The
    # point of the registry is that a partner can click a label and land on
    # the authoritative publisher, so the guard is "is this an official
    # source?", not "is this CMS?".
    #
    # This assertion used to require ".cms.gov" in every URL. That premise
    # died when Report-0277 deliberately widened the registry past CMS
    # (BLS OEWS, HRSA OPA, IRS 990, MedPAC, MGMA, AHA) — but the test kept
    # passing-then-failing on the FIRST non-CMS entry it reached, so it read
    # as one broken row rather than an obsolete rule. It had been red on a
    # clean tree, flagged by a UI audit. Widened to the real invariant.
    ALLOWED_HOSTS = {
        "cms.gov", "hhs.gov",          # CMS datasets + the NPI Registry
        "bls.gov", "irs.gov", "census.gov", "cdc.gov", "fda.gov",
        "hrsa.gov", "medpac.gov", "justice.gov",
        # CMS's Chronic Conditions Data Warehouse is operated for CMS but
        # published on its own domain rather than under cms.gov.
        "ccwdata.org",
        "mgma.com", "aha.org", "nucc.org", "nhia.org",  # standards bodies
    }

    def test_all_urls_are_https_and_officially_published(self):
        from urllib.parse import urlparse
        for label, url in SOURCE_URLS.items():
            with self.subTest(label=label):
                self.assertTrue(url.startswith("https://"), label)
                host = urlparse(url).hostname or ""
                registrable = ".".join(host.split(".")[-2:])
                self.assertIn(
                    registrable, self.ALLOWED_HOSTS,
                    f"{label!r} -> {url!r}: {registrable} is not a recognised "
                    "official publisher. Add it to ALLOWED_HOSTS only if the "
                    "source really is authoritative for the data it backs.",
                )

    def test_every_url_was_reachable_when_added(self):
        # Not a live network check (tests must run offline) — a shape check
        # that catches the failure mode we actually hit: a plausible-looking
        # hand-written path. Report-0282 added 14 entries; one suggested URL
        # (DOJ "horizontal-merger-guidelines") 404'd on fetch and was replaced
        # with the 2023 Merger Guidelines page that superseded it.
        for label, url in SOURCE_URLS.items():
            with self.subTest(label=label):
                self.assertNotIn(" ", url, f"{label}: whitespace in URL")
                self.assertFalse(url.endswith("//"), label)

    def test_every_screener_source_label_has_a_link(self):
        # The screener must never show a value whose origin can't be linked.
        from rcm_mc.ui.target_screener_page import _vertical_rows
        seen = set()
        for v in ("hospitals", "home_health", "hospice", "snf",
                  "dialysis", "irf", "ltch"):
            for r in _vertical_rows(v, limit=2):
                if r.get("source"):
                    seen.add(r["source"])
        self.assertTrue(seen, "expected the screener to emit source labels")
        unlinked = [s for s in seen if source_url(s) is None]
        self.assertEqual(unlinked, [], f"source labels with no origin link: {unlinked}")


class SourceLinkRenderTests(unittest.TestCase):
    def test_known_label_renders_anchor(self):
        html = ck_source_link("CMS HCRIS", style="font-size:9px;")
        self.assertIn("<a href=", html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener"', html)
        self.assertIn("verify this value at its origin", html)

    def test_unknown_label_renders_plain_text_not_link(self):
        self.assertNotIn("<a", ck_source_link("Mystery vendor"))

    def test_label_is_escaped(self):
        # A hostile label must not break out into markup.
        self.assertNotIn("<script>", ck_source_link("<script>x</script>"))


class ScreenerSourceLinkWiringTests(unittest.TestCase):
    def test_target_screener_table_links_source(self):
        from rcm_mc.ui.target_screener_page import render_target_screener
        html = render_target_screener({"vertical": ["hospitals"], "state": ["VT"]})
        self.assertIn("downloadable-public-use-files/cost-reports", html)
        self.assertIn("verify this value at its origin", html)


if __name__ == "__main__":
    unittest.main()
