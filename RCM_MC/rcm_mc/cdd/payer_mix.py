"""NEW-03 Payer-mix analysis and shift waterfall.

Computes payer shares (share = payer value / total) for one or two periods,
the period-over-period mix shift, and a margin-weight overlay that weights
commercial above Medicare and Medicaid. Shares sum to 100 percent within 1e-9;
the shift deltas sum to zero within 1e-9. Source can be HCRIS S-3 days, target
billing, or a Definitive-style derived table.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "NEW-03"
SHARE_TOL = 1e-9

# Default margin weights: commercial weighted above Medicare and Medicaid.
DEFAULT_MARGIN_WEIGHTS = {
    "Commercial": 1.0,
    "Medicare": 0.6,
    "Medicaid": 0.4,
    "Self-pay": 0.2,
    "Other": 0.5,
}


def _shares(period: Mapping[str, float]) -> Dict[str, float]:
    total = float(sum(period.values()))
    return {k: safe_div(float(v), total) * 100.0 for k, v in period.items()}


def _weighted_score(shares_pct: Mapping[str, float], weights: Mapping[str, float]) -> float:
    # Score on share fractions in [0,1]; payers without a weight use 0.5.
    return sum((shares_pct[k] / 100.0) * float(weights.get(k, 0.5)) for k in shares_pct)


def payer_mix(
    period1: Mapping[str, float],
    period2: Optional[Mapping[str, float]] = None,
    *,
    margin_weights: Optional[Mapping[str, float]] = None,
    period1_label: str = "Period 1",
    period2_label: str = "Period 2",
    source: str = "HCRIS Worksheet S-3 days",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Payer shares for one period, or the mix shift between two periods."""
    if not period1:
        raise ValueError("payer_mix requires at least one period of data")
    weights = dict(margin_weights) if margin_weights else dict(DEFAULT_MARGIN_WEIGHTS)

    s1 = _shares(period1)
    reconciliations: List[Reconciliation] = [
        Reconciliation(
            identity=f"{period1_label} shares sum to 100 percent",
            lhs=sum(s1.values()),
            rhs=100.0,
            tolerance=SHARE_TOL,
        )
    ]
    flags: List[Flag] = []
    series: List[Series] = [
        Series(
            name=f"Payer mix, {period1_label}",
            kind="bar",
            points=[{"label": k, "value": s1[k]} for k in s1],
        )
    ]
    score1 = _weighted_score(s1, weights)
    meta: Dict[str, Any] = {
        "shares_1": s1,
        "weighted_score_1": score1,
        "total_1": float(sum(period1.values())),
    }

    if period2 is not None:
        if not period2:
            raise ValueError("period2 was provided empty")
        s2 = _shares(period2)
        reconciliations.append(
            Reconciliation(
                identity=f"{period2_label} shares sum to 100 percent",
                lhs=sum(s2.values()),
                rhs=100.0,
                tolerance=SHARE_TOL,
            )
        )
        all_payers = sorted(set(s1) | set(s2))
        deltas = {k: s2.get(k, 0.0) - s1.get(k, 0.0) for k in all_payers}
        reconciliations.append(
            Reconciliation(
                identity="mix shift deltas sum to zero",
                lhs=sum(deltas.values()),
                rhs=0.0,
                tolerance=SHARE_TOL,
            )
        )
        # Shift waterfall ordered by magnitude.
        ordered = sorted(deltas.items(), key=lambda kv: abs(kv[1]), reverse=True)
        wf = [{"label": f"{period1_label} (100%)", "value": 100.0, "kind": "start", "color": "blue"}]
        for k, d in ordered:
            if abs(d) <= SHARE_TOL:
                continue
            wf.append({
                "label": k,
                "value": d,
                "kind": "delta",
                "color": "green" if d >= 0 else "red",
            })
        wf.append({"label": f"{period2_label} (100%)", "value": 100.0, "kind": "end", "color": "blue"})
        series.append(Series(name="Payer mix shift", kind="waterfall", points=wf))
        series.append(Series(
            name=f"Payer mix, {period2_label}",
            kind="bar",
            points=[{"label": k, "value": s2[k]} for k in s2],
        ))

        score2 = _weighted_score(s2, weights)
        meta.update({
            "shares_2": s2,
            "deltas": deltas,
            "weighted_score_2": score2,
            "weighted_score_change": score2 - score1,
            "total_2": float(sum(period2.values())),
        })
        # Margin-weight overlay (internal-only series exposes the raw weights).
        series.append(Series(
            name="Margin-weight overlay",
            kind="bar",
            internal_only=True,
            points=[{"label": k, "value": float(weights.get(k, 0.5))} for k in all_payers],
        ))
        if score2 < score1 - 1e-9:
            flags.append(Flag(
                code="margin_dilutive_shift",
                severity="warn",
                message=(
                    "Payer mix shifted toward lower-margin payers. Margin-weighted "
                    f"mix score fell from {score1:.3f} to {score2:.3f}."
                ),
                source=source,
            ))

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Shares are payer value divided by total, in percent.",
            "Margin weights are an internal overlay: commercial above Medicare and Medicaid.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Payer mix and shift",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{period1_label} weighted mix score {score1:.3f}."
            + (f" {period2_label} {meta.get('weighted_score_2', 0):.3f}."
               if period2 is not None else "")
        ),
        meta=meta,
    )
    return ex.validate()


def _demo() -> Exhibit:
    p1 = {"Medicare": 4000, "Medicaid": 2000, "Commercial": 3000, "Self-pay": 500, "Other": 500}
    p2 = {"Medicare": 4500, "Medicaid": 2500, "Commercial": 2500, "Self-pay": 300, "Other": 200}
    return payer_mix(p1, p2, period1_label="FY24", period2_label="FY25",
                     source="Demo HCRIS S-3", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Payer-mix analysis and waterfall",
        audience="both",
        demo=_demo,
    )
)
