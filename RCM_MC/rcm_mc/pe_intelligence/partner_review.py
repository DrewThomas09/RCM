"""Partner review — one entry point that wraps a packet in PE judgment.

This is the module intended for external callers (UI routes, CLI
exports, LP digests). It consumes a
:class:`rcm_mc.analysis.packet.DealAnalysisPacket` (or a raw dict —
useful for tests), derives a :class:`HeuristicContext` from it, runs
the reasonableness bands and heuristics, composes the partner-voice
narrative, and returns a :class:`PartnerReview`.

We deliberately do NOT modify the packet. The review is returned as a
new object; callers that want to persist it alongside the packet should
serialize ``PartnerReview.to_dict()`` into their own store.

The packet extraction is defensive: a minimal or
partly-populated packet still produces a review (with
``SectionStatus`` / verdict ``UNKNOWN`` on checks that lack inputs).
Missing optional subsections (``value_bridge_result``,
``ebitda_bridge``) are tolerated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .heuristics import (
    HeuristicContext,
    HeuristicHit,
    run_heuristics,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_MEDIUM,
    SEV_LOW,
)
from .red_flags import RED_FLAG_FIELDS, run_all_rules
from .narrative import (
    NarrativeBlock,
    REC_PASS,
    REC_PROCEED,
    REC_PROCEED_CAVEATS,
    REC_STRONG_PROCEED,
    compose_narrative,
)
from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
    run_reasonableness_checks,
)


# ── Dataclass ─────────────────────────────────────────────────────────

@dataclass
class PartnerReview:
    """The whole PE-partner judgment wrapped around a packet."""
    deal_id: str
    deal_name: str = ""
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context_summary: Dict[str, Any] = field(default_factory=dict)
    reasonableness_checks: List[BandCheck] = field(default_factory=list)
    heuristic_hits: List[HeuristicHit] = field(default_factory=list)
    narrative: NarrativeBlock = field(default_factory=NarrativeBlock)

    def has_critical_flag(self) -> bool:
        return any(h.severity == SEV_CRITICAL for h in self.heuristic_hits)

    def is_fundable(self) -> bool:
        return self.narrative.recommendation in (REC_PROCEED, REC_STRONG_PROCEED)

    def severity_counts(self) -> Dict[str, int]:
        out = {SEV_CRITICAL: 0, SEV_HIGH: 0, SEV_MEDIUM: 0, SEV_LOW: 0}
        for h in self.heuristic_hits:
            if h.severity in out:
                out[h.severity] += 1
        return out

    def band_counts(self) -> Dict[str, int]:
        out = {
            VERDICT_IN_BAND: 0, VERDICT_STRETCH: 0, VERDICT_OUT_OF_BAND: 0,
            VERDICT_IMPLAUSIBLE: 0, VERDICT_UNKNOWN: 0,
        }
        for b in self.reasonableness_checks:
            if b.verdict in out:
                out[b.verdict] += 1
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "context_summary": dict(self.context_summary),
            "reasonableness_checks": [b.to_dict() for b in self.reasonableness_checks],
            "heuristic_hits": [h.to_dict() for h in self.heuristic_hits],
            "narrative": self.narrative.to_dict(),
            "severity_counts": self.severity_counts(),
            "band_counts": self.band_counts(),
            "recommendation": self.narrative.recommendation,
            "has_critical_flag": self.has_critical_flag(),
            "is_fundable": self.is_fundable(),
        }


# ── Packet extraction ────────────────────────────────────────────────

def _packet_section(packet: Any, name: str) -> Any:
    """Read a section from a packet-like object tolerant of dict form."""
    if packet is None:
        return None
    if isinstance(packet, dict):
        return packet.get(name)
    return getattr(packet, name, None)


def _to_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        try:
            return obj.to_dict() or {}
        except Exception:
            return {}
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {}


def _get_metric_value(metrics: Any, key: str) -> Optional[float]:
    """Extract ``metrics[key].value`` from an observed/profile dict-like.

    Tolerant of ``{key: ObservedMetric}``, ``{key: {value: ...}}``, and
    ``{key: number}`` shapes.
    """
    if metrics is None:
        return None
    if isinstance(metrics, dict):
        v = metrics.get(key)
    else:
        v = getattr(metrics, key, None)
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        val = v.get("value")
        return float(val) if val is not None else None
    val = getattr(v, "value", None)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _payer_mix(profile: Any) -> Dict[str, float]:
    if profile is None:
        return {}
    if isinstance(profile, dict):
        mix = profile.get("payer_mix") or {}
    else:
        mix = getattr(profile, "payer_mix", None) or {}
    if not isinstance(mix, dict):
        return {}
    return {str(k): float(v) for k, v in mix.items() if v is not None}


def _hospital_type(profile: Any) -> Optional[str]:
    if profile is None:
        return None
    if isinstance(profile, dict):
        return profile.get("hospital_type") or profile.get("facility_type")
    for attr in ("hospital_type", "facility_type", "type"):
        val = getattr(profile, attr, None)
        if val:
            return str(val)
    return None


def _bed_count(profile: Any) -> Optional[int]:
    if profile is None:
        return None
    if isinstance(profile, dict):
        v = profile.get("bed_count")
    else:
        v = getattr(profile, "bed_count", None)
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _state(profile: Any) -> Optional[str]:
    if profile is None:
        return None
    if isinstance(profile, dict):
        return profile.get("state")
    return getattr(profile, "state", None)


def _teaching_status(profile: Any) -> Optional[str]:
    if profile is None:
        return None
    if isinstance(profile, dict):
        return profile.get("teaching_status")
    return getattr(profile, "teaching_status", None)


def _urban_rural(profile: Any) -> Optional[str]:
    if profile is None:
        return None
    if isinstance(profile, dict):
        return profile.get("urban_rural")
    return getattr(profile, "urban_rural", None)


def _pct(value: Optional[float]) -> Optional[float]:
    """Normalize a percentage-ish value to a fraction."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.5:
        return v / 100.0
    return v


