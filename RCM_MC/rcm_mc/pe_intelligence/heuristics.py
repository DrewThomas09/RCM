"""PE heuristics — codified rules of thumb a senior partner uses.

A heuristic is a triggerable rule: given a packet (or a bag of
metrics), fire a titled, severity-stamped finding if the pattern
matches. These are NOT band checks (those live in
:mod:`reasonableness`). Heuristics codify *advice* — "if you see X,
worry about Y".

Each heuristic is small, pure, and self-contained. It receives the
same ``HeuristicContext`` as every other heuristic and returns either
``None`` (did not fire) or a :class:`HeuristicHit`. The orchestrator
:func:`run_heuristics` calls every registered heuristic and returns
the list of hits, highest severity first.

The full catalog is also written into ``docs/PE_HEURISTICS.md`` as a
living doc. When you add or tune a heuristic here, update that file in
the same commit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ── Severity ──────────────────────────────────────────────────────────

SEV_INFO = "INFO"
SEV_LOW = "LOW"
SEV_MEDIUM = "MEDIUM"
SEV_HIGH = "HIGH"
SEV_CRITICAL = "CRITICAL"

_SEVERITY_ORDER = {SEV_INFO: 0, SEV_LOW: 1, SEV_MEDIUM: 2, SEV_HIGH: 3, SEV_CRITICAL: 4}


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class HeuristicContext:
    """Everything a heuristic might need, in one bag.

    The ``partner_review`` entry point fills this from a packet; tests
    construct it directly.
    """
    # Payer + size
    payer_mix: Dict[str, float] = field(default_factory=dict)
    ebitda_m: Optional[float] = None          # current EBITDA in $M
    revenue_m: Optional[float] = None         # current revenue in $M
    bed_count: Optional[int] = None
    hospital_type: Optional[str] = None
    state: Optional[str] = None
    urban_rural: Optional[str] = None
    teaching_status: Optional[str] = None

    # Operating KPIs (current / benchmarks)
    denial_rate: Optional[float] = None             # fraction, not bps
    final_writeoff_rate: Optional[float] = None
    days_in_ar: Optional[float] = None
    clean_claim_rate: Optional[float] = None
    case_mix_index: Optional[float] = None
    ebitda_margin: Optional[float] = None

    # Model assumptions
    exit_multiple: Optional[float] = None
    entry_multiple: Optional[float] = None
    hold_years: Optional[float] = None
    projected_irr: Optional[float] = None
    projected_moic: Optional[float] = None

    # Projections — lever claims over the hold
    denial_improvement_bps_per_yr: Optional[float] = None
    ar_reduction_days_per_yr: Optional[float] = None
    revenue_growth_pct_per_yr: Optional[float] = None
    margin_expansion_bps_per_yr: Optional[float] = None

    # Deal structure
    deal_structure: Optional[str] = None            # "FFS" | "capitation" | "VBC" | "hybrid"
    leverage_multiple: Optional[float] = None       # net debt / EBITDA at close
    covenant_headroom_pct: Optional[float] = None

    # Data-quality signals
    data_coverage_pct: Optional[float] = None
    has_case_mix_data: bool = True


@dataclass
class Heuristic:
    """Metadata describing one rule; the ``fn`` is how it fires."""
    id: str
    title: str
    description: str
    category: str                        # "PAYER" | "OPERATIONS" | "VALUATION" | "STRUCTURE" | "DATA"
    default_severity: str                # maximum severity when the rule fires fully
    fn: Callable[[HeuristicContext], Optional["HeuristicHit"]] = field(repr=False)

    def run(self, ctx: HeuristicContext) -> Optional["HeuristicHit"]:
        return self.fn(ctx)


@dataclass
class HeuristicHit:
    id: str
    title: str
    severity: str
    category: str
    finding: str                 # 1-2 sentences, what the rule detected
    partner_voice: str           # how the partner would phrase the pushback
    trigger_metrics: List[str] = field(default_factory=list)
    trigger_values: Dict[str, float] = field(default_factory=dict)
    remediation: str = ""        # action the deal team should take
    references: List[str] = field(default_factory=list)

    def severity_rank(self) -> int:
        return _SEVERITY_ORDER.get(self.severity, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "category": self.category,
            "finding": self.finding,
            "partner_voice": self.partner_voice,
            "trigger_metrics": list(self.trigger_metrics),
            "trigger_values": {k: float(v) for k, v in self.trigger_values.items()},
            "remediation": self.remediation,
            "references": list(self.references),
        }


# ── Helpers ──────────────────────────────────────────────────────────

def _norm_mix(mix: Dict[str, float]) -> Dict[str, float]:
    """Normalize payer-mix keys lowercased and values fractions."""
    if not mix:
        return {}
    low = {str(k).lower().strip(): float(v) for k, v in mix.items()
           if v is not None}
    total = sum(low.values())
    if total > 1.5:
        return {k: v / 100.0 for k, v in low.items()}
    return low


# ── Heuristic implementations ────────────────────────────────────────

def _h_medicare_heavy_multiple_ceiling(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    mix = _norm_mix(ctx.payer_mix)
    medicare = mix.get("medicare", 0.0)
    if medicare < 0.60:
        return None
    if ctx.exit_multiple is None:
        return None
    if ctx.exit_multiple <= 9.5:
        return None
    severity = SEV_HIGH if ctx.exit_multiple > 11.0 else SEV_MEDIUM
    return HeuristicHit(
        id="medicare_heavy_multiple_ceiling",
        title="Medicare-heavy deal assumes above-peer exit multiple",
        severity=severity,
        category="VALUATION",
        finding=(
            f"Medicare is {medicare * 100:.0f}% of payer mix and the model "
            f"exits at {ctx.exit_multiple:.2f}x. Medicare-heavy hospitals "
            f"have rarely traded above ~9.5x in recent comps."
        ),
        partner_voice=(
            "Show me one closed comp with a Medicare mix this high that "
            "cleared this multiple. If you can't, reset exit to 8.5–9.0x "
            "and tell me if the deal still clears the hurdle."
        ),
        trigger_metrics=["payer_mix.medicare", "exit_multiple"],
        trigger_values={"medicare_share": medicare, "exit_multiple": ctx.exit_multiple},
        remediation="Cap exit multiple at 9.0x in base case; keep 10.5x in upside only.",
        references=["PE_HEURISTICS#medicare-heavy-ceiling"],
    )


def _h_aggressive_denial_improvement(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    bps = ctx.denial_improvement_bps_per_yr
    if bps is None or bps <= 0:
        return None
    if bps <= 200:
        return None
    if bps <= 350:
        severity = SEV_MEDIUM
    elif bps <= 600:
        severity = SEV_HIGH
    else:
        severity = SEV_CRITICAL
    return HeuristicHit(
        id="aggressive_denial_improvement",
        title="Denial-rate improvement outpaces realistic ramp",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Plan assumes {bps:.0f} bps/yr denial-rate improvement. Mature "
            "RCM programs deliver 150–200 bps/yr; above that is stretch, "
            "and >600 bps/yr is not something we've seen sustain."
        ),
        partner_voice=(
            "If the seller's current denial rate is high, you'll get the "
            "first 200 bps from obvious edits. Beyond that you need a "
            "platform change, and that takes 18–24 months, not 12."
        ),
        trigger_metrics=["denial_improvement_bps_per_yr"],
        trigger_values={"denial_improvement_bps_per_yr": bps},
        remediation="Haircut years 2+ denial improvement by 40%; move the stretch into upside.",
        references=["PE_HEURISTICS#denial-improvement-ramp"],
    )


def _h_capitation_needs_different_math(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    structure = (ctx.deal_structure or "").lower().strip()
    if structure not in ("capitation", "cap", "vbc", "value_based_care", "value-based"):
        return None
    # If modeled with FFS-like growth assumptions, flag.
    rev_growth = ctx.revenue_growth_pct_per_yr
    if rev_growth is None:
        return None
    if rev_growth <= 4.0:
        return None
    return HeuristicHit(
        id="capitation_vbc_uses_ffs_growth",
        title="Capitation / VBC deal is modeled with FFS-style growth",
        severity=SEV_HIGH,
        category="STRUCTURE",
        finding=(
            f"Deal structure is {structure.upper()} but the projection "
            f"assumes {rev_growth:.1f}% annual revenue growth. Capitated "
            "revenue growth is tied to member growth and PMPM resets, not "
            "volume * rate. The math is structurally different."
        ),
        partner_voice=(
            "In cap/VBC you don't grow revenue by seeing more patients — "
            "you grow by adding lives and hitting shared-savings thresholds. "
            "Re-model this as member growth + PMPM, or don't underwrite it."
        ),
        trigger_metrics=["deal_structure", "revenue_growth_pct_per_yr"],
        trigger_values={"revenue_growth_pct_per_yr": rev_growth},
        remediation="Rebuild the revenue stack: members × PMPM × (1 - MLR) + shared savings.",
        references=["PE_HEURISTICS#capitation-vbc-math"],
    )


def _h_multiple_expansion_carrying_return(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.entry_multiple is None or ctx.exit_multiple is None:
        return None
    expansion = ctx.exit_multiple - ctx.entry_multiple
    if expansion < 1.0:
        return None
    # Only flag if expansion is a non-trivial share of entry.
    ratio = expansion / max(ctx.entry_multiple, 1.0)
    if ratio < 0.15:
        return None
    severity = SEV_MEDIUM if ratio < 0.30 else SEV_HIGH
    return HeuristicHit(
        id="multiple_expansion_carrying_return",
        title="Return leans on multiple expansion, not operating alpha",
        severity=severity,
        category="VALUATION",
        finding=(
            f"Entering at {ctx.entry_multiple:.2f}x, exiting at "
            f"{ctx.exit_multiple:.2f}x — that's {expansion:.2f}x ({ratio*100:.0f}%) "
            "of expansion in the model."
        ),
        partner_voice=(
            "Multiple expansion is the first thing that compresses in a bad "
            "cycle. Show me the return at a flat entry/exit multiple. If it "
            "still clears, we have a deal; if not, we're betting on the market."
        ),
        trigger_metrics=["entry_multiple", "exit_multiple"],
        trigger_values={"entry": ctx.entry_multiple, "exit": ctx.exit_multiple, "delta": expansion},
        remediation="Run a same-multiple sensitivity; underwrite expansion only with a named comp.",
        references=["PE_HEURISTICS#multiple-expansion-discipline"],
    )


def _h_margin_jump_implausible(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    bps = ctx.margin_expansion_bps_per_yr
    if bps is None:
        return None
    if bps <= 200:
        return None
    severity = SEV_MEDIUM if bps <= 400 else SEV_HIGH
    return HeuristicHit(
        id="margin_expansion_too_fast",
        title="Margin expansion per year exceeds realistic peer rates",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Plan assumes {bps:.0f} bps/yr EBITDA margin expansion. Healthy "
            "ops programs deliver 100–200 bps/yr; >400 bps/yr is usually "
            "a repricing or a divestiture story, not operating improvement."
        ),
        partner_voice=(
            "If you're claiming 400+ bps of margin per year, you're either "
            "repricing labor, cutting a service line, or double-counting RCM "
            "lift into cost takeout. Which one — and is it real?"
        ),
        trigger_metrics=["margin_expansion_bps_per_yr"],
        trigger_values={"margin_expansion_bps_per_yr": bps},
        remediation="Split margin plan into labor, RCM, service-line mix, pricing. Don't let them overlap.",
        references=["PE_HEURISTICS#margin-expansion-ceiling"],
    )


def _h_leverage_too_high_for_medicare(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.leverage_multiple is None:
        return None
    mix = _norm_mix(ctx.payer_mix)
    medicare = mix.get("medicare", 0.0)
    medicaid = mix.get("medicaid", 0.0)
    govt = medicare + medicaid
    # Government-heavy deals cannot sustain 6.0x+ leverage through a
    # bad reimbursement year.
    if govt < 0.60:
        return None
    if ctx.leverage_multiple <= 5.5:
        return None
    severity = SEV_HIGH if ctx.leverage_multiple <= 6.5 else SEV_CRITICAL
    return HeuristicHit(
        id="leverage_too_high_govt_mix",
        title="Leverage at close is too high for a government-heavy payer mix",
        severity=severity,
        category="STRUCTURE",
        finding=(
            f"Net debt / EBITDA = {ctx.leverage_multiple:.2f}x at close with "
            f"{govt*100:.0f}% government payers. A single rate cycle or "
            "sequestration extension can wipe out covenant headroom."
        ),
        partner_voice=(
            "If CMS cuts the rate update by 100 bps, where does EBITDA "
            "land? If that breaks covenant, the cap structure is wrong — "
            "not the rate cut."
        ),
        trigger_metrics=["leverage_multiple", "payer_mix.medicare", "payer_mix.medicaid"],
        trigger_values={
            "leverage_multiple": ctx.leverage_multiple,
            "govt_share": govt,
        },
        remediation="Lower debt to ≤5.5x at close or negotiate covenant-lite terms.",
        references=["PE_HEURISTICS#leverage-by-payer-mix"],
    )


def _h_covenant_headroom_tight(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.covenant_headroom_pct is None:
        return None
    if ctx.covenant_headroom_pct >= 0.20:
        return None
    severity = SEV_HIGH if ctx.covenant_headroom_pct < 0.10 else SEV_MEDIUM
    return HeuristicHit(
        id="covenant_headroom_tight",
        title="Covenant headroom is tight at close",
        severity=severity,
        category="STRUCTURE",
        finding=(
            f"Headroom is {ctx.covenant_headroom_pct*100:.1f}% against the "
            "maintenance covenant. Below 20% and you're one bad quarter "
            "from a waiver conversation."
        ),
        partner_voice=(
            "I don't mind tight covenants if the cash conversion is clean. "
            "But if you need a single quarter of working-capital release to "
            "make it, that's not headroom — that's luck."
        ),
        trigger_metrics=["covenant_headroom_pct"],
        trigger_values={"covenant_headroom_pct": ctx.covenant_headroom_pct},
        remediation="Negotiate a 25%+ headroom or equity cure right.",
        references=["PE_HEURISTICS#covenant-headroom"],
    )


def _h_data_coverage_too_low(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.data_coverage_pct is None:
        return None
    if ctx.data_coverage_pct >= 0.60:
        return None
    severity = SEV_HIGH if ctx.data_coverage_pct < 0.40 else SEV_MEDIUM
    return HeuristicHit(
        id="insufficient_data_coverage",
        title="Data coverage is too low for a reliable underwrite",
        severity=severity,
        category="DATA",
        finding=(
            f"Only {ctx.data_coverage_pct*100:.0f}% of the metric set is "
            "populated from observed/extracted sources. The rest is "
            "predicted or benchmark — which is fine for triage, not for IC."
        ),
        partner_voice=(
            "We don't underwrite benchmarks. Tell the seller we need the "
            "payer mix detail, the denial ledger, and two years of AR "
            "aging before we can name a number."
        ),
        trigger_metrics=["data_coverage_pct"],
        trigger_values={"data_coverage_pct": ctx.data_coverage_pct},
        remediation="Escalate data request; do not pencil a bid against imputed metrics.",
        references=["PE_HEURISTICS#data-coverage-minimum"],
    )


def _h_case_mix_missing(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.has_case_mix_data:
        return None
    if (ctx.hospital_type or "").lower() in ("asc", "outpatient", "clinic"):
        return None  # CMI is hospital-specific
    return HeuristicHit(
        id="case_mix_missing",
        title="Case Mix Index is missing on an acute-care underwrite",
        severity=SEV_MEDIUM,
        category="DATA",
        finding=(
            "CMI is absent from the metric set. For acute-care deals, CMI "
            "drives DRG-level reimbursement and acuity-adjusted peer comps."
        ),
        partner_voice=(
            "How do you benchmark reimbursement without CMI? Get it from "
            "HCRIS Worksheet S-3 before you finish the model."
        ),
        trigger_metrics=["case_mix_index"],
        remediation="Pull CMI from HCRIS or seller data room before running the bridge.",
        references=["PE_HEURISTICS#case-mix-required"],
    )


def _h_ar_days_above_peer(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.days_in_ar is None:
        return None
    if ctx.days_in_ar <= 55:
        return None
    severity = SEV_MEDIUM if ctx.days_in_ar <= 70 else SEV_HIGH
    return HeuristicHit(
        id="ar_days_above_peer",
        title="Days in AR is above peer median — working-capital drag",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Days in AR is {ctx.days_in_ar:.1f}. Acute-care peer median is "
            "45–55 days; above 70 is a symptom, not a number."
        ),
        partner_voice=(
            "High AR days is either a billing problem or a payer problem. "
            "Which is it? The fix path is very different for each."
        ),
        trigger_metrics=["days_in_ar"],
        trigger_values={"days_in_ar": ctx.days_in_ar},
        remediation="Diagnose AR aging buckets; map the cure path before committing to the lever.",
        references=["PE_HEURISTICS#ar-days-diagnosis"],
    )


def _h_denial_rate_elevated(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.denial_rate is None:
        return None
    if ctx.denial_rate <= 0.10:
        return None
    severity = SEV_MEDIUM if ctx.denial_rate <= 0.14 else SEV_HIGH
    return HeuristicHit(
        id="denial_rate_elevated",
        title="Initial denial rate is elevated — upside opportunity with caveats",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Initial denial rate is {ctx.denial_rate*100:.1f}%. Peer median "
            "is 8–10%; above 14% is a systemic intake/eligibility problem, "
            "not just a write-off story."
        ),
        partner_voice=(
            "Yes this is a lever — but only if the denial reason codes "
            "concentrate. If the top 10 codes are <60% of volume, there's "
            "no single fix."
        ),
        trigger_metrics=["denial_rate"],
        trigger_values={"denial_rate": ctx.denial_rate},
        remediation="Get denial-reason-code concentration; validate top-10 accounts for ≥60% before underwriting fix.",
        references=["PE_HEURISTICS#denial-concentration"],
    )


def _h_small_deal_mega_irr(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.ebitda_m is None or ctx.projected_irr is None:
        return None
    if ctx.ebitda_m >= 25.0:
        return None
    if ctx.projected_irr < 0.40:
        return None
    severity = SEV_HIGH if ctx.projected_irr >= 0.50 else SEV_MEDIUM
    return HeuristicHit(
        id="small_deal_mega_irr",
        title="Small deal IRR is unusually high — dispersion risk",
        severity=severity,
        category="VALUATION",
        finding=(
            f"${ctx.ebitda_m:.1f}M EBITDA deal with a projected {ctx.projected_irr*100:.1f}% IRR. "
            "Small deals show high dispersion — median > 40% is rare and "
            "usually means the entry multiple is understated."
        ),
        partner_voice=(
            "Small-deal IRRs look great on paper until you realize half "
            "the dispersion is execution risk you can't diversify away. "
            "Size the equity check accordingly."
        ),
        trigger_metrics=["ebitda_m", "projected_irr"],
        trigger_values={"ebitda_m": ctx.ebitda_m, "projected_irr": ctx.projected_irr},
        remediation="Stress the entry multiple +1 turn; re-check IRR distribution, not just the point estimate.",
        references=["PE_HEURISTICS#small-deal-dispersion"],
    )


def _h_hold_too_short_for_rcm_levers(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.hold_years is None:
        return None
    # Only relevant if the deal leans on RCM levers.
    has_rcm_lever = any(
        v is not None and v > 0 for v in (
            ctx.denial_improvement_bps_per_yr,
            ctx.ar_reduction_days_per_yr,
        )
    )
    if not has_rcm_lever:
        return None
    if ctx.hold_years >= 4.0:
        return None
    return HeuristicHit(
        id="hold_too_short_for_rcm",
        title="Hold period is too short to realize RCM levers",
        severity=SEV_MEDIUM,
        category="STRUCTURE",
        finding=(
            f"Hold is {ctx.hold_years:.1f} years and the thesis leans on "
            "RCM levers. Denial + AR programs take 18-24 months to mature; "
            "a sub-4-year hold gives the exit story 1-2 years of run-rate, "
            "not the full curve."
        ),
        partner_voice=(
            "If the RCM lever is the alpha, a 3-year hold leaves the "
            "second-stage cash for the buyer. Either extend the hold or "
            "don't pay for the full lever."
        ),
        trigger_metrics=["hold_years"],
        trigger_values={"hold_years": ctx.hold_years},
        remediation="Target 4-5yr hold or discount lever NPV by 30-40% to reflect exit timing.",
        references=["PE_HEURISTICS#hold-length-for-rcm"],
    )


def _h_writeoff_high_absolute(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.final_writeoff_rate is None:
        return None
    if ctx.final_writeoff_rate <= 0.06:
        return None
    severity = SEV_MEDIUM if ctx.final_writeoff_rate <= 0.09 else SEV_HIGH
    return HeuristicHit(
        id="writeoff_rate_high",
        title="Final write-off rate is elevated — margin drag",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Final write-off rate is {ctx.final_writeoff_rate*100:.1f}%. "
            "Top-quartile RCM shops run <4%; above 9% is a leak, not an "
            "operating norm."
        ),
        partner_voice=(
            "Every 100 bps of write-off at a $200M revenue hospital is "
            "$2M of EBITDA. What's the root cause — eligibility, coding, "
            "or timely filing?"
        ),
        trigger_metrics=["final_writeoff_rate"],
        trigger_values={"final_writeoff_rate": ctx.final_writeoff_rate},
        remediation="Bucket write-offs by reason code; size lever per bucket.",
        references=["PE_HEURISTICS#writeoff-benchmarks"],
    )


def _h_rural_critical_access_caveat(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    htype = (ctx.hospital_type or "").lower()
    if htype not in ("critical_access", "cah", "critical-access"):
        return None
    return HeuristicHit(
        id="critical_access_reimbursement",
        title="Critical Access Hospital — 101%-cost reimbursement model",
        severity=SEV_MEDIUM,
        category="PAYER",
        finding=(
            "CAH facilities are reimbursed at 101% of allowable Medicare "
            "cost. Operating levers that reduce cost reduce revenue almost "
            "1:1 — the RCM playbook is fundamentally different."
        ),
        partner_voice=(
            "You can't cost-cut your way to margin in a CAH. If the thesis "
            "is operating improvement, we're not in the right business."
        ),
        trigger_metrics=["hospital_type"],
        remediation="Restructure thesis around service-line mix, outpatient volume, or scale — not cost takeout.",
        references=["PE_HEURISTICS#cah-reimbursement"],
    )


def _h_high_moic_short_hold(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.projected_moic is None or ctx.hold_years is None:
        return None
    if ctx.hold_years <= 0 or ctx.projected_moic < 2.5:
        return None
    # Implied CAGR
    try:
        cagr = ctx.projected_moic ** (1.0 / ctx.hold_years) - 1.0
    except (ValueError, ZeroDivisionError):
        return None
    if cagr <= 0.28:
        return None
    severity = SEV_MEDIUM if cagr <= 0.36 else SEV_HIGH
    return HeuristicHit(
        id="moic_cagr_too_high",
        title="Implied MOIC CAGR is above top-quartile peer returns",
        severity=severity,
        category="VALUATION",
        finding=(
            f"{ctx.projected_moic:.2f}x MOIC over {ctx.hold_years:.1f} years "
            f"implies a {cagr*100:.1f}% CAGR on invested equity. Top-quartile "
            "healthcare PE funds land in the 25-30% range; above that, the "
            "model is underwriting luck."
        ),
        partner_voice=(
            "Take any single leg of that — entry multiple, exit multiple, "
            "EBITDA ramp — and shock it 15%. If MOIC drops below 2.0x the "
            "story is too fragile to fund."
        ),
        trigger_metrics=["projected_moic", "hold_years"],
        trigger_values={"moic": ctx.projected_moic, "hold_years": ctx.hold_years, "implied_cagr": cagr},
        remediation="Run three-way sensitivity (entry / exit / ramp); require 2.0x floor.",
        references=["PE_HEURISTICS#moic-cagr-ceiling"],
    )


def _h_teaching_hospital_complexity(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    teach = (ctx.teaching_status or "").lower()
    if teach not in ("major", "academic", "major_teaching", "aamc"):
        return None
    return HeuristicHit(
        id="teaching_hospital_complexity",
        title="Major teaching hospital — resident slots and GME cap apply",
        severity=SEV_LOW,
        category="PAYER",
        finding=(
            "Major teaching facility. GME/IME payments and resident-slot "
            "caps drive a material slice of reimbursement and cannot be "
            "modeled as normal DRG revenue."
        ),
        partner_voice=(
            "Separate GME from the RCM bridge entirely. It's regulated, "
            "non-operational, and does not respond to our levers."
        ),
        trigger_metrics=["teaching_status"],
        remediation="Carve GME/IME out of the bridge; forecast separately with CMS update rules.",
        references=["PE_HEURISTICS#teaching-carve-out"],
    )


def _h_ar_reduction_aggressive(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    days = ctx.ar_reduction_days_per_yr
    if days is None or days <= 0:
        return None
    if days <= 8:
        return None
    severity = SEV_MEDIUM if days <= 15 else SEV_HIGH
    return HeuristicHit(
        id="ar_reduction_aggressive",
        title="AR days reduction per year is aggressive for a single-program fix",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Plan assumes {days:.1f} days/yr AR reduction. Realistic range "
            "is 5–8 days/yr for a focused program; >15 implies a billing-"
            "system replacement, not a tuning project."
        ),
        partner_voice=(
            "Ten days of AR reduction sounds great. What's the capex to "
            "deliver it? If the answer is 'none', you're overestimating."
        ),
        trigger_metrics=["ar_reduction_days_per_yr"],
        trigger_values={"ar_reduction_days_per_yr": days},
        remediation="Pair the AR lever with a specific capex line; haircut years 2+.",
        references=["PE_HEURISTICS#ar-reduction-bands"],
    )


def _h_single_state_concentration(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Single-state safety-net exposure — flag high Medicaid concentration
    in states with unstable rates."""
    mix = _norm_mix(ctx.payer_mix)
    medicaid = mix.get("medicaid", 0.0)
    if medicaid < 0.30 or not ctx.state:
        return None
    # States with repeated rate freezes or pending rate changes.
    volatile_states = {"IL", "NY", "CA", "LA", "OK", "MS", "AR"}
    if ctx.state.upper() not in volatile_states:
        return None
    return HeuristicHit(
        id="state_medicaid_volatility",
        title="Medicaid-heavy in a state with historical rate volatility",
        severity=SEV_MEDIUM,
        category="PAYER",
        finding=(
            f"{medicaid*100:.0f}% Medicaid mix in {ctx.state}. This state "
            "has had multiple rate freezes or pending changes in recent "
            "years — base-case Medicaid rate growth should be 0% not +2-3%."
        ),
        partner_voice=(
            "I don't pay for Medicaid rate growth in this state. If the "
            "model assumes it, pull it out before we price."
        ),
        trigger_metrics=["payer_mix.medicaid", "state"],
        trigger_values={"medicaid_share": medicaid},
        remediation="Flat-line Medicaid rate growth in base case.",
        references=["PE_HEURISTICS#state-rate-volatility"],
    )


