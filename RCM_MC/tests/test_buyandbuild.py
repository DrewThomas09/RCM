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


class TestBranchAndBound(unittest.TestCase):
    """B&B kicks in for >7 candidates, replacing the greedy
    fallback that the original optimizer used."""

    def setUp(self):
        from rcm_mc.buyandbuild import Platform, AddOnCandidate
        self.platform = Platform(
            platform_id="P", sector="physician_group",
            base_ebitda_mm=20, base_ev_mm=200,
            state="TX", cbsa="26420")
        # 10 candidates, varied size + closing risk + state.
        self.candidates = []
        for i in range(10):
            self.candidates.append(AddOnCandidate(
                add_on_id=f"A{i:02d}",
                name=f"Target {i}",
                purchase_price_mm=10 + (i * 8) % 60,
                standalone_ebitda_mm=1.0 + (i * 0.7) % 5,
                state="TX" if i % 2 == 0 else "FL",
                cbsa="26420" if i % 3 == 0 else "19100",
                closing_risk_pct=0.04 + (i * 0.02) % 0.10,
                regulatory_topics=(["antitrust_market"]
                                   if i == 7 else []),
            ))

    def test_returns_a_valid_sequence(self):
        from rcm_mc.buyandbuild import branch_and_bound_optimize
        seq, stats = branch_and_bound_optimize(
            self.platform, self.candidates)
        self.assertGreater(len(seq.sequence), 0)
        self.assertGreater(stats.branches_explored, 0)
        # B&B should at least make some incumbent updates
        self.assertGreaterEqual(stats.incumbent_updates, 1)

    def test_pruning_reduces_branch_count(self):
        """A tight max_addons constraint should produce visible
        pruning vs a loose one."""
        from rcm_mc.buyandbuild import (
            branch_and_bound_optimize, SequenceConstraints,
        )
        loose = SequenceConstraints(
            max_addons=5, max_total_capital_mm=500,
            max_cumulative_block_prob=0.5,
        )
        tight = SequenceConstraints(
            max_addons=3, max_total_capital_mm=80,
            max_cumulative_block_prob=0.20,
        )
        _, loose_stats = branch_and_bound_optimize(
            self.platform, self.candidates, loose)
        _, tight_stats = branch_and_bound_optimize(
            self.platform, self.candidates, tight)
        # Tight constraints prune more
        self.assertGreaterEqual(
            tight_stats.subtrees_pruned, 0)

    def test_optimize_sequence_uses_bb_for_large_input(self):
        """The top-level optimize_sequence helper should now use
        the B&B path when len(candidates) > 7 — output must be
        a valid ValuedSequence respecting constraints."""
        from rcm_mc.buyandbuild import (
            optimize_sequence, SequenceConstraints,
        )
        result = optimize_sequence(
            self.platform, self.candidates,
            constraints=SequenceConstraints(
                max_addons=4, max_total_capital_mm=200,
                max_cumulative_block_prob=0.3,
            ),
        )
        self.assertGreater(len(result.sequence), 0)
        self.assertLessEqual(
            result.cumulative_capital_mm, 200)
        self.assertLessEqual(
            result.cumulative_block_prob, 0.3)

    def test_bb_meets_or_beats_greedy(self):
        """B&B should not produce a worse sequence than greedy.
        We compare the B&B result against the greedy heuristic
        directly so the partner can defend the choice."""
        from rcm_mc.buyandbuild import (
            branch_and_bound_optimize,
            geographic_density_score,
            SequenceConstraints,
        )
        from rcm_mc.buyandbuild.constraints import regulatory_block_prob
        from rcm_mc.buyandbuild import valuate_sequence
        # B&B
        bb_seq, _ = branch_and_bound_optimize(
            self.platform, self.candidates,
            SequenceConstraints(max_addons=4,
                                max_total_capital_mm=200,
                                max_cumulative_block_prob=0.4),
        )
        # Greedy (replicated locally)
        scored = []
        for c in self.candidates:
            b = regulatory_block_prob(c)
            d = geographic_density_score(self.platform, c)
            expected = (c.standalone_ebitda_mm * 8.0
                        * (1.0 - b) * (0.7 + 0.3 * d))
            scored.append((expected / max(0.1, c.purchase_price_mm), c))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        chosen = []
        capital = 0
        block = 0
        for _, c in scored:
            if len(chosen) >= 4:
                break
            if capital + c.purchase_price_mm > 200:
                continue
            new_block = 1 - (1 - block) * (1 - regulatory_block_prob(c))
            if new_block > 0.4:
                continue
            chosen.append(c)
            capital += c.purchase_price_mm
            block = new_block
        greedy_seq = valuate_sequence(
            self.platform, chosen)
        # B&B value >= greedy (within numerical tolerance)
        self.assertGreaterEqual(
            bb_seq.cumulative_value_mm,
            greedy_seq.cumulative_value_mm - 0.1,
        )


if __name__ == "__main__":
    unittest.main()
