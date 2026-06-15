"""Golden test for NEW-20 historic-versus-projected growth archetype map.

Hand-computed (threshold 5 percent):
    name      historic  projected  ebitda  quadrant
    A           0.03      0.12        49    Accelerators   (hist<5, proj>=5)
    B           0.08      0.10       250    Sustained      (hist>=5, proj>=5)
    C           0.06      0.02        60    Decelerators   (hist>=5, proj<5)
    D           0.01      0.01        30    Laggards       (hist<5, proj<5)

    total EBITDA = 389
    high-growth (projected>=5%) = A + B = 299, share = 299/389 = 0.76863...
"""
import unittest

from rcm_mc.cdd.growth_archetype import growth_archetype

SUBS = [
    {"name": "A", "historic": 0.03, "projected": 0.12, "ebitda": 49},
    {"name": "B", "historic": 0.08, "projected": 0.10, "ebitda": 250},
    {"name": "C", "historic": 0.06, "projected": 0.02, "ebitda": 60},
    {"name": "D", "historic": 0.01, "projected": 0.01, "ebitda": 30},
]


class TestGrowthArchetype(unittest.TestCase):
    def _build(self):
        return growth_archetype(SUBS, source="Golden", vintage="2024")

    def test_quadrant_assignment(self):
        pts = {p["label"]: p["quadrant"] for p in self._build().meta["points"]}
        self.assertEqual(pts["A"], "Accelerators")
        self.assertEqual(pts["B"], "Sustained growth")
        self.assertEqual(pts["C"], "Decelerators")
        self.assertEqual(pts["D"], "Laggards")

    def test_high_growth_share(self):
        self.assertAlmostEqual(self._build().meta["high_growth_share"],
                               299 / 389, delta=1e-9)

    def test_quadrant_ebitda(self):
        q = self._build().meta["quadrant_ebitda"]
        self.assertAlmostEqual(q["Sustained growth"], 250, delta=1e-9)
        self.assertAlmostEqual(q["Accelerators"], 49, delta=1e-9)

    def test_bubble_normalization(self):
        pts = {p["label"]: p["bubble_size"] for p in self._build().meta["points"]}
        self.assertAlmostEqual(pts["B"], 1.0, delta=1e-9)  # largest pool
        self.assertAlmostEqual(pts["D"], 30 / 250, delta=1e-9)

    def test_high_growth_small_flag(self):
        # above-line avg = (49+250)/2 = 149.5; below-line avg = (60+30)/2 = 45.
        # above is larger, so the flag should NOT fire here.
        self.assertNotIn("high_growth_pools_small", self._build().flag_codes())
        # Now make high-growth pools genuinely small.
        subs = [
            {"name": "small_fast", "historic": 0.02, "projected": 0.20, "ebitda": 5},
            {"name": "big_slow", "historic": 0.02, "projected": 0.01, "ebitda": 500},
        ]
        ex = growth_archetype(subs, source="Golden", vintage="2024")
        self.assertIn("high_growth_pools_small", ex.flag_codes())

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_requires_subsegment(self):
        with self.assertRaises(ValueError):
            growth_archetype([], source="Golden", vintage="2024")


if __name__ == "__main__":
    unittest.main()
