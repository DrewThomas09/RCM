"""Branch-and-bound add-on sequence search.

The existing optimizer enumerates every permutation up to 7
candidates (5,040 perms) and falls back to a greedy heuristic
above. Greedy fails when high-value add-ons depend on the
SEQUENCE position (the synergy curve is nonlinear in the count
of integrated add-ons; the i-th slot pays off differently than
the j-th).

Branch-and-bound stays optimal at scale by:

  1. Ordering candidates by per-dollar expected value (best-first
     branching — finds a good incumbent fast).
  2. DFS over partial sequences, extending the current branch one
     slot at a time.
  3. At each node, computing an UPPER BOUND on what the remaining
     subtree could achieve given the slots still open + the
     candidates not yet picked.
  4. Pruning the subtree if (current_value + upper_bound) <
     (incumbent best value).
  5. Returning the best complete sequence + the count of pruned
     subtrees.

The upper bound: each remaining add-on contributes at most its
"unconstrained max" — synergy curve at the max slot × option
value with zero closing risk × density factor 1.0. This is a
loose-but-tight-enough bound that prunes aggressively without
over-pruning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from .candidates import AddOnCandidate, Platform
from .constraints import (
    SequenceConstraints,
    regulatory_block_prob,
    geographic_density_score,
)
from .options import binomial_lattice_call
from .synergy import SynergyCurve, default_physician_rollup_curve
from .optimize import valuate_sequence, ValuedSequence


@dataclass
class BBStats:
    """Search-tree diagnostics — useful for partner-defensible
    "we explored N branches and pruned M" claims."""
    branches_explored: int = 0
    subtrees_pruned: int = 0
    incumbent_updates: int = 0


def _candidate_max_contribution(
    platform: Platform,
    candidate: AddOnCandidate,
    *,
    max_synergy_marginal: float,
    discount_rate: float,
    volatility: float,
) -> float:
    """Loose upper bound on what a single candidate could
    contribute at its best possible slot.

    Assumes:
      • synergy share = the logistic-curve max marginal slope
      • block probability = 0 (no regulatory friction)
      • density factor = 1.0 (perfect geographic density)
      • option time = 5 years (max in the candidate set)

    This bounds-but-doesn't-tighten so the B&B keeps it
    admissible (never under-bounds).
    """
    synergy_ebitda = (platform.base_ebitda_mm * max_synergy_marginal
                      + candidate.standalone_ebitda_mm)
    opt_value = binomial_lattice_call(
        S=synergy_ebitda * 8.0,
        K=candidate.purchase_price_mm,
        T=5.0,
        r=discount_rate,
        sigma=volatility,
        steps=20,
    )
    return float(opt_value * 1.0 * 1.0)  # block=0, density=1


def _candidate_contribution_at_slot(
    platform: Platform,
    candidate: AddOnCandidate,
    slot: int,                  # 0-indexed
    *,
    curve: SynergyCurve,
    discount_rate: float,
    volatility: float,
) -> float:
    """The contribution candidate makes when placed at slot
    ``slot``. Independent of other candidates in the sequence —
    only depends on slot index + candidate attributes + platform.

    This independence lets us precompute the entire (slot ×
    candidate) value matrix once and have the B&B DFS just sum
    cell values, avoiding the per-node binomial-lattice cost
    that made the naive implementation hang at 10 candidates.
    """
    marginal_share = curve.marginal(slot + 1)
    synergy_ebitda = (platform.base_ebitda_mm * marginal_share
                      + candidate.standalone_ebitda_mm)
    block_p = regulatory_block_prob(candidate)
    density = geographic_density_score(platform, candidate)
    T = 0.5 + 0.5 * slot
    opt_value = binomial_lattice_call(
        S=synergy_ebitda * 8.0,
        K=candidate.purchase_price_mm,
        T=T,
        r=discount_rate,
        sigma=volatility,
        steps=20,
    )
    return float(opt_value * (1.0 - block_p)
                 * (0.7 + 0.3 * density))


def branch_and_bound_optimize(
    platform: Platform,
    candidates: Iterable[AddOnCandidate],
    constraints: Optional[SequenceConstraints] = None,
    *,
    curve: Optional[SynergyCurve] = None,
    discount_rate: float = 0.10,
    volatility: float = 0.30,
    max_seq_len: Optional[int] = None,
) -> Tuple[ValuedSequence, BBStats]:
    """Branch-and-bound add-on sequence search with precomputed
    (slot × candidate) contribution matrix.

    Returns (best_sequence, search_stats).
    """
    constraints = constraints or SequenceConstraints()
    curve = curve or default_physician_rollup_curve()
    cand_list = [c for c in candidates]
    cap = max_seq_len or constraints.max_addons
    target_len = min(len(cand_list), cap)
    if target_len <= 0 or not cand_list:
        return (ValuedSequence(
            sequence=[], cumulative_value_mm=0.0,
            cumulative_capital_mm=0.0,
            cumulative_block_prob=0.0,
            synergy_share=0.0,
            notes=["no candidates supplied"],
        ), BBStats())

    # Branching order: per-dollar expected value, best-first
    scored: List[Tuple[float, AddOnCandidate]] = []
    for c in cand_list:
        block = regulatory_block_prob(c)
        density = geographic_density_score(platform, c)
        expected = (c.standalone_ebitda_mm * 8.0
                    * (1.0 - block) * (0.7 + 0.3 * density))
        ratio = expected / max(0.1, c.purchase_price_mm)
        scored.append((ratio, c))
    scored.sort(key=lambda kv: kv[0], reverse=True)
    ordered = [c for _, c in scored]
    cand_by_id = {c.add_on_id: c for c in ordered}

    # ── Precompute (slot × candidate) contribution matrix ──
    # contrib[slot][cid] = $-value of placing cid in this slot
    contrib: List[Dict[str, float]] = []
    for slot in range(target_len):
        row = {}
        for c in ordered:
            row[c.add_on_id] = _candidate_contribution_at_slot(
                platform, c, slot,
                curve=curve, discount_rate=discount_rate,
                volatility=volatility,
            )
        contrib.append(row)

    # Per-candidate upper bound (max contribution across any slot)
    max_contrib_per_cand = {
        c.add_on_id: max(contrib[s][c.add_on_id]
                         for s in range(target_len))
        for c in ordered
    }

    stats = BBStats()
    best_value: float = 0.0
    best_sequence: List[AddOnCandidate] = []
    best_block: float = 0.0
    best_capital: float = 0.0

    def _dfs(current: List[AddOnCandidate],
             current_value: float,
             remaining_ids: List[str],
             remaining_capital: float,
             survive_prob: float) -> None:
        nonlocal best_value, best_sequence, best_block, best_capital
        stats.branches_explored += 1

        # Update incumbent if current is feasible + better
        if current:
            cum_block = 1.0 - survive_prob
            cum_capital = sum(
                c.purchase_price_mm for c in current)
            feasible = (
                cum_capital <= constraints.max_total_capital_mm
                and cum_block
                <= constraints.max_cumulative_block_prob
            )
            if feasible and current_value > best_value:
                best_value = current_value
                best_sequence = list(current)
                best_block = cum_block
                best_capital = cum_capital
                stats.incumbent_updates += 1

        # Pruning + branching
        if len(current) >= target_len or not remaining_ids:
            return

        # Upper bound: top-(slots_left) max contributions among
        # remaining candidates
        slots_left = target_len - len(current)
        ub_remaining = sum(
            sorted(
                (max_contrib_per_cand[cid]
                 for cid in remaining_ids),
                reverse=True,
            )[:slots_left]
        )
        if (current_value + ub_remaining) <= best_value:
            stats.subtrees_pruned += 1
            return

        slot = len(current)
        contrib_this_slot = contrib[slot]
        # Branch: try each remaining candidate at this slot,
        # ordered by their contrib AT THIS SLOT (best-first).
        ordered_remaining = sorted(
            remaining_ids,
            key=lambda cid: contrib_this_slot[cid],
            reverse=True,
        )
        for cid in ordered_remaining:
            c = cand_by_id[cid]
            if c.purchase_price_mm > remaining_capital:
                continue
            new_survive = survive_prob * (
                1.0 - regulatory_block_prob(c))
            new_block = 1.0 - new_survive
            if new_block > constraints.max_cumulative_block_prob:
                continue
            new_current = current + [c]
            new_value = current_value + contrib_this_slot[cid]
            new_remaining = [r for r in remaining_ids if r != cid]
            _dfs(new_current, new_value, new_remaining,
                 remaining_capital - c.purchase_price_mm,
                 new_survive)

    _dfs([], 0.0, [c.add_on_id for c in ordered],
         constraints.max_total_capital_mm, 1.0)

    if not best_sequence:
        return (ValuedSequence(
            sequence=[], cumulative_value_mm=0.0,
            cumulative_capital_mm=0.0,
            cumulative_block_prob=0.0,
            synergy_share=0.0,
            notes=["no feasible sequence under constraints"],
        ), stats)

    # Final full valuation of the chosen sequence (so the
    # ValuedSequence has the proper notes / synergy_share fields).
    final = valuate_sequence(
        platform, best_sequence,
        curve=curve, discount_rate=discount_rate,
        volatility=volatility,
    )
    return final, stats
