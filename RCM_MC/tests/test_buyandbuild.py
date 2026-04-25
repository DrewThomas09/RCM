"""Tests for the BuyAndBuildOptimizer."""
from __future__ import annotations

import unittest


# ── Synergy curves ──────────────────────────────────────────────

class TestSynergyCurve(unittest.TestCase):
    def test_zero_addons_zero_synergy(self):
        from rcm_mc.buyandbuild import default_physician_rollup_curve
        curve = default_physician_rollup_curve()
        self.assertEqual(curve.cumulative(0), 0.0)

    def test_marginal_decreases_after_inflection(self):
        from rcm_mc.buyandbuild import default_physician_rollup_curve
        curve = default_physician_rollup_curve()
        # The first add-on around the inflection delivers more
        # synergy than the eighth.
        m_4 = curve.marginal(4)
        m_8 = curve.marginal(8)
        self.assertGreater(m_4, m_8)


# ── Black-Scholes / binomial lattice ────────────────────────────

class TestBlackScholes(unittest.TestCase):
    def test_atm_call_value_positive(self):
        from rcm_mc.buyandbuild import black_scholes_call
        v = black_scholes_call(S=100, K=100, T=1.0, r=0.05,
                               sigma=0.25)
        self.assertGreater(v, 0)
        self.assertLess(v, 100)

    def test_zero_volatility_collapses_to_intrinsic(self):
        from rcm_mc.buyandbuild import black_scholes_call
        v = black_scholes_call(S=120, K=100, T=1.0, r=0.0, sigma=0.0)
        self.assertAlmostEqual(v, 20.0, places=2)


class TestBinomialLattice(unittest.TestCase):
    def test_european_matches_black_scholes(self):
        """European binomial should converge to BS at high steps."""
        from rcm_mc.buyandbuild import (
            black_scholes_call, binomial_lattice_call,
        )
        bs = black_scholes_call(S=100, K=100, T=1, r=0.05, sigma=0.25)
        lat = binomial_lattice_call(S=100, K=100, T=1, r=0.05,
                                    sigma=0.25, steps=200,
                                    american=False)
        self.assertAlmostEqual(bs, lat, places=1)

    def test_american_at_least_european(self):
        """American option should be ≥ European value."""
        from rcm_mc.buyandbuild import binomial_lattice_call
        eur = binomial_lattice_call(S=100, K=100, T=1, r=0.05,
                                    sigma=0.25, steps=100,
                                    american=False)
        am = binomial_lattice_call(S=100, K=100, T=1, r=0.05,
                                   sigma=0.25, steps=100,
                                   american=True)
        self.assertGreaterEqual(am, eur)

    def test_compound_call_positive_when_optionality(self):
        from rcm_mc.buyandbuild import binomial_lattice_compound
        v = binomial_lattice_compound(
            S=100, K_inner=110, T_inner=2.0,
            K_outer=5.0, T_outer=1.0,
            r=0.05, sigma=0.30,
            steps_outer=20, steps_inner=20,
        )
        # Compound call should have positive value
        self.assertGreater(v, 0)


# ── Constraints ─────────────────────────────────────────────────

class TestConstraints(unittest.TestCase):
    def test_block_prob_rises_with_topics(self):
        from rcm_mc.buyandbuild import (
            AddOnCandidate, regulatory_block_prob,
        )
        clean = AddOnCandidate(
            add_on_id="A", name="Clean",
            closing_risk_pct=0.05, regulatory_topics=[])
        risky = AddOnCandidate(
            add_on_id="B", name="Risky",
            closing_risk_pct=0.05,
            regulatory_topics=["ftc_noncompete", "antitrust_market"])
        self.assertGreater(
            regulatory_block_prob(risky),
            regulatory_block_prob(clean),
        )

    def test_geographic_density_buckets(self):
        from rcm_mc.buyandbuild import (
            Platform, AddOnCandidate, geographic_density_score,
        )
        p = Platform(platform_id="P", sector="mso",
                     base_ebitda_mm=20, base_ev_mm=200,
                     state="TX", cbsa="26420")
        same_cbsa = AddOnCandidate(
            add_on_id="A1", name="A1", state="TX", cbsa="26420")
        same_state = AddOnCandidate(
            add_on_id="A2", name="A2", state="TX", cbsa="19100")
        diff_state = AddOnCandidate(
            add_on_id="A3", name="A3", state="IL", cbsa="16980")
        self.assertEqual(
            geographic_density_score(p, same_cbsa), 1.0)
        self.assertEqual(
            geographic_density_score(p, same_state), 0.6)
        self.assertEqual(
            geographic_density_score(p, diff_state), 0.2)


# ── Optimizer ───────────────────────────────────────────────────

class TestOptimize(unittest.TestCase):
    def setUp(self):
        from rcm_mc.buyandbuild import Platform, AddOnCandidate
        self.platform = Platform(
            platform_id="PLAT", sector="physician_group",
            base_ebitda_mm=20, base_ev_mm=200,
            state="TX", cbsa="26420",
        )
        self.candidates = [
            AddOnCandidate(
                add_on_id="A1", name="Houston Clinic",
                purchase_price_mm=20.0,
                standalone_ebitda_mm=2.5,
                state="TX", cbsa="26420",
                closing_risk_pct=0.05),
            AddOnCandidate(
                add_on_id="A2", name="DFW Group",
                purchase_price_mm=35.0,
                standalone_ebitda_mm=4.0,
                state="TX", cbsa="19100",
                closing_risk_pct=0.08),
            AddOnCandidate(
                add_on_id="A3", name="Chicago Clinic",
                purchase_price_mm=15.0,
                standalone_ebitda_mm=1.6,
                state="IL", cbsa="16980",
                closing_risk_pct=0.10),
            AddOnCandidate(
                add_on_id="A4", name="Antitrust Risk",
                purchase_price_mm=80.0,
                standalone_ebitda_mm=8.0,
                state="TX", cbsa="26420",
                closing_risk_pct=0.20,
                regulatory_topics=["antitrust_market", "ftc_noncompete"]),
        ]

    def test_optimizer_picks_some_addons(self):
        from rcm_mc.buyandbuild import optimize_sequence
        result = optimize_sequence(self.platform, self.candidates)
        self.assertGreater(len(result.sequence), 0)
        self.assertGreater(result.cumulative_value_mm, 0)

    def test_blocked_sequence_excluded(self):
        """A constraint with very low max block prob should
        prevent the high-risk antitrust target from being chosen
        late in the sequence."""
        from rcm_mc.buyandbuild import (
            optimize_sequence, SequenceConstraints,
        )
        result = optimize_sequence(
            self.platform, self.candidates,
            constraints=SequenceConstraints(
                max_addons=5,
                max_total_capital_mm=400,
                max_cumulative_block_prob=0.20,
            ),
        )
        # Cumulative block should respect the constraint
        self.assertLessEqual(result.cumulative_block_prob, 0.20)


if __name__ == "__main__":
    unittest.main()