def _ebitda_bridge_info(packet: Any) -> Dict[str, Any]:
    br = _packet_section(packet, "ebitda_bridge")
    return _to_dict(br)


def _value_bridge_info(packet: Any) -> Dict[str, Any]:
    vb = _packet_section(packet, "value_bridge_result")
    return _to_dict(vb) if vb else {}


def _simulation_info(packet: Any) -> Dict[str, Any]:
    sim = _packet_section(packet, "simulation")
    return _to_dict(sim) if sim else {}


def _enterprise_value_info(packet: Any) -> Dict[str, Any]:
    ev = _packet_section(packet, "enterprise_value_summary")
    return _to_dict(ev) if ev else {}


def _completeness_info(packet: Any) -> Dict[str, Any]:
    c = _packet_section(packet, "completeness")
    return _to_dict(c) if c else {}


def _derive_lever_claims(
    bridge_info: Dict[str, Any],
    hold_years: Optional[float],
) -> List[Dict[str, Any]]:
    """Extract lever claims from the EBITDA bridge per-metric impacts.

    Converts fractional-change magnitudes into the units the
    realizability bands expect (bps for rates, days for AR). Unknown
    levers are skipped — the band check would just return UNKNOWN
    anyway.
    """
    claims: List[Dict[str, Any]] = []
    impacts = bridge_info.get("per_metric_impacts") or []
    months = int(round((hold_years or 2.0) * 12))
    months = max(6, min(months, 60))

    unit_map = {
        "denial_rate": ("bps", 10_000.0),
        "initial_denial_rate": ("bps", 10_000.0),
        "final_writeoff_rate": ("bps", 10_000.0),
        "clean_claim_rate": ("bps", 10_000.0),
        "days_in_ar": ("days", 1.0),
        "ar_days": ("days", 1.0),
        "npsr_margin": ("pct", 100.0),
        "organic_rev_growth": ("pct", 100.0),
    }

    canonical = {
        "initial_denial_rate": "denial_rate",
        "ar_days": "days_in_ar",
    }

    for row in impacts:
        if not isinstance(row, dict):
            continue
        mkey = str(row.get("metric_key") or "").lower().strip()
        if not mkey or mkey not in unit_map:
            continue
        cur = row.get("current_value")
        tgt = row.get("target_value")
        if cur is None or tgt is None:
            continue
        try:
            cur_f, tgt_f = float(cur), float(tgt)
        except (TypeError, ValueError):
            continue
        delta = tgt_f - cur_f
        _, scale = unit_map[mkey]
        magnitude = abs(delta * scale)
        if magnitude <= 0:
            continue
        lever_name = canonical.get(mkey, mkey)
        claims.append({
            "lever": lever_name,
            "magnitude": magnitude,
            "months": months,
        })
    return claims


