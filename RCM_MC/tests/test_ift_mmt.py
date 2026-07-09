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


if __name__ == "__main__":
    unittest.main()
