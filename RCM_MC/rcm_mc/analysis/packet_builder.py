"""Master orchestrator for :class:`DealAnalysisPacket`.

The builder walks twelve sequential steps. A failure in any single
section does NOT kill the packet — it marks that section ``INCOMPLETE``
or ``FAILED`` with a reason string, so downstream renderers can skip
gracefully. The partner still sees everything that *did* succeed.

Callers:
- ``server.py`` builds a packet to render an API response.
- ``cli.py`` builds a packet for offline export.
- ``tests`` build packets with injected inputs to isolate logic.

None of the twelve steps do IO outside of the ``store`` handle passed
in — Monte Carlo reads YAML from disk via ``deal_sim_inputs`` only when
the relevant files actually exist; otherwise the simulation section is
``SKIPPED``.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .packet import (
    ComparableHospital,
    ComparableSet,
    CompletenessAssessment,
    DataNode,
    DealAnalysisPacket,
    DiligencePriority,
    DiligenceQuestion,
    EBITDABridgeResult,
    HospitalProfile,
    MetricImpact,
    MetricSource,
    ObservedMetric,
    PACKET_SCHEMA_VERSION,
    PercentileSet,
    PredictedMetric,
    ProfileMetric,
    ProvenanceSnapshot,
    RiskFlag,
    RiskSeverity,
    SectionStatus,
    SimulationSummary,
    hash_inputs,
)

logger = logging.getLogger(__name__)


# ── Constants ─────────────────────────────────────────────────────────

# ── Helpers ───────────────────────────────────────────────────────────

def _new_run_id() -> str:
    # Short, human-ish — partners copy/paste this into Slack.
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]


def _load_deal_row(store: Any, deal_id: str) -> Dict[str, Any]:
    """Fetch the deal row from the ``deals`` table. Returns a dict with
    ``name`` and parsed ``profile`` (or empty profile when absent).

    Does NOT raise if the deal is missing — returns an empty dict so the
    builder can produce a minimal packet with profile.status=FAILED.
    """
    store.init_db()
    with store.connect() as con:
        row = con.execute(
            "SELECT deal_id, name, profile_json FROM deals WHERE deal_id = ?",
            (str(deal_id),),
        ).fetchone()
    if row is None:
        return {}
    profile: Dict[str, Any] = {}
    raw = row["profile_json"] if "profile_json" in row.keys() else None
    if raw:
        try:
            profile = json.loads(raw) or {}
        except (json.JSONDecodeError, TypeError):
            profile = {}
    return {"deal_id": row["deal_id"], "name": row["name"] or "", "profile": profile}


def _coerce_observed(obj: Any) -> Optional[ObservedMetric]:
    """Turn raw inputs (int/float/dict/ObservedMetric) into ``ObservedMetric``."""
    if obj is None:
        return None
    if isinstance(obj, ObservedMetric):
        return obj
    if isinstance(obj, (int, float)):
        return ObservedMetric(value=float(obj), source="USER_INPUT")
    if isinstance(obj, dict):
        try:
            return ObservedMetric.from_dict(obj)
        except (KeyError, ValueError, TypeError):
            return None
    return None


def _finite(v: Any) -> bool:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return False
    return f == f and f not in (float("inf"), float("-inf"))


# ── Section builders ──────────────────────────────────────────────────

def _build_profile(
    deal_row: Dict[str, Any],
    override: Optional[Any],
) -> HospitalProfile:
    if override is not None:
        if isinstance(override, HospitalProfile):
            return override
        if isinstance(override, dict):
            return HospitalProfile.from_dict(override)
    profile_dict = (deal_row.get("profile") or {}) if deal_row else {}
    if not profile_dict and deal_row.get("name"):
        profile_dict = {"name": deal_row["name"]}
    elif deal_row.get("name") and not profile_dict.get("name"):
        profile_dict["name"] = deal_row["name"]
    return HospitalProfile.from_dict(profile_dict)


def _build_observed(
    override: Optional[Dict[str, Any]],
    deal_row: Dict[str, Any],
) -> Dict[str, ObservedMetric]:
    out: Dict[str, ObservedMetric] = {}
    if override:
        for k, v in override.items():
            m = _coerce_observed(v)
            if m is not None:
                out[str(k)] = m
        return out
    # Fall back to metrics embedded in profile_json.observed if present.
    prof = (deal_row.get("profile") or {})
    for k, v in (prof.get("observed_metrics") or {}).items():
        m = _coerce_observed(v)
        if m is not None:
            out[str(k)] = m
    return out


def _build_completeness(
    observed: Dict[str, ObservedMetric],
    profile: HospitalProfile,
    scenario_id: Optional[str],
    as_of: Optional[date],
    *,
    historical_values: Optional[Dict[str, Any]] = None,
    conflict_sources: Optional[Dict[str, Any]] = None,
) -> CompletenessAssessment:
    """Delegates to :func:`rcm_mc.analysis.completeness.assess_completeness`.

    The builder doesn't itself understand what "complete" means — the
    registry does. Keeping this pass-through lets the registry evolve
    (new HFMA MAP keys, adjusted benchmarks) without touching the
    builder.
    """
    from .completeness import assess_completeness
    return assess_completeness(
        observed, profile,
        as_of=as_of,
        historical_values=historical_values,
        conflict_sources=conflict_sources,
    )


def _build_comparables(
    profile: HospitalProfile,
    pool: Optional[Sequence[Dict[str, Any]]],
    max_results: int = 20,
) -> ComparableSet:
    if not pool:
        return ComparableSet(
            status=SectionStatus.INCOMPLETE,
            reason="no comparable pool provided",
        )
    try:
        from ..ml.comparable_finder import find_comparables, WEIGHTS
    except Exception as exc:  # noqa: BLE001
        return ComparableSet(status=SectionStatus.FAILED, reason=f"finder unavailable: {exc}")

    target = profile.to_dict()
    try:
        ranked = find_comparables(target, pool, max_results=max_results)
    except Exception as exc:  # noqa: BLE001
        return ComparableSet(status=SectionStatus.FAILED, reason=str(exc))

    peers: List[ComparableHospital] = []
    for r in ranked:
        peer_id = str(r.get("ccn") or r.get("id") or r.get("name") or len(peers))
        peers.append(ComparableHospital(
            id=peer_id,
            similarity_score=float(r.get("similarity_score") or 0.0),
            similarity_components={k: float(v) for k, v in (r.get("similarity_components") or {}).items()},
            # Drop the augmentation fields; keep the rest so downstream
            # renderers can pull any metric from the peer record.
            fields={k: v for k, v in r.items() if k not in ("similarity_score", "similarity_components")},
        ))

    # Robustness check: if the top peer is much more similar than the
    # 10th, the cohort is thin — flag it.
    robustness: Dict[str, Any] = {
        "n_peers": len(peers),
    }
    if len(peers) >= 10:
        robustness["top_similarity"] = peers[0].similarity_score
        robustness["tenth_similarity"] = peers[9].similarity_score
        robustness["gap"] = peers[0].similarity_score - peers[9].similarity_score
    status = SectionStatus.OK
    reason = ""
    if len(peers) < 5:
        status = SectionStatus.INCOMPLETE
        reason = f"only {len(peers)} peers available; predictions will be thin"

    return ComparableSet(
        peers=peers,
        features_used=list(WEIGHTS.keys()),
        weights=dict(WEIGHTS),
        robustness_check=robustness,
        status=status,
        reason=reason,
    )


def _build_predictions(
    observed: Dict[str, ObservedMetric],
    profile: HospitalProfile,
    comparables: ComparableSet,
) -> Dict[str, PredictedMetric]:
    """Conformal-calibrated Ridge + fallback ladder.

    Delegates to :func:`rcm_mc.ml.ridge_predictor.predict_missing_metrics`
    with the completeness registry as the metric universe. Each
    prediction round-trips through :func:`ridge_predictor.to_packet_predicted_metric`
    so the packet gets coverage_target + reliability_grade on each row.
    """
    if not comparables.peers:
        return {}
    try:
        from ..ml.ridge_predictor import (
            predict_missing_metrics, to_packet_predicted_metric,
        )
        from .completeness import RCM_METRIC_REGISTRY
    except Exception as exc:  # noqa: BLE001
        logger.debug("ridge predictor unavailable: %s", exc)
        return {}

    known: Dict[str, Any] = {k: v.value for k, v in observed.items()}
    if profile.bed_count is not None:
        known["bed_count"] = profile.bed_count
    if profile.payer_mix:
        known["payer_mix"] = dict(profile.payer_mix)
    if profile.region:
        known["region"] = profile.region

    try:
        raw = predict_missing_metrics(
            known, comparables, RCM_METRIC_REGISTRY, coverage=0.90,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("predict_missing_metrics raised: %s", exc)
        return {}

    upstream = list(observed.keys())
    out: Dict[str, PredictedMetric] = {}
    for k, rp in raw.items():
        try:
            out[str(k)] = to_packet_predicted_metric(rp, upstream=upstream)
        except (AttributeError, TypeError, ValueError):  # pragma: no cover
            continue
    return out


def _merge_rcm_profile(
    observed: Dict[str, ObservedMetric],
    predicted: Dict[str, PredictedMetric],
    peers: Sequence[ComparableHospital],
    *,
    auto_populated: Optional[Dict[str, float]] = None,
) -> Dict[str, ProfileMetric]:
    """Merge observed + auto-populated + predicted, preferring observed.

    Prompt 23 adds the ``auto_populated`` intermediate tier: values
    pulled from public data sources (HCRIS, Care Compare, IRS 990 via
    :func:`rcm_mc.data.auto_populate.auto_populate`) that slot between
    analyst-entered observations and ridge-predicted fallbacks. Each
    gets tagged :attr:`MetricSource.AUTO_POPULATED` and a ``medium``
    quality band so downstream renderers can show a distinct source
    badge.

    ``benchmark_percentile`` is computed against the peer cohort when a
    peer value distribution is available. Falls back to ``None`` so the
    UI shows a dash rather than a fake zero.
    """
    merged: Dict[str, ProfileMetric] = {}

    # Pull peer value distributions (for percentile bands)
    peer_vals: Dict[str, List[float]] = {}
    for p in peers:
        for k, v in (p.fields or {}).items():
            if _finite(v):
                peer_vals.setdefault(k, []).append(float(v))

    def _percentile(metric: str, v: float) -> Optional[float]:
        vals = peer_vals.get(metric)
        if not vals:
            return None
        n = len(vals)
        below = sum(1 for x in vals if x < v)
        return below / n

    for k, om in observed.items():
        merged[k] = ProfileMetric(
            value=om.value,
            source=MetricSource.OBSERVED,
            benchmark_percentile=_percentile(k, om.value),
            quality="high" if not om.quality_flags else "medium",
        )

    for k, v in (auto_populated or {}).items():
        if k in merged:
            continue   # observed wins
        if not _finite(v):
            continue
        merged[k] = ProfileMetric(
            value=float(v),
            source=MetricSource.AUTO_POPULATED,
            benchmark_percentile=_percentile(k, float(v)),
            quality="medium",
        )

    for k, pm in predicted.items():
        if k in merged:
            continue
        merged[k] = ProfileMetric(
            value=pm.value,
            source=MetricSource.PREDICTED,
            benchmark_percentile=_percentile(k, pm.value),
            ci_low=pm.ci_low,
            ci_high=pm.ci_high,
            quality=("high" if pm.r_squared >= 0.5
                     else "medium" if pm.r_squared >= 0.2
                     else "low"),
        )

    # Decorate each ProfileMetric with its economic-ontology context
    # so downstream renderers (workbench, explain endpoint) don't have
    # to look up the classification separately. Unknown metrics (keys
    # not yet in the ontology) keep the fields as None — we don't
    # invent domain metadata from thin air.
    _attach_ontology(merged)
    return merged


def _attach_ontology(merged: Dict[str, ProfileMetric]) -> None:
    """Populate ontology fields on each :class:`ProfileMetric`.

    Kept as a free helper so unit tests can call it against any profile
    dict without going through the full builder.
    """
    try:
        from ..domain.econ_ontology import (
            METRIC_ONTOLOGY, explain_causal_path,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("econ_ontology unavailable: %s", exc)
        return
    for key, pm in merged.items():
        defn = METRIC_ONTOLOGY.get(key)
        if defn is None:
            continue
        pm.domain = defn.domain.value
        pm.financial_pathway = defn.financial_pathway.value
        pm.mechanism_tags = list(defn.mechanism_tags)
        try:
            pm.causal_path_summary = explain_causal_path(key)
        except Exception:  # noqa: BLE001 — narrative must never break build
            pm.causal_path_summary = None


def _build_reimbursement_views(
    profile: HospitalProfile,
    rcm_profile: Dict[str, ProfileMetric],
    financials: Dict[str, Any],
    *,
    contract_overrides: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]],
           Optional[Dict[str, Dict[str, Any]]]]:
    """Build the reimbursement profile + realization path + per-metric
    sensitivity map. Returns ``(None, None, None)`` on any failure so
    the rest of the packet build continues unaffected.

    ``contract_overrides`` (Prompt 18) is forwarded to
    :func:`build_reimbursement_profile` as its
    ``optional_contract_inputs``. Any ``method_distribution`` entries
    will flip the corresponding provenance tags to ``ANALYST_OVERRIDE``.

    Each returned dict is already JSON-shaped (not a dataclass) so the
    packet's ``to_json`` / ``from_json`` roundtrip stays cheap.
    """
    try:
        from ..finance.reimbursement_engine import (
            build_reimbursement_profile,
            compute_revenue_realization_path,
            estimate_metric_revenue_sensitivity,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("reimbursement_engine unavailable: %s", exc)
        return (None, None, None)

    try:
        rp = build_reimbursement_profile(
            profile, dict(profile.payer_mix or {}),
            optional_contract_inputs=contract_overrides or None,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("build_reimbursement_profile failed: %s", exc)
        return (None, None, None)

    if not rp.method_weights:
        # No payer mix → skip downstream views, still return the
        # profile dict so partners see the inference notes.
        return (rp.to_dict(), None, None)

    # Revenue realization path. Use financial inputs when provided;
    # otherwise the engine will try to infer gross_revenue from the
    # contractual discount.
    current_metrics = {k: v.value for k, v in rcm_profile.items()}
    try:
        realization = compute_revenue_realization_path(
            current_metrics, rp,
            gross_revenue=float(financials.get("gross_revenue") or 0.0) or None,
            net_revenue=float(financials.get("net_revenue") or 0.0) or None,
        )
        realization_dict = realization.to_dict()
    except Exception as exc:  # noqa: BLE001
        logger.debug("compute_revenue_realization_path failed: %s", exc)
        realization_dict = None

    # Per-metric sensitivity map over the metrics actually in rcm_profile.
    sensitivity_map: Dict[str, Dict[str, Any]] = {}
    for metric in rcm_profile.keys():
        try:
            sensitivity_map[metric] = estimate_metric_revenue_sensitivity(metric, rp)
        except Exception:  # noqa: BLE001
            continue

    return (rp.to_dict(), realization_dict, sensitivity_map or None)


def _build_value_bridge_v2(
    rcm_profile: Dict[str, ProfileMetric],
    bridge_v1,
    reimbursement_profile_dict: Optional[Dict[str, Any]],
    revenue_realization_dict: Optional[Dict[str, Any]],
    financials: Dict[str, Any],
    *,
    ramp_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]],
           Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Run :func:`rcm_mc.pe.value_bridge_v2.compute_value_bridge` using
    the v1 bridge's targets. Returns the four packet-shaped section
    dicts (or all-None on failure).
    """
    try:
        from ..finance.reimbursement_engine import ReimbursementProfile
        from ..pe.value_bridge_v2 import (
            BridgeAssumptions, compute_value_bridge,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("value_bridge_v2 unavailable: %s", exc)
        return (None, None, None, None)

    if bridge_v1 is None or not bridge_v1.per_metric_impacts:
        return (None, None, None, None)

    # Reconstruct a ReimbursementProfile from the dict form.
    if reimbursement_profile_dict:
        reimbursement_profile = ReimbursementProfile.from_dict(
            reimbursement_profile_dict,
        )
    else:
        reimbursement_profile = None

    current_metrics = {imp.metric_key: imp.current_value
                       for imp in bridge_v1.per_metric_impacts}
    target_metrics = {imp.metric_key: imp.target_value
                      for imp in bridge_v1.per_metric_impacts}

    # Resolve ramp-curve overrides (Prompt 18). Missing / empty
    # ``ramp_overrides`` → the default curves. Only families the
    # analyst explicitly set are rewritten; untouched families keep
    # their shipped shape.
    ramp_curves_effective: Optional[Dict[str, Any]] = None
    if ramp_overrides:
        try:
            from ..pe.ramp_curves import DEFAULT_RAMP_CURVES, RampCurve
            resolved: Dict[str, Any] = {}
            for family, curve in DEFAULT_RAMP_CURVES.items():
                fields = dict(curve.to_dict())
                override_fields = ramp_overrides.get(family) or {}
                fields.update({str(k): int(v) for k, v in override_fields.items()})
                try:
                    resolved[family] = RampCurve.from_dict(fields)
                except ValueError:
                    resolved[family] = curve  # invalid override → ignore
            ramp_curves_effective = resolved
        except Exception as exc:  # noqa: BLE001
            logger.debug("ramp override resolution failed: %s", exc)

    assumptions = BridgeAssumptions(
        exit_multiple=float(financials.get("exit_multiple") or 10.0),
        cost_of_capital=float(financials.get("cost_of_capital_pct") or 0.08),
        collection_realization=float(
            financials.get("collection_realization") or 0.65
        ),
        denial_overturn_rate=float(
            financials.get("denial_overturn_rate") or 0.55
        ),
        rework_cost_per_claim=float(financials.get("cost_per_reworked_claim") or 30.0),
        claims_volume=int(financials.get("claims_volume") or 0),
        net_revenue=float(financials.get("net_revenue") or 0.0),
        implementation_ramp=float(
            financials.get("implementation_ramp") or 1.0
        ),
        evaluation_month=int(
            financials.get("evaluation_month") or 36
        ),
        ramp_curves=ramp_curves_effective,
    )

    try:
        result = compute_value_bridge(
            current_metrics, target_metrics,
            reimbursement_profile, assumptions,
            realization=revenue_realization_dict,
            current_ebitda=float(financials.get("current_ebitda") or 0.0),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("compute_value_bridge failed: %s", exc)
        return (None, None, None, None)

    # Leverage table — one row per lever with the four flavors.
    leverage_table: List[Dict[str, Any]] = [
        {
            "metric_key": li.metric_key,
            "current_value": float(li.current_value),
            "target_value": float(li.target_value),
            "recurring_revenue_uplift": float(li.recurring_revenue_uplift),
            "recurring_cost_savings": float(li.recurring_cost_savings),
            "one_time_working_capital_release": float(li.one_time_working_capital_release),
            "ongoing_financing_benefit": float(li.ongoing_financing_benefit),
            "recurring_ebitda_delta": float(li.recurring_ebitda_delta),
            "confidence": float(li.confidence),
            "pathway_tags": list(li.pathway_tags),
        }
        for li in result.lever_impacts
    ]

    recurring_vs_one_time = {
        "total_recurring_revenue_uplift": float(result.total_recurring_revenue_uplift),
        "total_recurring_cost_savings": float(result.total_recurring_cost_savings),
        "total_recurring_financing_benefit": float(result.total_financing_benefit),
        "total_recurring_ebitda_delta": float(result.total_recurring_ebitda_delta),
        "total_one_time_wc_release": float(result.total_one_time_wc_release),
        # Raw totals before cross-lever dependency adjustment (Prompt
        # 15). Shown alongside adjusted totals so partners can see
        # how much double-count was removed.
        "raw_total_recurring_ebitda_delta": float(result.raw_total_recurring_ebitda_delta),
        "raw_total_recurring_revenue_uplift": float(result.raw_total_recurring_revenue_uplift),
        "dependency_audit": [
            row.to_dict() if hasattr(row, "to_dict") else dict(row)
            for row in result.dependency_audit
        ],
    }
    ev_summary = {
        "exit_multiple": float(assumptions.exit_multiple),
        "enterprise_value_delta": float(result.enterprise_value_delta),
        "enterprise_value_from_recurring": float(result.enterprise_value_from_recurring),
        "cash_release_excluded_from_ev": float(result.cash_release_excluded_from_ev),
    }
    return (result.to_dict(), leverage_table, recurring_vs_one_time, ev_summary)


def _build_bridge(
    rcm_profile: Dict[str, ProfileMetric],
    profile: HospitalProfile,
    target_metrics: Optional[Dict[str, float]] = None,
    *,
    current_ebitda: float = 0.0,
    net_revenue: float = 0.0,
    gross_revenue: float = 0.0,
    cost_of_capital_pct: float = 0.08,
    cost_per_reworked_claim: float = 25.0,
    claims_volume: int = 0,
    payer_weighted_denial_value: float = 0.6,   # noqa: ARG001 — kept for API compat
    cost_to_collect_base_pct: float = 0.03,      # noqa: ARG001
) -> EBITDABridgeResult:
    """Delegates to :class:`rcm_mc.pe.rcm_ebitda_bridge.RCMEBITDABridge`.

    Build a :class:`FinancialProfile` from the packet inputs, pick
    target metrics (partner-supplied or defaults from the registry's
    moderate-tier P65), run the bridge, return the packet-shaped result.
    """
    from ..pe.rcm_ebitda_bridge import (
        FinancialProfile, RCMEBITDABridge,
    )
    from .completeness import RCM_METRIC_REGISTRY

    if not rcm_profile or (net_revenue or gross_revenue) <= 0:
        return EBITDABridgeResult(
            current_ebitda=current_ebitda,
            target_ebitda=current_ebitda,
            status=SectionStatus.INCOMPLETE,
            reason=("no metrics" if not rcm_profile else "no revenue baseline"),
        )

    fp = FinancialProfile(
        gross_revenue=float(gross_revenue),
        net_revenue=float(net_revenue or gross_revenue),
        current_ebitda=float(current_ebitda),
        cost_of_capital_pct=float(cost_of_capital_pct),
        total_claims_volume=int(claims_volume or 0),
        cost_per_reworked_claim=float(cost_per_reworked_claim),
        payer_mix=dict(profile.payer_mix or {}),
    )
    bridge = RCMEBITDABridge(fp)
    current_values: Dict[str, float] = {
        k: float(v.value) for k, v in rcm_profile.items()
        if k in bridge._LEVER_METHODS
    }
    # Targets: prefer caller-supplied; otherwise synthesize from the
    # moderate tier of the benchmark registry.
    targets: Dict[str, float] = {}
    if target_metrics:
        for k, v in target_metrics.items():
            if k in bridge._LEVER_METHODS and k in current_values:
                targets[k] = float(v)
    if not targets:
        rec = bridge.suggest_targets(current_values, None, RCM_METRIC_REGISTRY)
        targets = dict(rec.moderate.targets)
    if not targets:
        return EBITDABridgeResult(
            current_ebitda=current_ebitda, target_ebitda=current_ebitda,
            status=SectionStatus.INCOMPLETE,
            reason="no improvement targets produced by moderate tier",
        )
    return bridge.compute_bridge(current_values, targets)


def _build_rcm_monte_carlo(
    bridge_result: EBITDABridgeResult,
    profile: HospitalProfile,
    rcm_profile: Dict[str, ProfileMetric],
    predicted: Dict[str, PredictedMetric],
    *,
    n_sims: int = 2_000,
    seed: int = 42,
    gross_revenue: float = 0.0,
    net_revenue: float = 0.0,
    current_ebitda: float = 0.0,
    claims_volume: int = 0,
    cost_of_capital_pct: float = 0.08,
    entry_multiple: float = 10.0,
    exit_multiple: float = 10.0,
    hold_years: float = 5.0,
    organic_growth_pct: float = 0.0,
    moic_targets: tuple = (1.5, 2.0, 2.5, 3.0),
    covenant_leverage_threshold: Optional[float] = None,
) -> SimulationSummary:
    """Run the two-source Monte Carlo over the RCM bridge.

    Returns a :class:`SimulationSummary` shaped for the packet; the
    richer :class:`rcm_mc.mc.MonteCarloResult` is not yet the packet's
    canonical type (it carries more fields than the packet wire
    format supports). Callers wanting the full MC result should hit
    the ``/api/analysis/<id>/simulate/latest`` endpoint.
    """
    from ..pe.rcm_ebitda_bridge import FinancialProfile, RCMEBITDABridge
    from ..mc import (
        RCMMonteCarloSimulator,
        default_execution_assumption,
        from_conformal_prediction,
    )

    # Build assumptions from the bridge's per-lever impacts. Every lever
    # the bridge produced is a candidate for MC — but only if the
    # underlying metric is in rcm_profile (i.e., we have a current
    # value to anchor the "current → target" delta).
    assumptions: Dict[str, Any] = {}
    order: List[str] = []
    for imp in bridge_result.per_metric_impacts:
        key = imp.metric_key
        cur = imp.current_value
        tgt = imp.target_value
        # Prefer conformal CI when the metric came from the predictor.
        pred = predicted.get(key)
        if pred is not None and pred.ci_low is not None and pred.ci_high is not None:
            a = from_conformal_prediction(
                key, current_value=cur, target_value=tgt,
                ci_low=pred.ci_low, ci_high=pred.ci_high,
            )
        else:
            a = default_execution_assumption(
                key, current_value=cur, target_value=tgt,
            )
        assumptions[key] = a
        order.append(key)

    if not assumptions:
        return SimulationSummary(status=SectionStatus.SKIPPED,
                                  reason="bridge produced no levers for MC")

    fp = FinancialProfile(
        gross_revenue=float(gross_revenue),
        net_revenue=float(net_revenue),
        current_ebitda=float(current_ebitda),
        total_claims_volume=int(claims_volume),
        cost_of_capital_pct=float(cost_of_capital_pct),
        payer_mix=dict(profile.payer_mix or {}),
    )
    bridge = RCMEBITDABridge(fp)
    sim = RCMMonteCarloSimulator(
        bridge, n_simulations=int(n_sims), seed=int(seed),
    )
    current_metrics = {
        k: float(v.value) for k, v in rcm_profile.items()
    }
    sim.configure(
        current_metrics, assumptions,
        metric_order=order,
        entry_multiple=entry_multiple,
        exit_multiple=exit_multiple,
        hold_years=hold_years,
        organic_growth_pct=organic_growth_pct,
        moic_targets=moic_targets,
        covenant_leverage_threshold=covenant_leverage_threshold,
    )
    try:
        result = sim.run(scenario_label="default")
    except Exception as exc:  # noqa: BLE001
        return SimulationSummary(status=SectionStatus.FAILED, reason=f"MC failed: {exc}")

    return SimulationSummary(
        n_sims=int(result.n_simulations),
        seed=int(seed),
        ebitda_uplift=PercentileSet(
            p10=result.ebitda_impact.p10,
            p25=result.ebitda_impact.p25,
            p50=result.ebitda_impact.p50,
            p75=result.ebitda_impact.p75,
            p90=result.ebitda_impact.p90,
        ),
        moic=PercentileSet(
            p10=result.moic.p10, p25=result.moic.p25, p50=result.moic.p50,
            p75=result.moic.p75, p90=result.moic.p90,
        ),
        irr=PercentileSet(
            p10=result.irr.p10, p25=result.irr.p25, p50=result.irr.p50,
            p75=result.irr.p75, p90=result.irr.p90,
        ),
        probability_of_covenant_breach=float(result.probability_of_covenant_breach),
        variance_contribution_by_metric=dict(result.variance_contribution),
        convergence_check=result.convergence_check.to_dict(),
        status=SectionStatus.OK,
    )


def _build_v2_monte_carlo(
    bridge_v1,
    rcm_profile: Dict[str, ProfileMetric],
    predicted: Dict[str, PredictedMetric],
    reimbursement_profile_dict: Optional[Dict[str, Any]],
    revenue_realization_dict: Optional[Dict[str, Any]],
    financials: Dict[str, Any],
    *,
    n_sims: int,
    seed: int,
    ramp_overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Run the v2 Monte Carlo over ``compute_value_bridge``.

    Returns the ``V2MonteCarloResult.to_dict()`` on success; ``None``
    when the v2 bridge has nothing to simulate or the simulator fails.
    Failures are best-effort — the v2 MC is additive to the v1 MC and
    the packet remains valid if it's absent.
    """
    try:
        from ..finance.reimbursement_engine import ReimbursementProfile
        from ..mc.v2_monte_carlo import V2MonteCarloSimulator
        from ..mc.ebitda_mc import (
            default_execution_assumption, from_conformal_prediction,
        )
        from ..pe.value_bridge_v2 import BridgeAssumptions
    except Exception as exc:  # noqa: BLE001
        logger.debug("v2 Monte Carlo unavailable: %s", exc)
        return None

    if bridge_v1 is None or not bridge_v1.per_metric_impacts:
        return None

    # Build metric assumptions from the same levers the v1 bridge used.
    assumptions: Dict[str, Any] = {}
    order: List[str] = []
    for imp in bridge_v1.per_metric_impacts:
        key = imp.metric_key
        cur = imp.current_value
        tgt = imp.target_value
        pred = predicted.get(key)
        if pred is not None and pred.ci_low is not None and pred.ci_high is not None:
            a = from_conformal_prediction(
                key, current_value=cur, target_value=tgt,
                ci_low=pred.ci_low, ci_high=pred.ci_high,
            )
        else:
            a = default_execution_assumption(
                key, current_value=cur, target_value=tgt,
            )
        assumptions[key] = a
        order.append(key)
    if not assumptions:
        return None

    reimbursement_profile = (
        ReimbursementProfile.from_dict(reimbursement_profile_dict)
        if reimbursement_profile_dict else None
    )

    ramp_curves_effective: Optional[Dict[str, Any]] = None
    if ramp_overrides:
        try:
            from ..pe.ramp_curves import DEFAULT_RAMP_CURVES, RampCurve
            resolved: Dict[str, Any] = {}
            for family, curve in DEFAULT_RAMP_CURVES.items():
                fields = dict(curve.to_dict())
                override_fields = ramp_overrides.get(family) or {}
                fields.update({str(k): int(v) for k, v in override_fields.items()})
                try:
                    resolved[family] = RampCurve.from_dict(fields)
                except ValueError:
                    resolved[family] = curve
            ramp_curves_effective = resolved
        except Exception as exc:  # noqa: BLE001
            logger.debug("ramp override resolution (MC) failed: %s", exc)

    base_assumptions = BridgeAssumptions(
        exit_multiple=float(financials.get("exit_multiple") or 10.0),
        cost_of_capital=float(financials.get("cost_of_capital_pct") or 0.08),
        collection_realization=float(
            financials.get("collection_realization") or 0.65
        ),
        denial_overturn_rate=float(
            financials.get("denial_overturn_rate") or 0.55
        ),
        rework_cost_per_claim=float(financials.get("cost_per_reworked_claim") or 30.0),
        claims_volume=int(financials.get("claims_volume") or 0),
        net_revenue=float(financials.get("net_revenue") or 0.0),
        implementation_ramp=float(
            financials.get("implementation_ramp") or 1.0
        ),
        evaluation_month=int(
            financials.get("evaluation_month") or 36
        ),
        ramp_curves=ramp_curves_effective,
    )

    current_metrics = {
        k: float(v.value) for k, v in rcm_profile.items()
    }
    sim = V2MonteCarloSimulator(n_simulations=int(n_sims), seed=int(seed))
    sim.configure(
        current_metrics=current_metrics,
        metric_assumptions=assumptions,
        reimbursement_profile=reimbursement_profile,
        base_assumptions=base_assumptions,
        realization=revenue_realization_dict,
        current_ebitda=float(financials.get("current_ebitda") or 0.0),
        entry_multiple=float(financials.get("entry_multiple") or 10.0),
        hold_years=float(financials.get("hold_years") or 5.0),
        organic_growth_pct=float(financials.get("organic_growth_pct") or 0.0),
        moic_targets=tuple(
            financials.get("moic_targets") or (1.5, 2.0, 2.5, 3.0)
        ),
        metric_order=order,
    )
    try:
        result = sim.run(scenario_label="v2:default")
    except Exception as exc:  # noqa: BLE001
        logger.debug("v2 Monte Carlo run failed: %s", exc)
        return None
    return result.to_dict()


def _build_simulation(
    store: Any,
    deal_id: str,
    scenario_id: Optional[str],
    *,
    skip: bool,
    n_sims: int = 500,
    seed: int = 42,
) -> SimulationSummary:
    if skip:
        return SimulationSummary(status=SectionStatus.SKIPPED, reason="skip_simulation=True")
    # Look for configured sim inputs.
    try:
        from ..deals.deal_sim_inputs import get_inputs
        inputs = get_inputs(store, deal_id)
    except Exception as exc:  # noqa: BLE001
        return SimulationSummary(status=SectionStatus.FAILED, reason=f"sim inputs unavailable: {exc}")
    if not inputs:
        return SimulationSummary(status=SectionStatus.SKIPPED, reason="no sim inputs registered for deal")
    actual = inputs.get("actual_path")
    benchmark = inputs.get("benchmark_path")
    if not actual or not benchmark or not Path(actual).is_file() or not Path(benchmark).is_file():
        return SimulationSummary(status=SectionStatus.SKIPPED, reason="sim input files not on disk")
    try:
        from ..infra.config import load_and_validate
        from ..core.simulator import simulate_compare
        a_cfg = load_and_validate(str(actual))
        b_cfg = load_and_validate(str(benchmark))
        if scenario_id:
            # Best-effort scenario overlay: treat scenario_id as a path.
            try:
                from ..scenarios.scenario_overlay import apply_scenario, load_scenario
                if Path(scenario_id).is_file():
                    a_cfg = apply_scenario(a_cfg, load_scenario(scenario_id))
            except Exception as exc:  # noqa: BLE001
                logger.debug("scenario overlay failed: %s", exc)
        df = simulate_compare(a_cfg, b_cfg, n_sims=n_sims, seed=seed, align_profile=True)
    except Exception as exc:  # noqa: BLE001
        return SimulationSummary(status=SectionStatus.FAILED, reason=str(exc))

    def _pct(series, q: float) -> float:
        try:
            return float(series.quantile(q))
        except Exception:  # noqa: BLE001
            return 0.0

    # EBITDA uplift distribution: the Actual vs Benchmark drag IS the
    # uplift that closing the gap would yield. Sign-flip so positive =
    # uplift dollars.
    drag_col = df["ebitda_drag"] if "ebitda_drag" in df.columns else None
    if drag_col is None:
        return SimulationSummary(status=SectionStatus.FAILED, reason="simulation output missing ebitda_drag column")

    uplift_series = drag_col  # already positive when Actual > Benchmark
    return SimulationSummary(
        n_sims=len(df),
        seed=seed,
        ebitda_uplift=PercentileSet(
            p10=_pct(uplift_series, 0.10),
            p25=_pct(uplift_series, 0.25),
            p50=_pct(uplift_series, 0.50),
            p75=_pct(uplift_series, 0.75),
            p90=_pct(uplift_series, 0.90),
        ),
        moic=PercentileSet(),  # populated by caller if they have a bridge
        irr=PercentileSet(),
        probability_of_covenant_breach=0.0,
        variance_contribution_by_metric={},
        convergence_check={
            "n_sims": len(df),
            "mean": float(uplift_series.mean()) if len(df) else 0.0,
            "std": float(uplift_series.std()) if len(df) else 0.0,
        },
        status=SectionStatus.OK,
    )


def _build_risk_flags(
    rcm_profile: Dict[str, ProfileMetric],
    profile: HospitalProfile,
    completeness: CompletenessAssessment,
    *,
    comparables: Optional[ComparableSet] = None,
    bridge: Optional[EBITDABridgeResult] = None,
    regulatory_context: Optional[Dict[str, Any]] = None,
    metric_forecasts: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[RiskFlag]:
    """Delegates to :func:`rcm_mc.analysis.risk_flags.assess_risks`.

    Keeps the builder's call site stable while the flag-generation
    logic evolves in its own module. ``regulatory_context`` (Prompt
    24) is the output of
    :func:`rcm_mc.data.state_regulatory.assess_regulatory`.
    ``metric_forecasts`` (Prompt 27) drives the new
    TRENDING_DETERIORATION detector.
    """
    from .risk_flags import assess_risks
    return assess_risks(
        profile, rcm_profile, comparables, bridge,
        completeness=completeness,
        regulatory_context=regulatory_context,
        metric_forecasts=metric_forecasts,
    )


def _build_regulatory_context(
    profile: HospitalProfile,
) -> Optional[Dict[str, Any]]:
    """Build the static regulatory assessment from the deal's state
    + bed count + payer mix. ``None`` when no state is available —
    the detectors downstream no-op in that case.
    """
    state = (profile.state or "").strip()
    if not state:
        return None
    try:
        from ..data.state_regulatory import assess_regulatory
    except Exception as exc:  # noqa: BLE001
        logger.debug("state_regulatory unavailable: %s", exc)
        return None
    try:
        assessment = assess_regulatory(
            state,
            bed_count=profile.bed_count,
            payer_mix=dict(profile.payer_mix or {}),
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("assess_regulatory failed: %s", exc)
        return None
    return assessment.to_dict()


def _build_provenance(
    observed: Dict[str, ObservedMetric],
    predicted: Dict[str, PredictedMetric],
    bridge: EBITDABridgeResult,
    *,
    profile: Optional[HospitalProfile] = None,
    comparables: Optional[ComparableSet] = None,
    simulation: Optional[SimulationSummary] = None,
) -> ProvenanceSnapshot:
    """Delegate to the rich graph builder and flatten into the packet
    wire format.

    Keeping the rich graph as the single source of truth means every
    place that consumes provenance (packet, API endpoints, UI) sees
    the same node IDs and edges. The flat packet form drops the typed
    relationships — reconstructing those requires calling
    :func:`rcm_mc.provenance.build_rich_graph` on the packet.
    """
    from ..provenance.graph import build_rich_graph

    # Build a minimal stub packet carrying just what build_rich_graph
    # reads. Cheaper than rebuilding a full DealAnalysisPacket here.
    class _Stub:
        pass
    stub = _Stub()
    stub.observed_metrics = observed
    stub.predicted_metrics = predicted
    stub.ebitda_bridge = bridge
    stub.profile = profile or HospitalProfile()
    stub.comparables = comparables or ComparableSet()
    stub.simulation = simulation
    # rcm_profile is unused by build_rich_graph but expected to exist.
    stub.rcm_profile = {}
    rich = build_rich_graph(stub)
    return rich.to_packet_graph()


def _build_diligence_questions(
    risk_flags: List[RiskFlag],
    completeness: CompletenessAssessment,
    rcm_profile: Dict[str, ProfileMetric],
    *,
    profile: Optional[HospitalProfile] = None,
    comparables: Optional[ComparableSet] = None,
) -> List[DiligenceQuestion]:
    """Delegates to :func:`rcm_mc.analysis.diligence_questions.generate_diligence_questions`."""
    from .diligence_questions import generate_diligence_questions
    return generate_diligence_questions(
        profile or HospitalProfile(),
        rcm_profile, risk_flags, completeness, comparables,
    )


# ── The orchestrator ──────────────────────────────────────────────────

def build_analysis_packet(
    store: Any,
    deal_id: str,
    *,
    scenario_id: Optional[str] = None,
    as_of: Optional[date] = None,
    skip_simulation: bool = False,
    observed_override: Optional[Dict[str, Any]] = None,
    auto_populated: Optional[Dict[str, float]] = None,
    profile_override: Optional[Any] = None,
    comparables_pool: Optional[Sequence[Dict[str, Any]]] = None,
    target_metrics: Optional[Dict[str, float]] = None,
    financials: Optional[Dict[str, float]] = None,
    historical_values: Optional[Dict[str, Any]] = None,
    conflict_sources: Optional[Dict[str, Any]] = None,
) -> DealAnalysisPacket:
    """Build a fully-populated :class:`DealAnalysisPacket` for one deal.

    Each section runs in its own try-guard so a downstream failure never
    kills the upstream ones. See module docstring.

    ``financials`` opts-in the EBITDA-bridge dollar math. Expected keys:
    ``gross_revenue``, ``net_revenue``, ``current_ebitda``,
    ``claims_volume``, ``cost_of_capital_pct`` (0-1),
    ``payer_weighted_denial_value`` (0-1), ``cost_per_reworked_claim`` (USD).
    Missing fields default to conservative values.
    """
    # Input validation — catch common mistakes with clear messages.
    if not deal_id or not isinstance(deal_id, str):
        raise ValueError("deal_id must be a non-empty string")
    financials = dict(financials or {})
    # Coerce common mistakes: percentage-point scale on cost_of_capital.
    coc = financials.get("cost_of_capital_pct")
    if coc is not None and isinstance(coc, (int, float)) and coc > 1.0:
        # Partner passed 8 instead of 0.08 — auto-correct.
        financials["cost_of_capital_pct"] = float(coc) / 100.0
    # Validate observed_override values are numeric.
    if observed_override:
        for k, v in list(observed_override.items()):
            if v is None:
                continue
            if hasattr(v, "value"):
                continue   # ObservedMetric wrapper — fine.
            try:
                float(v)
            except (TypeError, ValueError):
                logger.warning(
                    "dropping non-numeric observed_override %s=%r", k, v,
                )
                del observed_override[k]

    # 1. Deal / profile
    deal_row = _load_deal_row(store, deal_id)
    profile = _build_profile(deal_row, profile_override)

    # 1b. Analyst overrides (Prompt 18). Loaded once, grouped, then
    # applied at each step that owns the matching namespace. ``store``
    # is ``None`` for in-memory test paths — we just skip the load.
    analyst_overrides_raw: Dict[str, Any] = {}
    analyst_overrides_grouped: Dict[str, Any] = {
        "payer_mix": {}, "method_distribution": {}, "bridge": {},
        "ramp": {}, "metric_target": {},
    }
    if store is not None:
        try:
            from .deal_overrides import get_overrides, group_overrides
            analyst_overrides_raw = get_overrides(store, deal_id)
            analyst_overrides_grouped = group_overrides(analyst_overrides_raw)
        except Exception as exc:  # noqa: BLE001
            logger.debug("deal_overrides unavailable: %s", exc)
    # Payer-mix override rewrites the profile's payer_mix in place so
    # every downstream consumer (risk flags, reimbursement engine,
    # provenance) sees the partner-authored mix.
    if analyst_overrides_grouped.get("payer_mix"):
        try:
            patched_mix = dict(profile.payer_mix or {})
            for payer, share in analyst_overrides_grouped["payer_mix"].items():
                patched_mix[str(payer)] = float(share)
            profile.payer_mix = patched_mix
        except Exception as exc:  # noqa: BLE001
            logger.debug("payer_mix override application failed: %s", exc)
    # Bridge-namespace overrides land in the ``financials`` dict so the
    # builder's existing pull-keys path picks them up without a
    # separate codepath. ``financials`` keys we know map 1:1 to
    # BridgeAssumptions field names after a tiny normalization.
    _BRIDGE_TO_FINANCIAL_KEY = {
        "exit_multiple": "exit_multiple",
        "cost_of_capital": "cost_of_capital_pct",
        "collection_realization": "collection_realization",
        "denial_overturn_rate": "denial_overturn_rate",
        "rework_cost_per_claim": "cost_per_reworked_claim",
        "implementation_ramp": "implementation_ramp",
        "claims_volume": "claims_volume",
        "net_revenue": "net_revenue",
        "evaluation_month": "evaluation_month",
    }
    for field_name, value in analyst_overrides_grouped.get("bridge", {}).items():
        financials[_BRIDGE_TO_FINANCIAL_KEY.get(field_name, field_name)] = value
    # Metric-target overrides merge on top of any caller-supplied
    # target_metrics (caller wins on conflict — call-site argument
    # beats stored override by design).
    if analyst_overrides_grouped.get("metric_target"):
        merged_targets = dict(analyst_overrides_grouped["metric_target"])
        if target_metrics:
            merged_targets.update(target_metrics)
        target_metrics = merged_targets

    # 2. Observed metrics
    observed = _build_observed(observed_override, deal_row)

    # 3. Completeness
    completeness = _build_completeness(
        observed, profile, scenario_id, as_of,
        historical_values=historical_values,
        conflict_sources=conflict_sources,
    )

    # 4. Comparables
    comparables = _build_comparables(profile, comparables_pool)

    # 4b. Anomaly detection (Prompt 28). Runs after comparables so
    #     the statistical / causal-consistency checks have cohort
    #     data to ground themselves against. HIGH/CRITICAL anomalies
    #     demote the completeness grade by one letter.
    try:
        from ..ml.anomaly_detector import detect_anomalies
        from ..domain.econ_ontology import causal_graph
        anomalies = detect_anomalies(
            observed, comparables,
            causal_graph=causal_graph(),
            historical_values=historical_values,
        )
    except Exception as exc:  # noqa: BLE001
        logger.debug("anomaly detection failed: %s", exc)
        anomalies = []
    if anomalies:
        completeness.anomalies = [a.to_dict() for a in anomalies]
        worst_sev = min(
            (
                {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}.get(
                    a.severity, 9,
                )
                for a in anomalies
            ),
            default=9,
        )
        if worst_sev <= 1 and completeness.grade:
            # Demote one letter (A→B, B→C, C→D, D stays D).
            demotion = {"A": "B", "B": "C", "C": "D", "D": "D"}
            completeness.grade = demotion.get(
                completeness.grade, completeness.grade,
            )

    # 5. Predicted metrics
    predicted = _build_predictions(observed, profile, comparables)

    # 6. Merge RCM profile
    rcm_profile = _merge_rcm_profile(
        observed, predicted, comparables.peers,
        auto_populated=auto_populated,
    )

    # 6b. Reimbursement + revenue-realization (Prompt 2). Purely
    # additive outputs — nothing below this line reads them yet; the
    # bridge still uses its Prompt 1 coefficients. We surface them on
    # the packet so Prompt 3 can pick them up without another builder
    # change.
    contract_overrides: Dict[str, Any] = {}
    if analyst_overrides_grouped.get("method_distribution"):
        contract_overrides["method_distribution_by_payer"] = (
            analyst_overrides_grouped["method_distribution"]
        )
    reimbursement_profile_dict, revenue_realization_dict, \
        metric_sensitivity_map = _build_reimbursement_views(
            profile, rcm_profile, financials or {},
            contract_overrides=contract_overrides or None,
        )

    # 7. EBITDA bridge
    bridge = _build_bridge(
        rcm_profile, profile,
        target_metrics,
        current_ebitda=float(financials.get("current_ebitda") or 0.0),
        net_revenue=float(financials.get("net_revenue") or 0.0),
        gross_revenue=float(financials.get("gross_revenue") or 0.0),
        cost_of_capital_pct=float(financials.get("cost_of_capital_pct") or 0.08),
        cost_per_reworked_claim=float(financials.get("cost_per_reworked_claim") or 25.0),
        claims_volume=int(financials.get("claims_volume") or 0),
        payer_weighted_denial_value=float(financials.get("payer_weighted_denial_value") or 0.6),
        cost_to_collect_base_pct=float(financials.get("cost_to_collect_base_pct") or 0.03),
    )

    # 7b. Value bridge v2 (Prompt 3) — unit-economics + reimbursement-
    # aware lever math. Uses the SAME targets as v1 so the two
    # versions can be compared side-by-side. Best-effort; failures
    # leave the packet's v2 sections as None.
    v2_result_dict, leverage_table, recurring_vs_one_time, ev_summary = \
        _build_value_bridge_v2(
            rcm_profile, bridge, reimbursement_profile_dict,
            revenue_realization_dict, financials,
            ramp_overrides=analyst_overrides_grouped.get("ramp"),
        )

    # 8. Monte Carlo — two-source (prediction + execution) when the
    # bridge is OK; otherwise fall back to the legacy YAML-based
    # simulate_compare path that keeps Phase-2 configs working.
    if skip_simulation:
        simulation = SimulationSummary(status=SectionStatus.SKIPPED,
                                        reason="skip_simulation=True")
    elif bridge.status == SectionStatus.OK and bridge.per_metric_impacts:
        simulation = _build_rcm_monte_carlo(
            bridge, profile, rcm_profile, predicted,
            n_sims=int((financials or {}).get("mc_n_sims") or 2000),
            seed=int((financials or {}).get("mc_seed") or 42),
            gross_revenue=float((financials or {}).get("gross_revenue") or 0.0),
            net_revenue=float((financials or {}).get("net_revenue") or 0.0),
            current_ebitda=float((financials or {}).get("current_ebitda") or 0.0),
            claims_volume=int((financials or {}).get("claims_volume") or 0),
            cost_of_capital_pct=float((financials or {}).get("cost_of_capital_pct") or 0.08),
            entry_multiple=float((financials or {}).get("entry_multiple") or 10.0),
            exit_multiple=float((financials or {}).get("exit_multiple") or 10.0),
            hold_years=float((financials or {}).get("hold_years") or 5.0),
            organic_growth_pct=float((financials or {}).get("organic_growth_pct") or 0.0),
            moic_targets=tuple((financials or {}).get("moic_targets") or (1.5, 2.0, 2.5, 3.0)),
            covenant_leverage_threshold=(
                float((financials or {}).get("covenant_leverage_threshold"))
                if (financials or {}).get("covenant_leverage_threshold") is not None
                else None
            ),
        )
    else:
        simulation = _build_simulation(
            store, deal_id, scenario_id, skip=skip_simulation,
        )

    # 8b. v2 Monte Carlo — runs alongside the v1 MC when the v2 bridge
    # produced levers. Partner-facing UI can render whichever the
    # scenario requested; both sit on the packet.
    v2_simulation_dict: Optional[Dict[str, Any]] = None
    if (
        not skip_simulation
        and v2_result_dict is not None
        and bridge.status == SectionStatus.OK
        and bridge.per_metric_impacts
    ):
        v2_simulation_dict = _build_v2_monte_carlo(
            bridge, rcm_profile, predicted,
            reimbursement_profile_dict, revenue_realization_dict,
            financials,
            n_sims=int((financials or {}).get("mc_v2_n_sims")
                        or (financials or {}).get("mc_n_sims")
                        or 1000),
            seed=int((financials or {}).get("mc_seed") or 42),
            ramp_overrides=analyst_overrides_grouped.get("ramp"),
        )

    # 9a. Static state regulatory / payer context (Prompt 24). Cheap
    #     registry lookup, feeds the new regulatory-context risk flags
    #     and the workbench's "Regulatory Environment" card.
    regulatory_context_dict = _build_regulatory_context(profile)

    # 8c. Per-metric temporal forecasts (Prompt 27). Only runs when the
    #     analyst supplied ``historical_values`` (typically via the
    #     document reader's multi-period path).
    metric_forecasts: Dict[str, Dict[str, Any]] = {}
    if historical_values:
        try:
            from ..ml.temporal_forecaster import forecast_all
            forecasts = forecast_all(historical_values)
            metric_forecasts = {
                k: v.to_dict() for k, v in forecasts.items()
            }
        except Exception as exc:  # noqa: BLE001
            logger.debug("forecast_all failed: %s", exc)

    # 9. Risk flags
    risk_flags = _build_risk_flags(
        rcm_profile, profile, completeness,
        comparables=comparables, bridge=bridge,
        regulatory_context=regulatory_context_dict,
        metric_forecasts=metric_forecasts,
    )

    # 10. Provenance graph
    provenance = _build_provenance(
        observed, predicted, bridge,
        profile=profile, comparables=comparables, simulation=simulation,
    )

    # 11. Diligence questions
    diligence_questions = _build_diligence_questions(
        risk_flags, completeness, rcm_profile,
        profile=profile, comparables=comparables,
    )

    packet = DealAnalysisPacket(
        deal_id=str(deal_id),
        deal_name=str(deal_row.get("name") or profile.name or deal_id),
        run_id=_new_run_id(),
        generated_at=datetime.now(timezone.utc),
        model_version=PACKET_SCHEMA_VERSION,
        scenario_id=scenario_id,
        as_of=as_of,
        profile=profile,
        observed_metrics=observed,
        completeness=completeness,
        comparables=comparables,
        predicted_metrics=predicted,
        rcm_profile=rcm_profile,
        ebitda_bridge=bridge,
        simulation=simulation,
        risk_flags=risk_flags,
        provenance=provenance,
        diligence_questions=diligence_questions,
        exports={
            # Sentinel value so the renderer knows "nothing exported yet
            # — build on demand". Real paths are filled in by export CLI.
            "json": "render_on_demand",
            "html": "render_on_demand",
            "pptx": "render_on_demand",
        },
        reimbursement_profile=reimbursement_profile_dict,
        revenue_realization=revenue_realization_dict,
        metric_sensitivity_map=metric_sensitivity_map,
        value_bridge_result=v2_result_dict,
        leverage_table=leverage_table,
        recurring_vs_one_time_summary=recurring_vs_one_time,
        enterprise_value_summary=ev_summary,
        v2_simulation=v2_simulation_dict,
        analyst_overrides=(dict(analyst_overrides_raw)
                            if analyst_overrides_raw else None),
        regulatory_context=regulatory_context_dict,
        metric_forecasts=metric_forecasts,
    )
    return packet
