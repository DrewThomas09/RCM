"""Real-path tests for the MMT county-resolved footprint model (ift_mmt).

Pins the OMB/Census structure (22 counties across 7 CBSAs), the demand roll-ups,
and the honesty + wiring invariants on the county-grain connectors (registered
dataset_ids, `__in` grammar, real county/FIPS columns, degrade-safe offline).
"""
from __future__ import annotations

import unittest

from rcm_mc.market_reports import ift_mmt as m
from rcm_mc.data_public import connector_estate as ce


class MmtFootprintTests(unittest.TestCase):
    def test_footprint_shape(self):
        s = m.footprint_summary()
        self.assertEqual(s.n_county, len(m.MMT_COUNTIES))
        self.assertEqual(s.n_cbsa, 7)
        self.assertEqual(s.n_msa + s.n_micro, s.n_cbsa)
        self.assertEqual(s.n_states, 2)          # NE + IA
        self.assertGreater(s.pop_2020, 1_000_000)  # ~1.56M
        self.assertTrue(0.10 < s.senior_share < 0.30)
        self.assertGreater(s.demand_missions, 0)
        self.assertGreater(s.demand_dollars, 0)

    def test_counties_have_valid_fips(self):
        for c in m.MMT_COUNTIES:
            self.assertEqual(len(c.fips), 5, c.name)
            self.assertTrue(c.fips.isdigit(), c.name)
            self.assertIn(c.state, ("NE", "IA"), c.name)
            self.assertGreater(c.pop_2020, 0, c.name)
            self.assertIn(c.role, ("core", "suburban", "rural-feeder"), c.name)

    def test_cbsa_rollups_sum_to_footprint(self):
        cbsas = m.footprint_cbsas()
        self.assertEqual(sum(len(b.counties) for b in cbsas), len(m.MMT_COUNTIES))
        self.assertEqual(sum(b.pop_2020 for b in cbsas),
                         sum(c.pop_2020 for c in m.MMT_COUNTIES))
        # biggest CBSA first, and Omaha (HQ) is the biggest
        self.assertEqual(cbsas[0].metro, "Omaha")
        self.assertEqual(cbsas, sorted(cbsas, key=lambda b: -b.pop_2020))

    def test_demand_model_is_age_split_and_positive(self):
        for c in m.MMT_COUNTIES:
            d = m.county_demand(c)
            self.assertGreaterEqual(d.demand_missions, 0, c.name)
            self.assertEqual(d.pop_65_plus, c.pop_65_plus, c.name)
            # a county with more seniors should generate more per-capita demand
        # footprint demand equals the sum of county demand
        tot = sum(m.county_demand(c).demand_missions for c in m.MMT_COUNTIES)
        self.assertEqual(m.footprint_summary().demand_missions, tot)


class MmtConnectorTests(unittest.TestCase):
    def setUp(self):
        self.cov = m.county_connector_coverage()

    def test_every_county_connector_is_registered(self):
        for c in self.cov:
            self.assertIsNotNone(
                ce.dataset_owner(c.dataset_id),
                f"{c.key}: unregistered dataset {c.dataset_id}")
            self.assertEqual(ce.dataset_owner(c.dataset_id), c.connector, c.key)

    def test_county_connectors_degrade_safely(self):
        # offline: network-gated, honest fallback, never SOURCED over zero rows
        for c in self.cov:
            self.assertIn(c.basis, ("SOURCED", "CONNECTOR"), c.key)
            if not c.available:
                self.assertEqual(c.n_rows, 0, c.key)
                self.assertTrue(c.fallback_citation, c.key)
            self.assertTrue(c.yields, c.key)

    def test_probe_filters_and_columns_are_valid(self):
        # the county filters MUST use the estate `__in` grammar on a real column,
        # or the probe can never flip to SOURCED. Validate against the schema.
        h = ce._load()
        if h is None:
            self.skipTest("estate not loadable")
        adapters = h[1].adapters()
        for p in m._COUNTY_PROBES:
            owner = ce.dataset_owner(p["dataset_id"])
            adapter = adapters.get(owner)
            if adapter is None:
                continue
            r = adapter.by_dataset_id().get(p["dataset_id"])
            table = adapter.tables_mod.TABLES.get(getattr(r, "target_table", None))
            cols = set(getattr(table, "columns", []) or [])
            if not cols:
                continue
            self.assertIn(p["group_by"], cols,
                          f"{p['key']}: group_by not on table")
            fc = p.get("filter_col")
            if fc:
                self.assertIn(fc, cols, f"{p['key']}: filter_col {fc} not on table")


