"""Golden test for NEW-15 competitive positioning map.

Players with thresholds share=0.30, attractiveness=0.5:
    Alpha: share 0.40, attr 0.8, rev 100 -> Leaders,      bubble 1.0
    Beta:  share 0.10, attr 0.3, rev 30  -> Niche,        bubble 0.3
    Gamma: share 0.25, attr 0.6, rev 60  -> Challengers,  bubble 0.6
"""
import unittest

from rcm_mc.cdd.positioning_map import positioning_map

PLAYERS = [
    {"name": "Alpha", "share": 0.40, "attractiveness": 0.8, "revenue": 100},
    {"name": "Beta", "share": 0.10, "attractiveness": 0.3, "revenue": 30},
    {"name": "Gamma", "share": 0.25, "attractiveness": 0.6, "revenue": 60},
]


class TestPositioningMap(unittest.TestCase):
    def _build(self):
        return positioning_map(PLAYERS, share_threshold=0.30,
                               attractiveness_threshold=0.5, source="Golden", vintage="2026")

    def test_coordinates_and_bubbles(self):
        pts = {p["label"]: p for p in self._build().meta["points"]}
        self.assertAlmostEqual(pts["Alpha"]["x"], 0.40, delta=1e-12)
        self.assertAlmostEqual(pts["Alpha"]["y"], 0.8, delta=1e-12)
        self.assertAlmostEqual(pts["Alpha"]["bubble_size"], 1.0, delta=1e-12)
        self.assertAlmostEqual(pts["Beta"]["bubble_size"], 0.30, delta=1e-12)
        self.assertAlmostEqual(pts["Gamma"]["bubble_size"], 0.60, delta=1e-12)

    def test_quadrants(self):
        pts = {p["label"]: p for p in self._build().meta["points"]}
        self.assertEqual(pts["Alpha"]["quadrant"], "Leaders")
        self.assertEqual(pts["Beta"]["quadrant"], "Niche")
        self.assertEqual(pts["Gamma"]["quadrant"], "Challengers")

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_default_thresholds_use_median(self):
        ex = positioning_map(PLAYERS, source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["share_threshold"], 0.25, delta=1e-12)
        self.assertAlmostEqual(ex.meta["attractiveness_threshold"], 0.6, delta=1e-12)

    def test_source_noted(self):
        fn = self._build().render()["footnote"]
        self.assertTrue(fn["source"])
        self.assertTrue(fn["vintage"])

    def test_single_player(self):
        ex = positioning_map([{"name": "solo", "share": 0.5, "attractiveness": 0.5, "revenue": 10}],
                             source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["points"][0]["bubble_size"], 1.0, delta=1e-12)
        self.assertTrue(ex.reconciled)


if __name__ == "__main__":
    unittest.main()
