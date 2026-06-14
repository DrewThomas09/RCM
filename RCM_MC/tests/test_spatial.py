"""Tests for spatial competition (Huff gravity + Moran's I)."""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.diligence.spatial import (
    DemandPoint,
    Facility,
    SpatialVerdict,
    competitor_impact,
    haversine_km,
    huff_capture,
    local_morans_i,
    morans_i,
)


class HaversineTests(unittest.TestCase):

    def test_known_distance(self):
        # NYC (40.71,-74.01) to LA (34.05,-118.24) ≈ 3936 km.
        d = haversine_km(40.71, -74.01, 34.05, -118.24)
        self.assertAlmostEqual(d, 3936, delta=40)

    def test_zero_distance(self):
        self.assertAlmostEqual(haversine_km(40, -75, 40, -75), 0.0, places=6)


class HuffTests(unittest.TestCase):

    def test_closer_bigger_facility_captures_more(self):
        demand = [DemandPoint("d1", 40.0, -75.0, 1000.0)]
        facilities = [
            Facility("near_big", 40.05, -75.0, 200.0),   # close + attractive
            Facility("far_small", 41.0, -75.0, 50.0),     # far + small
        ]
        res = huff_capture(demand, facilities, beta=2.0,
                           target_facility_id="near_big")
        self.assertGreater(res.facility_capture["near_big"],
                           res.facility_capture["far_small"])
        self.assertGreater(res.target_share, 0.5)

    def test_shares_sum_to_one(self):
        demand = [
            DemandPoint("d1", 40.0, -75.0, 500.0),
            DemandPoint("d2", 40.2, -75.1, 500.0),
        ]
        facilities = [
            Facility("a", 40.0, -75.0, 100.0),
            Facility("b", 40.1, -75.05, 100.0),
            Facility("c", 40.3, -75.2, 100.0),
        ]
        res = huff_capture(demand, facilities)
        self.assertAlmostEqual(sum(res.market_share.values()), 1.0, places=6)
        self.assertAlmostEqual(sum(res.facility_capture.values()), 1000.0,
                               places=2)

    def test_higher_beta_favors_proximity(self):
        demand = [DemandPoint("d1", 40.0, -75.0, 1000.0)]
        facilities = [
            Facility("near", 40.02, -75.0, 100.0),
            Facility("far_big", 40.5, -75.0, 400.0),
        ]
        low = huff_capture(demand, facilities, beta=1.0)
        high = huff_capture(demand, facilities, beta=3.0)
        # Stronger distance decay shifts share to the near facility.
        self.assertGreater(high.market_share["near"], low.market_share["near"])

    def test_no_facilities_raises(self):
        with self.assertRaises(ValueError):
            huff_capture([DemandPoint("d", 40, -75, 1)], [])

    def test_dict_and_headline(self):
        res = huff_capture(
            [DemandPoint("d", 40, -75, 100)],
            [Facility("a", 40, -75, 10)], target_facility_id="a",
        )
        self.assertTrue(res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "SP1")


class MoransITests(unittest.TestCase):

    def test_clustered_pattern_detected(self):
        # High values in the north, low in the south → positive autocorr.
        lats, lons, vals = [], [], []
        for i in range(6):
            lats.append(41.0 + i * 0.01)
            lons.append(-75.0)
            vals.append(100.0)
        for i in range(6):
            lats.append(40.0 + i * 0.01)
            lons.append(-75.0)
            vals.append(10.0)
        res = morans_i(lats, lons, vals)
        self.assertEqual(res.verdict, SpatialVerdict.CLUSTERED)
        self.assertGreater(res.morans_i, res.expected_i)

    def test_zero_variance_is_random(self):
        res = morans_i([40, 41, 42], [-75, -75, -75], [5.0, 5.0, 5.0])
        self.assertEqual(res.verdict, SpatialVerdict.RANDOM)

    def test_too_few_points(self):
        res = morans_i([40, 41], [-75, -75], [1.0, 2.0])
        self.assertEqual(res.verdict, SpatialVerdict.RANDOM)
        self.assertEqual(res.n, 2)

    def test_p_value_in_unit_interval(self):
        rng = np.random.default_rng(0)
        lats = (40 + rng.random(20)).tolist()
        lons = (-75 + rng.random(20)).tolist()
        vals = rng.random(20).tolist()
        res = morans_i(lats, lons, vals)
        self.assertGreaterEqual(res.p_value, 0.0)
        self.assertLessEqual(res.p_value, 1.0)

    def test_dict(self):
        res = morans_i([40, 41, 42, 43], [-75, -75, -75, -75],
                       [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(res.to_dict()["citation_key"], "SP1")


class LisaTests(unittest.TestCase):

    def test_hot_spot_detected(self):
        # North cluster high, south cluster low → north points are HH.
        lats = [41.0, 41.01, 41.02, 40.0, 40.01, 40.02]
        lons = [-75.0] * 6
        vals = [100.0, 102.0, 98.0, 10.0, 9.0, 11.0]
        res = local_morans_i(lats, lons, vals, permutations=199, seed=0)
        self.assertEqual(res.n, 6)
        quads = {p.index: p.quadrant for p in res.points}
        # The high northern points sit in a high neighborhood → HH.
        self.assertEqual(quads[0], "HH")
        self.assertEqual(quads[3], "LL")

    def test_zero_variance(self):
        res = local_morans_i([40, 41, 42], [-75, -75, -75], [5.0, 5.0, 5.0])
        self.assertEqual(res.points, [])

    def test_too_few(self):
        res = local_morans_i([40, 41], [-75, -75], [1.0, 2.0])
        self.assertEqual(res.n, 2)
        self.assertEqual(res.points, [])

    def test_pvalues_valid_and_dict(self):
        res = local_morans_i([40, 41, 42, 43], [-75, -75, -75, -75],
                             [1.0, 2.0, 3.0, 4.0], permutations=99)
        for p in res.points:
            self.assertGreater(p.p_value, 0.0)
            self.assertLessEqual(p.p_value, 1.0)
        self.assertEqual(res.to_dict()["citation_key"], "SP1")


class EntrantImpactTests(unittest.TestCase):

    def test_new_entrant_takes_volume(self):
        demand = [DemandPoint("d1", 40.0, -75.0, 1000.0)]
        existing = [Facility("target", 40.02, -75.0, 100.0),
                    Facility("incumbent", 40.5, -75.0, 100.0)]
        entrant = Facility("newco", 40.03, -75.0, 150.0)  # right next to target
        res = competitor_impact(demand, existing, entrant, "target")
        self.assertGreater(res.volume_at_risk, 0)
        self.assertLess(res.capture_after, res.capture_before)
        self.assertGreater(res.new_entrant_capture, 0)
        self.assertGreater(res.pct_volume_lost, 0)

    def test_distant_entrant_minimal_impact(self):
        demand = [DemandPoint("d1", 40.0, -75.0, 1000.0)]
        existing = [Facility("target", 40.01, -75.0, 100.0)]
        far = Facility("newco", 48.0, -110.0, 100.0)   # far away
        res = competitor_impact(demand, existing, far, "target")
        self.assertLess(res.pct_volume_lost, 0.05)

    def test_dict_and_headline(self):
        demand = [DemandPoint("d1", 40.0, -75.0, 100.0)]
        existing = [Facility("target", 40.0, -75.0, 100.0)]
        entrant = Facility("newco", 40.0, -75.0, 100.0)
        res = competitor_impact(demand, existing, entrant, "target")
        self.assertTrue(res.headline)
        self.assertEqual(res.to_dict()["citation_key"], "SP1")


if __name__ == "__main__":
    unittest.main()
