"""CIM Cross-Check / Variance Engine — pressure-test management's claims.

Week one of a Chartis CDD is checking the CIM's market numbers against
public data. This module automates the public-data side for the hospital
subsector: the consultant enters management's claims; each claim type has an
estimator that computes an independent figure from the CMS HCRIS universe
scoped to (state [, bed band] [, target CCN]), and the variance between
claim and estimate is flagged:

    green  ≤ 10% absolute variance
    yellow ≤ 25%
    red    > 25%
    unverifiable — the public side is a gap (empty scope / missing filing
                   data). NEVER rendered as a zero-variance pass.

Honesty rules (these are the product):
- every estimate carries value, n (entities behind it), source label,
  vintage hint, method line, and a drill URL into the underlying surface;
- margin medians use the core plausible band (rcm_mc.core.margins) so a
  junk-opex filing can't skew the benchmark the CIM is judged against;
- claims are partner-ENTERED; estimates are ACTUAL public data — the UI
  badges both;
- the engine never substitutes a fabricated baseline when scope is empty.

Pure logic — no UI imports; fully unit-testable. The page lives in
rcm_mc/ui/cim_crosscheck_page.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

from ..core.margins import margin_is_plausible_series

# Variance thresholds (absolute |claim/estimate - 1|). Spec per P2:
# green ≤10%, yellow 10–25%, red >25%.
GREEN_MAX = 0.10
YELLOW_MAX = 0.25

_SOURCE = "CMS HCRIS cost reports (latest authoritative filing per CCN)"


@dataclass
class Estimate:
    """One independent public-data estimate for a claim."""
    claim_key: str
    label: str
    value: Optional[float]          # None = unverifiable (gap, not zero)
    n: int                          # entities behind the estimate
    unit: str                       # "$", "%", "days", "count"
    method: str                     # one-line how-it-was-computed
    source: str = _SOURCE
    drill_url: str = ""             # where to inspect the underlying rows


@dataclass
class VarianceRow:
    claim_key: str
    label: str
    claim_value: float
    estimate: Estimate
    variance: Optional[float]       # (claim - est) / est; None when unverifiable
    flag: str                       # "green" | "yellow" | "red" | "unverifiable"
    expert_question: str = ""
    #: Where the CLAIM itself sits in the in-scope per-facility distribution
    #: (0–100), for distribution-shaped claims only (margins, day shares,
    #: target revenue). None for aggregates (market size, counts) and when
    #: the distribution is too small to rank honestly (n < 8). A claim at the
    #: p95+ tail is a finding even when the variance flag is green.
    claim_percentile: Optional[int] = None
    percentile_n: int = 0


@dataclass
class CrossCheckResult:
    scope_label: str
    state: str
    ccn: str
    rows: List[VarianceRow] = field(default_factory=list)

    def flag_counts(self) -> Dict[str, int]:
        out = {"green": 0, "yellow": 0, "red": 0, "unverifiable": 0}
        for r in self.rows:
            out[r.flag] = out.get(r.flag, 0) + 1
        return out


def classify_variance(variance: Optional[float]) -> str:
    """Flag a relative variance. None (no public estimate) is its own state —
    a consultant must treat 'we cannot verify this' differently from 'this
    checks out'."""
    if variance is None or variance != variance:  # None / NaN
        return "unverifiable"
    v = abs(variance)
    if v <= GREEN_MAX:
        return "green"
    if v <= YELLOW_MAX:
        return "yellow"
    return "red"


def _scope(df: pd.DataFrame, state: str, min_beds: Optional[float],
           max_beds: Optional[float]) -> pd.DataFrame:
    out = df[df["state"] == state] if state else df
    if min_beds is not None:
        out = out[out["beds"].fillna(0) >= min_beds]
    if max_beds is not None:
        out = out[out["beds"].fillna(0) <= max_beds]
    return out


def _drill(state: str) -> str:
    return f"/target-screener?vertical=hospitals&state={state}" if state \
        else "/target-screener?vertical=hospitals"


