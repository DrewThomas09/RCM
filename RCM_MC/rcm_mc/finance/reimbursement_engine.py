"""Reimbursement + revenue-realization engine.

The core insight this module encodes: **the same operational metric has
a different economic meaning depending on how the hospital gets paid.**
A 1% denial rate reduction is worth more on a DRG-prospective payment
hospital than on a capitated one. A 10-day AR improvement is pure
working-capital win under fee-for-service; under capitation it's
largely cosmetic. The old bridge ignored all of this and applied
uniform multipliers; this module makes that economic structure
explicit.

Design principles:
- **Explicit mechanism tables over opaque functions.** Every
  reimbursement method has one :class:`MethodSensitivity` entry that
  encodes its sensitivity to each RCM lever category on a 0-1 scale
  plus timing + gain-pathway metadata. Analysts can read the table
  and defend every cell in IC.
- **Transparent inference + provenance.** Whenever we fill in a gap
  (method distribution, contractual discount, cash-timing) we tag
  the field in the profile's ``provenance`` dict so downstream
  renderers show ``inferred_from_profile`` vs ``observed``.
- **Graceful degradation.** Missing inputs never raise. The profile
  comes back with whatever we could compute, tagged appropriately.
- **No hard-coded universal multipliers.** Every coefficient is
  conditional on the hospital's reimbursement exposure.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────

class ReimbursementMethod(str, Enum):
    """Reimbursement archetype a claim is paid under.

    Deliberately coarser than the 100+ specific contract types that
    exist in reality — partners can map any real contract to one of
    these for IC-level analysis.
    """
    FEE_FOR_SERVICE = "fee_for_service"
    DRG_PROSPECTIVE = "drg_prospective_payment"
    OUTPATIENT_APC = "outpatient_apc_like"
    PER_DIEM = "per_diem"
    CAPITATION = "capitation"
    CASE_RATE_BUNDLE = "case_rate_or_bundle"
    VALUE_BASED = "value_based_quality_linked"
    COST_BASED = "cost_based_reimbursement"


class PayerClass(str, Enum):
    COMMERCIAL = "commercial"
    MEDICARE_FFS = "medicare_ffs"
    MEDICARE_ADVANTAGE = "medicare_advantage"
    MEDICAID = "medicaid"
    SELF_PAY = "self_pay"
    MANAGED_GOVERNMENT = "managed_government"   # Medicaid managed care, TRICARE, etc.


class ProvenanceTag(str, Enum):
    """How a field landed at its value. Every inferred reimbursement
    assumption is tagged so renderers can show the origin.
    """
    OBSERVED = "observed"
    INFERRED_FROM_PROFILE = "inferred_from_profile"
    BENCHMARK_DEFAULT = "benchmark_default"
    ANALYST_OVERRIDE = "analyst_override"
    CALCULATED = "calculated"


# ── Core data types ─────────────────────────────────────────────────

@dataclass
class MethodSensitivity:
    """Per-method sensitivity table.

    Every field in the 0.0-1.0 range expresses "how much does this
    sensitivity driver move revenue under this reimbursement method."
    ``1.0`` = fully load-bearing; ``0.0`` = irrelevant.
    """
    primary_revenue_driver: str
    coding_cdi_acuity: float = 0.5
    auth_denials: float = 0.5
    eligibility_denials: float = 0.5
    medical_necessity: float = 0.5
    timely_filing: float = 0.5
    utilization_volume: float = 0.5
    site_of_care_migration: float = 0.5
    los_discharge_timing: float = 0.5
    #: Typical cash-realization DSO under this method (in days).
    cash_timing_days: int = 45
    #: Probability a paid claim gets adjusted or clawed back post-pay.
    clawback_likelihood: float = 0.15
    #: Where improvement gains surface: revenue / working_capital /
    #: cost_avoidance / mixed.
    gain_pathway: str = "revenue"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PayerClassProfile:
    """One payer class's slice of a hospital's revenue."""
    payer_class: PayerClass
    revenue_share: float
    #: Inner distribution across reimbursement methods. Sums to 1.0.
    method_distribution: Dict[ReimbursementMethod, float] = field(default_factory=dict)
    collection_difficulty: float = 0.5
    avg_contractual_discount: float = 0.0
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_class": self.payer_class.value,
            "revenue_share": float(self.revenue_share),
            "method_distribution": {
                k.value: float(v) for k, v in self.method_distribution.items()
            },
            "collection_difficulty": float(self.collection_difficulty),
            "avg_contractual_discount": float(self.avg_contractual_discount),
            "provenance": dict(self.provenance),
        }


@dataclass
class ReimbursementProfile:
    """Hospital-level view of how revenue flows in.

    Distinct from :class:`rcm_mc.domain.econ_ontology.ReimbursementProfile`
    (which describes *metric sensitivity* across regimes). This type
    describes a single hospital's *revenue exposure* across regimes.
    """
    payer_classes: Dict[PayerClass, PayerClassProfile] = field(default_factory=dict)
    #: Revenue-weighted method exposure aggregated across payers.
    #: Sums to 1.0 when payer shares sum to 1.0.
    method_weights: Dict[ReimbursementMethod, float] = field(default_factory=dict)
    inpatient_outpatient_mix: Optional[Dict[str, float]] = None
    notes: List[str] = field(default_factory=list)
    provenance: Dict[str, str] = field(default_factory=dict)

    def dominant_method(self) -> Optional[ReimbursementMethod]:
        if not self.method_weights:
            return None
        return max(self.method_weights.items(), key=lambda t: t[1])[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_classes": {
                k.value: v.to_dict() for k, v in self.payer_classes.items()
            },
            "method_weights": {
                k.value: float(v) for k, v in self.method_weights.items()
            },
            "inpatient_outpatient_mix": (
                dict(self.inpatient_outpatient_mix)
                if self.inpatient_outpatient_mix else None
            ),
            "notes": list(self.notes),
            "provenance": dict(self.provenance),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReimbursementProfile":
        d = d or {}
        payer_classes: Dict[PayerClass, PayerClassProfile] = {}
        for k, v in (d.get("payer_classes") or {}).items():
            try:
                pc = PayerClass(k)
            except ValueError:
                continue
            v = v or {}
            md: Dict[ReimbursementMethod, float] = {}
            for mk, mv in (v.get("method_distribution") or {}).items():
                try:
                    md[ReimbursementMethod(mk)] = float(mv)
                except (ValueError, TypeError):
                    continue
            payer_classes[pc] = PayerClassProfile(
                payer_class=pc,
                revenue_share=float(v.get("revenue_share") or 0.0),
                method_distribution=md,
                collection_difficulty=float(v.get("collection_difficulty") or 0.5),
                avg_contractual_discount=float(v.get("avg_contractual_discount") or 0.0),
                provenance=dict(v.get("provenance") or {}),
            )
        mw: Dict[ReimbursementMethod, float] = {}
        for k, v in (d.get("method_weights") or {}).items():
            try:
                mw[ReimbursementMethod(k)] = float(v)
            except (ValueError, TypeError):
                continue
        return cls(
            payer_classes=payer_classes,
            method_weights=mw,
            inpatient_outpatient_mix=(d.get("inpatient_outpatient_mix")
                                       if d.get("inpatient_outpatient_mix") else None),
            notes=list(d.get("notes") or []),
            provenance=dict(d.get("provenance") or {}),
        )


@dataclass
class ContractSensitivity:
    """One (method, payer_class) cell explaining how contract terms
    move a specific metric. Used by per-metric explain outputs."""
    method: ReimbursementMethod
    payer_class: PayerClass
    sensitivity_score: float
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method.value,
            "payer_class": self.payer_class.value,
            "sensitivity_score": float(self.sensitivity_score),
            "explanation": self.explanation,
        }


@dataclass
class RevenueAtRiskBreakdown:
    category: str
    dollar_amount: float
    share_of_gross: float
    #: Optional label for the stage (maps to RevenueRealizationPath fields).
    stage: str = ""
    provenance_tag: str = "calculated"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RevenueRealizationPath:
    """Decomposition from gross charges to final realized cash.

    Every field is an absolute dollar amount (leakages are non-negative
    — subtract them from the prior line). ``final_realized_cash`` is
    the sum of all the positive paths left standing after leakages.
    """
    gross_charges: float = 0.0
    contractual_adjustments: float = 0.0
    preventable_front_end_leakage: float = 0.0
    coding_documentation_leakage: float = 0.0
    initial_denial_leakage: float = 0.0
    final_denial_leakage: float = 0.0
    collectible_net_revenue: float = 0.0
    timing_drag: float = 0.0
    bad_debt_leakage: float = 0.0
    final_realized_cash: float = 0.0
    breakdowns: List[RevenueAtRiskBreakdown] = field(default_factory=list)
    assumptions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gross_charges": float(self.gross_charges),
            "contractual_adjustments": float(self.contractual_adjustments),
            "preventable_front_end_leakage": float(self.preventable_front_end_leakage),
            "coding_documentation_leakage": float(self.coding_documentation_leakage),
            "initial_denial_leakage": float(self.initial_denial_leakage),
            "final_denial_leakage": float(self.final_denial_leakage),
            "collectible_net_revenue": float(self.collectible_net_revenue),
            "timing_drag": float(self.timing_drag),
            "bad_debt_leakage": float(self.bad_debt_leakage),
            "final_realized_cash": float(self.final_realized_cash),
            "breakdowns": [b.to_dict() for b in self.breakdowns],
            "assumptions": dict(self.assumptions),
        }


# ── Mechanism tables ────────────────────────────────────────────────

METHOD_SENSITIVITY_TABLE: Dict[ReimbursementMethod, MethodSensitivity] = {
    ReimbursementMethod.FEE_FOR_SERVICE: MethodSensitivity(
        primary_revenue_driver="per-claim charge × negotiated rate",
        coding_cdi_acuity=0.70,
        auth_denials=0.90,
        eligibility_denials=0.90,
        medical_necessity=0.80,
        timely_filing=0.90,
        utilization_volume=0.95,
        site_of_care_migration=0.70,
        los_discharge_timing=0.40,
        cash_timing_days=50,
        clawback_likelihood=0.12,
        gain_pathway="revenue",
    ),
    ReimbursementMethod.DRG_PROSPECTIVE: MethodSensitivity(
        primary_revenue_driver="DRG relative weight × Medicare base rate",
        coding_cdi_acuity=1.00,     # CMI is the headline lever
        auth_denials=0.70,
        eligibility_denials=0.70,
        medical_necessity=0.85,     # RAC audit country
        timely_filing=0.65,
        utilization_volume=0.70,    # discharges, not charges
        site_of_care_migration=0.30,
        los_discharge_timing=0.60,  # cost outliers
        cash_timing_days=45,
        clawback_likelihood=0.25,   # RAC / MAC audits
        gain_pathway="revenue",
    ),
    ReimbursementMethod.OUTPATIENT_APC: MethodSensitivity(
        primary_revenue_driver="APC / ASC-style bundled per-visit rates",
        coding_cdi_acuity=0.75,
        auth_denials=0.85,
        eligibility_denials=0.85,
        medical_necessity=0.80,
        timely_filing=0.75,
        utilization_volume=0.90,
        site_of_care_migration=0.80,  # OP migration is the story here
        los_discharge_timing=0.20,
        cash_timing_days=40,
        clawback_likelihood=0.18,
        gain_pathway="revenue",
    ),
    ReimbursementMethod.PER_DIEM: MethodSensitivity(
        primary_revenue_driver="daily rate × LOS",
        coding_cdi_acuity=0.40,
        auth_denials=0.85,
        eligibility_denials=0.85,
        medical_necessity=0.75,
        timely_filing=0.70,
        utilization_volume=0.80,
        site_of_care_migration=0.50,
        los_discharge_timing=0.95,    # LOS is the primary driver
        cash_timing_days=55,
        clawback_likelihood=0.15,
        gain_pathway="revenue",
    ),
    ReimbursementMethod.CAPITATION: MethodSensitivity(
        primary_revenue_driver="PMPM rate × attributed lives",
        coding_cdi_acuity=0.40,      # HCC coding matters for risk adjustment
        auth_denials=0.15,           # intra-network
        eligibility_denials=0.25,
        medical_necessity=0.20,
        timely_filing=0.15,
        utilization_volume=0.20,     # more volume is cost, not revenue
        site_of_care_migration=0.25,
        los_discharge_timing=0.30,
        cash_timing_days=20,         # prepaid
        clawback_likelihood=0.05,
        gain_pathway="cost_avoidance",
    ),
    ReimbursementMethod.CASE_RATE_BUNDLE: MethodSensitivity(
        primary_revenue_driver="episode-based flat payment",
        coding_cdi_acuity=0.60,
        auth_denials=0.60,
        eligibility_denials=0.65,
        medical_necessity=0.60,
        timely_filing=0.65,
        utilization_volume=0.50,
        site_of_care_migration=0.55,
        los_discharge_timing=0.70,
        cash_timing_days=50,
        clawback_likelihood=0.30,    # reconciliation at end of episode
        gain_pathway="mixed",
    ),
    ReimbursementMethod.VALUE_BASED: MethodSensitivity(
        primary_revenue_driver="quality / total-cost-of-care performance",
        coding_cdi_acuity=0.55,
        auth_denials=0.40,
        eligibility_denials=0.40,
        medical_necessity=0.45,
        timely_filing=0.50,
        utilization_volume=0.35,
        site_of_care_migration=0.45,
        los_discharge_timing=0.55,
        cash_timing_days=180,        # shared-savings settlements are slow
        clawback_likelihood=0.35,
        gain_pathway="mixed",
    ),
    ReimbursementMethod.COST_BASED: MethodSensitivity(
        primary_revenue_driver="allowable cost × CMS cost-report settlement",
        coding_cdi_acuity=0.40,
        auth_denials=0.50,
        eligibility_denials=0.50,
        medical_necessity=0.40,
        timely_filing=0.55,
        utilization_volume=0.60,
        site_of_care_migration=0.30,
        los_discharge_timing=0.50,
        cash_timing_days=75,         # cost-report settlement is slow
        clawback_likelihood=0.20,
        gain_pathway="revenue",
    ),
}


# Default method distribution per payer class. Each inner dict sums to
# 1.0. These are the defaults when the hospital's actual contract
# inventory isn't provided — they're partner-defensible but always
# tagged ``inferred_from_profile`` in the provenance.

DEFAULT_PAYER_METHOD_DISTRIBUTION: Dict[PayerClass, Dict[ReimbursementMethod, float]] = {
    PayerClass.COMMERCIAL: {
        ReimbursementMethod.FEE_FOR_SERVICE: 0.45,
        ReimbursementMethod.CASE_RATE_BUNDLE: 0.30,
        ReimbursementMethod.DRG_PROSPECTIVE: 0.15,
        ReimbursementMethod.VALUE_BASED: 0.05,
        ReimbursementMethod.CAPITATION: 0.05,
    },
    PayerClass.MEDICARE_FFS: {
        # Split between inpatient DRG and outpatient APC-like for
        # general acute hospitals. Critical-access hospitals override
        # this at build_reimbursement_profile time.
        ReimbursementMethod.DRG_PROSPECTIVE: 0.55,
        ReimbursementMethod.OUTPATIENT_APC: 0.40,
        ReimbursementMethod.VALUE_BASED: 0.05,
    },
    PayerClass.MEDICARE_ADVANTAGE: {
        ReimbursementMethod.DRG_PROSPECTIVE: 0.55,
        ReimbursementMethod.OUTPATIENT_APC: 0.30,
        ReimbursementMethod.CASE_RATE_BUNDLE: 0.08,
        ReimbursementMethod.VALUE_BASED: 0.07,
    },
    PayerClass.MEDICAID: {
        # Varies enormously by state; default is roughly 50/50 FFS and
        # per-diem, with managed Medicaid sitting under MANAGED_GOVERNMENT.
        ReimbursementMethod.FEE_FOR_SERVICE: 0.50,
        ReimbursementMethod.PER_DIEM: 0.35,
        ReimbursementMethod.DRG_PROSPECTIVE: 0.10,
        ReimbursementMethod.COST_BASED: 0.05,
    },
    PayerClass.SELF_PAY: {
        ReimbursementMethod.FEE_FOR_SERVICE: 1.00,
    },
    PayerClass.MANAGED_GOVERNMENT: {
        ReimbursementMethod.FEE_FOR_SERVICE: 0.45,
        ReimbursementMethod.PER_DIEM: 0.35,
        ReimbursementMethod.CAPITATION: 0.15,
        ReimbursementMethod.VALUE_BASED: 0.05,
    },
}


# Default collection difficulty + contractual discount per payer class.
_PAYER_CLASS_DEFAULTS: Dict[PayerClass, Tuple[float, float]] = {
    # (collection_difficulty, avg_contractual_discount_as_share_of_gross)
    PayerClass.COMMERCIAL:          (0.25, 0.55),
    PayerClass.MEDICARE_FFS:        (0.20, 0.60),
    PayerClass.MEDICARE_ADVANTAGE:  (0.35, 0.62),
    PayerClass.MEDICAID:            (0.45, 0.75),
    PayerClass.SELF_PAY:            (0.80, 0.50),
    PayerClass.MANAGED_GOVERNMENT:  (0.45, 0.70),
}


# Map metric → which MethodSensitivity field(s) gate it. Each entry is
# ``(sensitivity_field, pathway_label)`` — the pathway_label goes into
# the per-metric explanation so we can tell partners "this is a
# revenue effect" vs "this is a working-capital effect".
_METRIC_SENSITIVITY_MAP: Dict[str, Dict[str, Any]] = {
    "denial_rate": {
        "fields": ["auth_denials", "eligibility_denials",
                    "medical_necessity", "coding_cdi_acuity"],
        "pathway": "revenue+cost",
    },
    "initial_denial_rate": {
        "fields": ["auth_denials", "eligibility_denials", "coding_cdi_acuity"],
        "pathway": "cost+timing",
    },
    "final_denial_rate": {
        "fields": ["auth_denials", "medical_necessity"],
        "pathway": "revenue",
    },
    "clean_claim_rate": {
        "fields": ["eligibility_denials", "coding_cdi_acuity"],
        "pathway": "cost+timing",
    },
    "first_pass_resolution_rate": {
        "fields": ["eligibility_denials", "coding_cdi_acuity"],
        "pathway": "cost+timing",
    },
    "days_in_ar": {
        "fields": ["timely_filing"],
        "pathway": "working_capital",
    },
    "ar_over_90_pct": {
        "fields": ["timely_filing"],
        "pathway": "working_capital+revenue",
    },
    "net_collection_rate": {
        "fields": ["auth_denials", "eligibility_denials",
                    "medical_necessity", "timely_filing"],
        "pathway": "revenue",
    },
    "cost_to_collect": {
        "fields": ["auth_denials", "eligibility_denials", "coding_cdi_acuity"],
        "pathway": "cost",
    },
    "discharged_not_final_billed_days": {
        "fields": ["coding_cdi_acuity"],
        "pathway": "working_capital",
    },
    "coding_denial_rate": {
        "fields": ["coding_cdi_acuity"],
        "pathway": "revenue+cost",
    },
    "auth_denial_rate": {
        "fields": ["auth_denials"],
        "pathway": "revenue+cost",
    },
    "eligibility_denial_rate": {
        "fields": ["eligibility_denials"],
        "pathway": "revenue+cost",
    },
    "timely_filing_denial_rate": {
        "fields": ["timely_filing"],
        "pathway": "revenue",
    },
    "medical_necessity_denial_rate": {
        "fields": ["medical_necessity"],
        "pathway": "revenue",
    },
    "case_mix_index": {
        "fields": ["coding_cdi_acuity"],
        "pathway": "revenue",
    },
    "bad_debt": {
        # Bad debt sensitivity is really about self-pay exposure and
        # eligibility failures; doesn't map cleanly onto one column of
        # the sensitivity table.
        "fields": ["eligibility_denials"],
        "pathway": "revenue+cost",
    },
}


# ── Core builder ────────────────────────────────────────────────────

def _normalize_payer_mix(payer_mix: Dict[str, float]) -> Dict[PayerClass, float]:
    """Coerce the free-form ``payer_mix`` dict (where keys are
    partner-typed like ``medicare``, ``commercial``) into the
    :class:`PayerClass` enum. Unknown keys are dropped.

    Accepts fractions (sum ≈ 1.0) or percentage points (sum ≈ 100);
    always returns fractions.
    """
    if not payer_mix:
        return {}
    alias_map = {
        "commercial": PayerClass.COMMERCIAL,
        "medicare": PayerClass.MEDICARE_FFS,   # treat bare "medicare" as FFS
        "medicare_ffs": PayerClass.MEDICARE_FFS,
        "medicare_advantage": PayerClass.MEDICARE_ADVANTAGE,
        "ma": PayerClass.MEDICARE_ADVANTAGE,
        "medicaid": PayerClass.MEDICAID,
        "managed_medicaid": PayerClass.MANAGED_GOVERNMENT,
        "self_pay": PayerClass.SELF_PAY,
        "selfpay": PayerClass.SELF_PAY,
        "uninsured": PayerClass.SELF_PAY,
        "tricare": PayerClass.MANAGED_GOVERNMENT,
        "managed_government": PayerClass.MANAGED_GOVERNMENT,
    }
    out: Dict[PayerClass, float] = {}
    total = 0.0
    for k, v in payer_mix.items():
        try:
            fv = float(v or 0.0)
        except (TypeError, ValueError):
            continue
        pc = alias_map.get(str(k).lower().replace("-", "_"))
        if pc is None:
            continue
        out[pc] = out.get(pc, 0.0) + fv
        total += fv
    if total <= 0:
        return {}
    # Scale down to fractions if the caller handed us pct-points.
    if total > 1.5:
        out = {k: v / total for k, v in out.items()}
    return out


def _method_distribution_for_payer(
    payer_class: PayerClass,
    hospital_profile: Any,
) -> Tuple[Dict[ReimbursementMethod, float], str]:
    """Return (distribution, provenance_tag).

    The distribution follows the payer default unless a hospital
    profile hint overrides it (e.g., a <25-bed critical-access
    hospital swings Medicare FFS toward cost-based reimbursement).
    """
    base = dict(DEFAULT_PAYER_METHOD_DISTRIBUTION.get(payer_class) or {})
    provenance = ProvenanceTag.BENCHMARK_DEFAULT.value

    if payer_class == PayerClass.MEDICARE_FFS:
        beds = getattr(hospital_profile, "bed_count", None)
        if beds is not None and beds < 25:
            # Critical-access hospitals are cost-based for Medicare.
            base = {
                ReimbursementMethod.COST_BASED: 0.70,
                ReimbursementMethod.OUTPATIENT_APC: 0.25,
                ReimbursementMethod.VALUE_BASED: 0.05,
            }
            provenance = ProvenanceTag.INFERRED_FROM_PROFILE.value
        elif beds is not None and beds < 100:
            # Small acute hospitals lean more outpatient.
            base = {
                ReimbursementMethod.DRG_PROSPECTIVE: 0.30,
                ReimbursementMethod.OUTPATIENT_APC: 0.60,
                ReimbursementMethod.VALUE_BASED: 0.10,
            }
            provenance = ProvenanceTag.INFERRED_FROM_PROFILE.value

    return base, provenance


def build_reimbursement_profile(
    hospital_profile: Any,
    payer_mix: Dict[str, float],
    optional_contract_inputs: Optional[Dict[str, Any]] = None,
) -> ReimbursementProfile:
    """Assemble a :class:`ReimbursementProfile` for one hospital.

    Parameters
    ----------
    hospital_profile
        The packet's :class:`HospitalProfile`. Used for heuristics
        like critical-access detection (bed_count < 25) and
        inpatient/outpatient mix inference.
    payer_mix
        Mapping of payer → fraction (or percentage points — we'll
        normalize). Unknown keys are dropped silently.
    optional_contract_inputs
        Optional analyst overrides. Supported keys:
        - ``method_distribution_by_payer``: dict[PayerClass,
          dict[ReimbursementMethod, float]]
        - ``avg_contractual_discount``: dict[PayerClass, float]
        - ``inpatient_outpatient_mix``: dict[str, float]
        When provided, the corresponding provenance tag flips to
        ``analyst_override``.
    """
    optional_contract_inputs = optional_contract_inputs or {}
    contract_overrides = optional_contract_inputs.get("method_distribution_by_payer") or {}
    discount_overrides = optional_contract_inputs.get("avg_contractual_discount") or {}
    io_mix_override = optional_contract_inputs.get("inpatient_outpatient_mix")

    normalized_mix = _normalize_payer_mix(payer_mix or {})
    if not normalized_mix:
        return ReimbursementProfile(
            notes=["no payer mix provided; skipping reimbursement inference"],
            provenance={"payer_mix": ProvenanceTag.BENCHMARK_DEFAULT.value},
        )

    payer_classes: Dict[PayerClass, PayerClassProfile] = {}
    for pc, share in normalized_mix.items():
        distribution, dist_prov = _method_distribution_for_payer(pc, hospital_profile)
        # Analyst override short-circuits the inference.
        override = contract_overrides.get(pc) or contract_overrides.get(pc.value)
        if isinstance(override, dict) and override:
            try:
                distribution = {
                    ReimbursementMethod(k) if not isinstance(k, ReimbursementMethod) else k:
                        float(v)
                    for k, v in override.items()
                }
                dist_prov = ProvenanceTag.ANALYST_OVERRIDE.value
            except (ValueError, TypeError):
                pass  # keep default distribution, keep inferred tag

        # Normalize distribution to sum to 1.0.
        total = sum(distribution.values())
        if total > 0:
            distribution = {k: v / total for k, v in distribution.items()}

        cd, disc = _PAYER_CLASS_DEFAULTS.get(pc, (0.5, 0.6))
        disc_override = discount_overrides.get(pc) or discount_overrides.get(pc.value)
        if disc_override is not None:
            try:
                disc = float(disc_override)
                disc_prov = ProvenanceTag.ANALYST_OVERRIDE.value
            except (TypeError, ValueError):
                disc_prov = ProvenanceTag.BENCHMARK_DEFAULT.value
        else:
            disc_prov = ProvenanceTag.BENCHMARK_DEFAULT.value

        payer_classes[pc] = PayerClassProfile(
            payer_class=pc,
            revenue_share=float(share),
            method_distribution=distribution,
            collection_difficulty=cd,
            avg_contractual_discount=disc,
            provenance={
                "method_distribution": dist_prov,
                "collection_difficulty": ProvenanceTag.BENCHMARK_DEFAULT.value,
                "avg_contractual_discount": disc_prov,
                "revenue_share": ProvenanceTag.OBSERVED.value,
            },
        )

    # Revenue-weighted method mix — the top-line summary the bridge
    # will read.
    method_weights: Dict[ReimbursementMethod, float] = {}
    for pcp in payer_classes.values():
        for method, share in pcp.method_distribution.items():
            method_weights[method] = (
                method_weights.get(method, 0.0) + share * pcp.revenue_share
            )

    # Inpatient/outpatient mix inference. If the partner gave us one
    # use it verbatim; otherwise guess from bed_count.
    io_mix: Optional[Dict[str, float]] = None
    io_prov = ProvenanceTag.INFERRED_FROM_PROFILE.value
    if io_mix_override and isinstance(io_mix_override, dict):
        try:
            total = sum(float(v) for v in io_mix_override.values())
            if total > 0:
                io_mix = {str(k): float(v) / total for k, v in io_mix_override.items()}
                io_prov = ProvenanceTag.ANALYST_OVERRIDE.value
        except (TypeError, ValueError):
            io_mix = None
    if io_mix is None:
        beds = getattr(hospital_profile, "bed_count", None)
        if beds is not None:
            if beds < 25:
                io_mix = {"inpatient": 0.35, "outpatient": 0.65}
            elif beds < 100:
                io_mix = {"inpatient": 0.45, "outpatient": 0.55}
            elif beds < 400:
                io_mix = {"inpatient": 0.55, "outpatient": 0.45}
            else:
                io_mix = {"inpatient": 0.65, "outpatient": 0.35}

    notes: List[str] = []
    beds = getattr(hospital_profile, "bed_count", None)
    if beds is not None and beds < 25:
        notes.append(
            "critical-access hospital detected (<25 beds); "
            "Medicare exposure shifted to cost-based reimbursement"
        )
    if not contract_overrides:
        notes.append(
            "method distributions are inferred from payer class defaults "
            "— supply optional_contract_inputs.method_distribution_by_payer "
            "to override with real contract inventory"
        )

    return ReimbursementProfile(
        payer_classes=payer_classes,
        method_weights=method_weights,
        inpatient_outpatient_mix=io_mix,
        notes=notes,
        provenance={
            "payer_mix": ProvenanceTag.OBSERVED.value,
            "method_weights": ProvenanceTag.CALCULATED.value,
            "inpatient_outpatient_mix": io_prov,
        },
    )


# ── Per-metric sensitivity ──────────────────────────────────────────

def _method_weighted_sensitivity(
    profile: ReimbursementProfile,
    sensitivity_fields: List[str],
) -> float:
    """Revenue-weighted average of the given sensitivity fields across
    the profile's methods. 0.0 when the profile is empty."""
    if not profile.method_weights:
        return 0.0
    acc = 0.0
    for method, weight in profile.method_weights.items():
        entry = METHOD_SENSITIVITY_TABLE.get(method)
        if entry is None:
            continue
        vals = [getattr(entry, f, 0.0) for f in sensitivity_fields]
        if not vals:
            continue
        acc += weight * (sum(vals) / len(vals))
    return acc


