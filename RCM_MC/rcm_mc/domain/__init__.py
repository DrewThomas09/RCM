"""Healthcare revenue-cycle economic ontology.

Every metric the platform touches has a place in the revenue cycle and
a well-defined relationship to EBITDA, cash, or risk. This subpackage
is the canonical mapping — what each metric *is*, where it sits, what
causes it, and how it flows into the P&L.

Public surface::

    from rcm_mc.domain import (
        METRIC_ONTOLOGY,
        Domain,
        Directionality,
        FinancialPathway,
        ConfidenceClass,
        ReimbursementType,
        MetricDefinition,
        MechanismEdge,
        CausalGraph,
        MetricReimbursementSensitivity,   # preferred name
        classify_metric,
        explain_causal_path,
        causal_graph,
    )

Note: ``MetricReimbursementSensitivity`` was previously named
``ReimbursementProfile``. The old name is still exported as a
back-compat alias, but new code should use the explicit one —
``rcm_mc.finance.reimbursement_engine`` also defines a
``ReimbursementProfile`` with different semantics (hospital-level
revenue exposure, not per-metric sensitivity).
"""
from .econ_ontology import (  # noqa: F401
    CausalGraph,
    ConfidenceClass,
    Directionality,
    Domain,
    FinancialPathway,
    METRIC_ONTOLOGY,
    MechanismEdge,
    MetricDefinition,
    MetricReimbursementSensitivity,
    ReimbursementProfile,   # back-compat alias for MetricReimbursementSensitivity
    ReimbursementType,
    causal_graph,
    classify_metric,
    explain_causal_path,
)

__all__ = [
    "METRIC_ONTOLOGY",
    "Domain", "Directionality", "FinancialPathway",
    "ConfidenceClass", "ReimbursementType",
    "MetricDefinition", "MechanismEdge", "CausalGraph",
    "MetricReimbursementSensitivity",
    "ReimbursementProfile",   # deprecated alias
    "classify_metric", "explain_causal_path", "causal_graph",
]