# ── Estimators — one per claim type ─────────────────────────────────────
# Each returns an Estimate. value=None means the public side is a gap.

def _est_market_size(scope: pd.DataFrame, state: str, **_: Any) -> Estimate:
    npr = scope["net_patient_revenue"].dropna()
    val = float(npr.sum()) if len(npr) else None
    return Estimate(
        "market_size_dollars", "Market size (hospital net patient revenue)",
        val, int(len(npr)), "$",
        "Σ net_patient_revenue across in-scope HCRIS hospital filings "
        "(state hospital patient-revenue base; excludes non-hospital sites "
        "of care)", drill_url=_drill(state))


def _est_provider_count(scope: pd.DataFrame, state: str, **_: Any) -> Estimate:
    n = int(len(scope))
    return Estimate(
        "provider_count", "Hospital count in market",
        float(n) if n else None, n, "count",
        "Count of HCRIS-filing hospitals in scope (CMS-certified; "
        "non-filing or newly opened facilities not captured)",
        drill_url=_drill(state))


def _est_median_margin(scope: pd.DataFrame, state: str, **_: Any) -> Estimate:
    if "operating_margin" in scope.columns:
        m = scope["operating_margin"]
    else:
        rev = scope["net_patient_revenue"]
        m = (rev - scope["operating_expenses"]) / rev.where(rev > 1e5)
    m = m[margin_is_plausible_series(m)].dropna()
    val = float(m.median()) * 100 if len(m) else None
    return Estimate(
        "median_operating_margin_pct", "Median operating margin (pct points)",
        val, int(len(m)), "%",
        "Median of (NPR − opex)/NPR across in-scope filings, restricted to "
        "the −40%…+30% plausible band (junk-opex filings excluded)",
        drill_url=_drill(state))


def _est_day_share(col: str, label: str):
    def _f(scope: pd.DataFrame, state: str, **_: Any) -> Estimate:
        s = scope[col].dropna() if col in scope.columns else pd.Series(dtype=float)
        val = float(s.median()) * 100 if len(s) else None
        return Estimate(
            col.replace("_day_pct", "_share_pct"), label,
            val, int(len(s)), "%",
            f"Median {col} across in-scope filings (Worksheet S-3 day share; "
            "filings without the split are excluded, not zero-filled)",
            drill_url=_drill(state))
    return _f


def _est_inpatient_days(scope: pd.DataFrame, state: str, **_: Any) -> Estimate:
    d = scope["total_patient_days"].dropna()
    val = float(d.sum()) if len(d) else None
    return Estimate(
        "inpatient_days", "Inpatient days in market (annual)",
        val, int(len(d)), "days",
        "Σ total_patient_days across in-scope filings",
        drill_url=_drill(state))


def _est_target_npr(scope: pd.DataFrame, state: str, *, full: pd.DataFrame,
                    ccn: str, **_: Any) -> Estimate:
    row = full[full["ccn"].astype(str) == str(ccn)] if ccn else full.iloc[0:0]
    if len(row) and pd.notna(row.iloc[0].get("net_patient_revenue")):
        val = float(row.iloc[0]["net_patient_revenue"])
        n = 1
    else:
        val, n = None, 0
    return Estimate(
        "target_net_revenue_dollars", "Target net patient revenue (filed)",
        val, n, "$",
        "The target CCN's own net_patient_revenue as filed in its latest "
        "HCRIS cost report — the CIM top line should reconcile to this",
        drill_url=(f"/diligence/hcris-xray?ccn={ccn}" if ccn else ""))


_ESTIMATORS = {
    "market_size_dollars": _est_market_size,
    "provider_count": _est_provider_count,
    "median_operating_margin_pct": _est_median_margin,
    "medicare_share_pct": _est_day_share("medicare_day_pct",
                                         "Median Medicare day share"),
    "medicaid_share_pct": _est_day_share("medicaid_day_pct",
                                         "Median Medicaid day share"),
    "inpatient_days": _est_inpatient_days,
    "target_net_revenue_dollars": _est_target_npr,
}