def _pathway_decomposition(
    profile: ReimbursementProfile, pathway_label: str,
) -> Dict[str, float]:
    """Split a sensitivity score into revenue / cost / working-capital
    components using the per-method ``gain_pathway`` tag as the router.
    ``pathway_label`` from the metric map constrains the allocation."""
    if not profile.method_weights:
        return {"revenue": 0.0, "cost": 0.0, "working_capital": 0.0}

    gain_weights = {"revenue": 0.0, "cost": 0.0, "working_capital": 0.0}
    total_weight = 0.0
    for method, weight in profile.method_weights.items():
        entry = METHOD_SENSITIVITY_TABLE.get(method)
        if entry is None:
            continue
        total_weight += weight
        pw = entry.gain_pathway
        if pw == "revenue":
            gain_weights["revenue"] += weight
        elif pw == "cost_avoidance":
            gain_weights["cost"] += weight
        elif pw == "working_capital":
            gain_weights["working_capital"] += weight
        else:  # mixed
            gain_weights["revenue"] += weight * 0.5
            gain_weights["cost"] += weight * 0.5

    if total_weight <= 0:
        return {"revenue": 0.0, "cost": 0.0, "working_capital": 0.0}
    # Normalize pathway weights to sum to 1.0.
    for k in list(gain_weights.keys()):
        gain_weights[k] /= total_weight

    # Metric-specific pathway label overrides the gain-pathway mix.
    # ``days_in_ar`` → primarily working_capital, regardless of the
    # per-method gain_pathway tags.
    if pathway_label == "working_capital":
        return {"revenue": 0.05, "cost": 0.05, "working_capital": 0.90}
    if pathway_label == "revenue":
        return {"revenue": 0.85, "cost": 0.10, "working_capital": 0.05}
    if pathway_label == "cost":
        return {"revenue": 0.05, "cost": 0.85, "working_capital": 0.10}
    if pathway_label == "working_capital+revenue":
        return {"revenue": 0.40, "cost": 0.10, "working_capital": 0.50}
    if pathway_label == "revenue+cost":
        return {"revenue": 0.55, "cost": 0.40, "working_capital": 0.05}
    if pathway_label == "cost+timing":
        return {"revenue": 0.10, "cost": 0.55, "working_capital": 0.35}
    # ``mixed`` → fall back to gain-weight distribution.
    return gain_weights