def _per_year(magnitude: Optional[float], hold_years: Optional[float]) -> Optional[float]:
    if magnitude is None or hold_years is None or hold_years <= 0:
        return None
    return magnitude / hold_years


def _extract_context(packet: Any) -> HeuristicContext:
    """Turn a packet (or dict) into a HeuristicContext."""
    profile = _packet_section(packet, "profile")
    observed = _packet_section(packet, "observed_metrics") or {}
    rcm_profile = _packet_section(packet, "rcm_profile") or {}

    bridge = _ebitda_bridge_info(packet)
    sim = _simulation_info(packet)
    vb = _value_bridge_info(packet)
    ev = _enterprise_value_info(packet)
    comp = _completeness_info(packet)

    # Current EBITDA (in $M). Bridge stores in $ (not $M). Tolerate both.
    raw_ebitda = bridge.get("current_ebitda")
    ebitda_m: Optional[float] = None
    if raw_ebitda is not None:
        try:
            v = float(raw_ebitda)
            # Heuristic: if > 10_000 assume dollars, else already in $M.
            ebitda_m = v / 1_000_000.0 if abs(v) > 10_000 else v
        except (TypeError, ValueError):
            ebitda_m = None
    if ebitda_m is None:
        ebitda_m = _get_metric_value(observed, "ebitda_m") or _get_metric_value(observed, "ebitda")

    # Current EBITDA margin (fraction)
    ebitda_margin = bridge.get("new_ebitda_margin")
    if ebitda_margin is None:
        ebitda_margin = _get_metric_value(observed, "ebitda_margin")
    ebitda_margin = _pct(ebitda_margin)

    # IRR / MOIC from sim p50
    irr_p50 = None
    moic_p50 = None
    if sim:
        irr_section = sim.get("irr")
        if isinstance(irr_section, dict):
            irr_p50 = irr_section.get("p50")
        moic_section = sim.get("moic")
        if isinstance(moic_section, dict):
            moic_p50 = moic_section.get("p50")
    # Fall back to value_bridge or enterprise_value
    if irr_p50 is None:
        irr_p50 = vb.get("irr") or ev.get("irr")
    if moic_p50 is None:
        moic_p50 = vb.get("moic") or ev.get("moic")

    # Exit multiple — try several placements
    exit_multiple = (ev.get("exit_multiple") or vb.get("exit_multiple")
                     or ev.get("exit_ev_multiple"))
    entry_multiple = (ev.get("entry_multiple") or vb.get("entry_multiple")
                      or ev.get("entry_ev_multiple"))
    leverage = (ev.get("leverage_multiple") or vb.get("leverage_multiple")
                or _get_metric_value(observed, "net_debt_to_ebitda"))
    covenant_headroom = (ev.get("covenant_headroom_pct")
                         or vb.get("covenant_headroom_pct")
                         or _get_metric_value(observed, "covenant_headroom"))
    covenant_headroom = _pct(covenant_headroom)

    # Hold
    hold_years = (ev.get("hold_years") or vb.get("hold_years") or vb.get("hold_period")
                  or _get_metric_value(observed, "hold_years"))
    try:
        hold_years = float(hold_years) if hold_years is not None else None
    except (TypeError, ValueError):
        hold_years = None

    # Operating KPIs from observed_metrics (preferred) → rcm_profile
    denial_rate = (_get_metric_value(observed, "initial_denial_rate")
                   or _get_metric_value(observed, "denial_rate")
                   or _get_metric_value(rcm_profile, "initial_denial_rate")
                   or _get_metric_value(rcm_profile, "denial_rate"))
    denial_rate = _pct(denial_rate)

    final_writeoff = (_get_metric_value(observed, "final_writeoff_rate")
                      or _get_metric_value(rcm_profile, "final_writeoff_rate"))
    final_writeoff = _pct(final_writeoff)

    days_in_ar = (_get_metric_value(observed, "days_in_ar")
                  or _get_metric_value(rcm_profile, "days_in_ar"))

    clean_claim = (_get_metric_value(observed, "clean_claim_rate")
                   or _get_metric_value(rcm_profile, "clean_claim_rate"))
    clean_claim = _pct(clean_claim)

    cmi = (_get_metric_value(observed, "case_mix_index")
           or _get_metric_value(rcm_profile, "case_mix_index"))

    # Lever-based per-year rates from bridge
    lever_claims = _derive_lever_claims(bridge, hold_years)
    denial_claim = next((c for c in lever_claims if c["lever"] == "denial_rate"), None)
    ar_claim = next((c for c in lever_claims if c["lever"] == "days_in_ar"), None)
    margin_claim = bridge.get("margin_improvement_bps")

    denial_bps_yr = _per_year(denial_claim["magnitude"] if denial_claim else None, hold_years)
    ar_days_yr = _per_year(ar_claim["magnitude"] if ar_claim else None, hold_years)
    margin_bps_yr = None
    if margin_claim is not None and hold_years:
        try:
            margin_bps_yr = float(margin_claim) / hold_years
        except (TypeError, ValueError):
            margin_bps_yr = None

    # Revenue growth — v2 bridge sometimes carries a pct figure.
    rev_growth = vb.get("organic_rev_growth_pct") or vb.get("revenue_growth_pct")
    rev_growth_pct = None
    if rev_growth is not None:
        try:
            rev_growth_pct = float(rev_growth)
        except (TypeError, ValueError):
            rev_growth_pct = None

    data_coverage = comp.get("coverage_pct")
    data_coverage = _pct(data_coverage) if data_coverage is not None else None

    # Deal structure — pulled from packet.scenario_id heuristic or explicit profile field.
    deal_structure = None
    if isinstance(profile, dict):
        deal_structure = profile.get("deal_structure")
    elif profile is not None:
        deal_structure = getattr(profile, "deal_structure", None)
    if not deal_structure and isinstance(vb, dict):
        deal_structure = vb.get("deal_structure")

    has_cmi = cmi is not None

    # Red-flag fields: pulled from profile or observed (duck-typed).
    red_flag_values: Dict[str, Any] = {}
    for field_name in RED_FLAG_FIELDS:
        for source in (profile, observed, vb, ev):
            if source is None:
                continue
            val = None
            if isinstance(source, dict):
                val = source.get(field_name)
                if isinstance(val, dict):
                    val = val.get("value")
            else:
                val = getattr(source, field_name, None)
            if val is not None:
                red_flag_values[field_name] = val
                break

    ctx_obj = HeuristicContext(
        payer_mix=_payer_mix(profile),
        ebitda_m=ebitda_m,
        revenue_m=_get_metric_value(observed, "net_patient_revenue_m")
                  or _get_metric_value(observed, "revenue_m"),
        bed_count=_bed_count(profile),
        hospital_type=_hospital_type(profile),
        state=_state(profile),
        urban_rural=_urban_rural(profile),
        teaching_status=_teaching_status(profile),
        denial_rate=denial_rate,
        final_writeoff_rate=final_writeoff,
        days_in_ar=days_in_ar,
        clean_claim_rate=clean_claim,
        case_mix_index=cmi,
        ebitda_margin=ebitda_margin,
        exit_multiple=float(exit_multiple) if exit_multiple is not None else None,
        entry_multiple=float(entry_multiple) if entry_multiple is not None else None,
        hold_years=hold_years,
        projected_irr=float(irr_p50) if irr_p50 is not None else None,
        projected_moic=float(moic_p50) if moic_p50 is not None else None,
        denial_improvement_bps_per_yr=denial_bps_yr,
        ar_reduction_days_per_yr=ar_days_yr,
        revenue_growth_pct_per_yr=rev_growth_pct,
        margin_expansion_bps_per_yr=margin_bps_yr,
        deal_structure=deal_structure,
        leverage_multiple=float(leverage) if leverage is not None else None,
        covenant_headroom_pct=covenant_headroom,
        data_coverage_pct=data_coverage,
        has_case_mix_data=has_cmi,
    )
    # Attach red-flag fields (duck-typed; not declared on the dataclass).
    for key, val in red_flag_values.items():
        setattr(ctx_obj, key, val)
    return ctx_obj


