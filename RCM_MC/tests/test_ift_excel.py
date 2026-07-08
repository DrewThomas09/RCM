"""Real-path tests for the IFT market-study Excel workbook (/api/ift/markets.xlsx).

Pins that the workbook always builds a real, openable .xlsx (a zip of XML parts)
carrying every analytic layer by market, and that it degrades — never raises —
when an analytic is unavailable, because the download must always succeed.
"""
from __future__ import annotations

import io
import unittest
import zipfile

from rcm_mc.market_reports.ift_excel import ift_workbook_xlsx


class IftWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.data = ift_workbook_xlsx()

    def test_returns_a_real_xlsx_zip(self):
        self.assertIsInstance(self.data, bytes)
        self.assertGreater(len(self.data), 5000)
        self.assertEqual(self.data[:2], b"PK")            # zip magic
        z = zipfile.ZipFile(io.BytesIO(self.data))
        names = z.namelist()
        self.assertIn("xl/workbook.xml", names)
        self.assertIn("[Content_Types].xml", names)
        self.assertIsNone(z.testzip())                     # not corrupt

    def _sheet_names(self):
        z = zipfile.ZipFile(io.BytesIO(self.data))
        import re
        wb = z.read("xl/workbook.xml").decode()
        return re.findall(r'name="([^"]+)"', wb)

    def test_carries_the_full_market_study_spine(self):
        names = self._sheet_names()
        # the funnel + every deepened analytic layer is present as its own sheet
        for expected in ("Overview", "TAM build", "SAM health systems",
                         "SOM footprint", "Markets structure", "Competitive",
                         "Insourcing", "Moat scorecard", "Clinical demand",
                         "Three-lever tracker", "Provenance"):
            self.assertIn(expected, names, f"missing sheet: {expected}")

    def test_provenance_sheet_always_present(self):
        # the honesty legend is the one sheet that must never drop
        self.assertIn("Provenance", self._sheet_names())

    def test_deterministic_and_repeatable(self):
        # cached analytics -> two builds are byte-identical (no Date.now drift)
        self.assertEqual(ift_workbook_xlsx(), ift_workbook_xlsx())

    def test_degrades_when_an_analytic_is_unavailable(self):
        # If a layer raises, its sheet is skipped but the workbook still builds.
        import rcm_mc.market_reports.ift_excel as X

        orig = X._an.health_system_sam
        try:
            X._an.health_system_sam = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
            data = ift_workbook_xlsx()
        finally:
            X._an.health_system_sam = orig
        self.assertEqual(data[:2], b"PK")
        self.assertGreater(len(data), 5000)


if __name__ == "__main__":
    unittest.main()
