"""Feature leakage audit — Phase 3 of the regression rebuild.

The regression page currently lists features like ``revenue_per_bed``,
``net_to_gross_ratio``, ``operating_margin``, and ``net_income``
alongside raw HCRIS columns. When the partner picks
``net_patient_revenue`` as the target, several of those features
LEAK the target into the right-hand side — ``revenue_per_bed`` is
literally ``net_patient_revenue / beds``, so fitting
``net_patient_revenue ~ revenue_per_bed + ...`` is partly fitting
``y ~ y/x``. R² inflates artificially; the model looks brilliant
but isn't actually predicting anything.

This module gives every feature a provenance record (which raw
HCRIS columns it's derived from) and a classifier that, given a
target, returns a per-feature verdict:

  - LEAKS — feature is mathematically derived from the target,
    OR target is derived from the feature
  - SAFE — feature shares no algebraic path with the target
  - SELF — feature IS the target (always excluded)
  - UNKNOWN — feature not in the registry; can't audit

The verdicts feed three downstream uses:
  1. The Phase-3 UI panel "Feature Leakage Audit" surfaces each
     feature with its verdict + reason, so a partner can see WHY
     R² fell when they untoggle leaky features.
  2. The "Drop leakage features" toggle filters leaky features
     out of the regression input set so the partner can run a
     clean fit in one click.
  3. PR 4 (cross-validation + influence diagnostics) will refuse
     to claim out-of-sample prediction power when leaky features
     are in the spec.

DIAGNOSTIC SCOPE: this module classifies leakage based on the
KNOWN formula provenance of features computed by
``regression_page._add_computed_features``. A leakage verdict
of SAFE means "no algebraic path between feature and target via
the registered formulas" — it does NOT prove the feature is
predictive (that's PR 4's job).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional


@dataclass(frozen=True)
class FeatureProvenance:
    """How a feature is constructed and when it's measurable.

    ``inputs``: the raw HCRIS columns that go into this feature's
    formula. For raw HCRIS columns (beds, net_patient_revenue, etc.)
    this is the empty set — they're not derived from anything else
    in the registry.

    ``known_before_period``: True if this feature could in principle
    be observed BEFORE the target period (i.e. it's available for
    out-of-sample forecasting once we have prior-period data). Phase
    3 sets this True for all HCRIS-rollup variables because the
    page does same-period analysis; a future cross-period rebuild
    can flip specific values to False as needed.

    ``explanation_only``: True if the feature is a useful descriptor
    of a hospital's economic state but should NOT be used for
    forecasting even when it doesn't algebraically leak — e.g. an
    audit flag (`margin_unreliable`) that's only available because
    we already saw the target.

    ``label``: partner-facing display name.
    """
    name: str
    label: str
    inputs: FrozenSet[str] = frozenset()
    known_before_period: bool = True
    explanation_only: bool = False
    note: str = ""


# ── Registry of feature provenance ──────────────────────────────
# Every entry here mirrors the formulas implemented in
# ``regression_page._add_computed_features`` (and the raw HCRIS
# columns). When a new feature gets added there, add the matching
# provenance record here so the leakage audit can reason about it.

_RAW_HCRIS = (
    "beds",
    "net_patient_revenue",
    "operating_expenses",
    "medicare_day_pct",
    "medicaid_day_pct",
    "total_patient_days",
    "medicare_days",
    "medicaid_days",
    "bed_days_available",
    "net_income",  # raw HCRIS column, but accountancy-derived from npr - opex; flagged below
    "gross_patient_revenue",
    "contractual_allowances",
)


def _raw(name: str, label: str, note: str = "") -> FeatureProvenance:
    return FeatureProvenance(
        name=name, label=label, inputs=frozenset(), note=note,
    )


def _derived(
    name: str, label: str, inputs: List[str],
    note: str = "", explanation_only: bool = False,
) -> FeatureProvenance:
    return FeatureProvenance(
        name=name, label=label,
        inputs=frozenset(inputs),
        explanation_only=explanation_only,
        note=note,
    )


PROVENANCE: Dict[str, FeatureProvenance] = {
    # ── Raw HCRIS columns ──
    "beds":                   _raw("beds", "Beds"),
    "net_patient_revenue":    _raw("net_patient_revenue", "Net Patient Revenue"),
    "operating_expenses":     _raw("operating_expenses", "Operating Expenses"),
    "medicare_day_pct":       _raw("medicare_day_pct", "Medicare Day %"),
    "medicaid_day_pct":       _raw("medicaid_day_pct", "Medicaid Day %"),
    "total_patient_days":     _raw("total_patient_days", "Total Patient Days"),
    "medicare_days":          _raw("medicare_days", "Medicare Days"),
    "medicaid_days":          _raw("medicaid_days", "Medicaid Days"),
    "bed_days_available":     _raw("bed_days_available", "Bed Days Available"),
    "gross_patient_revenue":  _raw("gross_patient_revenue", "Gross Patient Revenue"),
    "contractual_allowances": _raw("contractual_allowances", "Contractual Allowances"),
    # net_income arrives raw from CMS but is accountancy-derived
    # from net_patient_revenue - operating_expenses + non-operating
    # income. Treat it as derived for leakage purposes so picking
    # net_patient_revenue as the target correctly flags net_income
    # as leaky.
    "net_income": _derived(
        "net_income", "Net Income",
        inputs=["net_patient_revenue", "operating_expenses"],
        note=(
            "Accountancy-derived from net_patient_revenue minus "
            "operating_expenses (plus non-operating income). Flagged "
            "as derived even though it's a raw HCRIS column."
        ),
    ),
    # ── Computed features (formulas mirror _add_computed_features) ──
    "revenue_per_bed": _derived(
        "revenue_per_bed", "Revenue per Bed",
        inputs=["net_patient_revenue", "beds"],
    ),
    "occupancy_rate": _derived(
        "occupancy_rate", "Occupancy Rate",
        inputs=["total_patient_days", "bed_days_available"],
    ),
    "commercial_pct": _derived(
        "commercial_pct", "Commercial Payer %",
        inputs=["medicare_day_pct", "medicaid_day_pct"],
        note=(
            "Computed as 1 - medicare% - medicaid%, so it sums to "
            "100 with the other two payer percentages. Including "
            "all three in the same model produces perfect "
            "collinearity (the VIF panel will flag this)."
        ),
    ),
    "operating_margin": _derived(
        "operating_margin", "Operating Margin",
        inputs=["net_patient_revenue", "operating_expenses"],
    ),
    "net_to_gross_ratio": _derived(
        "net_to_gross_ratio", "Net-to-Gross Ratio",
        inputs=["net_patient_revenue", "gross_patient_revenue"],
    ),
    "expense_per_bed": _derived(
        "expense_per_bed", "Expense per Bed",
        inputs=["operating_expenses", "beds"],
    ),
    "revenue_per_day": _derived(
        "revenue_per_day", "Revenue per Patient Day",
        inputs=["net_patient_revenue", "total_patient_days"],
    ),
    "medicare_intensity": _derived(
        "medicare_intensity", "Medicare Intensity",
        inputs=["medicare_day_pct", "beds"],
    ),
    "payer_diversity": _derived(
        "payer_diversity", "Payer Diversity Index",
        inputs=["medicare_day_pct", "medicaid_day_pct"],
    ),
    "size_quartile": _derived(
        "size_quartile", "Size Quartile",
        inputs=["beds"],
        note=(
            "Quartile bucket of beds; technically a one-to-one "
            "transformation of beds, so adding both to the same "
            "model adds no information."
        ),
    ),
    # ── 2-hop derived features (built on other derived features) ──
    # These exist so the transitive FORMULA_RELATED detector has
    # real chains to catch. As soon as a feature lists a derived
    # parent in its inputs (rather than only raw HCRIS columns),
    # the atomic-input walk needs to keep going to find the true
    # shared ancestors of feature and target.
    "margin_per_bed": _derived(
        "margin_per_bed", "Margin per Bed",
        # operating_margin = (npr - opex) / npr; this rescales by
        # beds. Direct inputs reference operating_margin (derived)
        # so atomic_inputs has to walk through it to reach npr/opex.
        inputs=["operating_margin", "beds"],
        note=(
            "Multi-hop derivation: operating_margin × bed-scale. "
            "Atomic ancestors are {net_patient_revenue, "
            "operating_expenses, beds} — transitive FORMULA_RELATED "
            "with any feature that also depends on npr or opex."
        ),
    ),
}


@dataclass(frozen=True)
class LeakageVerdict:
    """Per-(feature, target) classification.

    ``verdict``: one of "LEAKS", "FORMULA_RELATED", "SAFE", "SELF",
    "UNKNOWN".
    ``severity``: "critical" / "warning" / "info" / "ok" — drives
    the UI badge tone:
      critical → LEAKS / SELF (always exclude)
      warning  → FORMULA_RELATED (accounting-identity cousins) or
                 explanation-only features (kept by default but
                 partner should know)
      info     → UNKNOWN (no provenance — caller decides)
      ok       → SAFE (no algebraic / shared-input relationship)
    ``reason``: human-readable explanation. Always set.

    ``transitive``: True when the verdict was reached via the
    atomic-input closure walk (multi-hop chain through intermediate
    derived features) rather than a 1-hop direct match. Only ever
    True for FORMULA_RELATED verdicts; gives the UI a hook to label
    these as "transitive" so partners know the registry detected a
    chain, not a direct shared input.
    """
    feature: str
    target: str
    verdict: str
    severity: str
    reason: str
    transitive: bool = False

    @property
    def leaks(self) -> bool:
        return self.verdict == "LEAKS"

    @property
    def is_target(self) -> bool:
        return self.verdict == "SELF"

    @property
    def formula_related(self) -> bool:
        return self.verdict == "FORMULA_RELATED"


def atomic_inputs(
    name: str,
    registry: Optional[Dict[str, FeatureProvenance]] = None,
    *,
    max_depth: int = 8,
) -> FrozenSet[str]:
    """Return the set of raw HCRIS columns this feature ultimately
    derives from, walking the provenance DAG transitively.

    For a raw column (empty .inputs) returns {name} — itself is the
    atomic ancestor. For a derived feature, returns the union of
    atomic_inputs of each direct input. Cycles are guarded via a
    visited set; depth is capped at ``max_depth`` to bound runtime
    if a future registry entry ever introduces a long chain.

    Used by the transitive FORMULA_RELATED detection — two features
    can share atomic inputs (and therefore have inflated R² when
    one is regressed on the other) without their direct .inputs
    sets overlapping at all. Example: target = roa (inputs:
    net_income, total_assets) and feature = operating_margin
    (inputs: npr, opex). Direct shared = ∅, but
    atomic(net_income) = {npr, opex} ⊆ atomic(operating_margin) so
    the chain is real.
    """
    reg = registry if registry is not None else PROVENANCE

    def _walk(n: str, visited: set, depth: int) -> FrozenSet[str]:
        if depth > max_depth or n in visited:
            return frozenset()
        meta = reg.get(n)
        if meta is None:
            # Unknown name — treat as atomic (caller's problem if it
            # really is a derived feature missing from the registry)
            return frozenset({n})
        if not meta.inputs:
            # Raw column — itself is its only atomic ancestor
            return frozenset({n})
        visited.add(n)
        result: set = set()
        for inp in meta.inputs:
            result |= _walk(inp, visited, depth + 1)
        visited.discard(n)
        return frozenset(result)

    return _walk(name, set(), 0)


def classify_feature_for_target(
    feature: str, target: str,
    registry: Optional[Dict[str, FeatureProvenance]] = None,
) -> LeakageVerdict:
    """Return a leakage verdict for a single (feature, target) pair.

    Algorithm (most-severe match wins):
      1. feature == target → SELF (always exclude).
      2. feature or target missing from registry → UNKNOWN.
      3. target ∈ feature.inputs → LEAKS (feature is downstream
         of target).
      4. feature ∈ target.inputs → LEAKS (target is downstream
         of feature; fitting "y ~ x" when y = f(x, …) recovers
         part of the definition).
      5. feature.inputs ∩ target.inputs ≠ ∅ AND both are derived
         (i.e. both have non-empty input sets) → FORMULA_RELATED
         (the v1.1 review addition: catches accounting-identity
         cousins like operating_margin and net_income, which both
         depend on npr + opex but neither contains the other).
      6. feature.explanation_only → SAFE with warning severity.
      7. Otherwise → SAFE.

    FORMULA_RELATED specifically does NOT fire when one of the two
    has empty inputs (i.e. is a raw HCRIS column with no formula).
    A raw column can't be "formula-related" to anything because it
    has no formula. This keeps SAFE clean for the common case
    of fitting a derived target against raw inputs.
    """
    reg = registry if registry is not None else PROVENANCE

    if feature == target:
        return LeakageVerdict(
            feature=feature, target=target, verdict="SELF",
            severity="critical",
            reason="Feature IS the target. Excluded automatically.",
        )

    f_meta = reg.get(feature)
    t_meta = reg.get(target)
    if f_meta is None or t_meta is None:
        return LeakageVerdict(
            feature=feature, target=target, verdict="UNKNOWN",
            severity="info",
            reason=(
                f"No provenance record for "
                f"{'feature' if f_meta is None else 'target'}. "
                f"Add a FeatureProvenance entry to "
                f"rcm_mc.finance.leakage.PROVENANCE to enable "
                f"leakage classification."
            ),
        )

    if target in f_meta.inputs:
        return LeakageVerdict(
            feature=feature, target=target, verdict="LEAKS",
            severity="critical",
            reason=(
                f"Feature is mathematically derived from {target} "
                f"({f_meta.label} = f({', '.join(sorted(f_meta.inputs))})). "
                f"Fitting target ~ this feature is partly fitting "
                f"y ~ y/x — R² will inflate without actually "
                f"predicting anything."
            ),
        )

    if feature in t_meta.inputs:
        return LeakageVerdict(
            feature=feature, target=target, verdict="LEAKS",
            severity="critical",
            reason=(
                f"Target is mathematically derived from this feature "
                f"({t_meta.label} = f({', '.join(sorted(t_meta.inputs))})). "
                f"Fitting target ~ this feature recovers part of the "
                f"target's definition; coefficients are not a real "
                f"causal estimate."
            ),
        )

    # FORMULA_RELATED — shared accounting inputs without direct
    # leakage. Only fires when BOTH have non-empty input sets;
    # raw HCRIS columns (empty inputs) can't be "formula-related".
    if f_meta.inputs and t_meta.inputs:
        shared = f_meta.inputs & t_meta.inputs
        if shared:
            shared_disp = ", ".join(sorted(shared))
            return LeakageVerdict(
                feature=feature, target=target,
                verdict="FORMULA_RELATED", severity="warning",
                reason=(
                    f"Feature and target are accounting-identity "
                    f"cousins — both derived from {{{shared_disp}}}. "
                    f"Neither contains the other, but they share "
                    f"underlying inputs, so the fit may still be "
                    f"artificially strong. Keep with caution; "
                    f"toggle 'strict' mode in forecasting_safe_features "
                    f"to drop these too."
                ),
            )
        # Transitive shared-input check — walks the inputs DAG to
        # the atomic raw columns and checks intersection there.
        # Catches multi-hop chains the 1-hop check above misses:
        # e.g. roa.inputs = {net_income, total_assets} and
        # operating_margin.inputs = {npr, opex} have empty direct
        # intersection, but net_income itself derives from
        # {npr, opex}, so the atomic closures overlap. Without this
        # check the partner would see roa ~ operating_margin as
        # SAFE and trust the inflated R².
        f_atomic = atomic_inputs(feature, reg)
        t_atomic = atomic_inputs(target, reg)
        atomic_shared = f_atomic & t_atomic
        # Subtract raw columns that are themselves the feature/target
        # (avoid claiming a circular "feature is its own atomic
        # ancestor" relationship when the feature happens to be a
        # raw column tagged as derived, like net_income).
        atomic_shared = atomic_shared - {feature, target}
        if atomic_shared:
            shared_disp = ", ".join(sorted(atomic_shared))
            return LeakageVerdict(
                feature=feature, target=target,
                verdict="FORMULA_RELATED", severity="warning",
                reason=(
                    f"Transitive accounting-cousin — feature and "
                    f"target share atomic inputs {{{shared_disp}}} "
                    f"via a multi-hop derivation chain (one or both "
                    f"go through an intermediate derived feature). "
                    f"Direct inputs don't overlap, but the underlying "
                    f"raw columns do, so R² may still be softly "
                    f"inflated. Toggle 'strict' mode to drop."
                ),
                transitive=True,
            )

    if f_meta.explanation_only:
        return LeakageVerdict(
            feature=feature, target=target, verdict="SAFE",
            severity="warning",
            reason=(
                "No algebraic leakage, but feature is marked "
                "explanation-only (useful for understanding a "
                "single hospital, not for out-of-sample forecasting)."
            ),
        )

    return LeakageVerdict(
        feature=feature, target=target, verdict="SAFE",
        severity="ok",
        reason="No algebraic path between feature and target.",
    )


def audit_features(
    features: List[str], target: str,
    registry: Optional[Dict[str, FeatureProvenance]] = None,
) -> List[LeakageVerdict]:
    """Run classify_feature_for_target across a feature list.

    Order is preserved (caller passes the order they care about),
    not sorted by severity — let the UI decide ordering.
    """
    return [
        classify_feature_for_target(f, target, registry)
        for f in features
    ]


def forecasting_safe_features(
    features: List[str], target: str,
    registry: Optional[Dict[str, FeatureProvenance]] = None,
    drop_explanation_only: bool = True,
    strict: bool = False,
) -> List[str]:
    """Return the subset of ``features`` that pass the leakage audit.

    SELF and LEAKS are always dropped. UNKNOWN is kept (caller must
    decide explicitly via the registry).

    ``drop_explanation_only`` (default True) drops SAFE features
    flagged ``explanation_only`` — turn off for explanatory
    analyses where those are still useful.

    ``strict`` (default False) also drops FORMULA_RELATED features
    — the accounting-identity cousins like operating_margin/
    net_income that share inputs without one literally containing
    the other. Default behavior keeps them because they often
    carry real signal (a feature can share an input with the
    target and still be a useful predictor); strict=True is the
    right call when the partner wants the cleanest possible
    "no shared accounting" feature set for a prediction-style
    fit.
    """
    out = []
    for f in features:
        v = classify_feature_for_target(f, target, registry)
        if v.verdict in ("SELF", "LEAKS"):
            continue
        if strict and v.verdict == "FORMULA_RELATED":
            continue
        # explanation_only fires as SAFE+warning; FORMULA_RELATED
        # also has severity warning. Only drop explanation_only
        # under the explanation_only flag, not via the generic
        # severity check.
        f_meta = (registry or PROVENANCE).get(f)
        if (drop_explanation_only and f_meta is not None
                and f_meta.explanation_only):
            continue
        out.append(f)
    return out
