"""Deal Library page (/deal-library) — renders the licensed company universe.

Uses the synthetic CapIQ fixture (no licensed data). Verifies the honest empty
state, the populated view (summary, missingness, frequency tables, sortable
table, pagination), filter/search, and that it is a benchmark library distinct
from Pipeline/Portfolio. Also guards that the old /library seed-corpus page
still imports/renders.
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


class TestDealLibraryPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PortfolioStore(os.path.join(self.tmp.name, "t.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def _load(self):
        recs, info = ing.ingest_file(_FIXTURE, source_system="Capital IQ")
        ing.flag_duplicates(recs)
        rep = ing.build_report(recs, [info], "Capital IQ")
        out = Path(self.tmp.name)
        ing.write_outputs(recs, rep, out)
        return dl.load_companies_csv(self.store, out / "deal_library_companies.csv")

    def test_empty_state_when_no_data(self):
        html = render_deal_library(self.store, {})
        self.assertIn("Deal Library is empty", html)
        self.assertIn("ingest_deal_library_exports", html)
        # honest: no fabricated rows
        self.assertNotIn("ck-pager", html)

    def test_populated_view(self):
        self.assertEqual(self._load(), 4)
        html = render_deal_library(self.store, {})
        self.assertIn("BENCHMARK COMPANY LIBRARY", html)
        self.assertIn("not your Pipeline", html)
        self.assertIn("Top sponsors", html)
        self.assertIn("missing", html)               # missingness surfaced
        self.assertIn("Synthetic Capital", html)      # sponsor present
        self.assertIn("—", html)                       # missing financials as dash

    def test_search_filters_rows(self):
        self._load()
        html = render_deal_library(self.store, {"search": "Dialysis"})
        self.assertIn("Beacon Dialysis", html)
        self.assertIn("Showing 1", html)

    def test_state_filter(self):
        self._load()
        html = render_deal_library(self.store, {"state": "tx"})
        self.assertIn("Acme Health", html)

    def test_in_library_subnav_and_breadcrumb_map(self):
        from rcm_mc.ui._chartis_kit import _SUB_NAV, _SUB_SECTION_MAP
        hrefs = [x["href"] for x in _SUB_NAV["library"]]
        self.assertIn("/deal-library", hrefs)
        self.assertEqual(_SUB_SECTION_MAP.get("/deal-library"), "library")

    def test_old_seed_library_still_renders(self):
        # /library (illustrative seed corpus) must keep working.
        from rcm_mc.ui.data_public.deals_library_page import render_deals_library
        html = render_deals_library()
        self.assertIn("ck-topbar", html)


if __name__ == "__main__":
    unittest.main()
