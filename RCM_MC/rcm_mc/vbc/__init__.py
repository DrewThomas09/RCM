"""Value-Based Care (VBC) modeling — Bridge v3.

Replaces per-encounter unit economics with multi-period cohort
patient lifetime value (LTV), incorporating CMS-HCC V28 risk
scoring, capitation revenue under PCC/TCC, two-sided risk shared-
savings/losses, and quality withhold.

Built for RCM diligence on VBC-heavy targets: ACOs, MA-focused
primary care, FQHCs, and any provider operating under capitation
or shared-savings contracts. Specifically anchored to:

  • CMS-HCC V28 — the risk-adjustment model used by Medicare
    Advantage and ACO REACH PY2026+. V28 phases out 2,000+
    HCCs from the V24 model and re-weights coding intensity.
    The "V28 cliff" (PY2026: 67% V28 / 33% V24 → PY2027: 100%
    V28) is a concrete revenue hit modeled here.

  • ACO REACH — Direct Contracting successor; PCC/TCC capitation
    with 100% upside / 100% downside risk above MSR/MLR thresholds,
    quality withhold of 2% of benchmark.

  • LEAD model — CMMI's 2027-launching alternative payment model
    for primary care, modeled here as a TCC variant.

Public API::

    from rcm_mc.vbc import (
        Cohort, CohortPanel, ContractTerms,
        # HCC scoring
        compute_hcc_score, V28_PHASE_IN,
        # Capitation revenue
        compute_capitation_revenue,
        # LTV
        compute_cohort_ltv, project_panel_lifetime_value,
        # Shrinkage
        bayesian_shrink_cohort,
    )

The math is intentionally deterministic + auditable — every line
of revenue / cost can be traced to its inputs. No external deps
beyond stdlib + numpy.
"""
from .cohort import Cohort, CohortPanel
from .hcc import (
    compute_hcc_score,
    V28_PHASE_IN,
    HCCWeights,
)
from .contracts import (
    ContractTerms,
    compute_capitation_revenue,
    compute_shared_savings,
)
from .ltv import (
    compute_cohort_ltv,
    project_panel_lifetime_value,
    LTVResult,
)
from .shrinkage import bayesian_shrink_cohort

__all__ = [
    "Cohort",
    "CohortPanel",
    "ContractTerms",
    "compute_hcc_score",
    "V28_PHASE_IN",
    "HCCWeights",
    "compute_capitation_revenue",
    "compute_shared_savings",
    "compute_cohort_ltv",
    "project_panel_lifetime_value",
    "LTVResult",
    "bayesian_shrink_cohort",
]
