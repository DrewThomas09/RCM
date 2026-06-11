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
        # fertility gained a deals-only dive in W2-65 — only truly
        # unregistered keys return None now.
        self.assertIsNone(deep_dive_for("nope"))
        self.assertIsNone(deep_dive_for("blank"))

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


class BehavioralAscIndustryTests(unittest.TestCase):
    """Industries #7–8 — behavioral health + ASC: SAMHSA/CMS-anchored
    chains, deals-only dives (no CMS facility file → geography omitted
    rather than fabricated)."""

    def test_bh_and_asc_chains(self):
        from rcm_mc.diligence.tam_sam import (
            asc_template, behavioral_health_template, compute,
        )
        bh = compute(behavioral_health_template())
        self.assertAlmostEqual(bh["tam"], 59_000_000 * 0.5 * 3_000,
                               places=2)
        names = {g["name"]: g["annual_pct"] for g in bh["growth_drivers"]}
        self.assertLess(names["Clinician workforce shortage"], 0)
        asc = compute(asc_template())
        self.assertAlmostEqual(asc["tam"], 6_300 * 3_650 * 2_000, places=2)

    def test_deals_only_dive_no_fabricated_geography(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        for key in ("behavioral_health", "asc"):
            h = render_tam_sam_page({"template": [key]})
            self.assertIn("What this sector traded for", h, key)
            self.assertNotIn("State footprint", h, key)
            self.assertIn("rather than fabricated", h, key)


class FourMoreVerticalsTests(unittest.TestCase):
    """Industries #9–12 — physician groups, dental, oncology, urgent
    care. All chains anchored to named public sources; deals-only dives."""

    def test_all_four_chains_pin_to_public_magnitudes(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "physician_group": 580_000 * 0.42 * 750_000,
            "dental": 165e9 * 0.95,
            "oncology": 2_000_000 * 0.55 * 150_000,
            "urgent_care": 14_000 * 14_600 * 165,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            # Every template carries at least one honest headwind.
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)

    def test_every_registered_template_renders(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        for key in TEMPLATES:
            h = render_tam_sam_page({"template": [key]})
            self.assertIn("TAM / SAM Builder", h, key)
            self.assertIn("Sources", h, key)

    def test_every_template_exports_valid_xlsx(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        from rcm_mc.ui.tam_sam_page import tam_sam_xlsx
        for key in TEMPLATES:
            data = tam_sam_xlsx({"template": [key]})
            z = zipfile.ZipFile(io.BytesIO(data))
            self.assertIsNone(z.testzip(), key)


class SensitivityTornadoTests(unittest.TestCase):
    def test_sensitivity_math(self):
        from rcm_mc.diligence.tam_sam import (
            fertility_ivf_template, sensitivity,
        )
        rows = sensitivity(fertility_ivf_template())
        self.assertEqual(len(rows), 4)            # one bar per driver
        base = 3_660_000 * 0.023 * 2.5 * 20_000
        for r in rows:
            self.assertLess(r["tam_low"], base)
            self.assertGreater(r["tam_high"], base)
        # Sorted by impact descending.
        self.assertGreaterEqual(rows[0]["impact"], rows[-1]["impact"])

    def test_rate_clamps_at_100pct(self):
        # A 95% rate swung +20% must clamp at 100%, not reach 114%.
        from rcm_mc.diligence.tam_sam import (
            DriverStep, TamSamModel, sensitivity,
        )
        m = TamSamModel(name="t", chain=[
            DriverStep("base", 100.0, op="base"),
            DriverStep("rate", 0.95, op="rate"),
            DriverStep("price", 10.0, op="price"),
        ])
        rows = sensitivity(m)
        rate_row = next(r for r in rows if r["name"] == "rate")
        self.assertAlmostEqual(rate_row["tam_high"], 100 * 1.0 * 10,
                               places=6)

    def test_tornado_renders(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["snf"]})
        self.assertIn("Driver sensitivity", h)
        self.assertIn('aria-label="Driver sensitivity tornado"', h)


class HospitalsFlagshipTests(unittest.TestCase):
    """Industry #13 — hospitals, the flagship: the dive is computed from
    the real HCRIS universe (state NPR in filed dollars, size-tier
    structure, margin medians), and the cross-industry comparison panel
    shows every vertical side by side."""

    def test_hospitals_chain(self):
        from rcm_mc.diligence.tam_sam import compute, hospitals_template
        out = compute(hospitals_template())
        self.assertAlmostEqual(out["tam"], 1.4e12 * 0.62, places=2)

    def test_hcris_dive_real_dollars(self):
        from rcm_mc.diligence.industry_deep_dive import hospitals_deep_dive
        d = hospitals_deep_dive()
        self.assertEqual(d["n_facilities"], 6123)     # the HCRIS universe
        self.assertEqual(d["top_states"][0]["state"], "CA")
        self.assertGreater(d["top_states"][0]["npr"], 1e11)  # $154B real
        # Size tiers (HCRIS has no ownership field — size is the honest
        # structure read); the mid-size pool is the PE-able middle.
        tier_names = [c["org"] for c in d["chains"]]
        self.assertIn("Mid-size ($250M–$1B)", tier_names)
        self.assertGreater(d["n_independent"], 1000)
        # Margin medians within the plausibility band, in percent points.
        for st, q in d["quality_by_state"].items():
            self.assertGreaterEqual(q["value"], -40.0, st)
            self.assertLessEqual(q["value"], 30.0, st)

    def test_cross_industry_comparison_panel(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["hospitals"]})
        self.assertIn("Cross-industry view", h)
        # Every sized template appears as a linked row.
        self.assertGreaterEqual(
            h.count("/diligence/tam-sam?template="), 14)


class SegmentDivergenceTests(unittest.TestCase):
    """Per-segment growth — the within-industry 'where it's growing
    fastest' map (autism/IDD at +10% vs psych inpatient at +1%)."""

    def test_segment_growth_math(self):
        from rcm_mc.diligence.tam_sam import (
            behavioral_health_template, compute,
        )
        out = compute(behavioral_health_template())
        autism = next(s for s in out["segments"]
                      if s["name"].startswith("Autism"))
        self.assertTrue(autism.get("is_fastest"))
        self.assertAlmostEqual(
            autism["tam_y_final"],
            autism["tam_value"] * 1.10 ** 5, places=2)

    def test_columns_only_when_growth_set(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["behavioral_health"]})
        self.assertIn("Growth %/yr", h)
        self.assertIn("★", h)
        # Templates without per-segment growth keep the lean table.
        h2 = render_tam_sam_page({"template": ["snf"]})
        self.assertNotIn("Growth %/yr", h2)