def _context_summary(ctx: HeuristicContext) -> Dict[str, Any]:
    """Flatten a context into a JSON-safe dict for the review."""
    return {
        "payer_mix": dict(ctx.payer_mix),
        "ebitda_m": ctx.ebitda_m,
        "revenue_m": ctx.revenue_m,
        "bed_count": ctx.bed_count,
        "hospital_type": ctx.hospital_type,
        "state": ctx.state,
        "teaching_status": ctx.teaching_status,
        "denial_rate": ctx.denial_rate,
        "final_writeoff_rate": ctx.final_writeoff_rate,
        "days_in_ar": ctx.days_in_ar,
        "ebitda_margin": ctx.ebitda_margin,
        "exit_multiple": ctx.exit_multiple,
        "entry_multiple": ctx.entry_multiple,
        "hold_years": ctx.hold_years,
        "projected_irr": ctx.projected_irr,
        "projected_moic": ctx.projected_moic,
        "leverage_multiple": ctx.leverage_multiple,
        "covenant_headroom_pct": ctx.covenant_headroom_pct,
        "data_coverage_pct": ctx.data_coverage_pct,
        "has_case_mix_data": ctx.has_case_mix_data,
        "denial_improvement_bps_per_yr": ctx.denial_improvement_bps_per_yr,
        "ar_reduction_days_per_yr": ctx.ar_reduction_days_per_yr,
        "margin_expansion_bps_per_yr": ctx.margin_expansion_bps_per_yr,
        "deal_structure": ctx.deal_structure,
    }


