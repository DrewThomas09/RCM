"""Branch-and-bound search across feasible add-on sequences.

For each candidate sequence:
  1. Compute cumulative synergy via the SynergyCurve.
  2. Compound regulatory-blocking probability across the
     sequence — sequences with high cumulative blocking are
     pruned.
  3. Use the binomial-lattice compound option to value the
     optionality of holding off on the late-stage add-ons.

Returns the best sequence + its value (NPV-style number).

The search space is the permutations of ``candidates`` truncated
to ``constraints.max_addons``; with N=8 candidates that's 40,320.
We branch-and-bound by ordering candidates by per-dollar
expected synergy and pruning subtrees whose upper bound falls
below the current incumbent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations
from typing import Iterable, List, Optional, Tuple

from .candidates import AddOnCandidate, Platform
from .constraints import (
    SequenceConstraints,
    regulatory_block_prob,
    geographic_density_score,
)
from .options import binomial_lattice_call
from .synergy import SynergyCurve, default_physician_rollup_curve


@dataclass
class ValuedSequence:
    sequence: List[str]                 # add-on IDs in order
    cumulative_value_mm: float
    cumulative_capital_mm: float
    cumulative_block_prob: float
    synergy_share: float                # fraction of platform EBITDA
    notes: List[str] = field(default_factory=list)


def _seq_block_prob(seq: List[AddOnCandidate]) -> float:
    """Compound 1 − Π(1 − p_i)."""
    survive = 1.0
    for a in seq:
        survive *= (1.0 - regulatory_block_prob(a))
    return 1.0 - survive


def valuate_sequence(
    platform: Platform,
    sequence: List[AddOnCandidate],
    *,
    curve: Optional[SynergyCurve] = None,
    discount_rate: float = 0.10,
    volatility: float = 0.30,
) -> ValuedSequence:
    """Compute the expected NPV of a specific add-on sequence."""
    curve = curve or default_physician_rollup_curve()

    cumulative_value = 0.0
    cumulative_capital = 0.0
    notes: List[str] = []

    survive_prob = 1.0
    for i, addon in enumerate(sequence):
        # Synergy contribution from the i-th add-on (1-indexed)
        marginal_share = curve.marginal(i + 1)
        synergy_ebitda = (platform.base_ebitda_mm * marginal_share
                          + addon.standalone_ebitda_mm)
        # Compound block probability
        block_p = regulatory_block_prob(addon)
        density = geographic_density_score(platform, addon)

        # Real-options value of the add-on right at this stage.
        # Time-to-decision = 0.5 + 0.5 × i (years) so later add-ons
        # have more time-value.
        T = 0.5 + 0.5 * i
        opt_value = binomial_lattice_call(
            S=synergy_ebitda * 8.0,    # 8x EBITDA exit multiple
            K=addon.purchase_price_mm,
            T=T,
            r=discount_rate,
            sigma=volatility,
            steps=20,
        )

        # Realized value = option value × success probability ×
        # density factor
        contribution = opt_value * (1.0 - block_p) * (
            0.7 + 0.3 * density)
        cumulative_value += contribution
        cumulative_capital += addon.purchase_price_mm

        survive_prob *= (1.0 - block_p)
        notes.append(
            f"#{i+1} {addon.name}: synergy share {marginal_share:.3f}, "
            f"block_p {block_p:.2%}, density {density:.1f}, "
            f"contribution ${contribution:.2f}M"
        )

    cumulative_block_prob = 1.0 - survive_prob
    synergy_share = curve.cumulative(len(sequence))

    return ValuedSequence(
        sequence=[a.add_on_id for a in sequence],
        cumulative_value_mm=round(cumulative_value, 2),
        cumulative_capital_mm=round(cumulative_capital, 2),
        cumulative_block_prob=round(cumulative_block_prob, 4),
        synergy_share=round(synergy_share, 4),
        notes=notes,
    )


def optimize_sequence(
    platform: Platform,
    candidates: Iterable[AddOnCandidate],
    constraints: Optional[SequenceConstraints] = None,
    *,
    curve: Optional[SynergyCurve] = None,
    discount_rate: float = 0.10,
    volatility: float = 0.30,
    max_seq_len: Optional[int] = None,
) -> ValuedSequence:
    """Find the highest-NPV feasible sequence.

    Uses straight enumeration up to ~7 candidates (5,040 perms);
    above that, falls back to branch-and-bound search with
    per-candidate upper-bound pruning. Branch-and-bound stays
    optimal where greedy can miss good sequences in which the
    high-value candidates depend on slot position (the synergy
    curve is nonlinear in count of integrated add-ons).
    """
    constraints = constraints or SequenceConstraints()
    cand_list = [c for c in candidates]
    cap = max_seq_len or constraints.max_addons
    target_len = min(len(cand_list), cap)

    if target_len <= 0:
        return ValuedSequence(
            sequence=[], cumulative_value_mm=0.0,
            cumulative_capital_mm=0.0,
            cumulative_block_prob=0.0,
            synergy_share=0.0,
            notes=["no candidates supplied"],
        )

    if len(cand_list) <= 7:
        # Full enumeration over permutations of all subsets
        # bounded by max_seq_len.
        best: Optional[ValuedSequence] = None
        for size in range(1, target_len + 1):
            for perm in permutations(cand_list, size):
                cap_total = sum(a.purchase_price_mm for a in perm)
                if cap_total > constraints.max_total_capital_mm:
                    continue
                bp = _seq_block_prob(list(perm))
                if bp > constraints.max_cumulative_block_prob:
                    continue
                v = valuate_sequence(
                    platform, list(perm), curve=curve,
                    discount_rate=discount_rate,
                    volatility=volatility,
                )
                if best is None or (
                    v.cumulative_value_mm > best.cumulative_value_mm
                ):
                    best = v
        return best or ValuedSequence(
            sequence=[], cumulative_value_mm=0.0,
            cumulative_capital_mm=0.0,
            cumulative_block_prob=0.0,
            synergy_share=0.0,
            notes=["no feasible sequence under constraints"],
        )
    else:
        # Branch-and-bound: optimal at scale. Per-candidate
        # upper-bound pruning prevents the exponential blow-up
        # that pure enumeration would hit at len > 7.
        from .branch_and_bound import branch_and_bound_optimize
        best, _stats = branch_and_bound_optimize(
            platform, cand_list, constraints,
            curve=curve, discount_rate=discount_rate,
            volatility=volatility, max_seq_len=max_seq_len,
        )
        return best
