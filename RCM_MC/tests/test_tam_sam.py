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


class NicheVerticalsBatch1Tests(unittest.TestCase):
    """Industries #14–16 — infusion, imaging, physical therapy: the
    niche-vertical sprint. Public-source chains, divergence, real corpus
    trade history (geography omitted, never fabricated)."""

    def test_three_chains_pin_to_public_magnitudes(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "infusion": 3_200_000 * 18 * 650,
            "imaging": 7_000 * 21_000 * 280,
            "physical_therapy": 38_000 * 8_300 * 105,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            # Each carries a divergence map with a flagged fastest.
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_biosimilar_headwind_named(self):
        # The infusion template must carry the biosimilar deflation
        # headwind — the number-one diligence question in this vertical.
        from rcm_mc.diligence.tam_sam import compute, infusion_template
        out = compute(infusion_template())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["Biosimilar price deflation"], 0)

    def test_dives_carry_real_trade_history(self):
        from rcm_mc.diligence.industry_deep_dive import (
            imaging_deep_dive, infusion_deep_dive,
            physical_therapy_deep_dive,
        )
        self.assertGreaterEqual(infusion_deep_dive()["sector_deals"]["n"], 2)
        self.assertGreaterEqual(imaging_deep_dive()["sector_deals"]["n"], 5)
        self.assertGreaterEqual(
            physical_therapy_deep_dive()["sector_deals"]["n"], 5)


class NicheVerticalsBatch2Tests(unittest.TestCase):
    """Industries #17–19 — veterinary, medspa, EMS: the niches PE took
    mainstream that CDD tooling never covers."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "veterinary": 87_000_000 * 2.4 * 260,
            "medspa": 10_500 * 1_600_000,
            "ems": 22_000_000 * 0.40 * 1_350,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_vertical_specific_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Veterinary: the DVM shortage is the binding constraint.
        vet = compute(TEMPLATES["veterinary"]())
        names = {g["name"]: g["annual_pct"] for g in vet["growth_drivers"]}
        self.assertLess(names["Veterinarian shortage"], 0)
        # Medspa: consumer-cyclical exposure carried as the bear case.
        spa = compute(TEMPLATES["medspa"]())
        names = {g["name"]: g["annual_pct"] for g in spa["growth_drivers"]}
        self.assertLess(names["Consumer-cyclical exposure"], 0)
        # EMS: a near-flat market (+0.4%) — the tool doesn't inflate it.
        ems = compute(TEMPLATES["ems"]())
        self.assertLess(ems["composite_cagr_pct"], 1.0)

    def test_every_template_still_renders_and_exports(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page, tam_sam_xlsx
        for key in TEMPLATES:
            self.assertIn("TAM / SAM Builder",
                          render_tam_sam_page({"template": [key]}), key)
            z = zipfile.ZipFile(io.BytesIO(
                tam_sam_xlsx({"template": [key]})))
            self.assertIsNone(z.testzip(), key)


class NicheVerticalsBatch3Tests(unittest.TestCase):
    """Industries #20–22 — clinical labs, specialty pharmacy, vision."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "clinical_labs": 14e9 * 0.35 * 14,
            "specialty_pharmacy": 400e9 * 0.80,
            "vision": 195_000_000 * 310,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_vertical_specific_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Labs: PAMA is the structural headwind.
        labs = compute(TEMPLATES["clinical_labs"]())
        names = {g["name"]: g["annual_pct"]
                 for g in labs["growth_drivers"]}
        self.assertLess(names["PAMA rate cuts"], 0)
        # Specialty pharmacy: the SAM is honestly SMALL (PBM verticals
        # own the channel) — sam_share must be well under half.
        from rcm_mc.diligence.tam_sam import specialty_pharmacy_template
        self.assertLessEqual(specialty_pharmacy_template().sam_share,
                             0.25)


