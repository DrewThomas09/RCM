"""Tests for the PayerNegotiationSimulator.

Coverage: outside-options percentile math, Nash bargaining at
varying alpha, repeated-game leverage convergence, post-merger
counterfactual rate uplift, antitrust HHI bands.
"""
from __future__ import annotations

import os
import tempfile
import unittest


def _seed_payer_rates(db: str) -> None:
    """Populate the pricing store with a synthetic payer-rate
    landscape for CPT 27447 across 4 NPIs × 4 payers."""
    from rcm_mc.pricing import PricingStore
    store = PricingStore(db)
    store.init_db()
    rates = [
        # (payer, npi, rate)
        ("Aetna (CVS)", "N1", 24500),
        ("Aetna (CVS)", "N2", 23000),
        ("Aetna (CVS)", "N3", 26000),
        ("Aetna (CVS)", "N4", 27500),
        ("BCBS Texas",  "N1", 25800),
        ("BCBS Texas",  "N2", 24200),
        ("BCBS Texas",  "N3", 27300),
        ("BCBS Texas",  "N4", 28800),
        ("UnitedHealthcare", "N1", 26200),
        ("UnitedHealthcare", "N2", 24800),
        ("UnitedHealthcare", "N3", 28000),
        ("UnitedHealthcare", "N4", 29200),
        ("Cigna",       "N1", 25500),
        ("Cigna",       "N2", 23900),
        ("Cigna",       "N3", 27800),
        ("Cigna",       "N4", 28500),
    ]
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        for payer, npi, rate in rates:
            con.execute(
                "INSERT INTO pricing_payer_rates "
                "(payer_name, plan_name, npi, code, code_type, "
                " negotiation_arrangement, negotiated_rate, "
                " loaded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (payer, "PPO", npi, "27447", "CPT", "ffs",
                 rate, now),
            )
        con.commit()


# ── Outside options ─────────────────────────────────────────────

class TestOutsideOptions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_payer_rates(self.db)
        from rcm_mc.pricing import PricingStore
        self.store = PricingStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_summarizes_distribution(self):
        from rcm_mc.negotiation import compute_outside_options
        # NPI N1 across 4 payers — rates 24500, 25500, 25800, 26200.
        # Linear-interp p25=25250, p50=25650, p75=25900.
        oo = compute_outside_options(self.store, "N1", "27447")
        self.assertEqual(oo.rate_count, 4)
        self.assertEqual(oo.payer_count, 4)
        self.assertAlmostEqual(oo.p25, 25250, places=0)
        self.assertAlmostEqual(oo.p75, 25900, places=0)
        self.assertAlmostEqual(oo.surplus, 25900 - 25250, places=0)

    def test_excludes_focus_payer(self):
        """Outside options FROM Aetna's perspective should drop
        Aetna's own rate from the comparison."""
        from rcm_mc.negotiation import compute_outside_options
        oo = compute_outside_options(
            self.store, "N1", "27447",
            exclude_payer="Aetna (CVS)",
        )
        # 4 - 1 = 3 rates remaining
        self.assertEqual(oo.rate_count, 3)
        self.assertEqual(oo.payer_count, 3)


# ── Nash bargaining ─────────────────────────────────────────────

class TestNashBargaining(unittest.TestCase):
    def test_equal_power_picks_midpoint(self):
        from rcm_mc.negotiation import (
            nash_bargaining, OutsideOptions,
        )
        oo = OutsideOptions(
            npi="N1", code="27447",
            p25=24000.0, p75=28000.0, surplus=4000.0,
        )
        state = nash_bargaining(oo, alpha=0.5)
        self.assertEqual(state.negotiated_rate, 26000.0)

    def test_strong_provider_lifts_rate(self):
        from rcm_mc.negotiation import (
            nash_bargaining, OutsideOptions,
        )
        oo = OutsideOptions(
            npi="N1", code="27447",
            p25=24000.0, p75=28000.0, surplus=4000.0,
        )
        weak = nash_bargaining(oo, alpha=0.2).negotiated_rate
        strong = nash_bargaining(oo, alpha=0.9).negotiated_rate
        self.assertGreater(strong, weak)


# ── Repeated game ───────────────────────────────────────────────

class TestRepeatedGame(unittest.TestCase):
    def test_high_payer_leverage_drops_rate(self):
        from rcm_mc.negotiation import (
            repeated_game_rate, OutsideOptions,
        )
        oo = OutsideOptions(
            npi="N1", code="27447",
            p25=24000.0, p75=28000.0, surplus=4000.0,
        )
        weak_payer = repeated_game_rate(
            oo, payer_name="A",
            payer_leverage=0.1,    # provider strong
        )
        strong_payer = repeated_game_rate(
            oo, payer_name="A",
            payer_leverage=0.9,    # payer strong
        )
        self.assertGreater(weak_payer.negotiated_rate,
                           strong_payer.negotiated_rate)


# ── Post-merger counterfactual ──────────────────────────────────

class TestPostMerger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_payer_rates(self.db)
        from rcm_mc.pricing import PricingStore
        self.store = PricingStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_merger_uplift_positive(self):
        """Merging two NPIs reduces the payer's outside options →
        post-merger rate higher than pre-merger."""
        from rcm_mc.negotiation import simulate_post_merger_rate
        result = simulate_post_merger_rate(
            self.store,
            npi_list=["N1", "N2"],
            code="27447",
            payer_name="Aetna (CVS)",
        )
        self.assertGreaterEqual(result["uplift_dollars"], 0)
        self.assertEqual(result["merging_npi_count"], 2)


# ── Antitrust risk ──────────────────────────────────────────────

class TestAntitrustRisk(unittest.TestCase):
    def test_unconcentrated_market(self):
        from rcm_mc.negotiation import antitrust_risk_score
        # 10 evenly-distributed competitors → 1000 HHI
        result = antitrust_risk_score([0.1] * 10)
        self.assertEqual(result["band"], "unconcentrated")
        self.assertAlmostEqual(result["hhi"], 1000.0, places=1)

    def test_highly_concentrated_market(self):
        from rcm_mc.negotiation import antitrust_risk_score
        # One firm with 80%, two with 10% each
        result = antitrust_risk_score([0.8, 0.1, 0.1])
        self.assertEqual(result["band"], "highly_concentrated")
        self.assertGreater(result["hhi"], 2500)


if __name__ == "__main__":
    unittest.main()
