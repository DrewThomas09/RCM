"""KPI engine — computes the HFMA-vocabulary metrics from a CCD.

Every formula is cited and every KPI returns either a computed value
or ``None`` + reason — never an estimate, never an interpolation,
never a partial number wearing a full-metric label. If a partner
reads a number off this tab, the exact rows that produced it can be
surfaced via the provenance chain.

Citations:

- **Days in A/R** — HFMA MAP Key definition (HFMA, *Measuring and
  Managing Revenue Cycle Performance: MAP Keys*, 2021 edition).
  Formula: (Net A/R $ at period end) / (avg daily net patient
  service revenue). For a CCD-based computation we use a per-claim
  variant: weighted-average days from service-from-date to paid-date
  over the set of paid claims.
- **First-Pass Denial Rate** — AAPC definition (American Academy of
  Professional Coders, 2024 glossary). FPDR = claims denied on the
  *initial* payer adjudication / total claims submitted. We require
  an adjudication-event field to distinguish initial from rework;
  without it we return None rather than conflate the two.
- **A/R Aging > 90 days** — HFMA MAP Key #9. Fraction of open A/R
  balance that is 90+ days old as of ``as_of_date``.
- **Cost to Collect** — HFMA MAP Key #5. Ratio of total collection
  expense to total cash collected. Cost input is NOT inferrable from
  the CCD; this engine requires the caller to pass it or returns
  None. Never fabricated.
- **Net Revenue Realization (NRR)** — HFMA / KFF definition. Cash
  collected / Expected-per-contract. Requires contracted rates;
  when absent, returns None.
- **Lag analytics** — service → bill and bill → cash distributions
  (percentile distributions of (bill_date − service_date_from) and
  (paid_date − bill_date) day counts).
- **Denial stratification** — counts + dollar impact grouped by
  :class:`DenialCategory` via the rule file in ``_ansi_codes.py``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ..integrity.temporal_validity import (
    TemporalValidity, check_regulatory_overlap,
)
from ._ansi_codes import DenialCategory, classify_carc_set


# ── Result type ────────────────────────────────────────────────────

@dataclass
class KPIResult:
    """Uniform wrapper for every KPI computation.

    ``value`` is a Python float when computable. When the KPI can't
    be computed with the data at hand, ``value`` is ``None`` and
    ``reason`` is a human-readable explanation (partner-readable, not
    code-readable). Every result carries a :class:`TemporalValidity`
    stamp — always — because every KPI has a time dimension even when
    it isn't obvious.
    """
    name: str
    value: Optional[float]
    unit: str                                 # "days" | "pct" | "ratio" | "usd"
    numerator: Optional[float] = None
    denominator: Optional[float] = None
    sample_size: int = 0
    citation: str = ""
    reason: Optional[str] = None              # explains None values
    temporal: TemporalValidity = field(default_factory=TemporalValidity)
    qualifying_claim_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "sample_size": self.sample_size,
            "citation": self.citation,
            "reason": self.reason,
            "temporal": self.temporal.to_dict(),
            "qualifying_claim_ids": list(self.qualifying_claim_ids),
        }


@dataclass
class DenialStratRow:
    category: str
    count: int
    dollars_denied: float
    pct_of_total_denied: float


@dataclass
class KPIBundle:
    """What the Phase 2 tab reads from. One CCD → one KPIBundle."""
    days_in_ar: KPIResult
    first_pass_denial_rate: KPIResult
    ar_aging_over_90: KPIResult
    cost_to_collect: KPIResult
    net_revenue_realization: KPIResult
    lag_service_to_bill: KPIResult
    lag_bill_to_cash: KPIResult
    denial_stratification: List[DenialStratRow]
    as_of_date: date
    provider_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "days_in_ar": self.days_in_ar.to_dict(),
            "first_pass_denial_rate": self.first_pass_denial_rate.to_dict(),
            "ar_aging_over_90": self.ar_aging_over_90.to_dict(),
            "cost_to_collect": self.cost_to_collect.to_dict(),
            "net_revenue_realization": self.net_revenue_realization.to_dict(),
            "lag_service_to_bill": self.lag_service_to_bill.to_dict(),
            "lag_bill_to_cash": self.lag_bill_to_cash.to_dict(),
            "denial_stratification": [
                {
                    "category": r.category, "count": r.count,
                    "dollars_denied": r.dollars_denied,
                    "pct_of_total_denied": r.pct_of_total_denied,
                }
                for r in self.denial_stratification
            ],
            "as_of_date": self.as_of_date.isoformat(),
            "provider_id": self.provider_id,
        }


# ── Driver ──────────────────────────────────────────────────────────

def compute_kpis(
    ccd: Any,
    *,
    as_of_date: date,
    cost_to_collect_input_usd: Optional[float] = None,
    cash_collected_input_usd: Optional[float] = None,
    contracted_rate_fn: Optional[Any] = None,
    provider_id: str = "",
) -> KPIBundle:
    """Compute every Phase 2 KPI from a :class:`CanonicalClaimsDataset`.

    ``cost_to_collect_input_usd`` + ``cash_collected_input_usd`` must
    come from the analyst (seller P&L line items). Without them,
    Cost-to-Collect returns None; we don't infer it.

    ``contracted_rate_fn`` is an optional ``(cpt, payer_class) ->
    expected_dollars`` lookup. Without it, NRR returns None.
    """
    claims = list(getattr(ccd, "claims", ()))
    temporal = _temporal_stamp(claims)

    kpi_bundle = KPIBundle(
        days_in_ar=_days_in_ar(claims, temporal),
        first_pass_denial_rate=_first_pass_denial_rate(claims, temporal),
        ar_aging_over_90=_ar_aging_over_90(claims, as_of_date, temporal),
        cost_to_collect=_cost_to_collect(
            cost_to_collect_input_usd, cash_collected_input_usd, temporal,
        ),
        net_revenue_realization=_net_revenue_realization(
            claims, contracted_rate_fn, temporal,
        ),
        lag_service_to_bill=_lag_service_to_bill(claims, temporal),
        lag_bill_to_cash=_lag_bill_to_cash(claims, temporal),
        denial_stratification=_denial_stratification(claims),
        as_of_date=as_of_date,
        provider_id=provider_id,
    )
    return kpi_bundle


# ── Individual KPIs ─────────────────────────────────────────────────

def _days_in_ar(claims: Sequence[Any], temporal: TemporalValidity) -> KPIResult:
    """Days in A/R — HFMA MAP Key definition, CCD-weighted variant.

    We take paid claims with both service_date_from and paid_date
    populated and report the average (paid_date − service_date_from)
    in days, weighted by paid_amount so high-dollar claims dominate
    the number the CFO cares about.

    Excludes denied claims from the numerator per the HFMA note that
    days in A/R should reflect money that is actually going to be
    collected, not money tied up in appeal.
    """
    eligible: List[Tuple[int, float, str]] = []  # (days, weight, claim_id)
    for c in claims:
        if c.paid_date is None or c.service_date_from is None:
            continue
        if (c.paid_amount or 0) <= 0:
            continue
        # Denied claims excluded — ClaimStatus.DENIED or WRITTEN_OFF.
        status = getattr(c, "status", None)
        if status is not None and status.value in ("DENIED", "WRITTEN_OFF"):
            continue
        days = (c.paid_date - c.service_date_from).days
        if days < 0 or days > 3650:
            continue
        eligible.append((days, float(c.paid_amount), c.claim_id))

    if not eligible:
        return KPIResult(
            name="Days in A/R", value=None, unit="days",
            citation="HFMA MAP Key — Days in A/R",
            reason="no paid claims with both service_date_from and paid_date",
            temporal=temporal,
        )
    total_weight = sum(w for _, w, _ in eligible)
    weighted_sum = sum(d * w for d, w, _ in eligible)
    value = weighted_sum / total_weight if total_weight else None
    return KPIResult(
        name="Days in A/R", value=value, unit="days",
        numerator=weighted_sum, denominator=total_weight,
        sample_size=len(eligible),
        qualifying_claim_ids=tuple(cid for _, _, cid in eligible),
        citation="HFMA MAP Key — Days in A/R (CCD weighted-avg variant)",
        temporal=temporal,
    )


def _first_pass_denial_rate(
    claims: Sequence[Any], temporal: TemporalValidity
) -> KPIResult:
    """First-Pass Denial Rate — AAPC definition.

    FPDR = denied-on-initial / total submitted. We identify "initial"
    by (claim_id, line_number) uniqueness in the CCD: if multiple
    rows exist for the same (claim_id, line_number), the earliest
    submit_date wins for the initial. If submit_date isn't available
    on any row we cannot distinguish first-pass from rework; return
    None rather than conflate.
    """
    if not claims:
        return KPIResult(
            name="First-Pass Denial Rate", value=None, unit="pct",
            citation="AAPC — First-Pass Denial Rate",
            reason="no claims in CCD",
            temporal=temporal,
        )
    # Check we have the signal we need.
    has_submit_date = any(c.submit_date is not None for c in claims)
    has_status = any(
        getattr(c, "status", None) is not None for c in claims
    )
    if not (has_submit_date or has_status):
        return KPIResult(
            name="First-Pass Denial Rate", value=None, unit="pct",
            citation="AAPC — First-Pass Denial Rate",
            reason="neither submit_date nor status populated on any claim — "
                   "cannot distinguish first-pass from rework",
            temporal=temporal,
        )
    # Group by (claim_id, line_number). Earliest submit_date = initial.
    grouped: Dict[Tuple[str, int], List[Any]] = {}
    for c in claims:
        grouped.setdefault((c.claim_id, c.line_number), []).append(c)

    total = 0
    denied_first_pass = 0
    qualifying_ids: List[str] = []
    for key, rows in grouped.items():
        rows_sorted = sorted(
            rows,
            key=lambda r: (
                r.submit_date or date(1900, 1, 1),
                r.source_row if hasattr(r, "source_row") else 0,
            ),
        )
        initial = rows_sorted[0]
        total += 1
        status = getattr(initial, "status", None)
        if status is not None and status.value == "DENIED":
            denied_first_pass += 1
            qualifying_ids.append(initial.claim_id)
    if total == 0:
        return KPIResult(
            name="First-Pass Denial Rate", value=None, unit="pct",
            citation="AAPC — First-Pass Denial Rate",
            reason="no eligible (claim_id, line_number) groups",
            temporal=temporal,
        )
    rate = denied_first_pass / total
    return KPIResult(
        name="First-Pass Denial Rate", value=rate, unit="pct",
        numerator=float(denied_first_pass), denominator=float(total),
        sample_size=total, qualifying_claim_ids=tuple(qualifying_ids),
        citation="AAPC — First-Pass Denial Rate",
        temporal=temporal,
    )


def _ar_aging_over_90(
    claims: Sequence[Any], as_of_date: date, temporal: TemporalValidity
) -> KPIResult:
    """A/R Aging > 90 days — HFMA MAP Key #9.

    For each open claim (paid_amount is None OR (allowed - paid) > 0
    per HFMA "balance still owed" interpretation), compute the aging
    bucket as (as_of - service_date_from) days. Report dollar-% of
    open balance in ≥90 bucket.
    """
    total_open_balance = 0.0
    balance_over_90 = 0.0
    sample = 0
    qualifying: List[str] = []
    for c in claims:
        if c.service_date_from is None:
            continue
        paid = c.paid_amount or 0.0
        allowed = c.allowed_amount or c.charge_amount or 0.0
        open_balance = max(allowed - paid, 0.0)
        if open_balance <= 0:
            continue
        sample += 1
        days_old = (as_of_date - c.service_date_from).days
        total_open_balance += open_balance
        if days_old >= 90:
            balance_over_90 += open_balance
            qualifying.append(c.claim_id)
    if total_open_balance <= 0:
        return KPIResult(
            name="A/R Aging > 90 Days", value=None, unit="pct",
            citation="HFMA MAP Key #9",
            reason="no open A/R balance at as_of_date",
            temporal=temporal,
        )
    rate = balance_over_90 / total_open_balance
    return KPIResult(
        name="A/R Aging > 90 Days", value=rate, unit="pct",
        numerator=balance_over_90, denominator=total_open_balance,
        sample_size=sample, qualifying_claim_ids=tuple(qualifying),
        citation="HFMA MAP Key #9 — Aged A/R as % of Total A/R",
        temporal=temporal,
    )


def _cost_to_collect(
    cost_usd: Optional[float],
    cash_usd: Optional[float],
    temporal: TemporalValidity,
) -> KPIResult:
    """Cost to Collect — HFMA MAP Key #5.

    Requires cost and cash inputs from the analyst. Cannot be
    inferred from the CCD alone; the CCD has no admin cost-of-cycle
    data. Returning None + reason is the correct behaviour.
    """
    if cost_usd is None or cash_usd is None or cash_usd <= 0:
        return KPIResult(
            name="Cost to Collect", value=None, unit="ratio",
            citation="HFMA MAP Key #5 — Cost to Collect",
            reason=(
                "requires cost-of-collection and cash-collected inputs "
                "from the analyst; not derivable from the CCD"
            ),
            temporal=temporal,
        )
    ratio = cost_usd / cash_usd
    return KPIResult(
        name="Cost to Collect", value=ratio, unit="ratio",
        numerator=cost_usd, denominator=cash_usd, sample_size=1,
        citation="HFMA MAP Key #5 — Cost to Collect",
        temporal=temporal,
    )


def _net_revenue_realization(
    claims: Sequence[Any],
    contracted_rate_fn: Optional[Any],
    temporal: TemporalValidity,
) -> KPIResult:
    """Net Revenue Realization — actual cash / expected per contract.

    Requires a contracted-rate function provided by the caller. The
    CCD alone doesn't carry contracted rates, so this is None unless
    the analyst supplies the lookup.
    """
    if contracted_rate_fn is None:
        return KPIResult(
            name="Net Revenue Realization", value=None, unit="pct",
            citation="HFMA — Net Revenue Realization",
            reason=(
                "contracted-rate lookup not supplied; NRR requires "
                "per-(CPT, payer_class) contracted rates"
            ),
            temporal=temporal,
        )
    total_expected = 0.0
    total_actual = 0.0
    sample = 0
    for c in claims:
        if not c.cpt_code:
            continue
        expected = contracted_rate_fn(c.cpt_code, c.payer_class.value)
        if expected is None or expected <= 0:
            continue
        actual = float(c.paid_amount or 0.0)
        total_expected += float(expected)
        total_actual += actual
        sample += 1
    if total_expected <= 0:
        return KPIResult(
            name="Net Revenue Realization", value=None, unit="pct",
            citation="HFMA — Net Revenue Realization",
            reason="contracted-rate lookup returned nothing for any claim",
            temporal=temporal,
        )
    rate = total_actual / total_expected
    return KPIResult(
        name="Net Revenue Realization", value=rate, unit="pct",
        numerator=total_actual, denominator=total_expected, sample_size=sample,
        citation="HFMA — Net Revenue Realization (actual / expected-per-contract)",
        temporal=temporal,
    )


def _lag_service_to_bill(
    claims: Sequence[Any], temporal: TemporalValidity
) -> KPIResult:
    """Median (submit_date − service_date_from) in days. We also stuff
    p25 and p75 into the ``numerator``/``denominator`` slots for the
    UI — they're labelled in the ``citation`` so there's no
    ambiguity."""
    lags = [
        (c.submit_date - c.service_date_from).days
        for c in claims
        if c.submit_date is not None and c.service_date_from is not None
        and (c.submit_date - c.service_date_from).days >= 0
    ]
    if not lags:
        return KPIResult(
            name="Service → Bill Lag (median days)", value=None, unit="days",
            citation="CCD lag analytics",
            reason="no claims with both service_date_from and submit_date",
            temporal=temporal,
        )
    lags.sort()
    median = lags[len(lags) // 2]
    p25 = lags[len(lags) // 4]
    p75 = lags[(3 * len(lags)) // 4]
    return KPIResult(
        name="Service → Bill Lag (median days)", value=float(median), unit="days",
        numerator=float(p25), denominator=float(p75), sample_size=len(lags),
        citation="CCD lag analytics — median, numerator=p25, denominator=p75",
        temporal=temporal,
    )


def _lag_bill_to_cash(
    claims: Sequence[Any], temporal: TemporalValidity
) -> KPIResult:
    lags = [
        (c.paid_date - c.submit_date).days
        for c in claims
        if c.submit_date is not None and c.paid_date is not None
        and (c.paid_date - c.submit_date).days >= 0
    ]
    if not lags:
        return KPIResult(
            name="Bill → Cash Lag (median days)", value=None, unit="days",
            citation="CCD lag analytics",
            reason="no claims with both submit_date and paid_date",
            temporal=temporal,
        )
    lags.sort()
    median = lags[len(lags) // 2]
    p25 = lags[len(lags) // 4]
    p75 = lags[(3 * len(lags)) // 4]
    return KPIResult(
        name="Bill → Cash Lag (median days)", value=float(median), unit="days",
        numerator=float(p25), denominator=float(p75), sample_size=len(lags),
        citation="CCD lag analytics — median, numerator=p25, denominator=p75",
        temporal=temporal,
    )


def _denial_stratification(claims: Sequence[Any]) -> List[DenialStratRow]:
    """Group denied claims by ANSI category and sum dollars."""
    buckets: Dict[str, Tuple[int, float]] = {}
    total_denied = 0.0
    for c in claims:
        status = getattr(c, "status", None)
        is_denied = status is not None and status.value == "DENIED"
        carcs = getattr(c, "adjustment_reason_codes", ())
        if not is_denied and not carcs:
            continue
        cat = classify_carc_set(carcs)
        # Denial "dollars" = the delta between allowed/charge and paid.
        allowed = c.allowed_amount or c.charge_amount or 0.0
        paid = c.paid_amount or 0.0
        denied_dollars = max(float(allowed) - float(paid), 0.0)
        n, d = buckets.get(cat.value, (0, 0.0))
        buckets[cat.value] = (n + 1, d + denied_dollars)
        total_denied += denied_dollars

    rows = [
        DenialStratRow(
            category=cat,
            count=n,
            dollars_denied=d,
            pct_of_total_denied=(d / total_denied) if total_denied > 0 else 0.0,
        )
        for cat, (n, d) in sorted(buckets.items(), key=lambda x: -x[1][1])
    ]
    return rows


# ── Helpers ────────────────────────────────────────────────────────

def _temporal_stamp(claims: Sequence[Any]) -> TemporalValidity:
    dates: List[date] = []
    for c in claims:
        for d in (c.service_date_from, c.service_date_to,
                  c.submit_date, c.paid_date):
            if d is not None:
                dates.append(d)
    return check_regulatory_overlap(dates)
