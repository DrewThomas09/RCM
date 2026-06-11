"""TAM/SAM Builder — driver-tree market sizing + formatted exports.

The fertility/IVF template mirrors how CDD teams size that market: total
births → % via IVF → cycles per delivery → price per cycle, age-band
segments, TAM→SAM→SOM funnel, growth-driver-decomposed projection.
"""
from __future__ import annotations

import io
import os
import tempfile
import threading
import unittest
import urllib.request
import zipfile
import xml.etree.ElementTree as ET


class ModelTests(unittest.TestCase):
    def test_fertility_chain_math(self):
        from rcm_mc.diligence.tam_sam import compute, fertility_ivf_template
        out = compute(fertility_ivf_template())
        # 3.66M × 2.3% × 2.5 × $20K = $4.209B
        self.assertAlmostEqual(out["tam"], 3_660_000 * 0.023 * 2.5 * 20_000,
                               places=2)
        self.assertLess(out["sam"], out["tam"])
        self.assertLess(out["som"], out["sam"])
        # Audit trail: running value at every step.
        self.assertEqual(len(out["steps"]), 4)
        self.assertAlmostEqual(out["steps"][1]["running"],
                               3_660_000 * 0.023, places=2)

    def test_growth_decomposition_composes(self):
        from rcm_mc.diligence.tam_sam import (
            GrowthDriver, TamSamModel, DriverStep, compute,
        )
        m = TamSamModel(
            name="t",
            chain=[DriverStep("base", 100.0, op="base"),
                   DriverStep("price", 10.0, op="price")],
            growth_drivers=[GrowthDriver("a", 10.0), GrowthDriver("b", 10.0)],
            horizon_years=2,
        )
        out = compute(m)
        # (1.10 × 1.10) − 1 = 21% composite, NOT 20% — multiplicative.
        self.assertAlmostEqual(out["composite_cagr_pct"], 21.0, places=6)
        self.assertAlmostEqual(out["projection"][2]["tam"],
                               1000.0 * 1.21 ** 2, places=6)

    def test_segments_slice_tam(self):
        from rcm_mc.diligence.tam_sam import compute, fertility_ivf_template
        out = compute(fertility_ivf_template())
        total_share = sum(s["share_of_volume"] for s in out["segments"])
        self.assertAlmostEqual(total_share, 1.0, places=6)
        self.assertEqual(out["segments"][0]["name"], "<35")


class DialysisTemplateTests(unittest.TestCase):
    def test_dialysis_chain_math(self):
        from rcm_mc.diligence.tam_sam import compute, dialysis_template
        out = compute(dialysis_template())
        # 810K × 69% × 84% × 156 × $280
        self.assertAlmostEqual(
            out["tam"], 810_000 * 0.69 * 0.84 * 156 * 280, places=2)
        # Payer-mix segments sum to 1.0.
        self.assertAlmostEqual(
            sum(s["share_of_volume"] for s in out["segments"]), 1.0,
            places=6)
        # The home-shift headwind is carried as a NEGATIVE driver, not
        # netted away silently.
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["Home-modality shift"], 0)

    def test_template_selectable_on_page(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["dialysis"]})
        self.assertIn("US ESRD patients", h)
        self.assertIn("$20.51B", h)


class PageAndExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from rcm_mc.server import build_server
        cls._tmp = tempfile.TemporaryDirectory()
        db = os.path.join(cls._tmp.name, "t.db")
        cls.server, _ = build_server(port=0, db_path=db, host="127.0.0.1")
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever,
                         daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls._tmp.cleanup()

    def _get(self, path: str) -> bytes:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{path}", timeout=15) as r:
            return r.read()

    def test_page_renders_funnel_and_chain(self):
        h = self._get("/diligence/tam-sam").decode()
        self.assertIn("TAM / SAM Builder", h)
        self.assertIn("$4.21B", h)            # fertility template TAM
        self.assertIn("Driver chain", h)
        self.assertIn("38–40", h)             # age-band segments
        self.assertIn("Benefit expansion", h)  # named growth drivers

    def test_override_recomputes(self):
        # % via IVF 2.3 → 5.0 lifts TAM proportionally.
        h = self._get("/diligence/tam-sam?step1=5.0").decode()
        self.assertIn("$9.15B", h)

    def test_csv_export_carries_the_build(self):
        out = self._get("/api/diligence/tam-sam.csv").decode()
        self.assertIn("Total US births", out)
        self.assertIn("Composite CAGR", out)
        self.assertIn("Year", out)

    def test_xlsx_export_is_a_valid_formatted_workbook(self):
        data = self._get("/api/diligence/tam-sam.xlsx")
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertIsNone(z.testzip())
        names = z.namelist()
        for part in ("[Content_Types].xml", "xl/workbook.xml",
                     "xl/styles.xml", "xl/worksheets/sheet1.xml",
                     "xl/worksheets/sheet2.xml", "xl/worksheets/sheet3.xml"):
            self.assertIn(part, names)
        # Every part is well-formed XML, and the styles ship real number
        # formats (the "formatted" in formatted export).
        for n in names:
            ET.fromstring(z.read(n))
        self.assertIn(b"$#,##0", z.read("xl/styles.xml"))

    def test_hostile_overrides_never_500(self):
        for q in ("step0=NaN", "step1=-5", "sam_share=999",
                  "growth0=abc", "template=<script>"):
            h = self._get(f"/diligence/tam-sam?{q}").decode()
            self.assertIn("TAM / SAM Builder", h)


if __name__ == "__main__":
    unittest.main()
