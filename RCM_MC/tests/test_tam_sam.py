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


class IndustryDeepDiveTests(unittest.TestCase):
    """The deep-dive layer under the sizing build — real CMS data, never
    fabricated. Dialysis is the first industry in the sprint."""

    def test_dialysis_dive_aggregates_real_facilities(self):
        from rcm_mc.diligence.industry_deep_dive import dialysis_deep_dive
        d = dialysis_deep_dive()
        self.assertGreater(d["n_facilities"], 7000)   # 7.5K CMS facilities
        self.assertEqual(d["top_states"][0]["state"], "TX")
        # The duopoly is the defining market structure — pin it visible.
        self.assertGreater(d["duopoly_share"], 0.5)
        self.assertGreater(d["n_independent"], 500)
        # Whitespace ranked by independent count, all real states.
        self.assertTrue(all(s["independent"] > 0
                            for s in d["whitespace_states"][:3]))

    def test_unknown_industry_returns_none_not_500(self):
        from rcm_mc.diligence.industry_deep_dive import deep_dive_for
        self.assertIsNone(deep_dive_for("fertility_ivf"))
        self.assertIsNone(deep_dive_for("nope"))

    def test_dialysis_page_renders_dive_panels(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["dialysis"]})
        self.assertIn("State footprint", h)
        self.assertIn("Consolidation map", h)
        self.assertIn("What this sector traded for", h)
        self.assertIn("independent facilities", h)
        # Drill links into the live surfaces.
        self.assertIn("/deal-search?sector=dialysis", h)
        self.assertIn("/target-screener?vertical=dialysis", h)

    def test_growth_drivers_show_directionality(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["dialysis"]})
        self.assertIn("▲", h)   # tailwinds
        self.assertIn("▼", h)   # the home-shift headwind, shown as one


class HomeHealthIndustryTests(unittest.TestCase):
    """Industry #2 in the sprint — HH agencies + star ratings + the
    density whitespace (agencies per 10K seniors from real ACS data)."""

    def test_hh_template_math(self):
        from rcm_mc.diligence.tam_sam import compute, home_health_template
        out = compute(home_health_template())
        # 67M × 5% × 2.9 × $2,010 ≈ $19.5B — anchors to MedPAC HH spend.
        self.assertAlmostEqual(
            out["tam"], 67_000_000 * 0.05 * 2.9 * 2_010, places=2)
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["PDGM / rate pressure"], 0)   # headwind shown

    def test_hh_dive_real_aggregates(self):
        from rcm_mc.diligence.industry_deep_dive import home_health_deep_dive
        d = home_health_deep_dive()
        self.assertGreater(d["n_facilities"], 12_000)
        self.assertEqual(d["top_states"][0]["state"], "CA")
        self.assertGreater(d["n_independent"], 8_000)   # for-profit pool
        # Density whitespace: lowest agencies-per-10K-seniors first, all
        # real ACS-derived values.
        ws = d["whitespace_states"]
        self.assertTrue(all(w["per_10k_seniors"] > 0 for w in ws))
        self.assertLessEqual(ws[0]["per_10k_seniors"],
                             ws[-1]["per_10k_seniors"])
        self.assertNotIn("-", [c["org"] for c in d["chains"]])

    def test_hh_page_renders_dive(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["home_health"]})
        self.assertIn("State footprint", h)
        self.assertIn("Star rating", h)
        self.assertIn("per 10K seniors", h)
        self.assertIn("/deal-search?sector=home_health", h)

    def test_dialysis_panels_unaffected_by_generalization(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["dialysis"]})
        self.assertIn("Stations", h)
        self.assertIn("Hosp. rate", h)
        self.assertIn("independent facilities", h)


class HospiceIndustryTests(unittest.TestCase):
    """Industry #3 — hospice: the most PE-penetrated post-acute vertical,
    with the CA license glut visible in the density read."""

    def test_hospice_template_math(self):
        from rcm_mc.diligence.tam_sam import compute, hospice_template
        out = compute(hospice_template())
        # 1.72M users × 80 days × $185/day ≈ $25.5B (MedPAC magnitude).
        self.assertAlmostEqual(
            out["tam"], 1_720_000 * 80 * 185, places=2)
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["Program-integrity scrutiny"], 0)

    def test_hospice_dive_real_aggregates(self):
        from rcm_mc.diligence.industry_deep_dive import hospice_deep_dive
        d = hospice_deep_dive()
        self.assertGreater(d["n_facilities"], 6_500)
        self.assertEqual(d["top_states"][0]["state"], "CA")  # the glut
        self.assertGreater(d["n_independent"], 4_000)        # for-profit
        ws = d["whitespace_states"]
        self.assertTrue(all(w["per_10k_seniors"] > 0 for w in ws))
        self.assertNotIn("-", [c["org"] for c in d["chains"]])

    def test_hospice_page_renders_dive(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["hospice"]})
        self.assertIn("State footprint", h)
        self.assertIn("Care index", h)
        self.assertIn("/deal-search?sector=hospice", h)


