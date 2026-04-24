"""Data-integrity gauntlet.

Every guardrail that has to be in place before a CCD-derived metric
can flow into the packet or the PE brain. Each module is load-bearing
and runs as a hard precondition — not a warning — at specific points
in the pipeline.

Modules:

- :mod:`leakage_audit` — assert that no feature used to predict a
  metric for hospital X itself derives from hospital X's data. Caught
  at packet-build time before any ridge prediction.
- :mod:`split_enforcer` — provider-disjoint three-way split
  (train / calibration / test) for conformal CIs.
- :mod:`distribution_shift` — PSI / KS check on an uploaded CCD vs
  the benchmark corpus the brain was trained on. Flags when a dental
  DSO gets piped into acute-hospital-trained reflexes.
- :mod:`temporal_validity` — date-range + regulatory-calendar
  annotations on every KPI; refuses to report lookahead-biased
  numbers in cohort analytics.

The gauntlet is designed to fail loud with the specific chain that
caused the violation. Silent coercion is not an option — every caller
handles the exception (or re-raises) and records the event in the
packet's audit trail.
"""
from __future__ import annotations

from .cohort_censoring import CensoringCheck, check_cohort_censoring
from .distribution_shift import (
    DistributionScore,
    DistributionShiftReport,
    check_distribution_shift,
    classify_shift,
    score_distribution,
)
from .leakage_audit import (
    FeatureSource,
    LeakageError,
    LeakageFinding,
    audit_features,
    check_leakage,
)
from .preflight import (
    GuardrailViolation,
    PreflightReport,
    run_ccd_guardrails,
    to_integrity_checks,
)
from .split_enforcer import (
    GuardrailResult,
    ProviderSplit,
    SplitManifest,
    SplitViolation,
    assert_provider_disjoint,
    build_split_manifest,
    check_split_manifest,
    make_three_way_split,
)
from .temporal_validity import (
    TemporalValidity,
    check_regulatory_overlap,
    scan_for_discontinuities,
)

__all__ = [
    "CensoringCheck",
    "DistributionScore",
    "DistributionShiftReport",
    "FeatureSource",
    "GuardrailResult",
    "GuardrailViolation",
    "LeakageError",
    "LeakageFinding",
    "PreflightReport",
    "ProviderSplit",
    "SplitManifest",
    "SplitViolation",
    "TemporalValidity",
    "assert_provider_disjoint",
    "audit_features",
    "build_split_manifest",
    "check_cohort_censoring",
    "check_distribution_shift",
    "check_leakage",
    "check_regulatory_overlap",
    "check_split_manifest",
    "classify_shift",
    "make_three_way_split",
    "run_ccd_guardrails",
    "scan_for_discontinuities",
    "score_distribution",
    "to_integrity_checks",
]
