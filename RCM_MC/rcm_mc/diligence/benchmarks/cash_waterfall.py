"""Cash Waterfall / Quality of Revenue output.

Walks every claim from gross charges → contractual adjustments →
front-end leakage → initial denials (net of appeals) → bad debt →
realized cash, cohorted by date-of-service month and optionally
sliced by payer class. The output is the industry-standard QoR
report a diligence team shows a CFO to defend the revenue number.

Why this exists:

    KPI summaries (Days in A/R, First-Pass Denial Rate) tell you
    "how" the cycle performs; they don't tell you "where the money
    goes." A $1.2B gross-charge practice might report $600M in net
    revenue; if the waterfall shows only $540M walks through the
    claims-side cascade, that $60M gap is a quality-of-revenue
    concern worth a partner question — independent of whether the
    management accruals are defensible.

    This module computes the claims-side view. It does NOT try to
    reconcile to the general ledger or replace management's books.
    The output is the divergence itself; interpretation is the
    analyst's job.

Censoring (spec §non-goals / honor gauntlet):

    A cohort whose age at ``as_of_date`` is less than
    ``realization_window_days`` (default 120) returns
    ``status=INSUFFICIENT_DATA``. We never estimate. Never
    interpolate. The partner sees "in-flight" instead of a number
    that is 30 days short of reality.

Provenance:

    Every :class:`WaterfallStep` carries the ``claim_ids`` that
    contributed, so the UI drill-through resolves back to canonical
    claim rows + (via the CCD transformation log) to source-file
    rows. No gaps.

Non-goals restated:
    - Not a cash-to-accrual engine; not a GL replacement.
    - Does not parse payer contracts. Contract re-pricing is a
      separate module (session N+2 per the roadmap).
    - Does not infer management-reported revenue. If the caller
      supplies it we compute divergence; otherwise we don't flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from ._ansi_codes import DenialCategory, classify_carc_set
from .cohort_liquidation import CohortStatus, _cohort_key, _cohort_start_date


# ── Constants ────────────────────────────────────────────────────────

DEFAULT_REALIZATION_WINDOW_DAYS = 120
DEFAULT_BAD_DEBT_AGE_DAYS = 180        # claims open >180d on net-collectable

# QoR divergence thresholds — the published healthcare-QoR standard
# from VMG Health and A&M methodology: <2% is noise, 2-5% warrants
# a closer look, >5% is a material finding a partner quotes.
QOR_THRESHOLD_IMMATERIAL = 0.02
QOR_THRESHOLD_WATCH = 0.05
# Legacy alias used by earlier callers; matches the WATCH threshold
# (anything ≥ 5% flags).
DEFAULT_QOR_DIVERGENCE_THRESHOLD = QOR_THRESHOLD_WATCH


class DivergenceStatus(str, Enum):
    """Status banding for waterfall-computed accrual revenue vs
    management-reported accrual revenue. Thresholds follow the
    VMG / A&M QoR convention (<2% / 2-5% / >5%)."""
    IMMATERIAL = "IMMATERIAL"   # |divergence| < 2%
    WATCH      = "WATCH"        # 2% ≤ |divergence| < 5%
    CRITICAL   = "CRITICAL"     # |divergence| ≥ 5%
    UNKNOWN    = "UNKNOWN"      # no management number supplied


def classify_divergence(divergence_pct: Optional[float]) -> DivergenceStatus:
    """Band a divergence percentage into IMMATERIAL / WATCH / CRITICAL.

    ``divergence_pct`` is a signed fraction (e.g. -0.07 means
    waterfall is 7% below management). ``None`` → UNKNOWN so the
    summary card can render "not supplied" rather than a fake tier.
    """
    if divergence_pct is None:
        return DivergenceStatus.UNKNOWN
    abs_pct = abs(float(divergence_pct))
    if abs_pct < QOR_THRESHOLD_IMMATERIAL:
        return DivergenceStatus.IMMATERIAL
    if abs_pct < QOR_THRESHOLD_WATCH:
        return DivergenceStatus.WATCH
    return DivergenceStatus.CRITICAL

# Ordered waterfall step names. The order matters — the running
# balance walks down in exactly this sequence.
WATERFALL_STEPS: Tuple[str, ...] = (
    "gross_charges",
    "contractual_adjustments",
    "front_end_leakage",
    "initial_denials_gross",
    "appeals_recovered",
    "bad_debt",
    "realized_cash",
)


# ── Result dataclasses ──────────────────────────────────────────────

@dataclass
class WaterfallStep:
    """One row in the waterfall cascade for one cohort.

    ``amount_usd`` is always a *non-negative* dollar figure. Whether
    it's added to or subtracted from the running balance is the
    step's semantic (``gross_charges`` is the starting balance;
    ``appeals_recovered`` is an ADD-BACK; everything else
    subtracts).

    ``running_balance_usd`` is the balance *after* this step applies,
    so the last step's running_balance is the realized cash.
    """
    name: str
    label: str
    amount_usd: float
    running_balance_usd: float
    claim_count: int
    claim_ids: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "amount_usd": self.amount_usd,
            "running_balance_usd": self.running_balance_usd,
            "claim_count": self.claim_count,
            "claim_ids": list(self.claim_ids),
        }


@dataclass
class WaterfallCohort:
    """One (cohort_month, payer_class) waterfall cascade."""
    cohort_month: str
    payer_class: str                       # "ALL" for the roll-up
    status: CohortStatus
    steps: List[WaterfallStep] = field(default_factory=list)
    claim_count: int = 0

    # Partner-facing summary fields.
    gross_charges_usd: float = 0.0
    realized_cash_usd: float = 0.0
    realization_rate: Optional[float] = None
    # Waterfall-computed accrual revenue =
    #   gross − contractuals − final_denials − bad_debt
    # where final_denials = initial_denials_gross − appeals_recovered.
    # Omits front-end leakage because accrual accounting reserves
    # eligibility-denied claims out of reported revenue anyway.
    accrual_revenue_usd: Optional[float] = None

    # QoR divergence vs management-reported accrual revenue.
    management_reported_revenue_usd: Optional[float] = None
    qor_divergence_usd: Optional[float] = None
    qor_divergence_pct: Optional[float] = None
    qor_flag: bool = False
    divergence_status: str = DivergenceStatus.UNKNOWN.value

    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cohort_month": self.cohort_month,
            "payer_class": self.payer_class,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "claim_count": self.claim_count,
            "gross_charges_usd": self.gross_charges_usd,
            "realized_cash_usd": self.realized_cash_usd,
            "realization_rate": self.realization_rate,
            "accrual_revenue_usd": self.accrual_revenue_usd,
            "management_reported_revenue_usd": self.management_reported_revenue_usd,
            "qor_divergence_usd": self.qor_divergence_usd,
            "qor_divergence_pct": self.qor_divergence_pct,
            "qor_flag": self.qor_flag,
            "divergence_status": self.divergence_status,
            "reason": self.reason,
        }


@dataclass
class CashWaterfallReport:
    """One CCD × as_of_date → waterfall report."""
    as_of_date: date
    realization_window_days: int = DEFAULT_REALIZATION_WINDOW_DAYS
    cohorts_all_payers: List[WaterfallCohort] = field(default_factory=list)
    cohorts_by_payer_class: Dict[str, List[WaterfallCohort]] = \
        field(default_factory=dict)

    # Top-line roll-up across all MATURE cohorts, all payers.
    total_gross_charges_usd: float = 0.0
    total_realized_cash_usd: float = 0.0
    total_realization_rate: Optional[float] = None
    total_accrual_revenue_usd: Optional[float] = None
    total_management_revenue_usd: Optional[float] = None
    total_qor_divergence_usd: Optional[float] = None
    total_qor_divergence_pct: Optional[float] = None
    total_qor_flag: bool = False
    total_divergence_status: str = DivergenceStatus.UNKNOWN.value

    def mature_cohorts(self) -> List[WaterfallCohort]:
        return [c for c in self.cohorts_all_payers
                if c.status == CohortStatus.MATURE]

    def censored_cohorts(self) -> List[WaterfallCohort]:
        return [c for c in self.cohorts_all_payers
                if c.status == CohortStatus.INSUFFICIENT_DATA]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "as_of_date": self.as_of_date.isoformat(),
            "realization_window_days": self.realization_window_days,
            "cohorts_all_payers": [c.to_dict() for c in self.cohorts_all_payers],
            "cohorts_by_payer_class": {
                k: [c.to_dict() for c in v]
                for k, v in self.cohorts_by_payer_class.items()
            },
            "total_gross_charges_usd": self.total_gross_charges_usd,
            "total_realized_cash_usd": self.total_realized_cash_usd,
            "total_realization_rate": self.total_realization_rate,
            "total_accrual_revenue_usd": self.total_accrual_revenue_usd,
            "total_management_revenue_usd": self.total_management_revenue_usd,
            "total_qor_divergence_usd": self.total_qor_divergence_usd,
            "total_qor_divergence_pct": self.total_qor_divergence_pct,
            "total_qor_flag": self.total_qor_flag,
            "total_divergence_status": self.total_divergence_status,
        }


# ── Public API ──────────────────────────────────────────────────────

def compute_cash_waterfall(
    claims: Sequence[Any],
    *,
    as_of_date: date,
    realization_window_days: int = DEFAULT_REALIZATION_WINDOW_DAYS,
    bad_debt_age_days: int = DEFAULT_BAD_DEBT_AGE_DAYS,
    management_reported_revenue_by_cohort_month: Optional[Mapping[str, float]] = None,
    qor_divergence_threshold: float = DEFAULT_QOR_DIVERGENCE_THRESHOLD,
    cohort_granularity: str = "month",
    by_payer_class: bool = True,
) -> CashWaterfallReport:
    """Cohort every claim by DOS and walk the gross-to-cash cascade.

    Cohorts whose age at ``as_of_date`` is less than
    ``realization_window_days`` come back with
    ``status=INSUFFICIENT_DATA`` and no computed numbers — the
    spec's censoring invariant.

    ``management_reported_revenue_by_cohort_month`` is an optional
    ``{cohort_month: usd}`` map from the analyst's management
    accruals file. When present, each cohort gets a QoR divergence
    % and flag; when absent, divergence fields stay ``None``.
    """
    mgmt = management_reported_revenue_by_cohort_month or {}

    # Pass 1: build all-payer cohorts.
    by_cohort_all: Dict[str, List[Any]] = {}
    for c in claims:
        if c.service_date_from is None:
            continue
        key = _cohort_key(c.service_date_from, cohort_granularity)
        by_cohort_all.setdefault(key, []).append(c)

    cohorts_all: List[WaterfallCohort] = []
    for key in sorted(by_cohort_all.keys()):
        cohort_claims = by_cohort_all[key]
        cohort_start = _cohort_start_date(key, cohort_granularity)
        age_days = (as_of_date - cohort_start).days
        cohort = _compute_cohort_waterfall(
            cohort_month=key,
            payer_class="ALL",
            cohort_claims=cohort_claims,
            cohort_age_days=age_days,
            as_of_date=as_of_date,
            realization_window_days=realization_window_days,
            bad_debt_age_days=bad_debt_age_days,
        )
        # Attach QoR divergence when a management number is available.
        mgmt_revenue = mgmt.get(key)
        if mgmt_revenue is not None and cohort.status == CohortStatus.MATURE:
            _attach_qor_divergence(cohort, mgmt_revenue, qor_divergence_threshold)
        cohorts_all.append(cohort)

    # Pass 2: per-payer-class slices.
    cohorts_by_class: Dict[str, List[WaterfallCohort]] = {}
    if by_payer_class:
        per_class_buckets: Dict[str, Dict[str, List[Any]]] = {}
        for c in claims:
            if c.service_date_from is None:
                continue
            pc = _payer_class_label(c)
            key = _cohort_key(c.service_date_from, cohort_granularity)
            per_class_buckets.setdefault(pc, {}).setdefault(key, []).append(c)
        for pc, ck_map in per_class_buckets.items():
            out: List[WaterfallCohort] = []
            for key in sorted(ck_map.keys()):
                cohort_claims = ck_map[key]
                cohort_start = _cohort_start_date(key, cohort_granularity)
                age_days = (as_of_date - cohort_start).days
                cohort = _compute_cohort_waterfall(
                    cohort_month=key,
                    payer_class=pc,
                    cohort_claims=cohort_claims,
                    cohort_age_days=age_days,
                    as_of_date=as_of_date,
                    realization_window_days=realization_window_days,
                    bad_debt_age_days=bad_debt_age_days,
                )
                out.append(cohort)
            cohorts_by_class[pc] = out

    report = CashWaterfallReport(
        as_of_date=as_of_date,
        realization_window_days=realization_window_days,
        cohorts_all_payers=cohorts_all,
        cohorts_by_payer_class=cohorts_by_class,
    )
    _roll_up_totals(report, mgmt, qor_divergence_threshold)
    return report


# ── Per-cohort computation ──────────────────────────────────────────

def _compute_cohort_waterfall(
    *,
    cohort_month: str,
    payer_class: str,
    cohort_claims: Sequence[Any],
    cohort_age_days: int,
    as_of_date: date,
    realization_window_days: int,
    bad_debt_age_days: int,
) -> WaterfallCohort:
    """Build the waterfall cascade for one cohort."""
    if cohort_age_days < realization_window_days:
        return WaterfallCohort(
            cohort_month=cohort_month,
            payer_class=payer_class,
            status=CohortStatus.INSUFFICIENT_DATA,
            claim_count=len(cohort_claims),
            reason=(
                f"cohort age {cohort_age_days}d < realization window "
                f"{realization_window_days}d — in-flight, insufficient "
                f"data for a cash waterfall"
            ),
        )
    if not cohort_claims:
        return WaterfallCohort(
            cohort_month=cohort_month, payer_class=payer_class,
            status=CohortStatus.EMPTY,
            reason="no claims in this cohort",
        )

    # --- Step amounts + provenance claim-id lists ------------------

    gross_charges = 0.0
    gross_ids: List[str] = []

    contractual_amt = 0.0
    contractual_ids: List[str] = []

    front_end_amt = 0.0
    front_end_ids: List[str] = []

    initial_denials_amt = 0.0
    initial_denials_ids: List[str] = []

    appeals_recovered_amt = 0.0
    appeals_recovered_ids: List[str] = []

    bad_debt_amt = 0.0
    bad_debt_ids: List[str] = []

    realized_amt = 0.0
    realized_ids: List[str] = []

    for c in cohort_claims:
        charge = float(c.charge_amount or 0.0)
        allowed = float(c.allowed_amount or 0.0)
        paid = float(c.paid_amount or 0.0)
        status = getattr(c, "status", None)
        status_val = status.value if status is not None else ""
        cid = str(c.claim_id or "")

        # Gross charges.
        if charge > 0:
            gross_charges += charge
            gross_ids.append(cid)

        # Contractual adjustments = charge - allowed when both are
        # present. Negative deltas (allowed > charge, rare) zero out.
        if charge > 0 and allowed > 0 and charge > allowed:
            contractual_amt += (charge - allowed)
            contractual_ids.append(cid)

        # Denial categorisation. A claim is a denial if its status is
        # DENIED or it has CARCs in a denial category.
        carcs = getattr(c, "adjustment_reason_codes", ()) or ()
        carc_cat = classify_carc_set(carcs) if carcs else DenialCategory.UNCLASSIFIED

        is_denied = status_val in ("DENIED", "WRITTEN_OFF")
        is_recovered = (status_val == "PAID" and bool(carcs) and carc_cat in (
            DenialCategory.CLINICAL, DenialCategory.CODING,
            DenialCategory.PAYER_BEHAVIOR,
        ))

        if is_denied and carc_cat == DenialCategory.FRONT_END:
            # Front-end leakage uses ALLOWED as the loss basis — the
            # contractual adjustment was already booked upstream;
            # what didn't materialize is the allowed amount.
            front_end_amt += allowed if allowed > 0 else charge
            front_end_ids.append(cid)
        elif is_denied:
            # Everything else denied rolls into initial_denials.
            initial_denials_amt += allowed if allowed > 0 else charge
            initial_denials_ids.append(cid)
        elif is_recovered:
            # Paid but originally denied → appeal success. Adds back
            # to the collectable side of the cascade.
            appeals_recovered_amt += paid
            appeals_recovered_ids.append(cid)

        # Bad debt: open balance on a claim that's MATURE-aged and
        # status is not DENIED (denied went to a prior bucket).
        if not is_denied and allowed > 0 and paid < allowed:
            if c.service_date_from is not None:
                age = (as_of_date - c.service_date_from).days
                if age >= bad_debt_age_days:
                    bad_debt_amt += (allowed - paid)
                    bad_debt_ids.append(cid)

        # Realized cash = actual paid_amount, across all claims. Even
        # on appeals-recovered claims the paid amount is collected
        # cash — no double-count, because appeals_recovered is
        # bookkeeping for the cascade narrative, not a separate
        # money movement.
        if paid > 0:
            realized_amt += paid
            realized_ids.append(cid)

    # --- Build the cascade (running balance walks down) ------------

    steps: List[WaterfallStep] = []
    running = gross_charges
    steps.append(WaterfallStep(
        name="gross_charges", label="Gross Charges",
        amount_usd=gross_charges, running_balance_usd=running,
        claim_count=len(gross_ids),
        claim_ids=tuple(gross_ids),
    ))

    running -= contractual_amt
    steps.append(WaterfallStep(
        name="contractual_adjustments", label="Contractual Adjustments",
        amount_usd=contractual_amt, running_balance_usd=running,
        claim_count=len(contractual_ids),
        claim_ids=tuple(contractual_ids),
    ))

    running -= front_end_amt
    steps.append(WaterfallStep(
        name="front_end_leakage", label="Front-End Leakage",
        amount_usd=front_end_amt, running_balance_usd=running,
        claim_count=len(front_end_ids),
        claim_ids=tuple(front_end_ids),
    ))

    running -= initial_denials_amt
    steps.append(WaterfallStep(
        name="initial_denials_gross", label="Initial Denials (gross)",
        amount_usd=initial_denials_amt, running_balance_usd=running,
        claim_count=len(initial_denials_ids),
        claim_ids=tuple(initial_denials_ids),
    ))

    # Appeals recovered ADDS BACK to the cascade.
    running += appeals_recovered_amt
    steps.append(WaterfallStep(
        name="appeals_recovered", label="Appeals Recovered (add-back)",
        amount_usd=appeals_recovered_amt, running_balance_usd=running,
        claim_count=len(appeals_recovered_ids),
        claim_ids=tuple(appeals_recovered_ids),
    ))

    running -= bad_debt_amt
    steps.append(WaterfallStep(
        name="bad_debt", label="Bad Debt",
        amount_usd=bad_debt_amt, running_balance_usd=running,
        claim_count=len(bad_debt_ids),
        claim_ids=tuple(bad_debt_ids),
    ))

    # The realized_cash step is NOT a further subtraction — it's the
    # terminal label. ``amount_usd`` is the actual paid dollars;
    # ``running_balance_usd`` is the SAME number (the cascade has
    # walked down to this figure). If gross - subtractions ≈
    # realized_amt, the cascade closes; any gap is "unexplained
    # realization delta" and gets surfaced as the reconciliation
    # flag later in the session.
    steps.append(WaterfallStep(
        name="realized_cash", label="Realized Cash",
        amount_usd=realized_amt, running_balance_usd=realized_amt,
        claim_count=len(realized_ids),
        claim_ids=tuple(realized_ids),
    ))

    # Accrual revenue per the VMG/A&M QoR formula:
    #   gross − contractuals − (initial_denials − appeals_recovered) − bad_debt
    # This is the number management reports as earned revenue.
    # Front-end leakage is NOT subtracted here — accrual accounting
    # typically reserves eligibility-denied claims upstream, so
    # subtracting them would double-count the reserve.
    final_denials_net = max(initial_denials_amt - appeals_recovered_amt, 0.0)
    accrual_revenue = gross_charges - contractual_amt - final_denials_net - bad_debt_amt

    cohort = WaterfallCohort(
        cohort_month=cohort_month,
        payer_class=payer_class,
        status=CohortStatus.MATURE,
        steps=steps,
        claim_count=len(cohort_claims),
        gross_charges_usd=gross_charges,
        realized_cash_usd=realized_amt,
        realization_rate=(realized_amt / gross_charges) if gross_charges > 0 else None,
        accrual_revenue_usd=accrual_revenue,
    )
    return cohort


# ── QoR divergence ──────────────────────────────────────────────────

def _attach_qor_divergence(
    cohort: WaterfallCohort, mgmt_revenue: float, threshold: float,
) -> None:
    """Compare waterfall-computed ACCRUAL revenue to management-
    reported accrual revenue. Sets ``divergence_status`` banding
    (IMMATERIAL / WATCH / CRITICAL). A CRITICAL divergence means
    management's number disagrees with the claims-side reconstruction
    by more than the published QoR threshold — the headline finding
    a partner quotes.

    Does nothing on EMPTY / INSUFFICIENT_DATA cohorts (caller
    checks). The comparison is against ``accrual_revenue_usd``, not
    ``realized_cash_usd``, because accrual is the revenue
    recognition line — which is what management's books report.
    """
    cohort.management_reported_revenue_usd = float(mgmt_revenue)
    base = (cohort.accrual_revenue_usd
            if cohort.accrual_revenue_usd is not None
            else cohort.realized_cash_usd)
    delta = float(base) - float(mgmt_revenue)
    cohort.qor_divergence_usd = delta
    if mgmt_revenue:
        cohort.qor_divergence_pct = delta / float(mgmt_revenue)
        cohort.qor_flag = abs(cohort.qor_divergence_pct) >= threshold
        cohort.divergence_status = classify_divergence(
            cohort.qor_divergence_pct
        ).value
    else:
        cohort.qor_divergence_pct = None
        cohort.qor_flag = False
        cohort.divergence_status = DivergenceStatus.UNKNOWN.value


def _roll_up_totals(
    report: CashWaterfallReport,
    mgmt: Mapping[str, float],
    qor_threshold: float,
) -> None:
    """Aggregate across MATURE cohorts (all payers) for the top-line.

    The total divergence is computed against total ACCRUAL revenue
    (sum of per-cohort accrual_revenue_usd) vs management's total
    reported revenue — not against realized cash. This matches the
    per-cohort contract and produces the headline divergence-status
    band for the summary card at the top of the waterfall section.
    """
    mature = report.mature_cohorts()
    if not mature:
        return
    total_gross = sum(c.gross_charges_usd for c in mature)
    total_cash = sum(c.realized_cash_usd for c in mature)
    total_accrual = sum(
        (c.accrual_revenue_usd or 0.0) for c in mature
    )
    report.total_gross_charges_usd = total_gross
    report.total_realized_cash_usd = total_cash
    report.total_realization_rate = (total_cash / total_gross) if total_gross > 0 else None
    report.total_accrual_revenue_usd = total_accrual

    total_mgmt = 0.0
    have_any_mgmt = False
    for c in mature:
        m = mgmt.get(c.cohort_month)
        if m is not None:
            total_mgmt += float(m)
            have_any_mgmt = True
    if have_any_mgmt:
        report.total_management_revenue_usd = total_mgmt
        delta = total_accrual - total_mgmt
        report.total_qor_divergence_usd = delta
        if total_mgmt:
            report.total_qor_divergence_pct = delta / total_mgmt
            report.total_qor_flag = abs(report.total_qor_divergence_pct) >= qor_threshold
            report.total_divergence_status = classify_divergence(
                report.total_qor_divergence_pct
            ).value


# ── Helpers ─────────────────────────────────────────────────────────

def _payer_class_label(claim: Any) -> str:
    pc = getattr(claim, "payer_class", None)
    if pc is None:
        return "UNKNOWN"
    return pc.value if hasattr(pc, "value") else str(pc)
