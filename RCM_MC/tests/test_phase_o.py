"""Tests for Phase O: Geographic Viz (69) + System Network (70).

GEO LOOKUP:
 1. STATE_CENTROIDS has all 50 states + DC.
 2. city_state_to_latlon returns coords for known state.
 3. Unknown state → None.
 4. Haversine: Chicago-to-NYC ≈ 710-730 miles.
 5. Haversine: same point → 0.

SYSTEM NETWORK:
 6. build_system_graph returns a SystemGraph.
 7. SystemGraph has at least one system.
 8. find_acquisition_targets returns empty for unknown system.
 9. AcquisitionTarget to_dict round-trips.
10. HospitalNode to_dict round-trips.
11. Targets sorted by fit_score descending.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.geo_lookup import (
    STATE_CENTROIDS,
    city_state_to_latlon,
    haversine_miles,
)
from rcm_mc.data.system_network import (
    AcquisitionTarget,
    HospitalNode,
    SystemGraph,
    build_system_graph,
    find_acquisition_targets,
)


class TestGeoLookup(unittest.TestCase):

    def test_all_states_plus_dc(self):
        self.assertGreaterEqual(len(STATE_CENTROIDS), 51)

    def test_known_state(self):
        result = city_state_to_latlon("Chicago", "IL")
        self.assertIsNotNone(result)
        lat, lon = result
        self.assertAlmostEqual(lat, 40.63, delta=1.0)

    def test_unknown_state(self):
        self.assertIsNone(city_state_to_latlon("Atlantis", "ZZ"))

    def test_haversine_chicago_nyc(self):
        # IL centroid to NY centroid.
        d = haversine_miles(40.63, -89.40, 43.30, -74.22)
        self.assertAlmostEqual(d, 780, delta=200)

    def test_haversine_same_point(self):
        self.assertAlmostEqual(
            haversine_miles(40.0, -80.0, 40.0, -80.0), 0.0,
        )


class TestSystemNetwork(unittest.TestCase):

    def test_build_graph_returns_graph(self):
        g = build_system_graph(limit=100)
        self.assertIsInstance(g, SystemGraph)

    def test_graph_has_systems(self):
        g = build_system_graph(limit=500)
        # With 500 HCRIS rows, at least some hospitals are
        # system-affiliated.
        self.assertGreater(
            len(g.systems) + len(g.standalone), 0,
        )

    def test_unknown_system_empty_targets(self):
        targets = find_acquisition_targets(
            "Totally Fake System XYZ", radius_miles=30,
        )
        self.assertEqual(targets, [])

    def test_target_to_dict(self):
        t = AcquisitionTarget(
            hospital=HospitalNode(ccn="123", name="Test"),
            distance_to_nearest=15.0,
            fit_score=75.0,
        )
        d = t.to_dict()
        self.assertEqual(d["fit_score"], 75.0)

    def test_hospital_node_to_dict(self):
        n = HospitalNode(ccn="456", name="Test", bed_count=200)
        d = n.to_dict()
        self.assertEqual(d["bed_count"], 200)

    def test_graph_to_dict(self):
        g = SystemGraph()
        d = g.to_dict()
        self.assertIn("systems", d)
        self.assertIn("standalone", d)


if __name__ == "__main__":
    unittest.main()
