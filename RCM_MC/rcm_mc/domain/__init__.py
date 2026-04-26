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
``ReimbursementProfile``. The old name remains accessible via
``rcm_mc.domain.ReimbursementProfile`` for back-compat, but it now
emits a ``DeprecationWarning`` on access (PEP 562 module ``__getattr__``)
because ``rcm_mc.finance.reimbursement_engine`` also defines a
``ReimbursementProfile`` class with different semantics (hospital-level
revenue exposure, not per-metric sensitivity). The two share a name
but the type system cannot distinguish them; new code should import
``MetricReimbursementSensitivity`` from this package or
``ReimbursementProfile`` from ``finance.reimbursement_engine`` —
never the deprecated alias.
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
    "classify_metric", "explain_causal_path", "causal_graph",
]


def __getattr__(name: str):
    # PEP 562: lazy back-compat shim. Imports of
    # ``rcm_mc.domain.ReimbursementProfile`` keep working but warn so
    # the name-collision with ``finance.reimbursement_engine.ReimbursementProfile``
    # is surfaced at runtime instead of silently shipping the wrong class.
    # Cross-link Report 0094 MR516.
    if name == "ReimbursementProfile":
        import warnings as _w
        _w.warn(
            "rcm_mc.domain.ReimbursementProfile is a deprecated back-compat "
            "alias for MetricReimbursementSensitivity. It collides by name "
            "with finance.reimbursement_engine.ReimbursementProfile, which "
            "has different semantics. Import MetricReimbursementSensitivity "
            "explicitly, or import ReimbursementProfile from "
            "rcm_mc.finance.reimbursement_engine if that is what you want.",
            DeprecationWarning,
            stacklevel=2,
        )
        return MetricReimbursementSensitivity
    raise AttributeError(f"module 'rcm_mc.domain' has no attribute {name!r}")
