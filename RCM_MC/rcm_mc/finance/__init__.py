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
from .life_sciences import (  # noqa: F401
    # Enums / tables
    DevelopmentPhase,
    TherapeuticArea,
    PHASE_SUCCESS_TABLE,
    PHASE_DEFAULTS,
    PhaseSuccess,
    PhaseEconomics,
    # Core rNPV
    AssetRNPVConfig,
    RNPVResult,
    RNPVYear,
    value_asset_rnpv,
    build_rnpv,
    cumulative_loa,
    likelihood_of_approval,
    # Peak-sales epidemiology
    EpidemiologyFunnel,
    peak_sales_from_epidemiology,
    # Deal economics
    LicensingDeal,
    RoyaltyTier,
    value_licensing_deal,
    # Portfolio / company
    value_pipeline,
    PipelineResult,
    runway_analysis,
    RunwayResult,
    # Stochastic + analytics
    StochasticInputs,
    MonteCarloResult,
    monte_carlo_rnpv,
    sensitivity_tornado,
    TornadoResult,
    sensitivity_grid,
    SensitivityGrid,
    breakeven_peak_sales,
    breakeven_loa,
    expected_value_blend,
    ExpectedValueResult,
    # Real options
    CommercialScenario,
    RealOptionsResult,
    real_options_value,
    # Competition
    competition_adjusted_peak_sales,
    # Adjacent subsectors
    cdmo_capacity_model,
    CDMOResult,
    diagnostics_unit_economics,
    DiagnosticsResult,
    # Side-by-side comparison
    Comparison,
    ComparisonRow,
    compare_assets,
    compare_assets_deep,
    compare_scenarios,
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
    # Life sciences — enums / tables
    "DevelopmentPhase", "TherapeuticArea",
    "PHASE_SUCCESS_TABLE", "PHASE_DEFAULTS",
    "PhaseSuccess", "PhaseEconomics",
    # Life sciences — core rNPV
    "AssetRNPVConfig", "RNPVResult", "RNPVYear",
    "value_asset_rnpv", "build_rnpv",
    "cumulative_loa", "likelihood_of_approval",
    # Life sciences — peak-sales epidemiology
    "EpidemiologyFunnel", "peak_sales_from_epidemiology",
    # Life sciences — deal economics
    "LicensingDeal", "RoyaltyTier", "value_licensing_deal",
    # Life sciences — portfolio / company
    "value_pipeline", "PipelineResult",
    "runway_analysis", "RunwayResult",
    # Life sciences — stochastic + analytics
    "StochasticInputs", "MonteCarloResult", "monte_carlo_rnpv",
    "sensitivity_tornado", "TornadoResult",
    "sensitivity_grid", "SensitivityGrid",
    "breakeven_peak_sales", "breakeven_loa",
    "expected_value_blend", "ExpectedValueResult",
    # Life sciences — real options
    "CommercialScenario", "RealOptionsResult", "real_options_value",
    # Life sciences — competition
    "competition_adjusted_peak_sales",
    # Life sciences — adjacent subsectors
    "cdmo_capacity_model", "CDMOResult",
    "diagnostics_unit_economics", "DiagnosticsResult",
    # Life sciences — side-by-side comparison
    "Comparison", "ComparisonRow",
    "compare_assets", "compare_assets_deep", "compare_scenarios",
]