class ScenarioPresetTests(unittest.TestCase):
    """One-click Conservative / Base / Aggressive — Conservative halves
    tailwinds and amplifies headwinds ×1.5; Aggressive mirrors; typed
    driver overrides always win."""

    def test_scenarios_order(self):
        from rcm_mc.diligence.tam_sam import compute
        from rcm_mc.ui.tam_sam_page import model_from_qs
        vals = {}
        for s in ("conservative", "base", "aggressive"):
            out = compute(model_from_qs(
                {"template": ["behavioral_health"], "scenario": [s]}))
            vals[s] = out["composite_cagr_pct"]
        self.assertLess(vals["conservative"], vals["base"])
        self.assertLess(vals["base"], vals["aggressive"])

    def test_typed_override_beats_scenario(self):
        from rcm_mc.ui.tam_sam_page import model_from_qs
        m = model_from_qs({"template": ["behavioral_health"],
                           "scenario": ["conservative"],
                           "growth0": ["9.0"]})
        self.assertEqual(m.growth_drivers[0].annual_pct, 9.0)

    def test_scenario_chips_render(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["snf"],
                                 "scenario": ["aggressive"]})
        self.assertIn("scenario=conservative", h)
        self.assertIn("scenario=base", h)


class ExportParityTests(unittest.TestCase):
    """The exports carry everything the page shows — segment divergence
    columns and the scenario tag (a deal team must never get a thinner
    file than the screen)."""

    def test_csv_carries_divergence(self):
        from rcm_mc.ui.tam_sam_page import tam_sam_csv
        out = tam_sam_csv({"template": ["behavioral_health"]})
        self.assertIn("Growth %/yr", out)
        self.assertIn("Y5 slice", out)

    def test_xlsx_carries_divergence_and_scenario(self):
        from rcm_mc.ui.tam_sam_page import tam_sam_xlsx
        data = tam_sam_xlsx({"template": ["behavioral_health"],
                             "scenario": ["aggressive"]})
        z = zipfile.ZipFile(io.BytesIO(data))
        self.assertIsNone(z.testzip())
        self.assertIn(b"AGGRESSIVE scenario",
                      z.read("xl/worksheets/sheet1.xml"))
        self.assertIn(b"Growth %/yr", z.read("xl/worksheets/sheet2.xml"))


class PayerDimensionTests(unittest.TestCase):
    """State × payer — the hospitals dive carries filed Medicare day-share
    state medians from HCRIS; fertility gains its real trade history."""

    def test_hospitals_medicare_mix_medians(self):
        from rcm_mc.diligence.industry_deep_dive import hospitals_deep_dive
        d = hospitals_deep_dive()
        with_mix = [s for s in d["top_states"]
                    if s.get("medicare_mix_med") is not None]
        self.assertGreater(len(with_mix), 5)
        for s in with_mix:
            self.assertGreaterEqual(s["medicare_mix_med"], 0.0)
            self.assertLessEqual(s["medicare_mix_med"], 1.0)

    def test_payer_column_only_where_computed(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        self.assertIn("Medicare mix (med)",
                      render_tam_sam_page({"template": ["hospitals"]}))
        self.assertNotIn("Medicare mix (med)",
                         render_tam_sam_page({"template": ["dialysis"]}))

    def test_fertility_trade_history(self):
        from rcm_mc.diligence.industry_deep_dive import fertility_deep_dive
        f = fertility_deep_dive()
        self.assertGreaterEqual(f["sector_deals"]["n"], 2)


class ChainHHITests(unittest.TestCase):
    """Chain-concentration HHI (DOJ/FTC) — only over named operators."""

    def test_dialysis_hhi_highly_concentrated(self):
        from rcm_mc.diligence.industry_deep_dive import (
            _chain_hhi, dialysis_deep_dive,
        )
        d = dialysis_deep_dive()
        hhi = _chain_hhi(d["chains"], d["pool_label"])
        # DaVita + Fresenius ~37% each → well over the 2,500 "highly
        # concentrated" DOJ threshold.
        self.assertGreater(hhi, 2500)

    def test_hhi_none_for_ownership_buckets(self):
        # SNF/HH/hospice chains are ownership/size buckets, not operators
        # — HHI is meaningless there and must not render.
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        for key in ("home_health", "hospice", "snf", "hospitals"):
            self.assertNotIn("Chain-concentration",
                             render_tam_sam_page({"template": [key]}), key)

    def test_dialysis_page_shows_hhi(self):
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        h = render_tam_sam_page({"template": ["dialysis"]})
        self.assertIn("Chain-concentration", h)
        self.assertIn("highly concentrated", h)
