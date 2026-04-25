"""DealComparablesEngine — PSM + Mahalanobis comp selection.

The existing ``rcm_mc.diligence.comparable_outcomes`` module ranks
corpus deals by hand-weighted feature similarity. That's good for
the partner-glance view, but doesn't survive a rigorous diligence
defense — the weights are arbitrary and there's no statistical
basis for "these N deals are the right comp set."

This package provides the rigorous version:

  • Propensity-score matching (PSM): logistic regression treats
    "is this the target deal?" as a binary classification on the
    full corpus + target. The propensity score per corpus deal is
    P(treatment | sector, size, vintage, geography, payer_mix).
    Caliper-NN matching then pulls the K nearest comps within a
    propensity-score caliper.

  • Mahalanobis distance: direct distance on the standardized
    feature space, using the regularized inverse covariance
    matrix. Works as a sanity check against PSM and as a primary
    method when propensity scores are unstable.

Either method outputs a weight matrix (per-comp similarity score)
plus the entry/exit multiple distribution and margin-expansion
benchmarks across the matched set.

Public API::

    from rcm_mc.comparables import (
        extract_features, FeatureVector,
        LogisticRegression, fit_propensity_scores,
        psm_match, mahalanobis_match,
        run_comparables_engine, ComparablesResult,
    )
"""
from .features import extract_features, FeatureVector
from .logistic import LogisticRegression, fit_logistic
from .psm import (
    fit_propensity_scores,
    psm_match,
    PSMConfig,
)
from .mahalanobis import (
    mahalanobis_match,
    mahalanobis_distance_matrix,
)
from .engine import (
    run_comparables_engine,
    ComparablesResult,
)
from .consensus import (
    consensus_match,
    balance_diagnostics,
    ConsensusMatch,
    ConsensusResult,
    BalanceDiagnostic,
)

__all__ = [
    "extract_features",
    "FeatureVector",
    "LogisticRegression",
    "fit_logistic",
    "fit_propensity_scores",
    "psm_match",
    "PSMConfig",
    "mahalanobis_match",
    "mahalanobis_distance_matrix",
    "run_comparables_engine",
    "ComparablesResult",
    "consensus_match",
    "balance_diagnostics",
    "ConsensusMatch",
    "ConsensusResult",
    "BalanceDiagnostic",
]