# ── Registry ──────────────────────────────────────────────────────────

def all_heuristics() -> List[Heuristic]:
    """Return every registered heuristic. Order is stable and used by
    tests — new heuristics append at the end."""
    return [
        Heuristic(
            id="medicare_heavy_multiple_ceiling",
            title="Medicare-heavy exit multiple ceiling",
            description="If Medicare ≥ 60% of payer mix, exit multiples > 9.5x are hard to defend.",
            category="VALUATION",
            default_severity=SEV_HIGH,
            fn=_h_medicare_heavy_multiple_ceiling,
        ),
        Heuristic(
            id="aggressive_denial_improvement",
            title="Denial-rate improvement > 200 bps/yr",
            description="Denial programs deliver ~150-200 bps/yr; above that is stretch.",
            category="OPERATIONS",
            default_severity=SEV_HIGH,
            fn=_h_aggressive_denial_improvement,
        ),
        Heuristic(
            id="capitation_vbc_uses_ffs_growth",
            title="Capitation / VBC modeled with FFS math",
            description="Capitated / VBC revenue must be modeled as lives × PMPM, not volume × rate.",
            category="STRUCTURE",
            default_severity=SEV_HIGH,
            fn=_h_capitation_needs_different_math,
        ),
        Heuristic(
            id="multiple_expansion_carrying_return",
            title="Multiple expansion is carrying the return",
            description="Expansion > 15% of entry multiple — deal leans on market, not operating alpha.",
            category="VALUATION",
            default_severity=SEV_HIGH,
            fn=_h_multiple_expansion_carrying_return,
        ),
        Heuristic(
            id="margin_expansion_too_fast",
            title="Margin expansion > 200 bps/yr",
            description="Margin programs deliver ~100-200 bps/yr; >400 is usually repricing, not ops.",
            category="OPERATIONS",
            default_severity=SEV_HIGH,
            fn=_h_margin_jump_implausible,
        ),
        Heuristic(
            id="leverage_too_high_govt_mix",
            title="Leverage too high for government-heavy payer mix",
            description="Government-heavy deals shouldn't carry > 5.5x net debt at close.",
            category="STRUCTURE",
            default_severity=SEV_CRITICAL,
            fn=_h_leverage_too_high_for_medicare,
        ),
        Heuristic(
            id="covenant_headroom_tight",
            title="Covenant headroom < 20%",
            description="Tight covenants + single-quarter surprise = waiver conversation.",
            category="STRUCTURE",
            default_severity=SEV_HIGH,
            fn=_h_covenant_headroom_tight,
        ),
        Heuristic(
            id="insufficient_data_coverage",
            title="Data coverage too low",
            description="< 60% observed/extracted metrics — do not pencil IC bid.",
            category="DATA",
            default_severity=SEV_HIGH,
            fn=_h_data_coverage_too_low,
        ),
        Heuristic(
            id="case_mix_missing",
            title="Missing CMI on acute-care deal",
            description="Hospital underwrite without CMI is not defensible.",
            category="DATA",
            default_severity=SEV_MEDIUM,
            fn=_h_case_mix_missing,
        ),
        Heuristic(
            id="ar_days_above_peer",
            title="Days in AR above peer median",
            description="AR days > 55 is a symptom; > 70 needs a named root cause.",
            category="OPERATIONS",
            default_severity=SEV_HIGH,
            fn=_h_ar_days_above_peer,
        ),
        Heuristic(
            id="denial_rate_elevated",
            title="Initial denial rate > 10%",
            description="Elevated denial is an opportunity if reason codes concentrate.",
            category="OPERATIONS",
            default_severity=SEV_HIGH,
            fn=_h_denial_rate_elevated,
        ),
        Heuristic(
            id="small_deal_mega_irr",
            title="Small deal with IRR > 40%",
            description="Small-deal high IRR is often entry-multiple understated.",
            category="VALUATION",
            default_severity=SEV_HIGH,
            fn=_h_small_deal_mega_irr,
        ),
        Heuristic(
            id="hold_too_short_for_rcm",
            title="Hold < 4yr with RCM-driven thesis",
            description="RCM programs take 18-24 months to mature; short hold leaves value on table.",
            category="STRUCTURE",
            default_severity=SEV_MEDIUM,
            fn=_h_hold_too_short_for_rcm_levers,
        ),
        Heuristic(
            id="writeoff_rate_high",
            title="Final write-off rate > 6%",
            description="Above 6% is a leak; above 9% needs root-cause diagnosis.",
            category="OPERATIONS",
            default_severity=SEV_HIGH,
            fn=_h_writeoff_high_absolute,
        ),
        Heuristic(
            id="critical_access_reimbursement",
            title="CAH 101%-cost reimbursement",
            description="CAH deals cannot be cost-cut to margin; thesis must be mix or scale.",
            category="PAYER",
            default_severity=SEV_MEDIUM,
            fn=_h_rural_critical_access_caveat,
        ),
        Heuristic(
            id="moic_cagr_too_high",
            title="Implied MOIC CAGR > 28%",
            description="Top-quartile healthcare PE lands 25-30%; above that is underwriting luck.",
            category="VALUATION",
            default_severity=SEV_HIGH,
            fn=_h_high_moic_short_hold,
        ),
        Heuristic(
            id="teaching_hospital_complexity",
            title="Major teaching hospital — GME carve-out",
            description="GME/IME payments must be modeled separately from operating revenue.",
            category="PAYER",
            default_severity=SEV_LOW,
            fn=_h_teaching_hospital_complexity,
        ),
        Heuristic(
            id="ar_reduction_aggressive",
            title="AR reduction > 8 days/yr",
            description="Realistic AR programs deliver 5-8 days/yr; > 15 needs capex commitment.",
            category="OPERATIONS",
            default_severity=SEV_HIGH,
            fn=_h_ar_reduction_aggressive,
        ),
        Heuristic(
            id="state_medicaid_volatility",
            title="Medicaid-heavy in volatile-rate state",
            description="States with rate freezes (IL, NY, CA, LA, OK, MS, AR) warrant flat-lined rate growth.",
            category="PAYER",
            default_severity=SEV_MEDIUM,
            fn=_h_single_state_concentration,
        ),
    ]


def run_heuristics(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Run every registered heuristic against ``ctx``. Return hits
    sorted highest-severity-first, then by id for determinism.
    """
    hits: List[HeuristicHit] = []
    for h in all_heuristics():
        try:
            result = h.run(ctx)
        except Exception as exc:  # defensive — never fail the review
            result = HeuristicHit(
                id=h.id,
                title=f"{h.title} (evaluation failed)",
                severity=SEV_LOW,
                category=h.category,
                finding=f"Heuristic raised an unexpected error: {exc}",
                partner_voice="",
                remediation="Review heuristic inputs for missing/bad values.",
            )
        if result is not None:
            hits.append(result)
    hits.sort(key=lambda h: (-h.severity_rank(), h.id))
    return hits
