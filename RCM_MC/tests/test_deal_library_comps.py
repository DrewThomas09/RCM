"""Deal Library disclosed-financial multiples (/deal-library/comps).

The only honestly-supportable financial use of this export: EV/Revenue and
EV/EBITDA over the small subset that discloses both, with positive
denominators. Missing must be EXCLUDED (never 0), the sample size shown, and no
prediction implied.
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
from rcm_mc.ui.deal_library_page import render_deal_comps  # noqa: E402
from rcm_mc.portfolio.store import PortfolioStore  # noqa: E402

_FIXTURE = _ROOT / "tests" / "fixtures" / "deal_library_capiq_sample.csv"


class TestMultiples(unittest.TestCase):
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

    def test_multiples_summary_excludes_missing(self):
        # Fixture: only "Beacon Dialysis" has EV(1250)+revenue(310); EBITDA is
        # negative (-15.5) so EV/EBITDA must be excluded (no positive denom).
        s = dl.multiples_summary(self.store)
        self.assertEqual(s["ev_revenue"]["n"], 1)
        self.assertAlmostEqual(s["ev_revenue"]["median"], round(1250.0 / 310.0, 2))
        self.assertEqual(s["ev_ebitda"]["n"], 0)        # negative EBITDA excluded
        self.assertIsNone(s["ev_ebitda"]["median"])

    def test_companies_with_multiples(self):
        res = dl.companies_with_multiples(self.store)
        self.assertEqual(res["total"], 1)
        row = res["rows"][0]
        self.assertEqual(row["company_name"], "Beacon Dialysis Inc.")
        self.assertAlmostEqual(row["ev_revenue_multiple"], round(1250.0 / 310.0, 2))
        self.assertIsNone(row["ev_ebitda_multiple"])    # negative → not computed, not 0

    def test_page_renders_with_caveat_and_sample_size(self):
        html = render_deal_comps(self.store, {})
        self.assertIn("DISCLOSED-FINANCIAL MULTIPLES", html)
        self.assertIn("never treated as zero", html)    # honesty caveat
        self.assertIn("not a curated comp set", html)
        self.assertIn("n=", html)                         # sample size shown
        self.assertIn("Beacon Dialysis", html)

    def test_empty_state(self):
        empty = PortfolioStore(os.path.join(self.tmp.name, "e.db"))
        self.assertIn("No data yet", render_deal_comps(empty, {}))


if __name__ == "__main__":
    unittest.main()
