"""Golden test for NEW-01 Bottom-up TAM/SAM/SOM engine.

Hand-computed 3-segment toy market:

    A Hospital outpatient: 1000 units x $10, penetration 0.5, reachable
    B ASC:                  500 units x $20, penetration 0.4, reachable
    C Office:              2000 units x $5,  penetration 0.3, NOT reachable

    TAM = 1000*10 + 500*20 + 2000*5 = 10000 + 10000 + 10000 = 30000
    SAM = reachable (A,B)           = 10000 + 10000          = 20000
    SAM units                        = 1000 + 500            = 1500
    blended reachable price          = 20000 / 1500          = 13.33333...
    demand ceiling = 1000*0.5*10 + 500*0.4*20 = 5000 + 4000  = 9000
    winnable units = capacity 600 * win_rate 0.5             = 300
    SOM capacity   = 300 * 13.33333...                       = 4000
    SOM = min(4000, 9000)                                    = 4000

Top-down 33000 diverges 3000/33000 = 9.09% (within 20%, no flag).
Top-down 50000 diverges 20000/50000 = 40% (above 20%, must flag).
"""
import unittest

from rcm_mc.cdd.tam_sam_som import tam_sam_som

SEGMENTS = [
    {"segment": "Hospital outpatient", "unit_count": 1000, "price": 10.0, "penetration_rate": 0.5},
    {"segment": "ASC", "unit_count": 500, "price": 20.0, "penetration_rate": 0.4},
    {"segment": "Office", "unit_count": 2000, "price": 5.0, "penetration_rate": 0.3, "reachable": False},
]

TOL = 1e-6


class TestTamSamSom(unittest.TestCase):
    def _build(self, top_down):
        return tam_sam_som(
            SEGMENTS,
            sales_capacity_units=600,
            win_rate=0.5,
            top_down=top_down,
            source="Golden fixture",
            vintage="2026",
        )

    def test_hand_computed_values(self):
        ex = self._build(33000.0)
        m = ex.meta
        self.assertAlmostEqual(m["tam"], 30000.0, delta=TOL,
                               msg=f"TAM expected 30000 got {m['tam']}")
        self.assertAlmostEqual(m["sam"], 20000.0, delta=TOL,
                               msg=f"SAM expected 20000 got {m['sam']}")
        self.assertAlmostEqual(m["demand_ceiling"], 9000.0, delta=TOL)
        self.assertAlmostEqual(m["blended_reachable_price"], 20000.0 / 1500.0, delta=TOL)
        self.assertAlmostEqual(m["winnable_units"], 300.0, delta=TOL)
        self.assertAlmostEqual(m["som"], 4000.0, delta=TOL,
                               msg=f"SOM expected 4000 got {m['som']}")
        # Ordering invariant.
        self.assertLessEqual(m["som"], m["sam"] + TOL)
        self.assertLessEqual(m["sam"], m["tam"] + TOL)

    def test_convergence_within_tolerance_no_flag(self):
        ex = self._build(33000.0)
        self.assertNotIn("tam_divergence", ex.flag_codes())
        self.assertTrue(ex.reconciled,
                        msg="9.09% divergence should reconcile within 20% tolerance")

    def test_divergence_above_tolerance_flags(self):
        ex = self._build(50000.0)
        self.assertIn("tam_divergence", ex.flag_codes(),
                      msg="40% divergence must raise tam_divergence flag")
        self.assertFalse(ex.reconciled,
                         msg="40% divergence must not reconcile within 20% tolerance")

    def test_assumptions_editable_and_sourced(self):
        ex = self._build(33000.0)
        self.assertTrue(ex.assumptions, "must expose assumption nodes")
        keys = {a.key for a in ex.assumptions}
        self.assertIn("win_rate", keys)
        self.assertIn("sales_capacity_units", keys)
        for a in ex.assumptions:
            self.assertTrue(a.source, f"assumption {a.key} must be sourced")
            self.assertTrue(a.editable, f"assumption {a.key} must be editable")

    def test_partner_view_hides_assumptions_internal_shows(self):
        ex = self._build(33000.0)
        partner = ex.render(internal_mode=False)
        internal = ex.render(internal_mode=True)
        self.assertNotIn("assumptions", partner,
                         msg="partner view must not leak assumption nodes")
        self.assertIn("assumptions", internal)
        self.assertTrue(internal["assumptions"])
        # Internal-only segment series is stripped for the partner.
        partner_series = {s["name"] for s in partner["series"]}
        internal_series = {s["name"] for s in internal["series"]}
        self.assertNotIn("Segments", partner_series)
        self.assertIn("Segments", internal_series)

    def test_footnote_present_and_machine_readable(self):
        ex = self._build(33000.0)
        fn = ex.render(internal_mode=False)["footnote"]
        self.assertTrue(fn["source"])
        self.assertTrue(fn["vintage"])
        self.assertTrue(fn["assumptions"])

    def test_reconciliation_emitted(self):
        ex = self._build(50000.0)
        rec = ex.render()["reconciliations"]
        self.assertEqual(len(rec), 1)
        # Reconciliation prints expected vs actual so a failure is actionable.
        r = rec[0]
        self.assertAlmostEqual(r["lhs"], 20000.0 / 50000.0, delta=TOL,
                               msg=f"divergence expected 0.40 got {r['lhs']}, gap {r['gap']}")

    def test_degenerate_single_segment_does_not_crash(self):
        ex = tam_sam_som(
            [{"segment": "Solo", "unit_count": 10, "price": 5.0, "penetration_rate": 0.5}],
            sales_capacity_units=4,
            win_rate=0.5,
            source="Golden fixture",
            vintage="2026",
        )
        self.assertAlmostEqual(ex.meta["tam"], 50.0, delta=TOL)
        # capacity 4 * 0.5 = 2 winnable units * price 5 = 10; demand 10*0.5*5=25
        self.assertAlmostEqual(ex.meta["som"], 10.0, delta=TOL)

    def test_empty_segments_raises(self):
        with self.assertRaises(ValueError):
            tam_sam_som([], sales_capacity_units=1, win_rate=0.5)


if __name__ == "__main__":
    unittest.main()
