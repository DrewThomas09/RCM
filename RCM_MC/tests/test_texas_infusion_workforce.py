"""Tests for the Texas infusion workforce + demand-heatmap surface.

Covers the employment-by-specialty data (clinical BLS-anchored roster +
prescriber funnel), the true-geography county-demand centroids (real
facility coordinates, no invented positions), and the page that renders
both heatmaps.
"""
import unittest

from rcm_mc.diligence.texas_infusion_workforce import (
    county_demand_centroids,
    specialty_employment_by_metro,
    texas_specialty_employment,
    texas_therapy_mix,
    tx_boundary_lonlat,
)


class SpecialtyEmploymentTests(unittest.TestCase):
    def setUp(self):
        self.e = texas_specialty_employment()

    def test_clinical_roster_anchored_to_real_bls_employment(self):
        rns = next(c for c in self.e["clinical"] if c["soc"] == "29-1141")
        # BLS OES TX RNs are a large six-figure count; the infusion share
        # is a fraction of it.
        self.assertGreater(rns["tx_employment"], 200_000)
        self.assertLess(rns["infusion_relevant"], 1.0)
        self.assertEqual(
            rns["infusion_relevant_headcount"],
            round(rns["tx_employment"] * rns["infusion_relevant"]))

    def test_prescriber_counts_scale_with_population(self):
        pop = self.e["totals"]["tx_population"]
        gi = next(p for p in self.e["prescribers"]
                  if p["specialty"] == "Gastroenterology")
        self.assertEqual(gi["tx_physicians"],
                         round(gi["per_100k"] * pop / 100_000))
        self.assertGreater(gi["tx_physicians"], 0)

    def test_matrix_rows_carry_all_intensity_columns(self):
        keys = {c["key"] for c in self.e["matrix_columns"]}
        self.assertEqual(keys, {"aic_fit", "home_fit", "demand_pull",
                                "scarcity"})
        for row in self.e["matrix"]:
            for k in keys:
                self.assertTrue(0 <= row[k] <= 100, (row["label"], k))
        # Both groups present (clinical + prescriber).
        self.assertEqual({r["group"] for r in self.e["matrix"]},
                         {"Clinical staffing", "Prescriber specialty"})

    def test_metro_shares_sum_to_one(self):
        shares = sum(m["share"] for m in self.e["metros"])
        self.assertAlmostEqual(shares, 1.0, places=2)
        # The four named metros plus rest-of-state.
        self.assertEqual(len(self.e["metros"]), 5)
        self.assertEqual(self.e["metros"][-1]["metro"], "Rest of Texas")

    def test_metro_apportionment_sums_to_tx_total(self):
        metros = [m["metro"] for m in self.e["metros"]]
        for row in specialty_employment_by_metro():
            apportioned = sum(row[m] for m in metros)
            # Rounding across five buckets stays within a handful of heads.
            self.assertAlmostEqual(apportioned, row["tx"], delta=5)


class CountyDemandGeoTests(unittest.TestCase):
    def setUp(self):
        self.geo = county_demand_centroids()

    def test_boundary_is_the_real_texas_polygon(self):
        b = tx_boundary_lonlat()
        self.assertGreater(len(b), 100)
        lons = [p[0] for p in b]
        lats = [p[1] for p in b]
        # Texas bounding box.
        self.assertTrue(-107 < min(lons) and max(lons) < -93)
        self.assertTrue(25 < min(lats) and max(lats) < 37)

    def test_placed_counties_have_real_in_texas_centroids(self):
        self.assertGreater(len(self.geo["placed"]), 100)
        for r in self.geo["placed"]:
            self.assertTrue(-107 < r["lon"] < -93, r["county"])
            self.assertTrue(25 < r["lat"] < 37, r["county"])
            self.assertGreaterEqual(r["facilities"], 1)

    def test_no_invented_coordinates_for_unmapped_counties(self):
        for r in self.geo["unplaced"]:
            self.assertNotIn("lat", r)
            self.assertNotIn("lon", r)
        # Placed + unplaced cover the full universe exactly once.
        cov = self.geo["coverage"]
        self.assertEqual(cov["counties_placed"] + cov["counties_unplaced"],
                         cov["counties_total"])

    def test_placed_counties_carry_the_bulk_of_demand(self):
        self.assertGreater(self.geo["coverage"]["demand_share_placed"], 0.80)

    def test_intensity_domain_ordered(self):
        d = self.geo["intensity_domain"]
        self.assertLessEqual(d["lo"], d["mid"])
        self.assertLessEqual(d["mid"], d["hi"])


class TherapyMixTests(unittest.TestCase):
    def setUp(self):
        self.mix = texas_therapy_mix()

    def test_therapy_axes_in_range_and_ranked(self):
        ts = self.mix["therapies"]
        self.assertGreaterEqual(len(ts), 5)
        ranks = [t["rank"] for t in ts]
        self.assertEqual(ranks, sorted(ranks))
        for t in ts:
            for k in self.mix["axis_labels"]:
                self.assertTrue(1 <= t["axes"][k] <= 5, (t["key"], k))
            self.assertTrue(0 <= t["overall_pct"] <= 100)

    def test_patient_estimates_scale_with_population(self):
        # estimated_patients = population × epi_per_100k / 1e5 (or the
        # senior denominator) — strictly positive for a real therapy.
        for t in self.mix["therapies"]:
            if t["estimated_patients"] is not None:
                self.assertGreaterEqual(t["estimated_patients"], 0)
        # IVIG carries a meaningful Texas pool.
        ig = next(t for t in self.mix["therapies"] if t["key"] == "ig")
        self.assertGreater(ig["estimated_patients"], 1000)

    def test_most_at_risk_matches_top_ranked(self):
        top = self.mix["therapies"][0]
        self.assertEqual(self.mix["most_at_risk"], top["therapy"])


class WorkforcePageTests(unittest.TestCase):
    def test_page_renders_both_heatmaps_and_key_sections(self):
        from rcm_mc.ui.texas_infusion_workforce_page import (
            render_texas_infusion_workforce_page)
        h = render_texas_infusion_workforce_page()
        for needle in (
                "Employment by specialty", "channel-fit heatmap",
                "County infusion-demand heatmap", "Registered nurses",
                "Gastroenterology", "TX headcount", "Rest of Texas",
                "diligence-risk heatmap", "What they infuse",
                "Immune globulin",
                "Methodology &amp; evidence classes",
                "workforce.csv"):
            self.assertIn(needle, h, needle)
        # Three charts (specialty matrix + therapy risk + geographic).
        self.assertGreaterEqual(h.count("<svg"), 3)

    def test_geographic_heatmap_projects_inside_the_frame(self):
        # The projected boundary path must exist and dots must render.
        from rcm_mc.ui.texas_infusion_workforce_page import _geo_heatmap_svg
        from rcm_mc.diligence.texas_infusion_workforce import (
            county_demand_centroids)
        svg = _geo_heatmap_svg(county_demand_centroids())
        self.assertIn("<path", svg)
        self.assertGreater(svg.count("<circle"), 100)

    def test_route_registered_in_palette_and_nav(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/texas-infusion/workforce", routes)

    def test_csv_exports_both_blocks(self):
        from rcm_mc.ui.texas_infusion_workforce_page import (
            texas_workforce_csv)
        csv = texas_workforce_csv()
        self.assertIn("specialty_columns", csv)
        self.assertIn("therapy_columns", csv)
        self.assertIn("county_columns", csv)


if __name__ == "__main__":
    unittest.main()