def estimate_metric_revenue_sensitivity(
    metric_key: str,
    reimbursement_profile: ReimbursementProfile,
) -> Dict[str, Any]:
    """Return the split of a metric's economic weight across
    revenue / cost / working-capital, plus confidence + narrative.

    Shape of the return dict::

        {
            "metric": <key>,
            "overall_sensitivity": 0.0-1.0,
            "revenue_sensitivity": 0.0-1.0,
            "cost_sensitivity": 0.0-1.0,
            "working_capital_sensitivity": 0.0-1.0,
            "confidence": 0.0-1.0,
            "explanation": <str>,
            "dominant_method": <method value or None>,
        }
    """
    entry = _METRIC_SENSITIVITY_MAP.get(metric_key)
    if entry is None:
        return {
            "metric": metric_key,
            "overall_sensitivity": 0.0,
            "revenue_sensitivity": 0.0,
            "cost_sensitivity": 0.0,
            "working_capital_sensitivity": 0.0,
            "confidence": 0.0,
            "explanation": f"{metric_key!r} is not mapped into the "
                           f"reimbursement sensitivity table.",
            "dominant_method": None,
        }

    overall = _method_weighted_sensitivity(reimbursement_profile, entry["fields"])
    pathway = _pathway_decomposition(reimbursement_profile, entry["pathway"])
    rev = overall * pathway["revenue"]
    cost = overall * pathway["cost"]
    wc = overall * pathway["working_capital"]

    # Confidence: strong when both mix is well-defined and the overall
    # sensitivity is non-trivial. Weak when we had to infer method
    # distributions.
    n_inferred = sum(
        1 for pcp in reimbursement_profile.payer_classes.values()
        if pcp.provenance.get("method_distribution") ==
            ProvenanceTag.INFERRED_FROM_PROFILE.value
        or pcp.provenance.get("method_distribution") ==
            ProvenanceTag.BENCHMARK_DEFAULT.value
    )
    n_total = max(1, len(reimbursement_profile.payer_classes))
    inference_penalty = 0.4 * (n_inferred / n_total)
    confidence = max(0.0, min(1.0, 0.85 - inference_penalty))

    dominant = reimbursement_profile.dominant_method()
    dominant_label = dominant.value if dominant else None

    # Build the explanation.
    bits: List[str] = []
    if overall < 0.1:
        bits.append(f"{metric_key} has minimal economic leverage under this "
                    f"hospital's reimbursement exposure.")
    else:
        pathway_label = {
            "revenue": "revenue",
            "cost": "cost",
            "working_capital": "working capital",
            "working_capital+revenue": "working capital with a revenue tail",
            "revenue+cost": "both revenue and cost",
            "cost+timing": "cost with timing drag",
        }.get(entry["pathway"], entry["pathway"])
        bits.append(
            f"{metric_key} primarily moves the {pathway_label} pathway "
            f"under the hospital's reimbursement mix."
        )
    if dominant_label:
        bits.append(
            f"Dominant reimbursement method: {dominant_label.replace('_', ' ')}."
        )
    if n_inferred and n_total:
        bits.append(
            f"{n_inferred}/{n_total} payer method distributions are "
            f"inferred from payer-class defaults — partner inputs "
            f"would tighten the estimate."
        )

    return {
        "metric": metric_key,
        "overall_sensitivity": float(overall),
        "revenue_sensitivity": float(rev),
        "cost_sensitivity": float(cost),
        "working_capital_sensitivity": float(wc),
        "confidence": float(confidence),
        "explanation": " ".join(bits),
        "dominant_method": dominant_label,
    }