# ── Entry point ──────────────────────────────────────────────────────

def partner_review(packet: Any) -> PartnerReview:
    """Run the full PE-partner review over a packet.

    The packet can be a real :class:`DealAnalysisPacket`, a dict (from
    ``packet.to_dict()``), or any duck-typed object with the same
    attributes. Missing subsections are tolerated — the review
    downgrades to ``UNKNOWN`` for checks it can't run.
    """
    ctx = _extract_context(packet)

    # Build lever-claims directly from the bridge for the band check.
    bridge = _ebitda_bridge_info(packet)
    lever_claims = _derive_lever_claims(bridge, ctx.hold_years)

    bands = run_reasonableness_checks(
        irr=ctx.projected_irr,
        ebitda_margin=ctx.ebitda_margin,
        ebitda_m=ctx.ebitda_m,
        exit_multiple=ctx.exit_multiple,
        hospital_type=ctx.hospital_type,
        payer_mix=ctx.payer_mix,
        lever_claims=lever_claims,
    )
    hits = run_all_rules(ctx)
    narrative = compose_narrative(
        bands=bands,
        hits=hits,
        hospital_type=ctx.hospital_type,
        ebitda_m=ctx.ebitda_m,
        payer_mix=ctx.payer_mix,
    )

    deal_id = str(_packet_section(packet, "deal_id") or "")
    deal_name = str(_packet_section(packet, "deal_name") or "")

    return PartnerReview(
        deal_id=deal_id,
        deal_name=deal_name,
        generated_at=datetime.now(timezone.utc),
        context_summary=_context_summary(ctx),
        reasonableness_checks=bands,
        heuristic_hits=hits,
        narrative=narrative,
    )


def partner_review_from_context(ctx: HeuristicContext, *, deal_id: str = "",
                                deal_name: str = "") -> PartnerReview:
    """Test/CLI-friendly entry: run the review from a pre-built context
    without a packet. Useful for what-if sensitivities."""
    # Per-year rates → check against the 12-month band. This keeps the
    # realizability check calibrated to ramp speed, not hold length.
    lever_claims: List[Dict[str, Any]] = []
    if ctx.denial_improvement_bps_per_yr:
        lever_claims.append({
            "lever": "denial_rate",
            "magnitude": float(ctx.denial_improvement_bps_per_yr),
            "months": 12,
        })
    if ctx.ar_reduction_days_per_yr:
        lever_claims.append({
            "lever": "days_in_ar",
            "magnitude": float(ctx.ar_reduction_days_per_yr),
            "months": 12,
        })
    bands = run_reasonableness_checks(
        irr=ctx.projected_irr,
        ebitda_margin=ctx.ebitda_margin,
        ebitda_m=ctx.ebitda_m,
        exit_multiple=ctx.exit_multiple,
        hospital_type=ctx.hospital_type,
        payer_mix=ctx.payer_mix,
        lever_claims=lever_claims,
    )
    hits = run_all_rules(ctx)
    narrative = compose_narrative(
        bands=bands,
        hits=hits,
        hospital_type=ctx.hospital_type,
        ebitda_m=ctx.ebitda_m,
        payer_mix=ctx.payer_mix,
    )
    return PartnerReview(
        deal_id=deal_id,
        deal_name=deal_name,
        generated_at=datetime.now(timezone.utc),
        context_summary=_context_summary(ctx),
        reasonableness_checks=bands,
        heuristic_hits=hits,
        narrative=narrative,
    )
