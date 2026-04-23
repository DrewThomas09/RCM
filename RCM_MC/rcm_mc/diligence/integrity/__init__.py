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

from .distribution_shift import (
    DistributionScore,
    DistributionShiftReport,
    classify_shift,
    score_distribution,
)
from .leakage_audit import (
    FeatureSource,
    LeakageError,
    LeakageFinding,
    audit_features,
)
from .split_enforcer import (
    ProviderSplit,
    SplitViolation,
    assert_provider_disjoint,
    make_three_way_split,
)
from .temporal_validity import (
    TemporalValidity,
    check_regulatory_overlap,
)

__all__ = [
    "DistributionScore",
    "DistributionShiftReport",
    "FeatureSource",
    "LeakageError",
    "LeakageFinding",
    "ProviderSplit",
    "SplitViolation",
    "TemporalValidity",
    "assert_provider_disjoint",
    "audit_features",
    "check_regulatory_overlap",
    "classify_shift",
    "make_three_way_split",
    "score_distribution",
]