# ── Revenue realization path ────────────────────────────────────────

def _get_metric_value(current_metrics: Dict[str, Any], key: str) -> Optional[float]:
    """Accept both raw floats and packet-shaped metric dicts / objects."""
    v = current_metrics.get(key) if current_metrics else None
    if v is None:
        return None
    if hasattr(v, "value"):
        try:
            return float(v.value)
        except (TypeError, ValueError):
            return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compute_revenue_realization_path(
    current_metrics: Dict[str, Any],
    reimbursement_profile: ReimbursementProfile,
    *,
    gross_revenue: Optional[float] = None,
    net_revenue: Optional[float] = None,
) -> RevenueRealizationPath:
    """Decompose gross charges → final realized cash.

    Sequential stages (each leakage starts from the prior residual):

        gross_charges
          − contractual_adjustments          = expected_net_revenue
          − preventable_front_end_leakage
          − coding_documentation_leakage
          − initial_denial_leakage            (net of appeals recovery)
          − final_denial_leakage              = collectible_net_revenue
          − timing_drag                       (interest cost of AR)
          − bad_debt_leakage                  = final_realized_cash

    All metrics are on the 0-100 percentage-point scale (consistent
    with the rest of the platform).
    """
    # Start by inferring gross charges when the caller didn't supply them.
    assumptions: Dict[str, str] = {}
    if gross_revenue is None or gross_revenue <= 0:
        if net_revenue is not None and net_revenue > 0:
            # Weighted-avg contractual discount across the profile's
            # payer classes. Reverse-engineer the gross from net.
            total_discount = 0.0
            total_share = 0.0
            for pcp in reimbursement_profile.payer_classes.values():
                total_discount += pcp.revenue_share * pcp.avg_contractual_discount
                total_share += pcp.revenue_share
            if total_share > 0:
                blended_discount = total_discount / total_share
            else:
                blended_discount = 0.60
            gross_revenue = net_revenue / max(1e-3, 1.0 - blended_discount)
            assumptions["gross_charges"] = ProvenanceTag.INFERRED_FROM_PROFILE.value
        else:
            return RevenueRealizationPath(
                assumptions={"skipped": "no revenue baseline"},
            )
    else:
        assumptions["gross_charges"] = ProvenanceTag.OBSERVED.value

    # Contractual adjustments (the "gross-to-net" spread).
    total_discount = 0.0
    total_share = 0.0
    for pcp in reimbursement_profile.payer_classes.values():
        total_discount += pcp.revenue_share * pcp.avg_contractual_discount
        total_share += pcp.revenue_share
    blended_discount = (total_discount / total_share) if total_share > 0 else 0.60
    contractual = gross_revenue * blended_discount
    expected_net = gross_revenue - contractual
    assumptions["contractual_adjustments"] = ProvenanceTag.BENCHMARK_DEFAULT.value

    # Pull RCM leverages.
    elig_rate = _get_metric_value(current_metrics, "eligibility_denial_rate") or 0.0
    auth_rate = _get_metric_value(current_metrics, "auth_denial_rate") or 0.0
    coding_rate = _get_metric_value(current_metrics, "coding_denial_rate") or 0.0
    med_nec_rate = _get_metric_value(current_metrics, "medical_necessity_denial_rate") or 0.0
    timely_rate = _get_metric_value(current_metrics, "timely_filing_denial_rate") or 0.0
    init_denial_rate = _get_metric_value(current_metrics, "initial_denial_rate")
    if init_denial_rate is None:
        init_denial_rate = _get_metric_value(current_metrics, "denial_rate") or 0.0
    final_denial_rate = _get_metric_value(current_metrics, "final_denial_rate") or 0.0
    days_ar = _get_metric_value(current_metrics, "days_in_ar") or 45.0
    bad_debt_rate = _get_metric_value(current_metrics, "bad_debt") or 0.0

    # Reimbursement-weighted sensitivities used as scale factors — a
    # DRG-heavy hospital weights coding leakage higher.
    def _w(fields: List[str]) -> float:
        return _method_weighted_sensitivity(reimbursement_profile, fields)

    elig_weight = _w(["eligibility_denials"])
    auth_weight = _w(["auth_denials"])
    coding_weight = _w(["coding_cdi_acuity"])
    med_nec_weight = _w(["medical_necessity"])
    timely_weight = _w(["timely_filing"])

    # Front-end leakage: eligibility + auth denial rates, roughly
    # avoided by proper registration + prior-auth workflow. Scaled to
    # expected_net since they produce write-offs post-adjustment.
    pct = lambda x: float(x) / 100.0
    front_end = (
        expected_net
        * (pct(elig_rate) * elig_weight + pct(auth_rate) * auth_weight)
        * 0.4   # ~40% of auth/eligibility denials are preventable at cost
    )
    assumptions["preventable_front_end_leakage"] = (
        ProvenanceTag.CALCULATED.value
    )

    # Coding / documentation leakage — undercoding, missing modifiers,
    # rejected DRGs. Weighted heavily under DRG-prospective.
    coding_leak = (
        expected_net
        * (pct(coding_rate) + 0.01)   # baseline 1% ambient undercoding
        * coding_weight
        * 0.6
    )

    # Initial denial leakage net of typical appeal recovery. We assume
    # 60% of initial denials are appealed, 65% of appeals succeed,
    # leaving about 61% write-off cost. (These are industry averages,
    # tagged benchmark_default.)
    net_init_denial_rate = pct(init_denial_rate) - (
        pct(init_denial_rate) * 0.60 * 0.65
    )
    initial_leak = (
        expected_net * max(0.0, net_init_denial_rate)
    )
    assumptions["initial_denial_leakage"] = ProvenanceTag.BENCHMARK_DEFAULT.value

    # Final denial leakage: claims that stay denied after appeal +
    # medical-necessity + timely-filing permanent losses.
    final_leak = (
        expected_net * pct(final_denial_rate)
        + expected_net * pct(med_nec_rate) * med_nec_weight * 0.5
        + expected_net * pct(timely_rate) * timely_weight
    )

    collectible = expected_net - front_end - coding_leak - initial_leak - final_leak
    collectible = max(0.0, collectible)

    # Timing drag — AR days above a baseline of 30 cost cost_of_capital.
    baseline_ar = 30.0
    extra_days = max(0.0, float(days_ar) - baseline_ar)
    cost_of_capital = 0.08
    timing_drag = expected_net * (extra_days / 365.0) * cost_of_capital
    assumptions["timing_drag"] = ProvenanceTag.CALCULATED.value

    # Bad debt scales with self-pay exposure.
    self_pay = 0.0
    if PayerClass.SELF_PAY in reimbursement_profile.payer_classes:
        self_pay = reimbursement_profile.payer_classes[PayerClass.SELF_PAY].revenue_share
    bad_debt_pct = pct(bad_debt_rate) + self_pay * 0.10
    bad_debt_leak = collectible * bad_debt_pct

    realized = max(0.0, collectible - timing_drag - bad_debt_leak)

    # Breakdowns — one row per stage so downstream renderers can show
    # a proper waterfall / stacked bar.
    breakdowns: List[RevenueAtRiskBreakdown] = []

    def _add(stage: str, amt: float, category: str, tag: str) -> None:
        share = (amt / gross_revenue) if gross_revenue > 0 else 0.0
        breakdowns.append(RevenueAtRiskBreakdown(
            category=category, dollar_amount=float(amt),
            share_of_gross=float(share), stage=stage,
            provenance_tag=tag,
        ))

    _add("contractual_adjustments", contractual, "gross_to_net",
         ProvenanceTag.BENCHMARK_DEFAULT.value)
    _add("preventable_front_end_leakage", front_end, "front_end",
         ProvenanceTag.CALCULATED.value)
    _add("coding_documentation_leakage", coding_leak, "coding",
         ProvenanceTag.CALCULATED.value)
    _add("initial_denial_leakage", initial_leak, "denials",
         ProvenanceTag.CALCULATED.value)
    _add("final_denial_leakage", final_leak, "denials",
         ProvenanceTag.CALCULATED.value)
    _add("timing_drag", timing_drag, "working_capital",
         ProvenanceTag.CALCULATED.value)
    _add("bad_debt_leakage", bad_debt_leak, "collections",
         ProvenanceTag.CALCULATED.value)

    return RevenueRealizationPath(
        gross_charges=float(gross_revenue),
        contractual_adjustments=float(contractual),
        preventable_front_end_leakage=float(front_end),
        coding_documentation_leakage=float(coding_leak),
        initial_denial_leakage=float(initial_leak),
        final_denial_leakage=float(final_leak),
        collectible_net_revenue=float(collectible),
        timing_drag=float(timing_drag),
        bad_debt_leakage=float(bad_debt_leak),
        final_realized_cash=float(realized),
        breakdowns=breakdowns,
        assumptions=assumptions,
    )