class MmtLinkTests(unittest.TestCase):
    def test_clinical_drivers_carry_validated_icd10(self):
        drivers = m.clinical_drivers(10)
        self.assertTrue(drivers)
        for d in drivers:
            self.assertTrue(d.condition)
            self.assertLessEqual(d.codes_valid, d.codes_total)

    def test_metro_reads_tie_to_geo(self):
        reads = m.mmt_metro_reads()
        metros = {r.metro for r in reads}
        # MMT's five served metros are all present
        for expected in ("Omaha", "Lincoln", "North Platte", "Columbus (NE)",
                         "Grand Island / Kearney"):
            self.assertIn(expected, metros)
        # MMT itself is never listed as its own competitor
        for r in reads:
            for comp in r.competitors:
                self.assertNotIn("MMT", comp)


class MmtModelTests(unittest.TestCase):
    def test_serviceable_som_is_consistent_and_bounded(self):
        sm = m.mmt_serviceable_model()
        self.assertTrue(sm.rows)
        # SOM never exceeds serviceable never exceeds demand
        self.assertLessEqual(sm.mmt_som_missions, sm.total_serviceable)
        self.assertLessEqual(sm.total_serviceable, sm.total_demand)
        self.assertGreater(sm.mmt_som_dollars, 0)
        # s(m) matches the study funnel (reused from ift_analytics)
        from rcm_mc.market_reports import ift_analytics as _an, ift_geo as _geo
        cls = {md.name: md.insource_class for md in _geo.MARKETS}
        for r in sm.rows:
            want = _an._SERVICEABLE_SHARE.get(cls.get(r.metro), _an._SERVICEABLE_DEFAULT)
            self.assertAlmostEqual(r.serviceable_share, want, places=4, msg=r.metro)
            self.assertLessEqual(r.mmt_missions, r.serviceable_missions)
        # roll-up equals the row sum
        self.assertEqual(sm.mmt_som_missions,
                         sum(r.mmt_missions for r in sm.rows))

    def test_operating_model_margin_and_metrics(self):
        op = m.mmt_operating_model()
        self.assertGreater(len(op.metrics), 5)
        self.assertTrue(0.0 < op.contribution_margin_pct < 0.6)
        self.assertGreaterEqual(op.est_units, 1)
        self.assertTrue(op.headline)

    def test_growth_projection_compounds_and_platform_leads(self):
        gp = m.mmt_growth_projection(5)
        self.assertTrue(gp.available)
        self.assertEqual(len(gp.years), 6)                    # year 0..5
        # today == the SOM start on both cases
        self.assertAlmostEqual(gp.years[0].base_revenue, gp.start_revenue, places=2)
        # monotonically increasing and platform >= base each year
        for i in range(1, len(gp.years)):
            self.assertGreater(gp.years[i].base_revenue, gp.years[i - 1].base_revenue)
            self.assertGreaterEqual(gp.years[i].platform_revenue,
                                    gp.years[i].base_revenue)
        self.assertGreaterEqual(gp.platform_cagr, gp.base_cagr)

    def test_swot_has_all_four_quadrants(self):
        sw = m.mmt_swot()
        for quad in (sw.strengths, sw.weaknesses, sw.opportunities, sw.threats):
            self.assertGreaterEqual(len(quad), 3)

    def test_county_opportunity_ranks_and_splits(self):
        opp = m.mmt_county_opportunity()
        self.assertEqual(len(opp), len(m.MMT_COUNTIES))
        # ranked descending by contestable $, ranks 1..N, Douglas (Omaha) is #1
        self.assertEqual([o.rank for o in opp], list(range(1, len(opp) + 1)))
        self.assertEqual(opp[0].name, "Douglas")
        for o in opp:
            # current + headroom == the contestable book (share split)
            self.assertAlmostEqual(
                o.mmt_current_revenue + o.headroom_revenue,
                o.opportunity_revenue, places=2, msg=o.name)
        vals = [o.opportunity_revenue for o in opp]
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_payer_mix_reconciles_and_commercial_leads_revenue(self):
        pm = m.mmt_payer_mix()
        self.assertGreaterEqual(len(pm.rows), 3)
        # revenue shares sum to 1 and revenue dollars sum to the SOM
        self.assertAlmostEqual(sum(r.revenue_share for r in pm.rows), 1.0, places=4)
        self.assertAlmostEqual(sum(r.revenue_dollars for r in pm.rows),
                               pm.som_dollars, places=0)
        comm = next(r for r in pm.rows if r.payer == "Commercial")
        # commercial's revenue share exceeds its transport share (the multiple)
        self.assertGreater(comm.revenue_share, comm.share)

    def test_som_scenario_bands_bracket_the_base(self):
        sc = m.mmt_som_scenario()
        self.assertGreater(sc.base_som, 0)
        self.assertLess(sc.downside_som, sc.base_som)
        self.assertGreater(sc.upside_som, sc.base_som)
        self.assertGreaterEqual(len(sc.levers), 3)
        for lv in sc.levers:
            self.assertLess(lv.low_som, lv.high_som, lv.name)

    def test_model_json_is_serializable_and_complete(self):
        import json
        d = m.mmt_model_json()
        json.dumps(d)                     # must not raise
        for key in ("footprint", "counties", "serviceable", "scenario",
                    "operating_model", "growth", "opportunity",
                    "anchor_accounts", "connectors", "swot", "diligence"):
            self.assertIn(key, d, key)
        self.assertEqual(len(d["counties"]), len(m.MMT_COUNTIES))
        self.assertEqual(d["counties"][0].get("pop_65_plus") is not None, True)

    def test_anchor_accounts_carry_strategy(self):
        accts = m.mmt_anchor_accounts()
        self.assertGreaterEqual(len(accts), 5)
        systems = " ".join(a.system for a in accts)
        self.assertIn("CHI Health", systems)          # the #1 captive network
        for a in accts:
            self.assertTrue(a.metros and a.mmt_strategy and a.risk)
            self.assertIn(a.tier,
                          ("captive-network", "regional-hub", "independent"))

    def test_diligence_and_scorecard_are_populated(self):
        d = m.mmt_diligence()
        self.assertGreaterEqual(len(d.value_levers), 4)
        self.assertGreaterEqual(len(d.risks), 4)
        self.assertGreaterEqual(len(d.questions), 5)
        for rk in d.risks:
            self.assertIn(rk.tag, ("HIGH", "MEDIUM", "LOW"), rk.title)
        sc = m.mmt_positioning_scorecard()
        self.assertGreaterEqual(len(sc), 5)
        for r in sc:
            self.assertTrue(r.factor and r.mmt)