class SnfIndustryTests(unittest.TestCase):
    """Industry #4 — SNF: the richest CMS file (real beds, occupancy,
    CHOW flags). The base TAM driver is the ACTUAL certified-bed count."""

    def test_snf_template_math(self):
        from rcm_mc.diligence.tam_sam import compute, snf_template
        out = compute(snf_template())
        # 1.569M beds × 77% × 365 × $300 ≈ $132B — the known industry size.
        self.assertAlmostEqual(
            out["tam"], 1_569_000 * 0.77 * 365 * 300, places=2)
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["Staffing mandate / labor"], 0)

    def test_snf_dive_real_aggregates(self):
        from rcm_mc.diligence.industry_deep_dive import snf_deep_dive
        d = snf_deep_dive()
        self.assertGreater(d["n_facilities"], 14_000)
        # Real capacity: the bed total matches the vendored file.
        self.assertEqual(sum(s["stations"] for s in d["states"]), 1_569_384)
        self.assertEqual(d["top_states"][0]["state"], "TX")
        self.assertGreater(d["n_independent"], 10_000)   # for-profit
        # Whitespace = beds per 10K seniors ascending; the under-bedded
        # Western (HCBS-shift) states surface first.
        ws = d["whitespace_states"]
        self.assertLessEqual(ws[0]["per_10k_seniors"],
                             ws[-1]["per_10k_seniors"])
        self.assertIn(ws[0]["state"], ("AK", "AZ", "OR", "NV", "WA", "HI"))

    def test_snf_page_renders_dive(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["snf"]})
        self.assertIn("State footprint", h)
        self.assertIn("Beds", h)
        self.assertIn("changed ownership", h)   # the CHOW signal
        self.assertIn("/target-screener?vertical=snf", h)


class IrfLtchAndPolishTests(unittest.TestCase):
    """Industries #5–6 (IRF, LTCH) + the professionalism layer: numbered
    source footnotes, the TAM/SAM/SOM projection graph, and the Sources
    sheet in the Excel export."""

    def test_irf_and_ltch_templates(self):
        from rcm_mc.diligence.tam_sam import compute, irf_template, ltch_template
        irf = compute(irf_template())
        self.assertAlmostEqual(irf["tam"], 370_000 * 22_000, places=2)
        ltch = compute(ltch_template())
        self.assertAlmostEqual(ltch["tam"], 78_000 * 45_000, places=2)
        # LTCH is a structurally shrinking market — the tool sizes honest
        # declines: composite growth is NEGATIVE.
        self.assertLess(ltch["composite_cagr_pct"], 0)

    def test_irf_ltch_dives_real_aggregates(self):
        from rcm_mc.diligence.industry_deep_dive import (
            irf_deep_dive, ltch_deep_dive,
        )
        irf = irf_deep_dive()
        self.assertGreater(irf["n_facilities"], 1_200)
        self.assertEqual(irf["top_states"][0]["state"], "TX")
        ltch = ltch_deep_dive()
        self.assertGreater(ltch["n_facilities"], 300)
        self.assertGreater(ltch["n_independent"], 200)  # for-profit pool

    def test_every_template_renders_chart_and_footnotes(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        for key in TEMPLATES:
            h = render_tam_sam_page({"template": [key]})
            self.assertIn('aria-label="TAM SAM SOM projection"', h, key)
            self.assertIn("Sources", h, key)

    def test_xlsx_gains_sources_sheet(self):
        from rcm_mc.ui.tam_sam_page import tam_sam_xlsx
        data = tam_sam_xlsx({"template": ["snf"]})
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertIn("xl/worksheets/sheet4.xml", z.namelist())
        # The sheet carries the actual source strings.
        self.assertIn(b"MedPAC", z.read("xl/worksheets/sheet4.xml"))
