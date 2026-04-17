"""Healthcare revenue-cycle economic ontology.

Maps every metric the platform uses to a fixed slot in the revenue
cycle, a financial pathway through the P&L, a set of causal parents and
children, and a reimbursement-sensitivity profile. The ontology is what
makes every downstream model (predictor, bridge, MC, risk flags) land
on the same economic picture.

Design principles:
- **Explicit mappings, not inference.** Each metric's classification is
  a hand-written dict entry partners can defend in IC. We don't try to
  auto-learn the ontology from data.
- **Single source of truth.** Anywhere the code needs to know "is
  ``denial_rate`` lower-is-better?" or "does this metric move revenue
  or cost?", it consults this module.
- **No black-box abstractions.** The whole thing is dataclasses and
  dicts. A new analyst can read ``METRIC_ONTOLOGY`` top-to-bottom in
  ten minutes and leave knowing what every metric means.

References (sourced for the initial classifications):
- HFMA MAP Keys, 2023
- AHRQ Healthcare Cost and Utilization Project (HCUP) reimbursement docs
- CMS IPPS / OPPS rulemaking context (sequestration, VBP)
- KFF coverage + payer-mix research
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ── Enums ────────────────────────────────────────────────────────────

class Domain(str, Enum):
    """Top-level domain in the revenue cycle + economic lifecycle."""
    COVERAGE_PAYER_MIX = "coverage_payer_mix"
    REIMBURSEMENT_METHODOLOGY = "reimbursement_methodology"
    FRONT_END_ACCESS = "front_end_access"            # eligibility, auth, registration
    MIDDLE_CYCLE_CODING = "middle_cycle_coding"       # coding, CDI, charge capture
    BACK_END_CLAIMS = "back_end_claims"               # denials, appeals, collections, AR
    WORKING_CAPITAL = "working_capital"               # liquidity, cash conversion
    PROFITABILITY = "profitability"                   # EBITDA, margin
    POLICY_REGULATORY = "policy_regulatory"           # OBBBA, sequestration
    MARKET_STRUCTURE = "market_structure"             # substitution / consolidation


class Directionality(str, Enum):
    HIGHER_IS_BETTER = "higher_is_better"
    LOWER_IS_BETTER = "lower_is_better"
    DEPENDS = "depends"       # payer mix entries — right level depends on strategy


class FinancialPathway(str, Enum):
    """Which P&L line the metric moves, primarily."""
    REVENUE = "revenue"
    COST = "cost"
    WORKING_CAPITAL = "working_capital"   # cash, not P&L (but financing cost is EBITDA)
    RISK = "risk"                          # tail exposure (denials may convert to write-off)
    MIXED = "mixed"                        # plausibly multiple pathways


class ConfidenceClass(str, Enum):
    """Partner-facing signal of how we typically know a metric's value.

    ``observed`` is the gold standard; ``benchmarked`` is the last
    resort (no hospital-specific information).
    """
    OBSERVED = "observed"          # seller data / actuals
    INFERRED = "inferred"          # partial data → extrapolated
    MODELED = "modeled"            # ridge / regression prediction
    BENCHMARKED = "benchmarked"    # registry fallback
    DERIVED = "derived"            # arithmetic of other metrics


class ReimbursementType(str, Enum):
    FEE_FOR_SERVICE = "fee_for_service"
    PROSPECTIVE_DRG = "prospective_drg"     # Medicare IPPS / OPPS
    CAPITATED = "capitated"
    BUNDLED = "bundled"                     # episode-based (BPCI, CJR)
    VALUE_BASED = "value_based"             # VBP, shared savings


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class MechanismEdge:
    """One causal link between two metrics.

    ``parent`` drives ``child``. ``effect_direction`` is ``+`` when an
    increase in the parent increases the child, ``-`` when it decreases.
    ``magnitude_hint`` is a partner-readable descriptor (``strong``,
    ``moderate``, ``weak``) — we deliberately avoid pretending to have
    a calibrated coefficient because the ontology is a structural
    model, not a regression.
    """
    parent: str
    child: str
    effect_direction: str = "+"
    magnitude_hint: str = "moderate"
    mechanism: str = ""                      # one-phrase explanation

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetricReimbursementSensitivity:
    """How a *metric* behaves under different reimbursement regimes.

    Each entry is ``1.0`` (fully load-bearing), ``0.5`` (moderate), or
    ``0.0`` (effectively irrelevant). Callers use these to weight the
    metric's economic importance given a hospital's payer mix.

    Distinct from :class:`rcm_mc.finance.reimbursement_engine.ReimbursementProfile`,
    which describes a *hospital's revenue exposure* across regimes.
    This type describes *per-metric sensitivity*. Same concept,
    different granularity.
    """
    fee_for_service: float = 0.0
    prospective_drg: float = 0.0
    capitated: float = 0.0
    bundled: float = 0.0
    value_based: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Back-compat alias — the old name is still imported by a handful of
# internal call sites. New code should use
# :class:`MetricReimbursementSensitivity`. Will be removed once every
# import site has been migrated.
ReimbursementProfile = MetricReimbursementSensitivity


@dataclass
class MetricDefinition:
    """Canonical record for one metric in the ontology.

    Populated by hand in :data:`METRIC_ONTOLOGY` and surfaced through
    :func:`classify_metric`. Never constructed from data at runtime.
    """
    metric_key: str
    display_name: str
    domain: Domain
    subdomain: str
    economic_mechanism: str
    directionality: Directionality
    financial_pathway: FinancialPathway
    confidence_class: ConfidenceClass
    reimbursement_sensitivity: MetricReimbursementSensitivity
    causal_parents: List[str] = field(default_factory=list)
    causal_children: List[str] = field(default_factory=list)
    mechanism_tags: List[str] = field(default_factory=list)
    unit: str = ""                            # pct / days / ratio / dollars / index

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["domain"] = self.domain.value
        d["directionality"] = self.directionality.value
        d["financial_pathway"] = self.financial_pathway.value
        d["confidence_class"] = self.confidence_class.value
        return d


@dataclass
class CausalGraph:
    """Directed graph over metric keys."""
    nodes: Dict[str, MetricDefinition] = field(default_factory=dict)
    edges: List[MechanismEdge] = field(default_factory=list)

    def parents_of(self, metric_key: str) -> List[MetricDefinition]:
        return [self.nodes[e.parent] for e in self.edges
                if e.child == metric_key and e.parent in self.nodes]

    def children_of(self, metric_key: str) -> List[MetricDefinition]:
        return [self.nodes[e.child] for e in self.edges
                if e.parent == metric_key and e.child in self.nodes]

    def edges_into(self, metric_key: str) -> List[MechanismEdge]:
        return [e for e in self.edges if e.child == metric_key]

    def edges_out_of(self, metric_key: str) -> List[MechanismEdge]:
        return [e for e in self.edges if e.parent == metric_key]


# ── Ontology registry ────────────────────────────────────────────────
#
# Helper factories to keep the long dict below readable.

def _r(ffs=0.0, drg=0.0, cap=0.0, bundled=0.0, vbp=0.0) -> MetricReimbursementSensitivity:
    return MetricReimbursementSensitivity(
        fee_for_service=ffs, prospective_drg=drg, capitated=cap,
        bundled=bundled, value_based=vbp,
    )


def _m(
    metric_key: str, display: str, *,
    domain: Domain, subdomain: str,
    mechanism: str,
    direction: Directionality = Directionality.LOWER_IS_BETTER,
    pathway: FinancialPathway = FinancialPathway.MIXED,
    confidence: ConfidenceClass = ConfidenceClass.OBSERVED,
    reimb: MetricReimbursementSensitivity = None,
    parents: List[str] = None,
    children: List[str] = None,
    tags: List[str] = None,
    unit: str = "pct",
) -> MetricDefinition:
    return MetricDefinition(
        metric_key=metric_key,
        display_name=display,
        domain=domain,
        subdomain=subdomain,
        economic_mechanism=mechanism,
        directionality=direction,
        financial_pathway=pathway,
        confidence_class=confidence,
        reimbursement_sensitivity=reimb or _r(),
        causal_parents=list(parents or []),
        causal_children=list(children or []),
        mechanism_tags=list(tags or []),
        unit=unit,
    )


# ── Metric definitions ───────────────────────────────────────────────

METRIC_ONTOLOGY: Dict[str, MetricDefinition] = {
    # ───── Denials family ───────────────────────────────────────
    "denial_rate": _m(
        "denial_rate", "Initial denial rate",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="denials.aggregate",
        mechanism=(
            "Share of submitted claims initially denied by the payer. "
            "Composite of eligibility, authorization, coding, medical "
            "necessity, and timely filing drivers; a small fraction "
            "of each rolls into final write-off, the rest recovers "
            "through appeals at a collection and time cost."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.MIXED,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.2, bundled=0.5, vbp=0.7),
        parents=["eligibility_denial_rate", "auth_denial_rate",
                 "coding_denial_rate", "medical_necessity_denial_rate",
                 "timely_filing_denial_rate", "clean_claim_rate"],
        children=["final_denial_rate", "days_in_ar",
                  "net_collection_rate", "cost_to_collect"],
        tags=["rework_cost", "cash_timing", "bad_debt_driver"],
    ),
    "initial_denial_rate": _m(
        "initial_denial_rate", "Initial denial rate (first-pass)",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="denials.first_pass",
        mechanism=(
            "Same measure as denial_rate but restricted to a claim's "
            "first adjudication. Leading indicator for front-end "
            "process quality."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.RISK,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.2, bundled=0.5, vbp=0.7),
        parents=["eligibility_denial_rate", "auth_denial_rate",
                 "coding_denial_rate", "clean_claim_rate"],
        children=["final_denial_rate", "days_in_ar"],
        tags=["leading_indicator", "front_end_signal"],
    ),
    "final_denial_rate": _m(
        "final_denial_rate", "Final write-off denial rate",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="denials.write_off",
        mechanism=(
            "Share of claims that remain denied after appeal. Directly "
            "hits net revenue — these dollars never come back."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.REVENUE,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.2, bundled=0.5, vbp=0.7),
        parents=["initial_denial_rate", "avoidable_denial_pct"],
        children=["net_collection_rate", "bad_debt"],
        tags=["write_off", "revenue_leak"],
    ),
    "eligibility_denial_rate": _m(
        "eligibility_denial_rate", "Eligibility denial rate",
        domain=Domain.FRONT_END_ACCESS,
        subdomain="eligibility",
        mechanism=(
            "Share of claims denied because the payer no longer covers "
            "the patient at service time. Traces to registration / "
            "verification gaps — usually correctable with tooling."
        ),
        pathway=FinancialPathway.COST,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.3),
        parents=[],
        children=["denial_rate", "initial_denial_rate", "clean_claim_rate"],
        tags=["registration", "tooling_fixable"],
    ),
    "auth_denial_rate": _m(
        "auth_denial_rate", "Prior-authorization denial rate",
        domain=Domain.FRONT_END_ACCESS,
        subdomain="authorization",
        mechanism=(
            "Share of claims denied because prior auth was missing, "
            "late, or for the wrong service. Payers increasingly use "
            "AI reviewers (especially MA), so this can move quickly."
        ),
        pathway=FinancialPathway.RISK,
        reimb=_r(ffs=1.0, drg=0.9, cap=0.3),
        parents=[],
        children=["denial_rate", "initial_denial_rate"],
        tags=["ma_sensitive", "policy_sensitive"],
    ),
    "coding_denial_rate": _m(
        "coding_denial_rate", "Coding denial rate",
        domain=Domain.MIDDLE_CYCLE_CODING,
        subdomain="coding.accuracy",
        mechanism=(
            "Denials driven by incorrect or incomplete coding. "
            "Responds to CDI program investment."
        ),
        pathway=FinancialPathway.COST,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.2, bundled=0.6),
        parents=[],
        children=["denial_rate", "final_denial_rate"],
        tags=["cdi_lever"],
    ),
    "medical_necessity_denial_rate": _m(
        "medical_necessity_denial_rate", "Medical-necessity denial rate",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="denials.clinical",
        mechanism=(
            "Denials challenging whether the service was medically "
            "necessary. Heavy in MA; often involves appeals through "
            "peer-to-peer review."
        ),
        pathway=FinancialPathway.RISK,
        reimb=_r(ffs=0.8, drg=0.9, cap=0.4),
        parents=[],
        children=["denial_rate", "final_denial_rate"],
        tags=["appeals_heavy", "ma_sensitive"],
    ),
    "timely_filing_denial_rate": _m(
        "timely_filing_denial_rate", "Timely-filing denial rate",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="denials.workflow",
        mechanism=(
            "Denials because the claim wasn't submitted within the "
            "payer's window. Purely operational — not recoverable."
        ),
        pathway=FinancialPathway.REVENUE,
        reimb=_r(ffs=1.0, drg=1.0),
        parents=["discharged_not_final_billed_days"],
        children=["denial_rate", "final_denial_rate"],
        tags=["workflow_failure", "non_recoverable"],
    ),
    "avoidable_denial_pct": _m(
        "avoidable_denial_pct", "Avoidable denials %",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="denials.attribution",
        mechanism=(
            "Share of total denials that a competent RCM operation "
            "could have prevented. The headroom for denial-management "
            "programs."
        ),
        pathway=FinancialPathway.MIXED,
        reimb=_r(ffs=1.0, drg=1.0, vbp=0.7),
        parents=["eligibility_denial_rate", "auth_denial_rate",
                 "coding_denial_rate"],
        children=[],
        tags=["headroom_metric"],
    ),

    # ───── Front-end / claims flow ──────────────────────────────
    "clean_claim_rate": _m(
        "clean_claim_rate", "Clean claim rate",
        domain=Domain.FRONT_END_ACCESS,
        subdomain="claims_quality",
        mechanism=(
            "Share of claims submitted without edit failures. Front-end "
            "quality gate; inversely correlated with initial denials."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.MIXED,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.3),
        parents=["eligibility_denial_rate", "coding_denial_rate"],
        children=["initial_denial_rate", "first_pass_resolution_rate"],
        tags=["front_end_quality"],
    ),
    "first_pass_resolution_rate": _m(
        "first_pass_resolution_rate", "First-pass resolution rate",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="claims_flow",
        mechanism=(
            "Share of claims that pay on first submission. Combines "
            "clean claim rate with first-pass denials. High FPR means "
            "minimal rework and tight cash cycle."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.MIXED,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.2),
        parents=["clean_claim_rate", "initial_denial_rate"],
        children=["days_in_ar", "cost_to_collect"],
        tags=["operational_health"],
    ),

    # ───── AR / working capital ─────────────────────────────────
    "days_in_ar": _m(
        "days_in_ar", "Net days in accounts receivable",
        domain=Domain.WORKING_CAPITAL,
        subdomain="ar_cycle",
        mechanism=(
            "Cash-conversion cycle in days. Longer AR ties up working "
            "capital (financing drag at the hospital's cost of "
            "capital) and raises the probability of non-collection."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.WORKING_CAPITAL,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.3, bundled=0.7),
        parents=["initial_denial_rate", "first_pass_resolution_rate",
                 "discharged_not_final_billed_days"],
        children=["ar_over_90_pct", "net_collection_rate", "bad_debt"],
        tags=["cash_conversion", "financing_drag"],
        unit="days",
    ),
    "ar_over_90_pct": _m(
        "ar_over_90_pct", "A/R > 90 days %",
        domain=Domain.WORKING_CAPITAL,
        subdomain="ar_aging",
        mechanism=(
            "Aged A/R concentration. Heavy >90-day bucket signals "
            "collection breakdown or payer dispute backlog. Strong "
            "predictor of eventual write-off."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.RISK,
        reimb=_r(ffs=1.0, drg=1.0),
        parents=["days_in_ar"],
        children=["bad_debt", "final_denial_rate"],
        tags=["write_off_leading_indicator"],
    ),
    "discharged_not_final_billed_days": _m(
        "discharged_not_final_billed_days",
        "Discharged-not-final-billed (DNFB) days",
        domain=Domain.MIDDLE_CYCLE_CODING,
        subdomain="charge_capture",
        mechanism=(
            "Days between patient discharge and claim submission. "
            "Caused by coding backlog, charge capture delays, or "
            "documentation queries. Compresses the cash cycle."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.WORKING_CAPITAL,
        reimb=_r(ffs=1.0, drg=1.0),
        parents=[],
        children=["days_in_ar", "timely_filing_denial_rate"],
        tags=["coding_bottleneck"],
        unit="days",
    ),

    # ───── Collections / cost ────────────────────────────────────
    "net_collection_rate": _m(
        "net_collection_rate", "Net collection rate",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="collections",
        mechanism=(
            "Cash collected as a share of expected (post-contract) "
            "revenue. Ceiling on revenue realization; every point "
            "recovered is nearly pure EBITDA."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.REVENUE,
        reimb=_r(ffs=1.0, drg=1.0, cap=0.3, bundled=0.8, vbp=0.9),
        parents=["denial_rate", "final_denial_rate", "days_in_ar"],
        children=["net_revenue", "ebitda_margin"],
        tags=["revenue_ceiling"],
    ),
    "cost_to_collect": _m(
        "cost_to_collect", "Cost to collect",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="collections_cost",
        mechanism=(
            "RCM operations spend as a share of net revenue. Drops "
            "with automation, self-service payments, and lower denial "
            "volume."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.COST,
        reimb=_r(ffs=1.0, drg=0.9, cap=0.4),
        parents=["denial_rate", "first_pass_resolution_rate"],
        children=["ebitda_margin"],
        tags=["opex"],
    ),

    # ───── Financials ────────────────────────────────────────────
    "gross_revenue": _m(
        "gross_revenue", "Gross patient revenue",
        domain=Domain.PROFITABILITY,
        subdomain="revenue.gross",
        mechanism=(
            "Charge-based revenue before contractual allowances. "
            "Scale variable; not a KPI to optimize directly."
        ),
        direction=Directionality.DEPENDS,
        pathway=FinancialPathway.REVENUE,
        confidence=ConfidenceClass.OBSERVED,
        parents=[],
        children=["net_revenue"],
        tags=["scale"],
        unit="dollars",
    ),
    "net_revenue": _m(
        "net_revenue", "Net patient service revenue (NPSR)",
        domain=Domain.PROFITABILITY,
        subdomain="revenue.net",
        mechanism=(
            "Revenue after contractual allowances, bad debt, and "
            "charity. The top line partners actually model."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.REVENUE,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(ffs=1.0, drg=1.0, cap=1.0, bundled=1.0, vbp=1.0),
        parents=["gross_revenue", "net_collection_rate",
                 "case_mix_index", "payer_mix_commercial"],
        children=["ebitda", "ebitda_margin"],
        tags=["top_line"],
        unit="dollars",
    ),
    "ebitda": _m(
        "ebitda", "EBITDA",
        domain=Domain.PROFITABILITY,
        subdomain="ebitda",
        mechanism=(
            "Operating earnings before interest, tax, depreciation, "
            "amortization. The single number PE underwrites."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.REVENUE,
        confidence=ConfidenceClass.DERIVED,
        parents=["net_revenue", "cost_to_collect"],
        children=["ebitda_margin"],
        tags=["headline"],
        unit="dollars",
    ),
    "ebitda_margin": _m(
        "ebitda_margin", "EBITDA margin",
        domain=Domain.PROFITABILITY,
        subdomain="margin",
        mechanism=(
            "EBITDA ÷ net revenue. Sub-5% margins leave little room "
            "for RCM execution risk; >10% suggests a well-run "
            "operation."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.MIXED,
        confidence=ConfidenceClass.DERIVED,
        parents=["ebitda", "net_revenue", "net_collection_rate",
                 "cost_to_collect"],
        children=[],
        tags=["health_score"],
    ),

    # ───── Payer mix / coverage ──────────────────────────────────
    "payer_mix_commercial": _m(
        "payer_mix_commercial", "Payer mix — commercial %",
        domain=Domain.COVERAGE_PAYER_MIX,
        subdomain="commercial",
        mechanism=(
            "Share of revenue from commercial payers. Highest "
            "reimbursement per unit; enables payer-renegotiation "
            "leverage."
        ),
        direction=Directionality.DEPENDS,
        pathway=FinancialPathway.REVENUE,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(ffs=1.0, drg=0.2, cap=0.5, bundled=0.6, vbp=0.6),
        parents=[],
        children=["net_revenue"],
        tags=["reimbursement_leverage"],
    ),
    "payer_mix_medicare": _m(
        "payer_mix_medicare", "Payer mix — Medicare %",
        domain=Domain.COVERAGE_PAYER_MIX,
        subdomain="medicare",
        mechanism=(
            "Share of revenue from Medicare (FFS + MA combined in this "
            "definition). Exposure to IPPS/OPPS rulemaking, "
            "sequestration, and MA prior-auth friction."
        ),
        direction=Directionality.DEPENDS,
        pathway=FinancialPathway.RISK,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(ffs=1.0, drg=1.0, vbp=0.9),
        parents=[],
        children=["denial_rate", "case_mix_index"],
        tags=["policy_exposure"],
    ),
    "payer_mix_medicaid": _m(
        "payer_mix_medicaid", "Payer mix — Medicaid %",
        domain=Domain.COVERAGE_PAYER_MIX,
        subdomain="medicaid",
        mechanism=(
            "Share of revenue from Medicaid. Lowest reimbursement "
            "rates; OBBBA coverage-loss projections create material "
            "bad-debt pressure."
        ),
        direction=Directionality.DEPENDS,
        pathway=FinancialPathway.RISK,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(ffs=0.7, drg=0.8, cap=0.5),
        parents=[],
        children=["bad_debt", "net_revenue"],
        tags=["obbba_exposure", "bad_debt_driver"],
    ),
    "payer_mix_self_pay": _m(
        "payer_mix_self_pay", "Payer mix — self-pay %",
        domain=Domain.COVERAGE_PAYER_MIX,
        subdomain="self_pay",
        mechanism=(
            "Share of revenue from uninsured / self-pay patients. "
            "Highest bad-debt risk; amenable to charity-care + "
            "financial-assistance programs."
        ),
        direction=Directionality.DEPENDS,
        pathway=FinancialPathway.RISK,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(ffs=0.3),
        parents=[],
        children=["bad_debt"],
        tags=["uncompensated_care"],
    ),

    # ───── Coding / CMI ──────────────────────────────────────────
    "case_mix_index": _m(
        "case_mix_index", "Case mix index (CMI)",
        domain=Domain.MIDDLE_CYCLE_CODING,
        subdomain="acuity",
        mechanism=(
            "Weighted average DRG relative weight. Reflects both "
            "acuity of patients served and documentation completeness. "
            "Each 0.01 CMI point lifts Medicare revenue ~0.5-1% — a "
            "CDI program is the usual lever."
        ),
        direction=Directionality.HIGHER_IS_BETTER,
        pathway=FinancialPathway.REVENUE,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(drg=1.0, vbp=0.6),   # high under DRG; low elsewhere
        parents=["coding_denial_rate"],
        children=["net_revenue"],
        tags=["cdi_lever", "drg_sensitive"],
        unit="index",
    ),

    # ───── Bad debt ──────────────────────────────────────────────
    "bad_debt": _m(
        "bad_debt", "Bad debt %",
        domain=Domain.BACK_END_CLAIMS,
        subdomain="collections.write_off",
        mechanism=(
            "Uncollectible receivables written off. Driven by aging "
            "A/R, self-pay concentration, and Medicaid exposure."
        ),
        direction=Directionality.LOWER_IS_BETTER,
        pathway=FinancialPathway.COST,
        confidence=ConfidenceClass.OBSERVED,
        reimb=_r(ffs=0.9, drg=0.9, cap=0.3),
        parents=["ar_over_90_pct", "payer_mix_medicaid",
                 "payer_mix_self_pay"],
        children=["ebitda_margin"],
        tags=["write_off"],
    ),
}


# ── Causal graph builder ────────────────────────────────────────────

def causal_graph() -> CausalGraph:
    """Return the assembled :class:`CausalGraph` with nodes + edges.

    The edges are derived from each :class:`MetricDefinition`'s
    ``causal_parents`` list — every (parent, metric) pair becomes one
    :class:`MechanismEdge`. The explicit child lists are a
    human-readable redundancy; the edges come from parents so we don't
    duplicate truth.
    """
    graph = CausalGraph(nodes=dict(METRIC_ONTOLOGY))
    for metric_key, defn in METRIC_ONTOLOGY.items():
        for parent_key in defn.causal_parents:
            if parent_key not in METRIC_ONTOLOGY:
                # Tolerate dangling parents (e.g. external inputs).
                continue
            graph.edges.append(MechanismEdge(
                parent=parent_key,
                child=metric_key,
                effect_direction=_infer_effect_direction(
                    METRIC_ONTOLOGY[parent_key], defn,
                ),
                magnitude_hint="moderate",
                mechanism=defn.economic_mechanism.split(".")[0][:80],
            ))
    return graph


def _infer_effect_direction(
    parent: MetricDefinition, child: MetricDefinition,
) -> str:
    """Best-effort sign of the parent→child relationship using the
    per-metric directionality hints. Not always right in complex
    relationships; callers should override when a curated edge needs a
    specific sign."""
    if parent.directionality == Directionality.HIGHER_IS_BETTER and \
       child.directionality == Directionality.LOWER_IS_BETTER:
        return "-"
    if parent.directionality == Directionality.LOWER_IS_BETTER and \
       child.directionality == Directionality.HIGHER_IS_BETTER:
        return "-"
    return "+"


# ── Public lookups ───────────────────────────────────────────────────

def classify_metric(metric_key: str) -> MetricDefinition:
    """Return the :class:`MetricDefinition` for ``metric_key`` or raise
    :class:`KeyError`.

    Never returns ``None`` — we want callers to fail loudly if they
    reference a metric that isn't in the ontology yet, so new metrics
    aren't silently orphaned.
    """
    defn = METRIC_ONTOLOGY.get(metric_key)
    if defn is None:
        raise KeyError(
            f"metric {metric_key!r} not in econ_ontology. Add an entry "
            f"to METRIC_ONTOLOGY before using it in production code."
        )
    return defn


def _reimb_summary(profile: MetricReimbursementSensitivity) -> str:
    """Short prose summary of which reimbursement regimes matter most."""
    slots = [
        ("fee-for-service", profile.fee_for_service),
        ("Medicare DRG / IPPS", profile.prospective_drg),
        ("capitated", profile.capitated),
        ("bundled", profile.bundled),
        ("value-based", profile.value_based),
    ]
    slots = [(name, s) for name, s in slots if s > 0]
    if not slots:
        return "reimbursement exposure is minimal under all studied regimes"
    slots.sort(key=lambda t: t[1], reverse=True)
    parts = []
    for name, s in slots[:3]:
        tier = "high" if s >= 0.8 else "moderate" if s >= 0.4 else "low"
        parts.append(f"{tier} under {name}")
    return "; ".join(parts)


def explain_causal_path(metric_key: str) -> str:
    """Plain-English paragraph: where the metric sits, what drives it,
    how it flows into the P&L, and how reimbursement regime affects
    its economic weight.

    Designed for the provenance tooltip in the workbench — terse
    enough to fit in ~200 words, specific enough to be useful.
    """
    try:
        defn = classify_metric(metric_key)
    except KeyError:
        return f"{metric_key} is not classified in the economic ontology."

    graph = causal_graph()
    parents = graph.parents_of(metric_key)
    children = graph.children_of(metric_key)

    parent_names = [p.display_name.lower() for p in parents]
    child_names = [c.display_name.lower() for c in children]

    pathway_narrative = {
        FinancialPathway.REVENUE: "the top line",
        FinancialPathway.COST: "operating cost",
        FinancialPathway.WORKING_CAPITAL: "cash / working capital",
        FinancialPathway.RISK: "tail risk (potential write-off)",
        FinancialPathway.MIXED: "both revenue and cost lines",
    }[defn.financial_pathway]

    direction_note = {
        Directionality.HIGHER_IS_BETTER: "higher is better",
        Directionality.LOWER_IS_BETTER: "lower is better",
        Directionality.DEPENDS: "direction depends on strategic context",
    }[defn.directionality]

    drivers = (
        f"Drivers typically include {', '.join(parent_names)}."
        if parent_names else "No upstream drivers modeled in the ontology."
    )
    downstream = (
        f"Downstream effects land in {', '.join(child_names)}."
        if child_names else "No downstream effects modeled yet."
    )

    reimb = _reimb_summary(defn.reimbursement_sensitivity)
    tags = ", ".join(defn.mechanism_tags) if defn.mechanism_tags else "—"

    return (
        f"{defn.display_name} sits in the {defn.domain.value.replace('_', ' ')} "
        f"domain ({defn.subdomain}). "
        f"{defn.economic_mechanism} "
        f"{drivers} {downstream} "
        f"It moves {pathway_narrative} — {direction_note}. "
        f"Reimbursement sensitivity: {reimb}. "
        f"Mechanism tags: {tags}."
    )