class MmtPageTests(unittest.TestCase):
    def setUp(self):
        from rcm_mc.ui.ift_mmt_page import render_ift_mmt
        self.html = render_ift_mmt()

    def test_renders_every_section(self):
        for needle in ("Company Deep Dive", "Footprint by CBSA",
                       "Every county MMT serves", "Serviceable market (SOM)",
                       "Operating model", "County-grain data-connector coverage",
                       "clinical drivers", "moat read", "Positioning scorecard",
                       "Growth projection", "SWOT", "County opportunity ranking",
                       "Anchor-system account map", "SOM scenario band",
                       "Payer mix", "VALUE-CREATION LEVERS", "DILIGENCE QUESTIONS",
                       # 2026-07-10 company-truth sections (research pull)
                       "NPPES-verified", "Ownership &amp; scale",
                       "Hospital-system customer deep dives",
                       "Competitive landscape", "Litigation",
                       "legacy core, county by county"):
            self.assertIn(needle, self.html, f"missing section: {needle}")

    def test_surfaces_counties_and_connectors(self):
        # a real county FIPS + the connector-estate deep links are present
        self.assertIn("31055", self.html)                       # Douglas County
        self.assertIn("connector-estate?dataset=census_acs_county_profile",
                      self.html)
        self.assertIn("/api/ift/markets.xlsx", self.html)

    def test_no_raw_none_or_dataclass_leaks(self):
        self.assertNotIn(">None<", self.html)
        self.assertNotIn("MmtCounty(", self.html)
        self.assertNotIn("object at 0x", self.html)


if __name__ == "__main__":
    unittest.main()