class NicheVerticalsBatch4Tests(unittest.TestCase):
    """Industries #23–25 — ABA/autism, plasma collection, clinical
    research sites: the hyper-niche layer."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "aba": 1_800_000 * 0.30 * 14 * 46 * 65,
            "plasma": 1_100 * 28_000 * 150,
            "clinical_research": 6_000 * 25 * 350_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)

    def test_structural_honesty(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, plasma_template,
        )
        # ABA: the labor shortage is the binding constraint.
        aba = compute(TEMPLATES["aba"]())
        names = {g["name"]: g["annual_pct"] for g in aba["growth_drivers"]}
        self.assertLess(names["BCBA/RBT labor shortage"], 0)
        # Plasma: 80% of the market is fractionator-owned and NOT
        # acquirable — the SAM says so.
        self.assertLessEqual(plasma_template().sam_share, 0.25)
        # Clinical research: biotech-funding cyclicality is the bear case.
        cr = compute(TEMPLATES["clinical_research"]())
        names = {g["name"]: g["annual_pct"] for g in cr["growth_drivers"]}
        self.assertLess(names["Biotech funding cyclicality"], 0)


class NicheVerticalsBatch5Tests(unittest.TestCase):
    """Industries #26–28 — wound care, sleep, occupational health."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "wound_care": 8_200_000 * 0.25 * 1.3 * 3_800,
            "sleep": 30_000_000 * 0.20 * 900,
            "occ_health": 135_000_000 * 190,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)

    def test_sleep_disruption_told_honestly(self):
        # In-lab PSG carries a NEGATIVE segment growth while HSAT grows
        # +9% — a declining segment inside a growing market, and the
        # GLP-1 OSA-indication bear case is named as a driver.
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        out = compute(TEMPLATES["sleep"]())
        psg = next(s for s in out["segments"] if "PSG" in s["name"])
        self.assertLess(psg["growth_pct"], 0)
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["GLP-1 OSA-indication effect"], 0)

    def test_catalogue_at_29_templates(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 29)   # 28 industries + blank


class NicheVerticalsBatch6Tests(unittest.TestCase):
    """Industries #29–31 — dermatology (a MATURE consolidation, told as
    one), interventional pain, hospital-at-home (waiver-risk priced)."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "dermatology": 12_500 * 1_500_000,
            "pain_management": 51_000_000 * 0.07 * 2.6 * 1_100,
            "hospital_at_home": 3_000_000 * 0.03 * 12_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)

    def test_maturity_and_waiver_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Derm: consolidation MATURITY is itself a headwind.
        derm = compute(TEMPLATES["dermatology"]())
        names = {g["name"]: g["annual_pct"]
                 for g in derm["growth_drivers"]}
        self.assertLess(names["Consolidation maturity"], 0)
        # Pain: utilization management is the defining payer headwind.
        pain = compute(TEMPLATES["pain_management"]())
        names = {g["name"]: g["annual_pct"]
                 for g in pain["growth_drivers"]}
        self.assertLess(names["Utilization management"], 0)
        # HaH: the waiver non-renewal risk is priced LARGE (≤ −5).
        hah = compute(TEMPLATES["hospital_at_home"]())
        names = {g["name"]: g["annual_pct"] for g in hah["growth_drivers"]}
        self.assertLessEqual(names["Waiver non-renewal risk"], -5.0)

    def test_catalogue_at_31_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 32)   # 31 + blank


class NicheVerticalsBatch7Tests(unittest.TestCase):
    """Industries #32–34 — LTC pharmacy, DME, IDD services."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "ltc_pharmacy": 3_100_000 * 110 * 55,
            "dme": 16_000_000 * 3_800,
            "idd_services": 1_500_000 * 45_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_structural_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # LTC pharmacy: generic deflation makes it near-flat (+0.9%) —
        # the tool does not inflate it.
        ltc = compute(TEMPLATES["ltc_pharmacy"]())
        self.assertLess(ltc["composite_cagr_pct"], 2.0)
        # DME: competitive bidding is the defining headwind.
        dme = compute(TEMPLATES["dme"]())
        names = {g["name"]: g["annual_pct"] for g in dme["growth_drivers"]}
        self.assertLess(names["Competitive bidding rounds"], 0)
        # IDD: the DSP workforce crisis is THE constraint.
        idd = compute(TEMPLATES["idd_services"]())
        names = {g["name"]: g["annual_pct"] for g in idd["growth_drivers"]}
        self.assertLessEqual(names["DSP workforce crisis"], -3.0)

    def test_catalogue_at_34_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 35)   # 34 + blank


