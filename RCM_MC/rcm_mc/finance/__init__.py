"""Reimbursement + revenue-realization layer.

Encodes how hospital revenue is actually generated, delayed, denied,
adjusted, or lost under different payer and reimbursement structures.
This is the economic substrate the EBITDA bridge needs to stop treating
every hospital as an identical fee-for-service entity.

Public surface::

    from rcm_mc.finance import (
        # Enums
        ReimbursementMethod, PayerClass, ProvenanceTag,
        # Data types
        ReimbursementProfile, PayerClassProfile,
        MethodSensitivity, ContractSensitivity,
        RevenueRealizationPath, RevenueAtRiskBreakdown,
        # API
        build_reimbursement_profile,
        estimate_metric_revenue_sensitivity,
        compute_revenue_realization_path,
        explain_reimbursement_logic,
    )
"""
from .reimbursement_engine import (  # noqa: F401
    # Enums
    PayerClass,
    ProvenanceTag,
    ReimbursementMethod,
    # Data types
    ContractSensitivity,
    MethodSensitivity,
    PayerClassProfile,
    ReimbursementProfile,
    RevenueAtRiskBreakdown,
    RevenueRealizationPath,
    # Tables
    METHOD_SENSITIVITY_TABLE,
    DEFAULT_PAYER_METHOD_DISTRIBUTION,
    # Functions
    build_reimbursement_profile,
    compute_revenue_realization_path,
    estimate_metric_revenue_sensitivity,
    explain_reimbursement_logic,
)

__all__ = [
    "ReimbursementMethod", "PayerClass", "ProvenanceTag",
    "ReimbursementProfile", "PayerClassProfile",
    "MethodSensitivity", "ContractSensitivity",
    "RevenueRealizationPath", "RevenueAtRiskBreakdown",
    "METHOD_SENSITIVITY_TABLE",
    "DEFAULT_PAYER_METHOD_DISTRIBUTION",
    "build_reimbursement_profile",
    "estimate_metric_revenue_sensitivity",
    "compute_revenue_realization_path",
    "explain_reimbursement_logic",
]
