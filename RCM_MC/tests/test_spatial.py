"""Tests for spatial competition (Huff gravity + Moran's I)."""
from __future__ import annotations

import unittest

import numpy as np

from rcm_mc.diligence.spatial import (
    DemandPoint,
    Facility,
    SpatialVerdict,
    haversine_km,
    huff_capture,
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


if __name__ == "__main__":
    unittest.main()