class NicheVerticalsBatch8Tests(unittest.TestCase):
    """Industries #35–37 — eating disorders, nephrology, O&P."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "eating_disorders": 9_000_000 * 0.10 * 9_000,
            "nephrology": 11_000 * 900_000,
            "orthotics_prosthetics": 5_500_000 * 1_300,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_thesis_layer_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Nephrology: the VBC thesis layer is the fastest (+15%) AND the
        # model-rule uncertainty headwind is named — both sides shown.
        neph = compute(TEMPLATES["nephrology"]())
        vbc = next(s for s in neph["segments"] if "Value-based" in s["name"])
        self.assertTrue(vbc.get("is_fastest"))
        names = {g["name"]: g["annual_pct"] for g in neph["growth_drivers"]}
        self.assertLess(names["Model-rule uncertainty"], 0)
        # ED: the 90% access gap is in the chain (10% treated).
        from rcm_mc.diligence.tam_sam import eating_disorders_template
        rate_step = eating_disorders_template().chain[1]
        self.assertLessEqual(rate_step.value, 0.15)

    def test_catalogue_at_37_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 38)   # 37 + blank


class NicheVerticalsBatch9Tests(unittest.TestCase):
    """Industries #38–40 — ophthalmology, RCM services (the
    meta-vertical), cardiology standalone."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "ophthalmology": 19_000 * 1_800_000,
            "rcm_services": 2.6e12 * 0.04 * 0.30,
            "cardiology": 33_000 * 1_400_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_cardiology_shrinking_pool_honesty(self):
        # ~80% hospital-employed: the SAM is honestly SMALL and the
        # employment gravity is a named headwind.
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, cardiology_template, compute,
        )
        self.assertLessEqual(cardiology_template().sam_share, 0.25)
        out = compute(TEMPLATES["cardiology"]())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["Hospital employment gravity"], 0)

    def test_rcm_meta_vertical(self):
        # The platform sizes its own industry — churn risk named.
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        out = compute(TEMPLATES["rcm_services"]())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["In-sourcing reversals"], 0)

    def test_catalogue_at_40_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 41)   # 40 + blank


class NicheVerticalsBatch10Tests(unittest.TestCase):
    """Industries #41–43 — GI, orthopedics, women's health: the
    remaining big PPM waves, standalone."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "gastroenterology": 16_000 * 1_350_000,
            "orthopedics": 31_000 * 1_600_000,
            "womens_health": 42_000 * 850_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_gi_cologuard_bear_case(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        out = compute(TEMPLATES["gastroenterology"]())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["Non-invasive screening substitution"], 0)

    def test_womens_health_ob_decline_honesty(self):
        # OB the volume anchor grows only +1% while births decline —
        # near-flat composite told as-is; fertility adjacency carries it.
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        out = compute(TEMPLATES["womens_health"]())
        self.assertLess(out["composite_cagr_pct"], 1.5)
        fert = next(s for s in out["segments"] if "Fertility" in s["name"])
        self.assertTrue(fert.get("is_fastest"))

    def test_catalogue_at_43_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 44)   # 43 + blank


class NicheVerticalsBatch11Tests(unittest.TestCase):
    """Industries #44–46 — podiatry, ENT/allergy, anesthesia."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "podiatry": 18_000 * 550_000,
            "ent_allergy": 16_500 * 950_000,
            "anesthesia": 60_000_000 * 420,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_anesthesia_nsa_playbook_honesty(self):
        # The NSA rate reset killed the OON playbook — the template
        # prices it as the defining headwind and the basis note says so.
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, anesthesia_template, compute,
        )
        out = compute(TEMPLATES["anesthesia"]())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLessEqual(names["No Surprises Act rate reset"], -2.0)
        self.assertIn("playbook", anesthesia_template().basis_note)

    def test_catalogue_at_46_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 47)   # 46 + blank