CLAIM_TYPES: List[Dict[str, str]] = [
    {"key": "market_size_dollars", "label": "Market size — hospital NPR ($)",
     "unit": "$", "hint": "CIM market-size claim for the state hospital market"},
    {"key": "provider_count", "label": "Hospital count in market", "unit": "count",
     "hint": "Number of competing hospitals management claims"},
    {"key": "median_operating_margin_pct", "label": "Typical operating margin (%)",
     "unit": "%", "hint": "Claimed 'industry/market margin' in percent points"},
    {"key": "medicare_share_pct", "label": "Medicare share of days (%)", "unit": "%",
     "hint": "Claimed Medicare mix for the market"},
    {"key": "medicaid_share_pct", "label": "Medicaid share of days (%)", "unit": "%",
     "hint": "Claimed Medicaid mix for the market"},
    {"key": "inpatient_days", "label": "Market inpatient days (annual)",
     "unit": "days", "hint": "Claimed annual market inpatient volume"},
    {"key": "target_net_revenue_dollars", "label": "Target net revenue ($)",
     "unit": "$", "hint": "CIM revenue top line — checked against the target's own filing (needs CCN)"},
]

_EXPERT_Q = {
    "market_size_dollars": "How was the ${claim:,.0f} market sized — which sites "
        "of care and payer revenue are included beyond hospital NPR?",
    "provider_count": "Which facilities does management count as competitors "
        "that don't file HCRIS (new entrants, specialty sites)?",
    "median_operating_margin_pct": "What cost basis produces a {claim:.1f}% "
        "margin claim vs the filed-market median — allocations or carve-outs?",
    "medicare_share_pct": "Is the {claim:.1f}% Medicare mix days- or "
        "revenue-weighted, and over what period?",
    "medicaid_share_pct": "Does the {claim:.1f}% Medicaid figure include "
        "managed-Medicaid days, and how were pending determinations treated?",
    "inpatient_days": "What population/utilization assumptions back "
        "{claim:,.0f} annual market days vs filed volumes?",
    "target_net_revenue_dollars": "Reconcile the CIM's ${claim:,.0f} revenue "
        "to the HCRIS filing — what sits in the bridge (period, entities, "
        "non-patient revenue)?",
}


def _claim_distribution(key: str, scope: pd.DataFrame) -> Optional[pd.Series]:
    """Per-facility values (in CLAIM units) for distribution-shaped claims.

    Aggregate claims (market size, provider count, market days) have no
    per-facility distribution to rank within — return None, never a
    fabricated one. Margin uses the same plausible-band screen the estimator
    uses, so the percentile and the estimate describe the SAME population.
    """
    if key == "median_operating_margin_pct":
        if "operating_margin" in scope.columns:
            m = scope["operating_margin"]
        else:
            rev = scope["net_patient_revenue"]
            m = (rev - scope["operating_expenses"]) / rev.where(rev > 1e5)
        return m[margin_is_plausible_series(m)].dropna() * 100
    if key in ("medicare_share_pct", "medicaid_share_pct"):
        col = key.replace("_share_pct", "_day_pct")
        if col in scope.columns:
            return scope[col].dropna() * 100
        return None
    if key == "target_net_revenue_dollars":
        return scope["net_patient_revenue"].dropna()
    return None


_PCTILE_MIN_N = 8


def _claim_percentile(key: str, claim_val: float,
                      scope: pd.DataFrame) -> tuple:
    """(percentile 0-100, n) of the claim within the in-scope distribution;
    (None, 0) for aggregates or n < 8 (too small to rank honestly).
    Rank = below + half of ties — the platform's percentile convention."""
    dist = _claim_distribution(key, scope)
    if dist is None or len(dist) < _PCTILE_MIN_N:
        return None, 0
    vals = dist.values
    below = float((vals < claim_val).sum())
    ties = float((vals == claim_val).sum())
    pct = int(round(100.0 * (below + ties / 2.0) / len(vals)))
    return max(0, min(100, pct)), int(len(vals))


