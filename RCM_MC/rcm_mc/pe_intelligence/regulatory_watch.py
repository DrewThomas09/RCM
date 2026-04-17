"""Regulatory watch — static registry of CMS / OIG / state actions
that affect healthcare PE underwriting.

This module is a curated reference, not a live feed. It answers the
partner's question: "what regulatory item should I worry about for a
[ASC / behavioral / acute] deal in [state / nationally]?"

Each item has:
- Scope: national or state-level.
- Status: proposed, finalized, effective, expired.
- Impact: what it does to reimbursement / margin.
- Window: when it takes effect or when comment closes.
- Partner relevance: what it means at IC.

The dataset here is a starting calibration. Production use should
refresh at least quarterly — the docstrings intentionally include a
``last_refreshed`` field so stale entries are visible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Model ────────────────────────────────────────────────────────────

@dataclass
class RegulatoryItem:
    """A single regulatory action / rule / trend."""
    id: str
    title: str
    scope: str                         # "national" | state code | "sector"
    status: str                        # "proposed" | "finalized" | "effective" | "expired" | "watch"
    affected_subsectors: List[str] = field(default_factory=list)
    affected_payers: List[str] = field(default_factory=list)
    impact_summary: str = ""
    partner_relevance: str = ""
    effective_year: Optional[int] = None
    last_refreshed: str = "2026-04-17"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "scope": self.scope,
            "status": self.status,
            "affected_subsectors": list(self.affected_subsectors),
            "affected_payers": list(self.affected_payers),
            "impact_summary": self.impact_summary,
            "partner_relevance": self.partner_relevance,
            "effective_year": self.effective_year,
            "last_refreshed": self.last_refreshed,
        }


# ── Registry ─────────────────────────────────────────────────────────

REGISTRY: List[RegulatoryItem] = [
    # ── National items ──────────────────────────────────────────────
    RegulatoryItem(
        id="cms_opps_site_neutral",
        title="CMS OPPS site-neutral payment policy expansion",
        scope="national",
        status="watch",
        affected_subsectors=["acute_care", "outpatient", "specialty"],
        affected_payers=["medicare"],
        impact_summary=(
            "CMS has steadily expanded site-neutral payments, which pay "
            "hospital outpatient departments at ASC/physician rates for "
            "designated services. Compresses revenue on the outpatient side."
        ),
        partner_relevance=(
            "If the deal leans on HOPD revenue for the outpatient "
            "expansion thesis, the revenue upside assumption should "
            "reflect ongoing site-neutral compression."
        ),
        effective_year=2025,
    ),
    RegulatoryItem(
        id="medicare_ipps_rate_update",
        title="Medicare IPPS annual rate update cycle",
        scope="national",
        status="effective",
        affected_subsectors=["acute_care"],
        affected_payers=["medicare"],
        impact_summary=(
            "Annual CMS update to inpatient rates; FY updates range "
            "+1.5% to +3.1% in recent cycles. Historically volatile under "
            "budget pressure."
        ),
        partner_relevance=(
            "Base case for IPPS update growth should be 1.5–2.5% — not "
            "the CMS proposed figure, which is typically trimmed by "
            "Congress."
        ),
        effective_year=2026,
    ),
    RegulatoryItem(
        id="340b_payback_schedule",
        title="340B reimbursement payback / ongoing policy",
        scope="national",
        status="finalized",
        affected_subsectors=["acute_care", "specialty", "behavioral"],
        affected_payers=["medicare"],
        impact_summary=(
            "2022 AHA ruling required CMS to unwind prior 340B cuts; "
            "payback schedule through 2026-2027 and forward policy "
            "remains politically contested."
        ),
        partner_relevance=(
            "Do not model 340B contribution as stable forward; hold "
            "bid to clear at 50% of current 340B benefit."
        ),
        effective_year=2024,
    ),
    RegulatoryItem(
        id="medicaid_redetermination",
        title="Medicaid PHE unwind / redetermination",
        scope="national",
        status="effective",
        affected_subsectors=["acute_care", "behavioral", "post_acute", "outpatient"],
        affected_payers=["medicaid"],
        impact_summary=(
            "PHE-era continuous enrollment ended April 2023. "
            "Redetermination has removed millions from Medicaid, "
            "shifting payer mix toward commercial or self-pay."
        ),
        partner_relevance=(
            "Historical Medicaid revenue may be structurally lower "
            "going forward. Re-check payer mix trend in TTM, not "
            "just trailing 3Y."
        ),
        effective_year=2024,
    ),
    RegulatoryItem(
        id="no_surprises_act",
        title="No Surprises Act (NSA) — out-of-network billing",
        scope="national",
        status="effective",
        affected_subsectors=["acute_care", "asc", "specialty", "outpatient"],
        affected_payers=["commercial"],
        impact_summary=(
            "Prohibits balance billing for out-of-network emergency "
            "and certain non-emergency care. IDR process has been "
            "contested in court; reimbursement outcomes uneven."
        ),
        partner_relevance=(
            "Out-of-network revenue is no longer a reliable upside. "
            "Underwrite in-network economics only."
        ),
        effective_year=2022,
    ),
    RegulatoryItem(
        id="hospital_price_transparency",
        title="Hospital price transparency + machine-readable files",
        scope="national",
        status="effective",
        affected_subsectors=["acute_care", "specialty"],
        affected_payers=["commercial", "medicare", "medicaid"],
        impact_summary=(
            "Hospitals must post payer-specific negotiated rates. "
            "Commercial rate discovery by payers compresses rate "
            "dispersion across markets."
        ),
        partner_relevance=(
            "Monitor payer-rate compression for commercial-heavy "
            "deals. Upside from rate negotiation is tighter than "
            "pre-2021."
        ),
        effective_year=2021,
    ),
    RegulatoryItem(
        id="stark_safe_harbor_expansion",
        title="Stark Law and anti-kickback safe-harbor expansions",
        scope="national",
        status="finalized",
        affected_subsectors=["outpatient", "asc", "specialty", "acute_care"],
        affected_payers=["medicare"],
        impact_summary=(
            "2021 final rule loosened value-based arrangement rules "
            "for coordinated care. Enables some previously-risky "
            "compensation structures in VBC entities."
        ),
        partner_relevance=(
            "Check whether physician comp structures use the new "
            "safe harbors; older deals may have legacy arrangements "
            "that now qualify under the expanded rule."
        ),
        effective_year=2021,
    ),
    RegulatoryItem(
        id="snf_vbp_program",
        title="SNF Value-Based Purchasing (VBP) program",
        scope="national",
        status="effective",
        affected_subsectors=["post_acute"],
        affected_payers=["medicare"],
        impact_summary=(
            "SNFs face up to 2% Medicare payment withhold tied to "
            "readmissions performance. Program expanded to include "
            "additional quality measures FY2026."
        ),
        partner_relevance=(
            "Underwrite post-acute deals with a 0–2% quality "
            "withhold baseline. If facility is in the bottom quartile "
            "on readmissions, assume the full withhold."
        ),
        effective_year=2024,
    ),
    RegulatoryItem(
        id="imd_exclusion_waiver",
        title="Medicaid IMD exclusion waiver (behavioral health)",
        scope="national",
        status="watch",
        affected_subsectors=["behavioral"],
        affected_payers=["medicaid"],
        impact_summary=(
            "Federal waiver allowing Medicaid to pay for behavioral-"
            "health care in facilities with >16 beds. Several state "
            "waivers expire 2027-2028."
        ),
        partner_relevance=(
            "For behavioral deals relying on Medicaid, check waiver "
            "status in target states. Expiry is a named rate cliff."
        ),
        effective_year=2027,
    ),
    RegulatoryItem(
        id="physician_fee_schedule",
        title="Medicare Physician Fee Schedule conversion factor",
        scope="national",
        status="effective",
        affected_subsectors=["outpatient", "asc", "specialty"],
        affected_payers=["medicare"],
        impact_summary=(
            "MPFS conversion factor has declined or stagnated in "
            "recent years under budget-neutrality rules. Specialty "
            "practices face persistent reimbursement pressure."
        ),
        partner_relevance=(
            "Physician-practice deals should model flat-to-negative "
            "Medicare rate growth. Do not extrapolate commercial "
            "rate trends."
        ),
        effective_year=2026,
    ),
    # ── State-level items ──────────────────────────────────────────
    RegulatoryItem(
        id="ca_hospital_seismic",
        title="California hospital seismic safety (SB 1953)",
        scope="CA",
        status="effective",
        affected_subsectors=["acute_care"],
        impact_summary=(
            "California hospitals face ongoing seismic-retrofit "
            "capex requirements. Acute-care assets in CA carry a "
            "persistent capex headwind."
        ),
        partner_relevance=(
            "CA acute-care deals must underwrite seismic capex "
            "explicitly. Do not credit deferred maintenance."
        ),
        effective_year=2030,
    ),
    RegulatoryItem(
        id="ny_medicaid_freeze",
        title="New York Medicaid rate freeze history",
        scope="NY",
        status="watch",
        affected_subsectors=["acute_care", "behavioral", "post_acute"],
        affected_payers=["medicaid"],
        impact_summary=(
            "NY has periodically frozen Medicaid rates during budget "
            "tightening. Recent cycles: 2011, 2014, 2020."
        ),
        partner_relevance=(
            "NY-heavy deals should flat-line Medicaid rate growth in "
            "base case and model a freeze in stress case."
        ),
    ),
    RegulatoryItem(
        id="tx_nsa_idr",
        title="Texas IDR outcomes under No Surprises Act",
        scope="TX",
        status="effective",
        affected_subsectors=["acute_care", "outpatient", "specialty"],
        affected_payers=["commercial"],
        impact_summary=(
            "Texas-specific IDR (independent dispute resolution) "
            "outcomes have been relatively provider-favorable, but "
            "volume backlog caps practical utility."
        ),
        partner_relevance=(
            "Don't over-weight NSA IDR revenue in TX deals; backlog "
            "is material."
        ),
        effective_year=2022,
    ),
    RegulatoryItem(
        id="fl_medicaid_expansion",
        title="Florida Medicaid expansion non-adoption",
        scope="FL",
        status="effective",
        affected_subsectors=["acute_care", "behavioral"],
        affected_payers=["medicaid"],
        impact_summary=(
            "FL has not expanded Medicaid under the ACA. Uninsured "
            "and bad-debt exposure is structurally higher than "
            "expansion states."
        ),
        partner_relevance=(
            "FL acute-care deals model higher bad-debt and lower "
            "insured mix than national averages."
        ),
    ),
    RegulatoryItem(
        id="ma_rate_setting",
        title="Maryland all-payer hospital rate-setting",
        scope="MD",
        status="effective",
        affected_subsectors=["acute_care"],
        impact_summary=(
            "Maryland has a unique all-payer rate-setting model "
            "(HSCRC). Pricing power is regulated; growth comes "
            "from volume and global-budget thresholds."
        ),
        partner_relevance=(
            "MD acute-care deals cannot underwrite commercial rate "
            "expansion — the rates are regulated. Focus on volume "
            "and population-health contracting."
        ),
    ),
]


# ── Lookup helpers ───────────────────────────────────────────────────

def list_items(
    *,
    scope: Optional[str] = None,
    subsector: Optional[str] = None,
    status: Optional[str] = None,
) -> List[RegulatoryItem]:
    """Filter the registry by any combination of scope, subsector, status."""
    out = REGISTRY
    if scope:
        out = [x for x in out if x.scope.lower() == scope.lower()]
    if subsector:
        sub = subsector.lower().strip()
        out = [x for x in out if sub in [s.lower() for s in x.affected_subsectors]
               or not x.affected_subsectors]
    if status:
        out = [x for x in out if x.status.lower() == status.lower()]
    return list(out)


def for_deal(
    subsector: Optional[str] = None,
    state: Optional[str] = None,
    payer_mix: Optional[Dict[str, float]] = None,
) -> List[RegulatoryItem]:
    """Return regulatory items relevant to a deal.

    A deal is "relevant" to a national item if its subsector matches,
    and to a state item if its state matches. Payer-mix filters items
    whose affected_payers are present in the mix (non-trivially).
    """
    out: List[RegulatoryItem] = []
    payer_keys = set()
    if payer_mix:
        for k, v in payer_mix.items():
            try:
                if float(v) > 0:
                    payer_keys.add(str(k).lower())
            except (TypeError, ValueError):
                continue
    for item in REGISTRY:
        # Scope filter
        if item.scope != "national":
            if not state or item.scope.upper() != state.upper():
                continue
        # Subsector filter
        if subsector and item.affected_subsectors:
            sub = subsector.lower().strip()
            if sub not in [s.lower() for s in item.affected_subsectors]:
                continue
        # Payer filter (only if the item identifies affected payers)
        if item.affected_payers and payer_keys:
            if not any(p.lower() in payer_keys for p in item.affected_payers):
                continue
        out.append(item)
    return out


def summarize_for_partner(items: List[RegulatoryItem]) -> str:
    """Short partner-voice summary of a list of items."""
    if not items:
        return "No active regulatory items flagged for this deal profile."
    lines: List[str] = [
        f"{len(items)} regulatory item(s) to flag at IC:",
    ]
    for item in items[:10]:
        lines.append(f"- [{item.status.upper()}] {item.title} — {item.partner_relevance}")
    if len(items) > 10:
        lines.append(f"- ... and {len(items) - 10} more.")
    return "\n".join(lines)