class NicheVerticalsBatch12Tests(unittest.TestCase):
    """Industries #47–49 — non-medical home care, PACE, teleradiology."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "home_care": 12_000_000 * 0.30 * 20 * 48 * 32,
            "pace": 80_000 * 95_000,
            "teleradiology": 650_000_000 * 0.12 * 22,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_structural_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute, pace_template
        # Home care: a declining funding segment (LTC insurance) inside
        # a growing market.
        hc = compute(TEMPLATES["home_care"]())
        ltci = next(s for s in hc["segments"] if "LTC insurance" in s["name"])
        self.assertLess(ltci["growth_pct"], 0)
        # PACE: compliance risk priced large — growth is a privilege
        # revoked on audit failure (the InnovAge lesson, in the basis).
        out = compute(TEMPLATES["pace"]())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLessEqual(names["Compliance / audit risk"], -3.0)
        self.assertIn("InnovAge", pace_template().basis_note)

    def test_catalogue_at_49_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 50)   # 49 + blank


class NicheVerticalsBatch13Tests(unittest.TestCase):
    """Industries #50–52 — correctional health, locum staffing, crisis
    services: the 50-industry milestone batch."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "correctional_health": 1_900_000 * 0.55 * 7_500,
            "locum_staffing": 9_000_000 * 0.35 * 1_900,
            "crisis_services": 15_000_000 * 0.25 * 1_400,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_risk_pricing_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Correctional: litigation risk priced, not hidden.
        ch = compute(TEMPLATES["correctional_health"]())
        names = {g["name"]: g["annual_pct"] for g in ch["growth_drivers"]}
        self.assertLess(names["Headline / litigation risk"], 0)
        # Staffing: the travel-nurse whiplash precedent priced large.
        ls = compute(TEMPLATES["locum_staffing"]())
        names = {g["name"]: g["annual_pct"] for g in ls["growth_drivers"]}
        self.assertLessEqual(names["Hospital cost crackdowns"], -3.0)
        # Crisis: the grant-funding cliff is the sustainability question.
        cs = compute(TEMPLATES["crisis_services"]())
        names = {g["name"]: g["annual_pct"] for g in cs["growth_drivers"]}
        self.assertLessEqual(names["Grant-funding cliff risk"], -3.0)

    def test_catalogue_crosses_50_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 53)   # 52 + blank


class NicheVerticalsBatch14Tests(unittest.TestCase):
    """Industries #53–55 — school services, mobile diagnostics,
    community palliative."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "school_services": 7_500_000 * 0.45 * 2_400,
            "mobile_diagnostics": 28_000_000 * 0.55 * 95,
            "palliative": 12_000_000 * 0.05 * 4_200,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_gap_thesis_honesty(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, palliative_template,
        )
        # Palliative: the 5% penetration IS the thesis — and the FFS
        # model's economic failure is priced as a negative driver.
        self.assertLessEqual(palliative_template().chain[1].value, 0.10)
        out = compute(TEMPLATES["palliative"]())
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["FFS economics weakness"], 0)
        # School services: the ESSER funding cliff is priced.
        ss = compute(TEMPLATES["school_services"]())
        names = {g["name"]: g["annual_pct"] for g in ss["growth_drivers"]}
        self.assertLess(names["District budget cyclicality"], 0)

    def test_catalogue_at_55_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 56)   # 55 + blank


class NicheVerticalsBatch15Tests(unittest.TestCase):
    """Industries #56–58 — senior living, vascular access, genetic
    testing."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "senior_living": 1_600_000 * 0.86 * 63_000,
            "vascular_access": 560_000 * 1.8 * 3_200,
            "genetic_testing": 8_000_000 * 850,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_structural_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Senior living: the affordability ceiling gates the TAM.
        sl = compute(TEMPLATES["senior_living"]())
        names = {g["name"]: g["annual_pct"] for g in sl["growth_drivers"]}
        self.assertLess(names["Affordability ceiling"], 0)
        # Vascular access: the atherectomy/OIG compliance headwind named.
        va = compute(TEMPLATES["vascular_access"]())
        names = {g["name"]: g["annual_pct"] for g in va["growth_drivers"]}
        self.assertLess(names["Atherectomy/UM scrutiny"], 0)
        # Genetic testing: reimbursement friction is the industry's
        # defining problem — priced largest among its headwinds.
        gt = compute(TEMPLATES["genetic_testing"]())
        names = {g["name"]: g["annual_pct"] for g in gt["growth_drivers"]}
        self.assertLessEqual(names["Reimbursement friction"], -3.0)

    def test_catalogue_at_58_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 59)   # 58 + blank


