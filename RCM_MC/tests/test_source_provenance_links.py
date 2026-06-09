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

    def test_all_urls_are_https_cms(self):
        for label, url in SOURCE_URLS.items():
            self.assertTrue(url.startswith("https://"), label)
            self.assertIn(".cms.gov", url, label)

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