# ── Explanation ─────────────────────────────────────────────────────

def explain_reimbursement_logic(
    metric_key: str,
    reimbursement_profile: ReimbursementProfile,
) -> str:
    """Plain-English narrative: why the metric matters under this
    specific reimbursement profile."""
    sensitivity = estimate_metric_revenue_sensitivity(
        metric_key, reimbursement_profile,
    )
    if reimbursement_profile is None or not reimbursement_profile.method_weights:
        return (
            f"{metric_key} — no reimbursement profile built for this "
            f"hospital yet; economic weight not determinable."
        )

    method_desc = sorted(
        reimbursement_profile.method_weights.items(),
        key=lambda t: t[1], reverse=True,
    )[:2]
    methods_label = ", ".join(
        f"{m.value.replace('_', ' ')} ({w*100:.0f}%)"
        for m, w in method_desc
    )

    # Which payer class exposure dominates.
    top_payer = None
    if reimbursement_profile.payer_classes:
        top_payer = max(
            reimbursement_profile.payer_classes.items(),
            key=lambda t: t[1].revenue_share,
        )[0]

    rev = sensitivity["revenue_sensitivity"]
    cost = sensitivity["cost_sensitivity"]
    wc = sensitivity["working_capital_sensitivity"]

    # Which pathway dominates?
    max_path_val = max(rev, cost, wc)
    if max_path_val < 0.05:
        dominant_path = "minimal direct effect"
    elif rev >= cost and rev >= wc:
        dominant_path = "primarily revenue"
    elif wc >= cost:
        dominant_path = "primarily timing / working capital"
    else:
        dominant_path = "primarily cost"

    # Payer-class tilt.
    if top_payer == PayerClass.COMMERCIAL:
        payer_tilt = (
            "Stronger under commercial-heavy mix because commercial "
            "denials have the widest appeal windows and rate variance."
        )
    elif top_payer == PayerClass.MEDICARE_FFS:
        payer_tilt = (
            "Stronger under Medicare FFS because DRG / APC payment "
            "rewards coding accuracy and exposes timing to RAC audits."
        )
    elif top_payer == PayerClass.MEDICARE_ADVANTAGE:
        payer_tilt = (
            "Stronger under Medicare Advantage because MA plans use "
            "AI-driven prior-auth + retrospective reviews aggressively."
        )
    elif top_payer == PayerClass.MEDICAID:
        payer_tilt = (
            "Weaker revenue leverage under Medicaid (low rates) but "
            "bad-debt exposure rises with coverage-loss / OBBBA risk."
        )
    elif top_payer == PayerClass.SELF_PAY:
        payer_tilt = (
            "Highest sensitivity under self-pay exposure — eligibility "
            "failures and patient balance collection dominate."
        )
    else:
        payer_tilt = ""

    inferred_note = ""
    n_inferred = sum(
        1 for pcp in reimbursement_profile.payer_classes.values()
        if pcp.provenance.get("method_distribution") in
           (ProvenanceTag.BENCHMARK_DEFAULT.value,
            ProvenanceTag.INFERRED_FROM_PROFILE.value)
    )
    if n_inferred:
        inferred_note = (
            f" Note: {n_inferred} payer method distribution(s) are "
            f"inferred rather than observed — partner override would "
            f"tighten this estimate."
        )

    return (
        f"{metric_key} under this reimbursement profile "
        f"({methods_label}): {dominant_path}. "
        f"{sensitivity['explanation']} "
        f"{payer_tilt}{inferred_note}"
    )