class NicheVerticalsBatch16Tests(unittest.TestCase):
    """Industries #59–61 — NEMT, 503B compounding, LOP medicine."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "nemt": 110_000_000 * 38,
            "compounding_503b": 80 * 30_000_000,
            "lop_medicine": 2_500_000 * 0.20 * 9_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_risk_pricing(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, lop_medicine_template,
        )
        # 503B: a bad FDA inspection closes a facility — quality IS the
        # license, priced at -3.
        cb = compute(TEMPLATES["compounding_503b"]())
        names = {g["name"]: g["annual_pct"] for g in cb["growth_drivers"]}
        self.assertLessEqual(names["FDA enforcement / 483 risk"], -3.0)
        # LOP: tort-reform risk + collectability BOTH priced large; the
        # basis names it the highest-diligence-burden vertical.
        lop = compute(TEMPLATES["lop_medicine"]())
        names = {g["name"]: g["annual_pct"] for g in lop["growth_drivers"]}
        self.assertLessEqual(names["Tort-reform risk"], -3.0)
        self.assertLessEqual(names["Collectability discounts"], -2.0)
        self.assertIn("highest-", lop_medicine_template().basis_note)

    def test_catalogue_at_61_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 62)   # 61 + blank


class NicheVerticalsBatch17Tests(unittest.TestCase):
    """Industries #62–64 — dental labs, HTM/clinical engineering,
    medical interpretation."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "dental_labs": 38_000_000 * 210,
            "htm_clinical_engineering": 25_000_000 * 280,
            "interpretation": 380_000_000 * 0.30 * 28,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_disruption_pricing(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, htm_clinical_engineering_template,
            interpretation_template,
        )
        # Dental labs: offshore substitution is the structural leak.
        dl = compute(TEMPLATES["dental_labs"]())
        names = {g["name"]: g["annual_pct"] for g in dl["growth_drivers"]}
        self.assertLess(names["Offshore substitution"], 0)
        # HTM: only the ISO+rental layers are acquirable — SAM ≤ 0.35.
        self.assertLessEqual(
            htm_clinical_engineering_template().sam_share, 0.35)
        # Interpretation: the AI displacement risk priced ≤ −3 and
        # called the diligence centerpiece.
        it = compute(TEMPLATES["interpretation"]())
        names = {g["name"]: g["annual_pct"] for g in it["growth_drivers"]}
        self.assertLessEqual(names["AI interpretation displacement"],
                             -3.0)
        self.assertIn("displacement curve",
                      interpretation_template().basis_note)

    def test_catalogue_at_64_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 65)   # 64 + blank


class NicheVerticalsBatch18Tests(unittest.TestCase):
    """Industries #65–67 — urology, rheumatology, neurology: the
    infusion-ancillary specialty map completed."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "urology": 13_500 * 1_300_000,
            "rheumatology": 6_000 * 1_100_000,
            "neurology": 14_000 * 900_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_specialty_honesty(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, rheumatology_template,
        )
        # Rheumatology: the biosimilar repricing of the margin engine
        # is THE IC question — priced ≤ −3 and named in the basis.
        rh = compute(TEMPLATES["rheumatology"]())
        names = {g["name"]: g["annual_pct"] for g in rh["growth_drivers"]}
        self.assertLessEqual(names["Biosimilar margin erosion"], -3.0)
        self.assertIn("margin engine", rheumatology_template().basis_note)
        # Neurology: the amyloid-era infusion line is the fastest (+11).
        ne = compute(TEMPLATES["neurology"]())
        inf = next(s for s in ne["segments"] if "Infusion" in s["name"])
        self.assertTrue(inf.get("is_fastest"))
        # Urology: the workforce cliff named (oldest surgical workforce).
        ur = compute(TEMPLATES["urology"]())
        names = {g["name"]: g["annual_pct"] for g in ur["growth_drivers"]}
        self.assertLess(names["Workforce cliff"], 0)

    def test_catalogue_at_67_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 68)   # 67 + blank


class NicheVerticalsBatch19Tests(unittest.TestCase):
    """Industries #68–70 — endocrinology/obesity (GLP-1 era),
    pulmonology, transplant services."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "endocrinology_obesity": 16_000_000 * 0.40 * 650,
            "pulmonology": 12_000 * 850_000,
            "transplant_services": 48_000 * 1_100_000,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_glp1_era_honesty(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, endocrinology_obesity_template,
            transplant_services_template,
        )
        # Endo: GLP-1s CANNIBALIZE bariatric — a negative segment
        # inside the same vertical (intra-vertical disruption).
        out = compute(TEMPLATES["endocrinology_obesity"]())
        bari = next(s for s in out["segments"] if "bariatric" in s["name"])
        self.assertLess(bari["growth_pct"], 0)
        # The drug-dollars-to-pharmacy honesty is in the basis.
        self.assertIn("pharmacy",
                      endocrinology_obesity_template().basis_note)
        # Transplant: SAM 0.15 — the centers are academic, only the
        # services shell is investable, and the basis says so.
        self.assertLessEqual(
            transplant_services_template().sam_share, 0.20)
        self.assertIn("academic",
                      transplant_services_template().basis_note)

    def test_catalogue_at_70_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 71)   # 70 + blank


