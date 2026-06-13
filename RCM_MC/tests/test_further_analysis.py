"""Tests for Further Analysis — the Tableau-style data explorer.

Exercises the data engine (every dataset loads offline and shapes cleanly),
the query resolver (clamping + scaling), the JSON API payload, and the page
renderer (real SVG, export toolbar, no crash across chart types).
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence import further_analysis as fa
from rcm_mc.ui.cdd_chart_kit import CHART_TYPES, render_cdd_chart
from rcm_mc.ui.further_analysis_page import render_further_analysis_page


class RegistryTests(unittest.TestCase):
    def test_registry_has_many_datasets_across_sources(self):
        ds = fa.list_datasets()
        self.assertGreaterEqual(len(ds), 10)
        cats = set(fa.categories())
        # Real public-data sources are represented.
        for c in ("CMS", "CDC", "Census", "Labor", "Markets"):
            self.assertIn(c, cats)

    def test_every_dataset_loads_offline_and_is_nonempty(self):
        for d in fa.list_datasets():
            focus = d.focus_options[0][0] if d.focus_options else None
            rows = d.loader(focus)
            self.assertTrue(rows, f"{d.id} returned no rows offline")
            # Each row carries the dimension key.
            self.assertIn(d.dim_key, rows[0], f"{d.id} missing dim_key")

    def test_every_measure_is_present_in_rows(self):
        for d in fa.list_datasets():
            focus = d.focus_options[0][0] if d.focus_options else None
            rows = d.loader(focus)
            keys = set().union(*[set(r.keys()) for r in rows])
            for m in d.measures:
                self.assertIn(m.key, keys,
                              f"{d.id}.{m.key} not in any row")


class CmsDatasetTests(unittest.TestCase):
    """The expanded CMS dataset coverage (HCAHPS, MA geo, PECOS supply, MIPS)."""

    def test_cms_is_the_largest_category(self):
        cms = [d for d in fa.list_datasets() if d.category == "CMS"]
        # The explorer is CMS-heavy by design — at least nine CMS sets.
        self.assertGreaterEqual(len(cms), 9)
        for needed in ("hcahps", "ma_geo", "provider_supply", "mips"):
            self.assertIn(needed, fa.DATASETS)
            self.assertEqual(fa.DATASETS[needed].category, "CMS")

    def test_hcahps_is_state_grain_top_box_pct(self):
        d = fa.DATASETS["hcahps"]
        self.assertEqual(d.grain, "state")
        table, meta = fa.shape_table(d, ["overall_rating_9_10"], top_n=51)
        self.assertEqual(meta["suffix"], "%")
        # Top-box shares are already 0-100 (pct100): not refractioned, plausible.
        for _, vals in table["rows"]:
            if vals[0] is not None:
                self.assertGreater(vals[0], 40.0)
                self.assertLessEqual(vals[0], 100.0)

    def test_ma_geo_enrollment_sorts_and_fractions_scale(self):
        d = fa.DATASETS["ma_geo"]
        table, _ = fa.shape_table(d, ["ma_enrollment"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))
        # California carries the most MA enrollment in the 2022 cut.
        self.assertEqual(table["rows"][0][0], "California")
        # dual_eligible_pct is a 0-1 fraction → display 0-100.
        dt, dmeta = fa.shape_table(d, ["dual_eligible_pct"], top_n=51)
        self.assertEqual(dmeta["suffix"], "%")
        for _, vals in dt["rows"]:
            if vals[0] is not None:
                self.assertGreater(vals[0], 1.0)
                self.assertLess(vals[0], 100.0)

    def test_provider_supply_category_grain(self):
        d = fa.DATASETS["provider_supply"]
        self.assertEqual(d.grain, "category")
        table, _ = fa.shape_table(d, ["enrolled_count"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))
        # Labels are title-cased, not the raw all-caps source strings.
        self.assertFalse(table["rows"][0][0].isupper())

    def test_mips_distribution_renders(self):
        d = fa.DATASETS["mips"]
        table, _ = fa.shape_table(d, ["mean", "median"], top_n=10)
        self.assertEqual(len(table["headers"]), 3)
        self.assertTrue(table["rows"])

    def test_postacute_footprint_aligns_five_verticals_by_state(self):
        d = fa.DATASETS["postacute_footprint"]
        self.assertEqual(d.grain, "state")
        # Five comparable facility-count measures (+ a quality reference).
        count_keys = ["snf_facilities", "hha_agencies", "hospice_count",
                      "dialysis_facilities", "irf_facilities"]
        for k in count_keys:
            self.assertIsNotNone(d.measure(k), f"missing measure {k}")
        table, _ = fa.shape_table(d, count_keys, top_n=10)
        # One dimension column + five measure columns.
        self.assertEqual(len(table["headers"]), 6)
        for _, vals in table["rows"]:
            self.assertEqual(len(vals), 5)

    def test_snf_owners_category_grain_sorts_desc(self):
        d = fa.DATASETS["snf_owners"]
        self.assertEqual(d.grain, "category")
        table, _ = fa.shape_table(d, ["facilities_owned"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_mssp_aco_state_footprint_covers_all_states(self):
        d = fa.DATASETS["mssp_aco_state"]
        self.assertEqual(d.grain, "state")
        rows = d.loader(None)
        self.assertEqual(len(rows), 51)
        table, _ = fa.shape_table(d, ["aco_count"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertTrue(all(v >= 0 for v in vals))

    def test_mssp_track_mix_is_category_grain(self):
        d = fa.DATASETS["mssp_track"]
        self.assertEqual(d.grain, "category")
        table, _ = fa.shape_table(d, ["acos"], top_n=10)
        self.assertTrue(table["rows"])
        # ENHANCED (full two-sided risk) is the largest track in the cut.
        self.assertEqual(table["rows"][0][0], "Enhanced")

    def test_consolidation_state_sums_snf_and_hospital_chow(self):
        d = fa.DATASETS["consolidation_state"]
        self.assertEqual(d.grain, "state")
        rows = {r["state"]: r for r in d.loader(None)}
        # total_chows is the sum of the two settings, never silently dropped.
        for r in rows.values():
            self.assertEqual(
                r["total_chows"],
                (r["snf_chows"] or 0) + (r["hospital_chows"] or 0))
        table, _ = fa.shape_table(d, ["total_chows"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_consolidation_trend_is_a_year_series(self):
        d = fa.DATASETS["consolidation_trend"]
        rows = d.loader(None)
        years = [r["year"] for r in rows]
        # One row per vintage year, labels are year strings.
        self.assertEqual(years, sorted(years))
        self.assertTrue(all(y.isdigit() for y in years))

    def test_hrsa_shortage_is_its_own_source_category(self):
        d = fa.DATASETS["hrsa_shortage"]
        self.assertEqual(d.category, "HRSA")
        self.assertIn("HRSA", fa.categories())
        table, _ = fa.shape_table(d, ["population_in_shortage"], top_n=5)
        self.assertTrue(table["rows"])

    def test_non_cms_public_sources_added(self):
        # OIG exclusions + ClinicalTrials.gov extend coverage beyond CMS/HRSA.
        cats = set(fa.categories())
        self.assertIn("OIG", cats)
        self.assertIn("NLM", cats)
        oig = fa.DATASETS["oig_exclusions_state"]
        self.assertEqual(oig.grain, "state")
        table, _ = fa.shape_table(oig, ["exclusions"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))
        trials = fa.DATASETS["clinical_trial_phase"]
        ttable, _ = fa.shape_table(trials, ["studies"], top_n=10)
        self.assertTrue(ttable["rows"])

    def test_partd_inflation_is_distinct_pct_set(self):
        d = fa.DATASETS["partd_inflation"]
        table, meta = fa.shape_table(d, ["price_cagr_19_23"], top_n=10)
        self.assertEqual(meta["suffix"], "%")
        # Steepest-inflation drugs differ from the top-spend list.
        spend_top = [lbl for lbl, _ in
                     fa.shape_table(fa.DATASETS["partd"], ["spend_2023"],
                                    top_n=10)[0]["rows"]]
        infl_top = [lbl for lbl, _ in table["rows"]]
        self.assertNotEqual(spend_top, infl_top)

    def test_cost_of_care_one_row_per_service_line(self):
        d = fa.DATASETS["cost_of_care"]
        rows = d.loader(None)
        lines = [r["service_line"] for r in rows]
        self.assertEqual(len(lines), len(set(lines)))  # deduped rollup
        table, _ = fa.shape_table(d, ["pppy"], top_n=20)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_metro_demographics_is_metro_grain(self):
        d = fa.DATASETS["metro_demographics"]
        rows = d.loader(None)
        self.assertGreater(len(rows), 300)   # ~382 metros
        table, _ = fa.shape_table(d, ["population"], top_n=3)
        self.assertIn("New York", table["rows"][0][0])

    def test_snf_turnover_covers_states_as_pct(self):
        d = fa.DATASETS["snf_turnover"]
        self.assertEqual(d.grain, "state")
        rows = d.loader(None)
        self.assertGreaterEqual(len(rows), 40)
        table, meta = fa.shape_table(d, ["median_turnover"], top_n=51)
        self.assertEqual(meta["suffix"], "%")

    def test_postacute_quality_multi_vertical_by_state(self):
        d = fa.DATASETS["postacute_quality"]
        self.assertEqual(d.grain, "state")
        table, _ = fa.shape_table(
            d, ["snf_overall", "hha_star", "dialysis_five_star"], top_n=10)
        self.assertEqual(len(table["headers"]), 4)
        # SNF/HHA/dialysis ratings sit on the 1-5 star scale.
        for _, vals in table["rows"]:
            for v in vals:
                if v is not None:
                    self.assertGreaterEqual(v, 1.0)
                    self.assertLessEqual(v, 5.0)

    def test_api_catalog_coverage_charts_the_catalog(self):
        from rcm_mc.data_public import public_api_catalog as pac
        d = fa.DATASETS["api_catalog_coverage"]
        rows = d.loader(None)
        # One row per diligence category; counts match the catalog.
        self.assertEqual(len(rows), len(pac.CATEGORIES))
        total = sum(r["sources"] for r in rows)
        self.assertEqual(total, len(pac.all_sources()))

    def test_apm_adoption_is_pct_by_payer(self):
        d = fa.DATASETS["apm_adoption"]
        self.assertEqual(d.grain, "category")
        table, meta = fa.shape_table(d, ["pct_apm"], top_n=10)
        self.assertEqual(meta["suffix"], "%")
        # Fractions scaled to 0-100; excludes the rolled-up Total/Unknown.
        labels = [lbl for lbl, _ in table["rows"]]
        self.assertNotIn("Total", labels)
        self.assertNotIn("Unknown", labels)
        for _, vals in table["rows"]:
            if vals[0] is not None:
                self.assertGreater(vals[0], 0.0)
                self.assertLess(vals[0], 100.0)

    def test_new_cms_datasets_appear_on_page(self):
        import html
        for did in ("hcahps", "ma_geo", "provider_supply", "mips",
                    "postacute_footprint", "snf_owners",
                    "mssp_aco_state", "mssp_track",
                    "consolidation_state", "consolidation_trend",
                    "hrsa_shortage", "oig_exclusions_state",
                    "oig_exclusions_type", "clinical_trial_phase",
                    "apm_adoption"):
            h = render_further_analysis_page({"dataset": [did]})
            self.assertIn("<svg", h, f"{did} produced no svg")
            self.assertIn(html.escape(fa.DATASETS[did].label), h)


class ShapeTests(unittest.TestCase):
    def test_shape_returns_chart_kit_table(self):
        d = fa.DATASETS["state_demographics"]
        table, meta = fa.shape_table(d, ["population"], top_n=10)
        self.assertEqual(table["headers"][0], "State")
        self.assertEqual(len(table["rows"]), 10)
        # Rows are (label, [values]) tuples consumable by render_cdd_chart.
        label, vals = table["rows"][0]
        self.assertIsInstance(label, str)
        self.assertEqual(len(vals), 1)

    def test_sort_descending_by_default(self):
        d = fa.DATASETS["state_demographics"]
        table, _ = fa.shape_table(d, ["population"], top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_ascending_flag_reverses(self):
        d = fa.DATASETS["state_demographics"]
        table, _ = fa.shape_table(d, ["population"], ascending=True, top_n=5)
        vals = [v[0] for _, v in table["rows"]]
        self.assertEqual(vals, sorted(vals))

    def test_pct_fraction_scaled_to_0_100(self):
        # demographics pct_age_65_plus is a 0-1 fraction → display 0-100.
        d = fa.DATASETS["state_demographics"]
        table, meta = fa.shape_table(d, ["pct_age_65_plus"], top_n=51)
        self.assertEqual(meta["suffix"], "%")
        for _, vals in table["rows"]:
            if vals[0] is not None:
                self.assertGreater(vals[0], 1.0)   # not still a fraction
                self.assertLess(vals[0], 100.0)

    def test_usd_billions_scaled(self):
        d = fa.DATASETS["hcris_state"]
        table, meta = fa.shape_table(d, ["total_npsr"], top_n=5)
        self.assertEqual(meta["suffix"], "B")
        # California NPSR in the hundreds of billions → scaled to ~hundreds.
        top = table["rows"][0][1][0]
        self.assertLess(top, 10000)

    def test_top_n_is_clamped(self):
        d = fa.DATASETS["state_demographics"]
        table, _ = fa.shape_table(d, ["population"], top_n=999)
        self.assertLessEqual(len(table["rows"]), 60)

    def test_multi_measure_table_has_aligned_columns(self):
        d = fa.DATASETS["hcris_state"]
        table, _ = fa.shape_table(d, ["total_npsr", "total_opex"], top_n=6)
        self.assertEqual(len(table["headers"]), 3)
        for _, vals in table["rows"]:
            self.assertEqual(len(vals), 2)

    def test_county_focus_changes_rows(self):
        d = fa.DATASETS["county_demographics"]
        tx, _ = fa.shape_table(d, ["population"], focus="TX", top_n=5)
        ca, _ = fa.shape_table(d, ["population"], focus="CA", top_n=5)
        self.assertNotEqual([r[0] for r in tx["rows"]],
                            [r[0] for r in ca["rows"]])


class ResolveQueryTests(unittest.TestCase):
    def test_defaults_resolve(self):
        spec = fa.resolve_query({})
        self.assertEqual(spec["dataset"].id, fa.list_datasets()[0].id)
        self.assertTrue(spec["table"]["rows"])

    def test_unknown_dataset_falls_back(self):
        spec = fa.resolve_query({"dataset": ["nope"]})
        self.assertEqual(spec["dataset"].id, fa.list_datasets()[0].id)

    def test_invalid_measures_drop_to_default(self):
        spec = fa.resolve_query({"dataset": ["labor"],
                                 "measures": ["bogus"]})
        self.assertEqual(spec["measures"],
                         [fa.DATASETS["labor"].measures[0].key])

    def test_single_series_chart_keeps_one_measure(self):
        spec = fa.resolve_query({
            "dataset": ["hcris_state"],
            "measures": ["total_npsr", "total_opex"],
            "type": ["pie"]})
        self.assertEqual(len(spec["measures"]), 1)

    def test_invalid_focus_clamps_to_first(self):
        spec = fa.resolve_query({"dataset": ["county_demographics"],
                                 "focus": ["ZZ"]})
        self.assertEqual(spec["focus"],
                         fa.DATASETS["county_demographics"].focus_options[0][0])

    def test_measures_comma_or_repeat_param(self):
        a = fa.resolve_query({"dataset": ["hcris_state"],
                              "measures": ["total_npsr,total_opex"]})
        b = fa.resolve_query({"dataset": ["hcris_state"],
                              "measures": ["total_npsr", "total_opex"]})
        self.assertEqual(a["measures"], b["measures"])


class JsonApiTests(unittest.TestCase):
    def test_payload_shape(self):
        out = fa.build_further_analysis({})
        self.assertIn("selected", out)
        self.assertIn("table", out)
        self.assertIn("catalog", out)
        self.assertEqual(len(out["catalog"]), len(fa.list_datasets()))
        # Catalog entries describe measures for programmatic discovery.
        self.assertTrue(out["catalog"][0]["measures"])

    def test_table_rows_are_labelled(self):
        out = fa.build_further_analysis({"dataset": ["partd"]})
        row = out["table"]["rows"][0]
        self.assertIn("label", row)
        self.assertIn("values", row)


class PageRenderTests(unittest.TestCase):
    def test_default_page_renders_with_chart_and_export(self):
        h = render_further_analysis_page({})
        self.assertIn("<svg", h)
        self.assertIn("faOut", h)            # export toolbar target
        self.assertIn("Further Analysis", h)

    def test_renders_for_every_chart_type_without_error(self):
        # Pick a multi-row dataset; render each chart type the page offers.
        for key, _label in CHART_TYPES:
            h = render_further_analysis_page({
                "dataset": ["state_demographics"],
                "measures": ["population"],
                "type": [key]})
            self.assertIn("<svg", h, f"chart type {key} produced no svg")

    def test_dataset_dropdown_lists_all_datasets(self):
        import html
        h = render_further_analysis_page({})
        for d in fa.list_datasets():
            self.assertIn(html.escape(d.label), h)

    def test_focus_selector_present_for_county_grain(self):
        h = render_further_analysis_page({"dataset": ["county_demographics"]})
        self.assertIn('name="focus"', h)

    def test_no_focus_selector_for_state_grain(self):
        h = render_further_analysis_page({"dataset": ["state_demographics"]})
        self.assertNotIn('name="focus"', h)

    def test_data_table_behind_chart_present(self):
        h = render_further_analysis_page({"dataset": ["labor"]})
        self.assertIn("DATA BEHIND THE CHART", h)

    def test_no_synthetic_data_disclaimer(self):
        h = render_further_analysis_page({})
        self.assertIn("No synthetic data", h)


class HttpSmokeTests(unittest.TestCase):
    """The page + JSON routes serve 200 over a real HTTP server."""

    @classmethod
    def setUpClass(cls):
        import os
        import tempfile
        import threading
        import time
        from rcm_mc.server import build_server

        cls._tmp = tempfile.TemporaryDirectory()
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        cls._port = s.getsockname()[1]
        s.close()
        srv, _ = build_server(
            port=cls._port, db_path=os.path.join(cls._tmp.name, "p.db"),
            host="127.0.0.1")
        cls._srv = srv
        cls._thread = threading.Thread(target=srv.serve_forever, daemon=True)
        cls._thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls._srv.shutdown()
        cls._srv.server_close()
        cls._tmp.cleanup()

    def _get(self, path):
        import urllib.error
        import urllib.request
        try:
            return urllib.request.urlopen(
                f"http://127.0.0.1:{self._port}{path}", timeout=10)
        except urllib.error.HTTPError as exc:
            return exc

    def test_page_route_serves_html(self):
        resp = self._get("/further-analysis?dataset=hcris_state&type=column")
        self.assertEqual(resp.status, 200)
        body = resp.read().decode()
        self.assertIn("Further Analysis", body)
        self.assertIn("<svg", body)

    def test_json_api_serves_catalog(self):
        import json
        resp = self._get("/api/further-analysis?dataset=partd")
        self.assertEqual(resp.status, 200)
        payload = json.loads(resp.read().decode())
        self.assertEqual(payload["selected"]["dataset"], "partd")
        self.assertTrue(payload["catalog"])


if __name__ == "__main__":
    unittest.main()
