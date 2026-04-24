"""Contract Re-Pricing Engine.

Takes a structured :class:`ContractSchedule` (payer × CPT →
contracted rate, with carve-outs, stop-loss, and withhold
primitives) and re-prices historical claims against it. The output
feeds :class:`~rcm_mc.pe.value_bridge_v2.BridgeAssumptions.payer_revenue_leverage`
so the v2 bridge reads **this deal's** contracted rates instead of
the generic module-level ``_PAYER_REVENUE_LEVERAGE`` defaults.

Why the engine exists:

    The hardcoded payer-leverage table (Commercial 1.00 / MA 0.80 /
    Medicare FFS 0.75 / Managed Gov 0.55 / Medicaid 0.50 / Self-
    Pay 0.40) is a reasonable default but a *bad answer* on any
    specific deal. A target's actual Medicare FFS contract might
    pay 0.82, or 0.68, or 0.95 depending on the DRG mix, the
    wage-index geography, and the specific provider-based
    arrangement. When the analyst has structured contract data,
    the model should use it.

What this module does NOT do:

- Parse PDF payer contracts. Contract-schedule input is structured
  data the analyst uploads or enters. Software doesn't read
  contracts; lawyers do. The dataclass surface is the contract.
- Mutate v2 bridge math. The engine produces a
  ``Dict[PayerClass, float]`` that drops into the existing
  ``BridgeAssumptions.payer_revenue_leverage`` override hook.
- Assume anything about the CCD's completeness. Claims without a
  matching (payer_class, cpt_code) rate fall through to a
  ``no_contract`` reason and contribute to the "unmatched" count;
  they don't corrupt the derived leverage.

Primitive contract terms supported:

- **allowed_amount_usd** — flat fee per unit (RBRVS-style PFS)
- **allowed_pct_of_charge** — percent of billed charge (common on
  carve-outs and out-of-network rates)
- **is_carve_out** — explicitly carved out of the fee schedule;
  pays at the schedule's ``default_carve_out_rate_pct`` of charge
- **withhold_pct** — payer withholds this fraction pending quality
  / utilization settle-up; reduces the observed allowed at
  adjudication time
- **stop_loss_threshold_usd** / **stop_loss_rate_pct_of_charge** —
  inpatient outlier logic: charges above the threshold pay at a
  separate (usually higher) percent-of-charge rate

Out-of-scope primitives deferred to a future session:
- Per-DRG outlier calculations beyond simple stop-loss
- Capitation / PMPM arrangements
- Shared-savings / risk-sharing contracts
- Interim rates (Medicare IPPS pass-through)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


# ── Payer-class mapping (CCD → bridge vocabulary) ───────────────────
#
# The CCD's PayerClass (``rcm_mc.diligence.ingest.ccd.PayerClass``)
# uses partner-facing labels: MEDICARE, MEDICAID, COMMERCIAL, etc.
# The v2 bridge's PayerClass (``rcm_mc.finance.reimbursement_engine.PayerClass``)
# uses a finer vocabulary: MEDICARE_FFS vs MEDICARE_ADVANTAGE,
# MANAGED_GOVERNMENT to cover TRICARE + Medicaid managed care.
#
# The contract re-pricer emits its derived leverage in the BRIDGE
# vocabulary so ``BridgeAssumptions.payer_revenue_leverage`` can
# consume it without translation. When the CCD can't distinguish
# (MEDICARE alone), the default mapping is MEDICARE_FFS — partners
# with an MA-dominant deal should ensure their CCD payer column
# carries "MEDICARE_ADVANTAGE" explicitly rather than bare
# "MEDICARE".
CCD_TO_BRIDGE_PAYER_CLASS: Dict[str, str] = {
    "COMMERCIAL":         "commercial",
    "MEDICARE":           "medicare_ffs",
    "MEDICARE_ADVANTAGE": "medicare_advantage",
    "MEDICAID":           "medicaid",
    "SELF_PAY":           "self_pay",
    "TRICARE":            "managed_government",
    "WORKERS_COMP":       "managed_government",
}


# ── Contract primitives ────────────────────────────────────────────

@dataclass
class ContractRate:
    """One (payer_class, CPT) → allowed-amount rule.

    Exactly one of ``allowed_amount_usd`` / ``allowed_pct_of_charge``
    should be set for a matched contract. When ``is_carve_out=True``,
    both are ignored and the schedule's
    ``default_carve_out_rate_pct`` applies.

    Values are expressed per-unit (per-claim-line). Multi-unit claims
    (e.g. 10 units of a drug) multiply through at re-pricing time.
    """
    payer_class: str       # CCD-side string, e.g. "MEDICARE" (not "medicare_ffs")
    cpt_code: str
    allowed_amount_usd: Optional[float] = None
    allowed_pct_of_charge: Optional[float] = None
    is_carve_out: bool = False
    withhold_pct: float = 0.0            # 0.0 = no withhold; 0.02 = 2% withheld
    stop_loss_threshold_usd: Optional[float] = None
    stop_loss_rate_pct_of_charge: Optional[float] = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.is_carve_out:
            # Carve-outs intentionally leave amount/pct unset; the
            # schedule's default_carve_out_rate_pct applies.
            return
        if (self.allowed_amount_usd is None
                and self.allowed_pct_of_charge is None):
            raise ValueError(
                f"ContractRate for ({self.payer_class}, {self.cpt_code}) must "
                f"set allowed_amount_usd or allowed_pct_of_charge, or be "
                f"marked is_carve_out=True"
            )
        if (self.allowed_amount_usd is not None
                and self.allowed_pct_of_charge is not None):
            raise ValueError(
                f"ContractRate for ({self.payer_class}, {self.cpt_code}) "
                f"cannot set both allowed_amount_usd and "
                f"allowed_pct_of_charge — pick one"
            )
        if not (0.0 <= self.withhold_pct <= 1.0):
            raise ValueError(
                f"withhold_pct must be in [0, 1]; got {self.withhold_pct}"
            )


@dataclass
class ContractSchedule:
    """Collection of :class:`ContractRate` entries + schedule-level
    defaults.

    ``rates`` is keyed by ``(payer_class, cpt_code)`` tuples — both
    strings in the CCD vocabulary. Lookup normalises both sides to
    upper-case so partners can be loose about CSV column casing.
    """
    rates: List[ContractRate] = field(default_factory=list)
    default_carve_out_rate_pct: float = 0.50
    name: str = "schedule"

    def __post_init__(self) -> None:
        # Build a lookup dict for O(1) access.
        self._lookup: Dict[Tuple[str, str], ContractRate] = {}
        for r in self.rates:
            key = (r.payer_class.upper(), str(r.cpt_code).upper())
            self._lookup[key] = r

    def lookup(
        self, payer_class: str, cpt_code: str,
    ) -> Optional[ContractRate]:
        if not payer_class or not cpt_code:
            return None
        key = (str(payer_class).upper(), str(cpt_code).upper())
        return self._lookup.get(key)

    def covered_payer_classes(self) -> List[str]:
        """Distinct CCD-vocabulary payer classes covered by ≥1 rate."""
        return sorted({r.payer_class.upper() for r in self.rates})


# ── Re-pricing result dataclasses ───────────────────────────────────

# Reason codes for per-claim re-pricing. Partner-facing; the UI
# surfaces them as filter chips on the Phase 3 drill-through.
REASON_MATCHED = "matched"
REASON_CARVE_OUT = "carve_out"
REASON_STOP_LOSS_APPLIED = "stop_loss_applied"
REASON_WITHHOLD_APPLIED = "withhold_applied"
REASON_NO_CONTRACT = "no_contract"
REASON_MISSING_DATA = "missing_data"


@dataclass
class RepricingResult:
    """Per-claim re-pricing outcome."""
    claim_id: str
    payer_class_ccd: str            # CCD-vocab string ("MEDICARE")
    payer_class_bridge: str         # bridge-vocab string ("medicare_ffs")
    cpt_code: str
    observed_allowed_usd: float
    repriced_allowed_usd: float
    delta_usd: float                # repriced − observed; + = under-collection
    reason: str                     # one of the REASON_* constants above
    contract_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "payer_class_ccd": self.payer_class_ccd,
            "payer_class_bridge": self.payer_class_bridge,
            "cpt_code": self.cpt_code,
            "observed_allowed_usd": self.observed_allowed_usd,
            "repriced_allowed_usd": self.repriced_allowed_usd,
            "delta_usd": self.delta_usd,
            "reason": self.reason,
            "contract_note": self.contract_note,
        }


@dataclass
class PayerRollUp:
    payer_class_bridge: str
    claim_count: int
    total_observed_allowed_usd: float
    total_repriced_allowed_usd: float
    avg_observed_per_claim: float
    avg_repriced_per_claim: float
    recovery_ratio: float    # observed / repriced, the payer-class's leverage

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_class_bridge": self.payer_class_bridge,
            "claim_count": self.claim_count,
            "total_observed_allowed_usd": self.total_observed_allowed_usd,
            "total_repriced_allowed_usd": self.total_repriced_allowed_usd,
            "avg_observed_per_claim": self.avg_observed_per_claim,
            "avg_repriced_per_claim": self.avg_repriced_per_claim,
            "recovery_ratio": self.recovery_ratio,
        }


@dataclass
class RepricingReport:
    """Aggregate output of ``reprice_claims``. Holds per-claim
    results plus roll-ups ready for the v2 bridge."""
    schedule_name: str
    total_claims: int = 0
    matched_claims: int = 0
    unmatched_claims: int = 0
    total_observed_allowed_usd: float = 0.0
    total_repriced_allowed_usd: float = 0.0
    total_delta_usd: float = 0.0
    by_payer_class: Dict[str, PayerRollUp] = field(default_factory=dict)
    per_claim_results: List[RepricingResult] = field(default_factory=list)

    def derived_payer_leverage(
        self, baseline: str = "commercial",
    ) -> Dict[str, float]:
        """Per-payer leverage normalised to the baseline payer class.

        The v2 bridge's ``_PAYER_REVENUE_LEVERAGE`` sets
        commercial=1.00 and scales others relative to it. This
        function reproduces that contract from live deal data:
        compute each payer's *average contracted rate per claim*,
        then divide every payer by the baseline's average.

        Baseline missing from the schedule → fallback to 1.0 scaling
        (every payer reports its own recovery_ratio; partners can
        still see directional leverage even without a Commercial
        comparator, but the number loses its "dollars per Commercial
        dollar" meaning).
        """
        out: Dict[str, float] = {}
        baseline_ratio: Optional[float] = None
        if baseline in self.by_payer_class:
            rollup = self.by_payer_class[baseline]
            if rollup.avg_repriced_per_claim > 0:
                baseline_ratio = rollup.avg_repriced_per_claim
        for pc_bridge, rollup in self.by_payer_class.items():
            if baseline_ratio and baseline_ratio > 0:
                out[pc_bridge] = (
                    rollup.avg_repriced_per_claim / baseline_ratio
                )
            else:
                out[pc_bridge] = rollup.recovery_ratio
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_name": self.schedule_name,
            "total_claims": self.total_claims,
            "matched_claims": self.matched_claims,
            "unmatched_claims": self.unmatched_claims,
            "total_observed_allowed_usd": self.total_observed_allowed_usd,
            "total_repriced_allowed_usd": self.total_repriced_allowed_usd,
            "total_delta_usd": self.total_delta_usd,
            "by_payer_class": {
                k: v.to_dict() for k, v in self.by_payer_class.items()
            },
            "per_claim_results": [r.to_dict() for r in self.per_claim_results],
            "derived_payer_leverage": self.derived_payer_leverage(),
        }


# ── The actual re-pricer ────────────────────────────────────────────

def reprice_claim(
    claim: Any,
    schedule: ContractSchedule,
) -> RepricingResult:
    """Re-price one :class:`CanonicalClaim` against ``schedule``.

    Returns a :class:`RepricingResult` for every claim including
    unmatched ones. A missing (payer, CPT) combination produces a
    result with ``reason=NO_CONTRACT`` and
    ``repriced_allowed_usd=observed_allowed_usd`` — the bridge can
    filter those out of its leverage computation without skipping
    the claim entirely.
    """
    claim_id = str(getattr(claim, "claim_id", ""))
    pc_obj = getattr(claim, "payer_class", None)
    payer_ccd = (pc_obj.value if hasattr(pc_obj, "value") else str(pc_obj)).upper()
    payer_bridge = CCD_TO_BRIDGE_PAYER_CLASS.get(payer_ccd, "")
    cpt = (getattr(claim, "cpt_code", None) or "").upper()
    observed = float(getattr(claim, "allowed_amount", 0) or 0)
    charge = float(getattr(claim, "charge_amount", 0) or 0)

    if not payer_ccd or not cpt:
        return RepricingResult(
            claim_id=claim_id,
            payer_class_ccd=payer_ccd, payer_class_bridge=payer_bridge,
            cpt_code=cpt,
            observed_allowed_usd=observed,
            repriced_allowed_usd=observed,
            delta_usd=0.0,
            reason=REASON_MISSING_DATA,
        )

    rate = schedule.lookup(payer_ccd, cpt)
    if rate is None:
        return RepricingResult(
            claim_id=claim_id,
            payer_class_ccd=payer_ccd, payer_class_bridge=payer_bridge,
            cpt_code=cpt,
            observed_allowed_usd=observed,
            repriced_allowed_usd=observed,
            delta_usd=0.0,
            reason=REASON_NO_CONTRACT,
        )

    # Carve-out branch: schedule's default carve-out rate × charge.
    if rate.is_carve_out:
        repriced = charge * schedule.default_carve_out_rate_pct
        return _apply_withhold_and_result(
            claim_id=claim_id, payer_ccd=payer_ccd, payer_bridge=payer_bridge,
            cpt=cpt, observed=observed, repriced=repriced,
            withhold_pct=rate.withhold_pct,
            reason=REASON_CARVE_OUT,
            contract_note=rate.note,
        )

    # Stop-loss branch: charge > threshold → outlier rate on the
    # full charge. (A more elaborate inpatient outlier model would
    # apply the stop-loss rate only to the excess, but for the MVP
    # we use a whole-claim outlier rate — matches the way most
    # inpatient contracts actually describe the logic.)
    if (rate.stop_loss_threshold_usd is not None
            and rate.stop_loss_rate_pct_of_charge is not None
            and charge >= rate.stop_loss_threshold_usd):
        repriced = charge * rate.stop_loss_rate_pct_of_charge
        return _apply_withhold_and_result(
            claim_id=claim_id, payer_ccd=payer_ccd, payer_bridge=payer_bridge,
            cpt=cpt, observed=observed, repriced=repriced,
            withhold_pct=rate.withhold_pct,
            reason=REASON_STOP_LOSS_APPLIED,
            contract_note=rate.note,
        )

    # Standard branch: either flat fee or pct-of-charge.
    if rate.allowed_amount_usd is not None:
        repriced = float(rate.allowed_amount_usd)
    else:
        repriced = charge * float(rate.allowed_pct_of_charge or 0.0)

    return _apply_withhold_and_result(
        claim_id=claim_id, payer_ccd=payer_ccd, payer_bridge=payer_bridge,
        cpt=cpt, observed=observed, repriced=repriced,
        withhold_pct=rate.withhold_pct,
        reason=REASON_MATCHED,
        contract_note=rate.note,
    )


def _apply_withhold_and_result(
    *,
    claim_id: str,
    payer_ccd: str,
    payer_bridge: str,
    cpt: str,
    observed: float,
    repriced: float,
    withhold_pct: float,
    reason: str,
    contract_note: str = "",
) -> RepricingResult:
    """Apply the contract's withhold to the repriced amount.

    A 2% withhold means the payer holds back 2% of the allowed at
    adjudication, subject to quality / utilization settlement. We
    reduce the repriced amount by that fraction so the re-pricer's
    output matches what actually lands on the 835 remittance.
    """
    if withhold_pct > 0:
        repriced *= (1.0 - withhold_pct)
        # Escalate the reason when withhold materially changes the
        # answer; preserves the "matched" label when withhold is 0.
        if reason == REASON_MATCHED:
            reason = REASON_WITHHOLD_APPLIED
    delta = repriced - observed
    return RepricingResult(
        claim_id=claim_id,
        payer_class_ccd=payer_ccd, payer_class_bridge=payer_bridge,
        cpt_code=cpt,
        observed_allowed_usd=observed,
        repriced_allowed_usd=repriced,
        delta_usd=delta,
        reason=reason,
        contract_note=contract_note,
    )


# ── Driver ─────────────────────────────────────────────────────────

def reprice_claims(
    claims: Sequence[Any],
    schedule: ContractSchedule,
) -> RepricingReport:
    """Re-price every claim + roll up per-payer-class."""
    report = RepricingReport(schedule_name=schedule.name)
    # Accumulators per bridge-side payer class.
    pc_accum: Dict[str, Dict[str, float]] = {}

    for claim in claims:
        result = reprice_claim(claim, schedule)
        report.per_claim_results.append(result)
        report.total_claims += 1
        report.total_observed_allowed_usd += result.observed_allowed_usd
        report.total_repriced_allowed_usd += result.repriced_allowed_usd
        report.total_delta_usd += result.delta_usd
        if result.reason in (REASON_NO_CONTRACT, REASON_MISSING_DATA):
            report.unmatched_claims += 1
            # Unmatched claims do NOT contribute to the per-payer-
            # class leverage roll-up — they'd bias the number with
            # "observed = repriced" tautology. Count them separately.
            continue
        report.matched_claims += 1
        pc = result.payer_class_bridge or "unknown"
        acc = pc_accum.setdefault(pc, {
            "claim_count": 0,
            "observed": 0.0, "repriced": 0.0,
        })
        acc["claim_count"] += 1
        acc["observed"] += result.observed_allowed_usd
        acc["repriced"] += result.repriced_allowed_usd

    for pc, acc in pc_accum.items():
        n = int(acc["claim_count"])
        obs = acc["observed"]
        rep = acc["repriced"]
        report.by_payer_class[pc] = PayerRollUp(
            payer_class_bridge=pc,
            claim_count=n,
            total_observed_allowed_usd=obs,
            total_repriced_allowed_usd=rep,
            avg_observed_per_claim=(obs / n) if n else 0.0,
            avg_repriced_per_claim=(rep / n) if n else 0.0,
            recovery_ratio=(obs / rep) if rep > 0 else 1.0,
        )
    return report


# ── v2 bridge helper ───────────────────────────────────────────────

def payer_leverage_for_bridge(
    report: RepricingReport,
    *,
    baseline: str = "commercial",
) -> Dict[str, float]:
    """One-liner callers use to feed the v2 bridge:

        from rcm_mc.pe.value_bridge_v2 import BridgeAssumptions
        rep = reprice_claims(ccd.claims, schedule)
        assumptions = BridgeAssumptions(
            payer_revenue_leverage=payer_leverage_for_bridge(rep),
            ...
        )

    The output key set matches the v2 bridge's PayerClass vocabulary
    (``commercial`` / ``medicare_ffs`` / ``medicare_advantage`` /
    ``medicaid`` / ``self_pay`` / ``managed_government``) so
    ``BridgeAssumptions.payer_revenue_leverage`` can consume it
    directly without translation.
    """
    return report.derived_payer_leverage(baseline=baseline)