class NicheVerticalsBatch20Tests(unittest.TestCase):
    """Industries #71–73 — retail clinics (the failure autopsy),
    surgical assist, HIT consulting."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "retail_clinics": 1_800 * 9_500 * 135,
            "surgical_assist": 12_000_000 * 0.25 * 350,
            "hit_consulting": 120e9 * 0.18,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_failure_autopsy_honesty(self):
        # Retail clinics: the template documents a FAILED thesis — the
        # big-box segment declines, the unit-economics lesson is priced
        # ≤ −3, and the basis says the training value is the autopsy.
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, retail_clinics_template,
        )
        out = compute(TEMPLATES["retail_clinics"]())
        bigbox = next(s for s in out["segments"] if "big-box" in s["name"])
        self.assertLess(bigbox["growth_pct"], 0)
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLessEqual(names["The unit-economics problem"], -3.0)
        self.assertIn("autopsy", retail_clinics_template().basis_note)

    def test_hit_ai_wave_fastest(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        out = compute(TEMPLATES["hit_consulting"]())
        ai = next(s for s in out["segments"] if "AI" in s["name"])
        self.assertTrue(ai.get("is_fastest"))
        # …and the shrunken original market is priced.
        names = {g["name"]: g["annual_pct"] for g in out["growth_drivers"]}
        self.assertLess(names["EHR-implementation maturity"], 0)

    def test_catalogue_at_73_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 74)   # 73 + blank


class NicheVerticalsBatch21Tests(unittest.TestCase):
    """Industries #74–76 — hospitalist groups, perfusion, sterile
    processing: the micro-niche layer."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "hospitalist": 44_000 * 0.35 * 380_000,
            "perfusion": 450_000 * 0.45 * 1_500,
            "sterile_processing": 180_000_000 * 0.08 * 28,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_micro_niche_honesty(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        # Hospitalist: the post-Envision trust deficit priced.
        h = compute(TEMPLATES["hospitalist"]())
        names = {g["name"]: g["annual_pct"] for g in h["growth_drivers"]}
        self.assertLess(names["Post-Envision contract caution"], 0)
        # Perfusion: scarcity is BOTH the constraint and the
        # outsourcing driver — and the market is honestly tiny (<$1B).
        p = compute(TEMPLATES["perfusion"]())
        self.assertLess(p["tam"], 1e9)
        # Sterile processing: a missed tray cancels a case — the
        # logistics risk priced.
        s = compute(TEMPLATES["sterile_processing"]())
        names = {g["name"]: g["annual_pct"] for g in s["growth_drivers"]}
        self.assertLess(names["Logistics cost / turnaround risk"], 0)

    def test_catalogue_at_76_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 77)   # 76 + blank


