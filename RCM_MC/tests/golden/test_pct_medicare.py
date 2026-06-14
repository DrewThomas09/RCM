"""Golden test for NEW-04 percentage-of-Medicare benchmarking.

Hand-computed fixture, medical-services-repriced basis:

    99213: comm 150, med 75,  vol 10 -> 200%,  comm 1500, med 750
    99214: comm 250, med 100, vol 4  -> 250%,  comm 1000, med 400
    70450: comm 180, med 120, vol 5  -> 150%,  comm 900,  med 600

    commercial total = 1500 + 1000 + 900 = 3400
    medicare total   =  750 +  400 + 600 = 1750
    blended pct      = 3400 / 1750 * 100 = 194.2857...
"""
import unittest

from rcm_mc.cdd.pct_medicare import (
    BASIS_FACILITY,
    BASIS_MEDICAL,
    pct_of_medicare,
)

CLAIMS = [
    {"code": "99213", "allowed": 150.0, "volume": 10},
    {"code": "99214", "allowed": 250.0, "volume": 4},
    {"code": "70450", "allowed": 180.0, "volume": 5},
]
SCHEDULE = {"99213": 75.0, "99214": 100.0, "70450": 120.0}


class TestPctMedicare(unittest.TestCase):
    def _build(self, basis=BASIS_MEDICAL, claims=None):
        return pct_of_medicare(claims or CLAIMS, SCHEDULE, basis=basis,
                               source="Golden", vintage="2026")

    def test_blended_and_per_code(self):
        m = self._build().meta
        self.assertAlmostEqual(m["blended_pct"], 3400.0 / 1750.0 * 100.0, delta=1e-9)
        by_code = {r["code"]: r["pct_of_medicare"] for r in m["per_code"]}
        self.assertAlmostEqual(by_code["99213"], 200.0, delta=1e-9)
        self.assertAlmostEqual(by_code["99214"], 250.0, delta=1e-9)
        self.assertAlmostEqual(by_code["70450"], 150.0, delta=1e-9)

    def test_basis_labeled_everywhere(self):
        ex = self._build()
        out = ex.render()
        self.assertEqual(out["footnote"]["basis"], BASIS_MEDICAL)
        self.assertIn(BASIS_MEDICAL, out["title"])
        self.assertEqual(ex.meta["basis"], BASIS_MEDICAL)

    def test_mixing_bases_flags(self):
        claims = [dict(c) for c in CLAIMS]
        claims[0]["basis"] = BASIS_FACILITY  # conflicts with requested medical basis
        ex = self._build(claims=claims)
        self.assertIn("basis_mismatch", ex.flag_codes())

    def test_invalid_basis_raises(self):
        with self.assertRaises(ValueError):
            pct_of_medicare(CLAIMS, SCHEDULE, basis="blended")

    def test_reference_anchors_present_and_labeled(self):
        anchors = self._build().meta["reference_anchors"]
        labels = {a["label"] for a in anchors}
        self.assertIn("Milliman medical services 2025", labels)
        # RAND facility-inclusive anchor must keep its basis label.
        rand = next(a for a in anchors if a["pct"] == 254.0)
        self.assertEqual(rand["basis"], BASIS_FACILITY)

    def test_missing_code_excluded_and_flagged(self):
        claims = CLAIMS + [{"code": "ZZZZZ", "allowed": 500.0, "volume": 1}]
        ex = self._build(claims=claims)
        self.assertIn("codes_missing_from_schedule", ex.flag_codes())
        # Blended unchanged because the missing code is excluded.
        self.assertAlmostEqual(ex.meta["blended_pct"], 3400.0 / 1750.0 * 100.0, delta=1e-9)

    def test_partner_hides_repricing_detail(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        self.assertNotIn("Repricing detail", partner)


if __name__ == "__main__":
    unittest.main()
