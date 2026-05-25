"""Deal Library sponsor intelligence — the dense, validated dimension.

99% of the licensed universe carries a parsed sponsor, so the high-value use is
a sponsor → portfolio / sourcing map. Tests the sponsor_index + sponsor_rollup
read API and the page's sponsor drill-down, on the synthetic fixture.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
import ingest_deal_library_exports as ing  # noqa: E402
from rcm_mc.data import deal_library as dl  # noqa: E402
from rcm_mc.ui.deal_library_page import render_deal_library  # noqa: E402
from rcm_mc.portfolio.store import PortfolioStore  # noqa: E402

_FIXTURE = _ROOT / "tests" / "fixtures" / "deal_library_capiq_sample.csv"


class TestSponsorIntel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "t.db"))
        recs, info = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        ing.flag_duplicates(recs)
        out = Path(self.tmp.name)
        ing.write_outputs(recs, ing.build_report(recs, [info], "Capital IQ"), out)
        dl.load_companies_csv(self.store, out / "deal_library_companies.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sponsor_index_counts_and_split(self):
        idx = dl.sponsor_index(self.store, limit=10, min_companies=1)
        top = {r["sponsor"]: r for r in idx}
        # 'Synthetic Capital' backs 3 fixture companies.
        self.assertIn("Synthetic Capital", top)
        self.assertEqual(top["Synthetic Capital"]["n_total"], 3)
        self.assertGreaterEqual(top["Synthetic Capital"]["n_current"], 1)
        # index is ranked descending by n_total
        counts = [r["n_total"] for r in idx]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_min_companies_threshold(self):
        big = dl.sponsor_index(self.store, min_companies=3)
        self.assertTrue(all(r["n_total"] >= 3 for r in big))

    def test_sponsor_rollup_footprint(self):
        roll = dl.sponsor_rollup(self.store, "Synthetic Capital")
        self.assertEqual(roll["n_total"], 3)
        self.assertGreaterEqual(roll["n_prior"], 1)   # Acme lists a prior sponsor
        self.assertTrue(roll["top_states"])

    def test_unknown_sponsor_returns_zero_not_invented(self):
        roll = dl.sponsor_rollup(self.store, "Nonexistent Fund XYZ")
        self.assertEqual(roll["n_total"], 0)
        self.assertEqual(roll["top_states"], [])

    def test_page_renders_rollup_and_clickable_sponsors(self):
        # Unfiltered: Top sponsors link to the filtered view.
        html = render_deal_library(self.store, {})
        self.assertIn("/deal-library?sponsor=", html)
        # Filtered: rollup card appears.
        html2 = render_deal_library(self.store, {"sponsor": "Synthetic Capital"})
        self.assertIn("Sponsor footprint", html2)
        self.assertIn("Synthetic Capital", html2)
        self.assertIn("healthcare companies", html2)


if __name__ == "__main__":
    unittest.main()
