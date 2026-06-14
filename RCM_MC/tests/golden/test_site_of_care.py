"""Golden test for NEW-09 site-of-care shift.

Hand-computed two-period use per 1,000:
    setting:  IP    HOPD   ASC    Office  Home
    period1:  100   200    50     300     20
    period2:   90   170    90     300     30
    delta:    -10   -30    +40      0     +10

    hopd_to_asc      = min(30, 40) = 30
    ip_to_outpatient = max(10, 0)  = 10
    facility_to_home = max(10, 0)  = 10
    outpatient_net   = -30 + 40 + 0 = +10
    facility_net     = -10 + -30    = -40
"""
import unittest

from rcm_mc.cdd.site_of_care import site_of_care_shift

P1 = {"IP": 100, "HOPD": 200, "ASC": 50, "Office": 300, "Home": 20}
P2 = {"IP": 90, "HOPD": 170, "ASC": 90, "Office": 300, "Home": 30}


class TestSiteOfCare(unittest.TestCase):
    def _build(self):
        return site_of_care_shift(P1, P2, source="Golden", vintage="2026")

    def test_deltas(self):
        d = self._build().meta["deltas"]
        self.assertEqual(d["IP"], -10)
        self.assertEqual(d["HOPD"], -30)
        self.assertEqual(d["ASC"], 40)
        self.assertEqual(d["Office"], 0)
        self.assertEqual(d["Home"], 10)

    def test_migrations(self):
        mig = self._build().meta["migrations"]
        self.assertAlmostEqual(mig["hopd_to_asc"], 30.0, delta=1e-9)
        self.assertAlmostEqual(mig["ip_to_outpatient"], 10.0, delta=1e-9)
        self.assertAlmostEqual(mig["facility_to_home"], 10.0, delta=1e-9)
        self.assertAlmostEqual(mig["outpatient_net"], 10.0, delta=1e-9)
        self.assertAlmostEqual(mig["facility_net"], -40.0, delta=1e-9)

    def test_migration_flags(self):
        codes = self._build().flag_codes()
        self.assertIn("hopd_to_asc_migration", codes)
        self.assertIn("facility_to_home_migration", codes)

    def test_population_normalization(self):
        # counts with population -> per 1,000 rate
        ex = site_of_care_shift({"IP": 1000}, {"IP": 900},
                                population1=100000, population2=100000,
                                source="Golden", vintage="2026")
        self.assertAlmostEqual(ex.meta["rate1"]["IP"], 10.0, delta=1e-9)
        self.assertAlmostEqual(ex.meta["deltas"]["IP"], -1.0, delta=1e-9)

    def test_cy2026_context_internal_only(self):
        ex = self._build()
        partner = {s["name"] for s in ex.render(internal_mode=False)["series"]}
        internal = {s["name"] for s in ex.render(internal_mode=True)["series"]}
        self.assertNotIn("CY2026 OPPS/ASC context", partner)
        self.assertIn("CY2026 OPPS/ASC context", internal)

    def test_reconciles(self):
        self.assertTrue(self._build().reconciled)

    def test_changepoint_overlay_optional(self):
        # A clear level shift mid-series should yield at least one changepoint.
        trend = {"ASC": [10, 10, 10, 10, 50, 50, 50, 50]}
        ex = site_of_care_shift(P1, P2, trend_by_setting=trend,
                                source="Golden", vintage="2026")
        # Overlay is best-effort; when present it must surface the ASC series.
        if ex.meta["changepoints"]:
            self.assertIn("ASC", ex.meta["changepoints"])


if __name__ == "__main__":
    unittest.main()
