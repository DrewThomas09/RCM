"""Cross-pattern digest — connective tissue across pattern libraries.

Partner statement: "One trap is a negotiation. Two traps on
the same axis is a pass."

The brain maintains three separate pattern libraries:

- ``historical_failure_library`` — named, dated PE disasters
  (envision, steward, U.S. renal, etc.).
- ``bear_book`` — abstract pattern templates (rollup
  integration failure, covid tailwind fade, etc.).
- ``partner_traps_library`` — seller-pitch traps partners
  reject (fix denials in 12 months, MA will make it up).

Each library answers a different question:

- Failures: "has this shape of deal blown up before?"
- Bear book: "does this fit a known failure template?"
- Traps: "is the seller selling us a story we've heard fail?"

A partner doesn't run these in isolation — they stack. If
**all three** libraries light up on the same axis (e.g.,
denials, payer mix, leverage), that's a signature pattern
the partner recognizes instantly: pass, or re-price.

This module provides:

1. A unified ``PatternContext`` that feeds all three
   libraries.
2. ``cross_pattern_scan()`` that runs all three and clusters
   matches by theme (denials, payer, leverage, operator,
   integration, regulatory, covid-tailwind).
3. Compound-risk detection — when ≥ 2 libraries fire on the
   same theme, the digest promotes that theme to a
   ``compound_risk``.
4. Partner-voice recommendation: **pass / re-price / more
   diligence / proceed-with-mitigants**.

The output is the "partner gut check" — what the partner
walks into IC having already read and weighted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .heuristics import HeuristicContext
from .historical_failure_library import (
    FailureMatch,
    match_failures,
)
from .bear_book import (
    BearPatternHit,
    scan_bear_book,
)
from .partner_traps_library import (
    TrapHit,
    match_traps,
)


# Theme tags keyed off pattern names. A pattern can carry
# multiple themes; compound-risk fires when ≥ 2 libraries tag
# the same theme.
PATTERN_THEMES: Dict[str, List[str]] = {
    # Historical failures.
    "envision_surprise_billing_2023": ["payer", "regulatory"],
    "steward_reit_sale_leaseback": ["leverage", "real_estate"],
    "us_renal_care_medicare_advantage": ["payer", "medicare"],
    "ivcare_home_health_cap_2019": ["payer", "medicare"],
    "team_health_pricing_fight": ["payer", "regulatory"],
    "adeptus_freestanding_er_2017": ["payer", "operator"],
    # Bear book.
    "rollup_integration_failure": ["integration", "operator", "leverage"],
    "medicare_margin_compression": ["medicare", "payer"],
    "carveout_tsa_sprawl": ["integration", "operator"],
    "turnaround_without_operator": ["operator"],
    "covid_tailwind_fade": ["covid_tailwind"],
    "high_leverage_thin_coverage": ["leverage"],
    "ffs_math_on_vbc": ["payer", "operator"],
    "rural_single_payer_cliff": ["payer", "medicare"],
    # Traps.
    "fix_denials_in_12_months": ["denials", "operator"],
    "payer_renegotiation_is_coming": ["payer"],
    "medicare_advantage_will_make_it_up": ["medicare", "payer"],
    "back_office_year_1_synergies": ["integration", "operator"],
    "robust_pipeline_of_add_ons": ["integration"],
    "ceo_will_stay_through_close": ["operator"],
    "underpenetrated_market": ["payer"],
    "quality_and_growth": ["operator"],
    "multiple_rerate_at_exit": ["leverage"],
    "tech_platform_play": ["integration", "operator"],
}

# Default priority weight applied when a pattern carries no
# explicit weight.
LIBRARY_SEVERITY: Dict[str, float] = {
    "failure": 1.0,    # named historical failure is heaviest
    "bear": 0.7,
    "trap": 0.5,
}


@dataclass
class PatternContext:
    """Unified context for all three pattern libraries.

    Accepts both HeuristicContext-style fields (for bear_book)
    and packet-dict-style fields (for failures and traps).
    The scanner auto-adapts.
    """
    # Bear-book / heuristic fields
    payer_mix: Dict[str, float] = field(default_factory=dict)
    ebitda_m: Optional[float] = None
    revenue_m: Optional[float] = None
    bed_count: Optional[int] = None
    hospital_type: Optional[str] = None
    state: Optional[str] = None
    urban_rural: Optional[str] = None
    denial_rate: Optional[float] = None
    final_writeoff_rate: Optional[float] = None
    days_in_ar: Optional[float] = None
    clean_claim_rate: Optional[float] = None
    case_mix_index: Optional[float] = None
    ebitda_margin: Optional[float] = None
    exit_multiple: Optional[float] = None
    entry_multiple: Optional[float] = None
    hold_years: Optional[float] = None
    projected_irr: Optional[float] = None
    projected_moic: Optional[float] = None
    denial_improvement_bps_per_yr: Optional[float] = None
    ar_reduction_days_per_yr: Optional[float] = None
    revenue_growth_pct_per_yr: Optional[float] = None
    margin_expansion_bps_per_yr: Optional[float] = None
    deal_structure: Optional[str] = None
    leverage_multiple: Optional[float] = None
    covenant_headroom_pct: Optional[float] = None
    data_coverage_pct: Optional[float] = None
    has_case_mix_data: bool = True

    # Extra dict of packet-dict-style fields for trap/failure
    # matchers (e.g., current_denial_rate, target_denial_rate,
    # months_to_target, medicare_advantage_pct, etc.).
    packet_fields: Dict[str, Any] = field(default_factory=dict)

    def to_heuristic_context(self) -> HeuristicContext:
        return HeuristicContext(
            payer_mix=dict(self.payer_mix),
            ebitda_m=self.ebitda_m,
            revenue_m=self.revenue_m,
            bed_count=self.bed_count,
            hospital_type=self.hospital_type,
            state=self.state,
            urban_rural=self.urban_rural,
            denial_rate=self.denial_rate,
            final_writeoff_rate=self.final_writeoff_rate,
            days_in_ar=self.days_in_ar,
            clean_claim_rate=self.clean_claim_rate,
            case_mix_index=self.case_mix_index,
            ebitda_margin=self.ebitda_margin,
            exit_multiple=self.exit_multiple,
            entry_multiple=self.entry_multiple,
            hold_years=self.hold_years,
            projected_irr=self.projected_irr,
            projected_moic=self.projected_moic,
            denial_improvement_bps_per_yr=self.denial_improvement_bps_per_yr,
            ar_reduction_days_per_yr=self.ar_reduction_days_per_yr,
            revenue_growth_pct_per_yr=self.revenue_growth_pct_per_yr,
            margin_expansion_bps_per_yr=self.margin_expansion_bps_per_yr,
            deal_structure=self.deal_structure,
            leverage_multiple=self.leverage_multiple,
            covenant_headroom_pct=self.covenant_headroom_pct,
            data_coverage_pct=self.data_coverage_pct,
            has_case_mix_data=self.has_case_mix_data,
        )

    def to_packet_dict(self) -> Dict[str, Any]:
        """For failure/trap matchers that expect a dict."""
        d: Dict[str, Any] = {}
        # Flatten numeric fields.
        for k, v in self.__dict__.items():
            if k in ("packet_fields", "payer_mix"):
                continue
            if v is None:
                continue
            d[k] = v
        # Derived fields traps expect.
        if self.payer_mix:
            d["payer_mix"] = dict(self.payer_mix)
            mix_lower = {str(k).lower(): float(v)
                         for k, v in self.payer_mix.items()}
            total = sum(mix_lower.values())
            # If values sum near 1.0, they're already fractions.
            # If they sum near 100, they're percentages — normalize.
            scale = 1.0 if total <= 1.5 else 100.0
            d["medicare_advantage_pct"] = (
                mix_lower.get("medicare_advantage", 0.0)
                + mix_lower.get("ma", 0.0)
            ) / scale
            d["medicare_pct"] = (
                mix_lower.get("medicare", 0.0) / scale
            )
        # Layer packet_fields last so they override defaults.
        d.update(self.packet_fields)
        return d


@dataclass
class PatternMatch:
    library: str                            # "failure"/"bear"/"trap"
    pattern_id: str
    name: str
    themes: List[str] = field(default_factory=list)
    severity: float = 0.0
    partner_voice: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "library": self.library,
            "pattern_id": self.pattern_id,
            "name": self.name,
            "themes": list(self.themes),
            "severity": self.severity,
            "partner_voice": self.partner_voice,
        }


@dataclass
class CompoundRisk:
    theme: str
    libraries_hit: List[str]        # which libraries fired
    patterns: List[str]             # pattern_ids contributing
    severity: float
    partner_voice: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "theme": self.theme,
            "libraries_hit": list(self.libraries_hit),
            "patterns": list(self.patterns),
            "severity": self.severity,
            "partner_voice": self.partner_voice,
        }


@dataclass
class CrossPatternDigest:
    matches: List[PatternMatch] = field(default_factory=list)
    compound_risks: List[CompoundRisk] = field(default_factory=list)
    total_severity: float = 0.0
    recommendation: str = ""           # pass/reprice/diligence/proceed
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "compound_risks": [c.to_dict() for c in self.compound_risks],
            "total_severity": self.total_severity,
            "recommendation": self.recommendation,
            "partner_note": self.partner_note,
        }


def _themes_for(pattern_id: str) -> List[str]:
    return list(PATTERN_THEMES.get(pattern_id, []))


def _partner_voice_for_theme(theme: str,
                              libraries_hit: List[str]) -> str:
    n = len(libraries_hit)
    head = f"{theme.replace('_',' ')} risk fires across {n} libraries "
    head += "(" + ", ".join(libraries_hit) + "). "
    tail_by_theme = {
        "payer": ("Payer mix / contracting is where the thesis lives. "
                   "If both a trap and a historical failure match, "
                   "the seller's story is already broken."),
        "denials": ("Denial reduction is the most over-promised lever "
                    "in healthcare RCM. When it stacks with operator "
                    "concerns, the plan is not executable."),
        "medicare": ("Medicare / MA exposure compounds with regulatory "
                     "calendar. Sequestration, site-neutral, OBBBA can "
                     "each trim 200-400 bps independently."),
        "leverage": ("Leverage stacking is the fastest way to lose the "
                     "equity — covenant trip in a down year wipes the "
                     "thesis regardless of operating performance."),
        "operator": ("Operator risk is existential. If the turnaround "
                     "needs a CEO change AND retention AND integration, "
                     "we are underwriting on faith."),
        "integration": ("Roll-ups die in integration, not in the "
                        "acquisition. Every library flags something "
                        "different — multiply the risk, do not add it."),
        "regulatory": ("Regulatory compounding means the deal is one "
                       "OIG settlement or CMS rule from re-pricing. "
                       "Price at stress case, not base case."),
        "covid_tailwind": ("COVID-era base year inflates recurring "
                            "EBITDA. When trap + bear book both flag, "
                            "the walk-away multiple is structurally "
                            "below seller's ask."),
        "real_estate": ("Sale-leaseback or REIT dependency is a ticking "
                        "bomb when rates move. Steward taught us this "
                        "lesson — partner should ask who owns the "
                        "ground before signing."),
    }
    return head + tail_by_theme.get(theme,
        "Multiple libraries flagging the same theme is a strong prior "
        "against the thesis. Partner should name the mitigant or re-"
        "price.")


def cross_pattern_scan(ctx: PatternContext,
                        *, bear_min_confidence: float = 0.30,
                        ) -> CrossPatternDigest:
    """Run all three libraries against the shared context and cluster."""
    matches: List[PatternMatch] = []

    # Failures.
    for fm in match_failures(ctx.to_packet_dict()):
        matches.append(PatternMatch(
            library="failure",
            pattern_id=fm.pattern.name,
            name=fm.pattern.name.replace("_", " "),
            themes=_themes_for(fm.pattern.name),
            severity=(LIBRARY_SEVERITY["failure"]
                       * (fm.pattern.ebitda_destruction_pct or 0.3)),
            partner_voice=fm.pattern.partner_lesson or fm.reason,
        ))

    # Bear book.
    hctx = ctx.to_heuristic_context()
    for bh in scan_bear_book(hctx, min_confidence=bear_min_confidence):
        matches.append(PatternMatch(
            library="bear",
            pattern_id=bh.pattern_id,
            name=bh.name,
            themes=_themes_for(bh.pattern_id),
            severity=LIBRARY_SEVERITY["bear"] * float(bh.confidence),
            partner_voice=bh.partner_voice or bh.failure_mode,
        ))

    # Traps.
    for th in match_traps(ctx.to_packet_dict()):
        matches.append(PatternMatch(
            library="trap",
            pattern_id=th.trap.name,
            name=th.trap.name.replace("_", " "),
            themes=_themes_for(th.trap.name),
            severity=LIBRARY_SEVERITY["trap"],
            partner_voice=th.partner_note or th.trap.partner_rebuttal,
        ))

    # Cluster by theme.
    theme_libs: Dict[str, List[str]] = {}
    theme_patterns: Dict[str, List[str]] = {}
    theme_sev: Dict[str, float] = {}
    for m in matches:
        for t in m.themes:
            theme_libs.setdefault(t, [])
            if m.library not in theme_libs[t]:
                theme_libs[t].append(m.library)
            theme_patterns.setdefault(t, []).append(m.pattern_id)
            theme_sev[t] = theme_sev.get(t, 0.0) + m.severity

    compounds: List[CompoundRisk] = []
    for theme, libs in theme_libs.items():
        if len(libs) >= 2:
            compounds.append(CompoundRisk(
                theme=theme,
                libraries_hit=sorted(libs),
                patterns=sorted(set(theme_patterns[theme])),
                severity=theme_sev[theme],
                partner_voice=_partner_voice_for_theme(theme, libs),
            ))
    compounds.sort(key=lambda c: -c.severity)

    total_sev = sum(m.severity for m in matches)
    matches.sort(key=lambda m: -m.severity)

    # Recommendation.
    if any(len(c.libraries_hit) >= 3 for c in compounds):
        rec = "pass"
        note = ("All three libraries fire on the same theme. "
                "Partner recommendation: pass unless seller accepts "
                "meaningful re-price + structural protections.")
    elif len(compounds) >= 2 or total_sev >= 1.5:
        rec = "reprice"
        note = ("Multiple compound risks. Partner recommendation: "
                "re-price down at least one turn or extract seller "
                "indemnity for the flagged exposures.")
    elif len(compounds) == 1 or total_sev >= 0.8:
        rec = "diligence_more"
        note = ("One compound risk or meaningful single-library "
                "hit. Partner recommendation: targeted diligence "
                "on the named theme before IC.")
    elif matches:
        rec = "proceed_with_mitigants"
        note = ("Isolated flags, no compound risk. Partner "
                "recommendation: proceed with named mitigants "
                "documented in the IC memo.")
    else:
        rec = "proceed"
        note = ("No pattern-library matches. Partner recommendation: "
                "proceed on the current thesis.")

    return CrossPatternDigest(
        matches=matches,
        compound_risks=compounds,
        total_severity=round(total_sev, 3),
        recommendation=rec,
        partner_note=note,
    )


def render_cross_pattern_markdown(d: CrossPatternDigest) -> str:
    lines = [
        "# Cross-pattern digest",
        "",
        f"**Recommendation:** `{d.recommendation}`",
        "",
        f"_{d.partner_note}_",
        "",
        f"- Total severity: {d.total_severity:.2f}",
        f"- Matches: {len(d.matches)}",
        f"- Compound risks: {len(d.compound_risks)}",
        "",
    ]
    if d.compound_risks:
        lines.append("## Compound risks")
        lines.append("")
        for c in d.compound_risks:
            lines.append(
                f"### {c.theme} "
                f"(libraries: {', '.join(c.libraries_hit)})"
            )
            lines.append(f"- Severity: {c.severity:.2f}")
            lines.append(f"- Patterns: {', '.join(c.patterns)}")
            lines.append(f"- Partner: {c.partner_voice}")
            lines.append("")
    if d.matches:
        lines.append("## All matches (severity desc)")
        lines.append("")
        lines.append("| Library | Pattern | Themes | Severity | Partner |")
        lines.append("|---|---|---|---|---|")
        for m in d.matches:
            lines.append(
                f"| {m.library} | {m.name} | "
                f"{', '.join(m.themes) or '—'} | "
                f"{m.severity:.2f} | {m.partner_voice} |"
            )
    return "\n".join(lines)