def run_crosscheck(
    hcris_df: pd.DataFrame,
    *,
    state: str,
    claims: Dict[str, float],
    ccn: str = "",
    min_beds: Optional[float] = None,
    max_beds: Optional[float] = None,
) -> CrossCheckResult:
    """Compute independent estimates + variance flags for the entered claims.

    ``claims`` maps claim_key → management's number (units per CLAIM_TYPES:
    $ as dollars, % as percent points, days/count as raw). Unknown keys are
    ignored; claims without an entered value are skipped (this is a
    cross-check of what the CIM asserts, not a form-completion exercise).
    """
    scope = _scope(hcris_df, state, min_beds, max_beds)
    beds_bit = ""
    if min_beds is not None or max_beds is not None:
        beds_bit = f", beds {int(min_beds or 0)}–{int(max_beds) if max_beds is not None else '+'}"
    scope_label = f"{state or 'US'} hospitals (n={len(scope)}{beds_bit})"

    result = CrossCheckResult(scope_label=scope_label, state=state, ccn=ccn)
    for ct in CLAIM_TYPES:
        key = ct["key"]
        if key not in claims or claims[key] is None:
            continue
        claim_val = float(claims[key])
        est = _ESTIMATORS[key](scope, state, full=hcris_df, ccn=ccn)
        if est.value is None or est.value == 0:
            variance: Optional[float] = None
        else:
            variance = (claim_val - est.value) / est.value
        flag = classify_variance(variance)
        q = _EXPERT_Q.get(key, "")
        try:
            q = q.format(claim=claim_val)
        except Exception:  # noqa: BLE001 — a memo nicety, never fatal
            pass
        pctile, pctile_n = _claim_percentile(key, claim_val, scope)
        result.rows.append(VarianceRow(
            claim_key=key, label=ct["label"], claim_value=claim_val,
            estimate=est, variance=variance, flag=flag, expert_question=q,
            claim_percentile=pctile, percentile_n=pctile_n))
    return result


def variance_memo(result: CrossCheckResult) -> str:
    """Plain-text variance memo: claim / independent estimate / variance /
    source / suggested expert-call question. Drops into call-prep notes."""
    lines = [
        "CIM CROSS-CHECK — VARIANCE MEMO",
        f"Scope: {result.scope_label}"
        + (f" · target CCN {result.ccn}" if result.ccn else ""),
        f"Source: {_SOURCE}",
        "Flags: green ≤10% variance · yellow ≤25% · red >25% · "
        "UNVERIFIABLE = no public estimate (not a pass)",
        "-" * 72,
    ]
    for r in result.rows:
        est = r.estimate
        est_s = "—" if est.value is None else (
            f"${est.value:,.0f}" if est.unit == "$"
            else f"{est.value:,.1f}%" if est.unit == "%"
            else f"{est.value:,.0f}")
        claim_s = (f"${r.claim_value:,.0f}" if est.unit == "$"
                   else f"{r.claim_value:,.1f}%" if est.unit == "%"
                   else f"{r.claim_value:,.0f}")
        var_s = "—" if r.variance is None else f"{r.variance*100:+,.1f}%"
        lines += [
            f"[{r.flag.upper():>12}] {r.label}",
            f"   CIM claim:            {claim_s}",
            f"   Independent estimate: {est_s} (n={est.n})",
            f"   Variance:             {var_s}",
        ]
        # Where the claim sits in the in-scope distribution — a tail claim
        # (≤p10/≥p90) is a finding even when the variance flag is green.
        if r.claim_percentile is not None:
            tail = (" ⚠ tail — scrutinize"
                    if r.claim_percentile >= 90 or r.claim_percentile <= 10
                    else "")
            lines.append(
                f"   Claim percentile:     p{r.claim_percentile} of "
                f"n={r.percentile_n} in-scope facilities{tail}")
        lines += [
            f"   Method:               {est.method}",
            f"   Expert-call question: {r.expert_question}",
            "",
        ]
    c = result.flag_counts()
    lines.append(
        f"Summary: {c['green']} green · {c['yellow']} yellow · "
        f"{c['red']} red · {c['unverifiable']} unverifiable")
    return "\n".join(lines)