class NicheVerticalsBatch22Tests(unittest.TestCase):
    """Industries #77–79 — air medical, pediatric PDN, ROI services."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "air_medical": 550_000 * 11_000,
            "pediatric_home_health": 400_000 * 0.45 * 40 * 50 * 42,
            "roi_services": 95_000_000 * 0.55 * 18,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_broken_playbook_and_constraint_pricing(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, air_medical_template, compute,
        )
        # Air medical: the NSA killed the balance-billing engine —
        # priced ≤ −3, Air Methods bankruptcy named as the case study.
        am = compute(TEMPLATES["air_medical"]())
        names = {g["name"]: g["annual_pct"] for g in am["growth_drivers"]}
        self.assertLessEqual(names["NSA IDR rate reset"], -3.0)
        self.assertIn("bankruptcy", air_medical_template().basis_note)
        # PDN: 30-40% of authorized hours go unstaffed — the largest
        # headwind in its template.
        pdn = compute(TEMPLATES["pediatric_home_health"]())
        names = {g["name"]: g["annual_pct"] for g in pdn["growth_drivers"]}
        self.assertLessEqual(names["Nurse staffing gap"], -3.0)
        # ROI: near-flat — fee caps + API disintermediation both priced.
        roi = compute(TEMPLATES["roi_services"]())
        self.assertLess(roi["composite_cagr_pct"], 1.5)

    def test_catalogue_at_79_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 80)   # 79 + blank


class NicheVerticalsBatch23Tests(unittest.TestCase):
    """Industries #80–82 — virtual primary care, RPM, care navigation:
    crossing the 80-industry milestone."""

    def test_three_chains_pin(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES, compute
        expect = {
            "virtual_primary_care": 35_000_000 * 0.15 * 420,
            "rpm": 60_000_000 * 0.03 * 1_100,
            "care_navigation": 110_000_000 * 0.25 * 36,
        }
        for key, tam in expect.items():
            out = compute(TEMPLATES[key]())
            self.assertAlmostEqual(out["tam"], tam, places=2, msg=key)
            self.assertTrue(any(g["annual_pct"] < 0
                                for g in out["growth_drivers"]), key)
            self.assertTrue(any(s.get("is_fastest")
                                for s in out["segments"]), key)

    def test_digital_era_honesty(self):
        from rcm_mc.diligence.tam_sam import (
            TEMPLATES, compute, rpm_template,
            virtual_primary_care_template,
        )
        # Virtual primary: the engagement gap IS the reckoning (≤ −3,
        # Teladoc impairment named).
        vp = compute(TEMPLATES["virtual_primary_care"]())
        names = {g["name"]: g["annual_pct"] for g in vp["growth_drivers"]}
        self.assertLessEqual(names["Engagement gap"], -3.0)
        self.assertIn("reckoning",
                      virtual_primary_care_template().basis_note)
        # RPM: a code-created market — OIG scrutiny ≤ −3 and the basis
        # says the CPT family is both the TAM and the risk.
        rpm = compute(TEMPLATES["rpm"]())
        names = {g["name"]: g["annual_pct"] for g in rpm["growth_drivers"]}
        self.assertLessEqual(names["OIG / billing-integrity scrutiny"],
                             -3.0)
        self.assertIn("CODE-CREATED", rpm_template().basis_note)
        # Navigation: the ROI-proof pressure priced.
        cn = compute(TEMPLATES["care_navigation"]())
        names = {g["name"]: g["annual_pct"] for g in cn["growth_drivers"]}
        self.assertLess(names["ROI-proof pressure"], 0)

    def test_catalogue_crosses_80_industries(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        self.assertGreaterEqual(len(TEMPLATES), 83)   # 82 + blank


class SegmentBarTests(unittest.TestCase):
    """The segment-composition stacked bar — one visual, every build."""

    def test_every_template_renders_the_bar(self):
        from rcm_mc.diligence.tam_sam import TEMPLATES
        from rcm_mc.ui.tam_sam_page import render_tam_sam_page
        for key in TEMPLATES:
            if key == "blank":
                continue
            h = render_tam_sam_page({"template": [key]})
            self.assertIn('aria-label="Segment composition"', h, key)

    def test_fastest_star_in_bar(self):
        from rcm_mc.ui.tam_sam_page import _segment_bar_svg
        svg = _segment_bar_svg([
            {"name": "Big", "share_of_volume": 0.7},
            {"name": "Fast", "share_of_volume": 0.3, "is_fastest": True},
        ])
        self.assertIn("★", svg)
        self.assertIn("70%", svg)
