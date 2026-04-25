"""Buy-and-build optimizer with compound real-options valuation.

Add-ons accounted for ~77% of 2024 PE healthcare deal volume; the
right *sequence* of add-ons under uncertainty is materially more
valuable than the same set picked in arbitrary order. This package
ships the math the partner uses to defend a sequencing choice:

  • Black-Scholes for single-stage option value (pure numpy)
  • Binomial lattice for multi-stage compound real options (pure
    numpy) — American-style early-exercise allowed at each lattice
    node
  • Synergy curves — revenue lift and cost-out as a function of
    add-on count (logistic-saturation form, calibrated to PE
    physician-rollup data)
  • Branch-and-bound search across feasible add-on sequences
    subject to regulatory-blocking and geographic-density
    constraints

Public API::

    from rcm_mc.buyandbuild import (
        AddOnCandidate, Platform,
        SynergyCurve, regulatory_block_prob,
        black_scholes_call, binomial_lattice_call,
        valuate_sequence, optimize_sequence,
    )
"""
from .candidates import AddOnCandidate, Platform
from .synergy import SynergyCurve, default_physician_rollup_curve
from .options import (
    black_scholes_call,
    binomial_lattice_call,
    binomial_lattice_compound,
)
from .constraints import (
    regulatory_block_prob,
    geographic_density_score,
    SequenceConstraints,
)
from .optimize import valuate_sequence, optimize_sequence, ValuedSequence
from .branch_and_bound import (
    branch_and_bound_optimize,
    BBStats,
)

__all__ = [
    "AddOnCandidate",
    "Platform",
    "SynergyCurve",
    "default_physician_rollup_curve",
    "black_scholes_call",
    "binomial_lattice_call",
    "binomial_lattice_compound",
    "regulatory_block_prob",
    "geographic_density_score",
    "SequenceConstraints",
    "valuate_sequence",
    "optimize_sequence",
    "ValuedSequence",
    "branch_and_bound_optimize",
    "BBStats",
]
