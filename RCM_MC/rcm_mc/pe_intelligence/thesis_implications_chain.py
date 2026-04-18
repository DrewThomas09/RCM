"""Thesis implications chain — walk downstream consequences.

Partner statement: "Tell me the chain. If denials come down,
what else has to be true?"

A seller's thesis is always a single headline claim. A
partner's rebuttal is the *chain* of downstream implications
that have to hold for the headline to be real:

- "Cut denials 300 bps/yr" → payer contracts support coding,
  coders retained, DAR compresses, cash conversion improves,
  EBITDA quality holds, cov headroom widens, exit multiple
  extends. Each link has an assumption. The seller owns the
  headline; the partner owns the chain.

- "Shift payer mix from Medicaid to commercial" → commercial
  payer leverage exists, provider network recontracts, state
  Medicaid doesn't retaliate with DSH pullback, length-of-
  stay shifts, case mix rises, margins widen, bad-debt
  improves, bridge reflects the phase-in not day-1.

- "Roll-up to 2x platform EBITDA in 5 years" → pipeline
  sized, integration playbook tested, debt capacity scales
  with EBITDA, management teams retain, synergies realized
  net of integration cost, exit multiple holds despite
  complexity, LBO stress cases clear.

This module implements a small library of **thesis chains**:
each chain is a named thesis (string) with an ordered list
of downstream implications. Each implication carries:

- the **claim** the seller must also be making (even if they
  haven't said it)
- a **partner_check** field — what the partner asks to
  verify it
- a **risk** tag — low / medium / high — the probability
  this link is the one that breaks
- an optional **packet_field** — a field in the packet that
  would either confirm or invalidate this implication

The scanner takes a packet-like context dict and a chosen
thesis and returns a `ThesisChainReport` with each
implication tagged as **confirmed**, **not_addressed**, or
**contradicted** by the packet.

Partner reads the report as "here's the chain; here are the
links you haven't nailed down."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable


@dataclass
class ThesisImplication:
    claim: str
    partner_check: str
    risk: str                          # "low"/"medium"/"high"
    packet_field: Optional[str] = None
    confirm_pred: Optional[Callable[[Dict[str, Any]], bool]] = None
    contradict_pred: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class ThesisChainEntry:
    claim: str
    partner_check: str
    risk: str
    status: str                        # "confirmed"/"not_addressed"/"contradicted"


@dataclass
class ThesisChainReport:
    thesis: str
    entries: List[ThesisChainEntry] = field(default_factory=list)
    not_addressed_count: int = 0
    contradicted_count: int = 0
    confirmed_count: int = 0
    high_risk_unresolved: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "thesis": self.thesis,
            "entries": [
                {"claim": e.claim, "partner_check": e.partner_check,
                 "risk": e.risk, "status": e.status}
                for e in self.entries
            ],
            "not_addressed_count": self.not_addressed_count,
            "contradicted_count": self.contradicted_count,
            "confirmed_count": self.confirmed_count,
            "high_risk_unresolved": self.high_risk_unresolved,
            "partner_note": self.partner_note,
        }


# ── Chains ───────────────────────────────────────────────────

def _denial_chain() -> List[ThesisImplication]:
    return [
        ThesisImplication(
            claim="Coders and front-end staff retain through the "
                  "improvement window.",
            partner_check="What's coder/front-end turnover rate? "
                          "Retention bonuses in place?",
            risk="high",
            packet_field="coder_turnover_annual_pct",
            confirm_pred=lambda c: float(
                c.get("coder_turnover_annual_pct", 0.5)) < 0.15,
            contradict_pred=lambda c: float(
                c.get("coder_turnover_annual_pct", 0)) > 0.25,
        ),
        ThesisImplication(
            claim="Payer contracts support the coding uplift — no "
                  "downcoding disputes baked in.",
            partner_check="Any open payer audits or coding "
                          "disputes in flight?",
            risk="high",
            packet_field="open_payer_coding_disputes",
            contradict_pred=lambda c: bool(
                c.get("open_payer_coding_disputes", False)),
        ),
        ThesisImplication(
            claim="DAR compresses alongside denial reduction — "
                  "cash conversion actually moves.",
            partner_check="DAR reduction trajectory — is it in the "
                          "plan, with milestones?",
            risk="medium",
            packet_field="dar_reduction_days_per_yr",
            confirm_pred=lambda c: float(
                c.get("dar_reduction_days_per_yr", 0)) >= 2.0,
        ),
        ThesisImplication(
            claim="EBITDA uplift is *recurring*, not a one-time "
                  "catch-up from A/R release.",
            partner_check="How much of Year 1 EBITDA gain is cash "
                          "release vs. run-rate?",
            risk="high",
            packet_field="year1_cash_release_share",
            contradict_pred=lambda c: float(
                c.get("year1_cash_release_share", 0)) > 0.40,
        ),
        ThesisImplication(
            claim="Covenant package clears the improvement curve, "
                  "not just endpoint.",
            partner_check="Model Y1 leverage on Y1 EBITDA — "
                          "does it hold?",
            risk="medium",
            packet_field="y1_leverage_on_y1_ebitda",
            contradict_pred=lambda c: float(
                c.get("y1_leverage_on_y1_ebitda", 0)) > 7.0,
        ),
        ThesisImplication(
            claim="Exit multiple is applied to recurring Year 5 "
                  "EBITDA, not peak.",
            partner_check="Which year's EBITDA does the exit "
                          "multiple apply to? Is it trailing or "
                          "forward?",
            risk="medium",
            packet_field="exit_ebitda_basis",
        ),
    ]


def _payer_mix_shift_chain() -> List[ThesisImplication]:
    return [
        ThesisImplication(
            claim="Commercial payers have the network and leverage "
                  "to absorb the shift.",
            partner_check="Which commercial payers add capacity? "
                          "Are the contracts open?",
            risk="high",
            packet_field="commercial_payer_capacity_confirmed",
            confirm_pred=lambda c: bool(
                c.get("commercial_payer_capacity_confirmed", False)),
        ),
        ThesisImplication(
            claim="State Medicaid doesn't retaliate via DSH / UPL "
                  "pullback on reduced Medicaid share.",
            partner_check="Is the state on Medicaid expansion? Is "
                          "DSH payment a material share of revenue?",
            risk="high",
            packet_field="dsh_revenue_share",
            contradict_pred=lambda c: float(
                c.get("dsh_revenue_share", 0)) > 0.10,
        ),
        ThesisImplication(
            claim="Case mix index rises with payer mix shift — "
                  "commercial patients aren't lower-acuity.",
            partner_check="What's projected CMI at exit? Any shift "
                          "toward ambulatory that dilutes it?",
            risk="medium",
            packet_field="cmi_at_exit",
        ),
        ThesisImplication(
            claim="Length-of-stay and bad-debt improve alongside "
                  "mix — or are they locked in by operations?",
            partner_check="Bad debt trend by payer class; LOS by "
                          "service line.",
            risk="medium",
            packet_field="bad_debt_trend_pct",
        ),
        ThesisImplication(
            claim="Phase-in is modeled, not day-1 uplift.",
            partner_check="When does commercial share reach "
                          "target? 12 months or 36?",
            risk="medium",
            packet_field="months_to_target_commercial_mix",
            contradict_pred=lambda c: int(
                c.get("months_to_target_commercial_mix", 99)) < 18,
        ),
    ]


def _rollup_chain() -> List[ThesisImplication]:
    return [
        ThesisImplication(
            claim="M&A pipeline is real and priced — not just "
                  "'opportunity universe'.",
            partner_check="How many signed LOIs? Cap rate on "
                          "pipeline acquisitions?",
            risk="high",
            packet_field="signed_lois_count",
            confirm_pred=lambda c: int(
                c.get("signed_lois_count", 0)) >= 3,
        ),
        ThesisImplication(
            claim="Integration playbook exists and has been tested "
                  "on at least two prior acquisitions.",
            partner_check="Show me the playbook. How long did the "
                          "last integration take vs. plan?",
            risk="high",
            packet_field="integration_playbook_maturity",
        ),
        ThesisImplication(
            claim="Debt capacity scales with platform EBITDA — "
                  "revolver + delayed-draw term loan sized.",
            partner_check="Is the debt package a unitranche with "
                          "acquisition accordion? What's the cap?",
            risk="medium",
            packet_field="delayed_draw_capacity_m",
        ),
        ThesisImplication(
            claim="Synergies are net of integration cost — not "
                  "gross run-rate.",
            partner_check="What's the integration cost ratio? 40% "
                          "of synergies is common in healthcare.",
            risk="medium",
            packet_field="integration_cost_ratio",
            contradict_pred=lambda c: float(
                c.get("integration_cost_ratio", 1.0)) < 0.20,
        ),
        ThesisImplication(
            claim="Exit multiple holds despite platform complexity "
                  "— buyers pay for integrated, not stapled.",
            partner_check="What's the exit multiple comp? Does it "
                          "include unintegrated rollups?",
            risk="medium",
            packet_field="exit_multiple_comp_integrated_only",
        ),
        ThesisImplication(
            claim="Management team retention through integration.",
            partner_check="Acquired-company leadership retention — "
                          "which CEOs roll into platform roles?",
            risk="high",
            packet_field="acquired_ceo_retention_pct",
            contradict_pred=lambda c: float(
                c.get("acquired_ceo_retention_pct", 1.0)) < 0.50,
        ),
    ]


def _cost_basis_compression_chain() -> List[ThesisImplication]:
    return [
        ThesisImplication(
            claim="Labor cost reduction doesn't trigger union action "
                  "or licensure short-falls.",
            partner_check="What's union status? Licensed staffing "
                          "ratios compliant post-cut?",
            risk="high",
            packet_field="union_contract_constraint",
            contradict_pred=lambda c: bool(
                c.get("union_contract_constraint", False)),
        ),
        ThesisImplication(
            claim="Contract labor (travel nurses, locum) reduction "
                  "holds — not just at hire-on, but on bed-day.",
            partner_check="What's the post-program contract-labor "
                          "mix target as % of worked hours?",
            risk="medium",
            packet_field="contract_labor_pct_target",
        ),
        ThesisImplication(
            claim="Quality metrics hold through the cost cut — no "
                  "star-rating downgrade.",
            partner_check="CMS star rating before and after the "
                          "cost program.",
            risk="high",
            packet_field="cms_star_rating_maintained",
        ),
        ThesisImplication(
            claim="Wage inflation in the local market doesn't "
                  "reverse the gain.",
            partner_check="What's local BLS healthcare wage growth "
                          "over the hold?",
            risk="medium",
            packet_field="local_wage_inflation_pct",
        ),
    ]


def _cmi_uplift_chain() -> List[ThesisImplication]:
    return [
        ThesisImplication(
            claim="CDI / clinical documentation improvement team "
                  "exists and is staffed — not outsourced hope.",
            partner_check="How many FTE CDI specialists? Coder "
                          "ratio to beds / visits?",
            risk="high",
            packet_field="cdi_fte_count",
        ),
        ThesisImplication(
            claim="Payer contracts support DRG uplift — no MS-DRG "
                  "audit recoupment risk.",
            partner_check="Any OIG CDI-related audits in the "
                          "sector? Payer CDI-specific audits?",
            risk="high",
            packet_field="cdi_audit_risk_material",
            contradict_pred=lambda c: bool(
                c.get("cdi_audit_risk_material", False)),
        ),
        ThesisImplication(
            claim="CMI lift is reflected in Medicare bridge at "
                  "realized rates, not target.",
            partner_check="What CMI uplift assumption drives the "
                          "Medicare bridge? Is it phased?",
            risk="medium",
            packet_field="cmi_uplift_phased",
        ),
        ThesisImplication(
            claim="Case-mix mix is sustainable — not driven by "
                  "temporary high-acuity patient surge.",
            partner_check="What's the CMI trend pre-COVID vs. "
                          "COVID peak vs. today?",
            risk="medium",
            packet_field="cmi_trend_pre_covid_baseline",
        ),
    ]


THESIS_CHAINS: Dict[str, Callable[[], List[ThesisImplication]]] = {
    "denial_reduction": _denial_chain,
    "payer_mix_shift": _payer_mix_shift_chain,
    "rollup_consolidation": _rollup_chain,
    "cost_basis_compression": _cost_basis_compression_chain,
    "cmi_uplift": _cmi_uplift_chain,
}


def list_thesis_chains() -> List[str]:
    return sorted(THESIS_CHAINS.keys())


def walk_thesis_chain(thesis: str,
                       packet: Dict[str, Any]) -> ThesisChainReport:
    builder = THESIS_CHAINS.get(thesis)
    if builder is None:
        return ThesisChainReport(
            thesis=thesis,
            entries=[],
            partner_note=(f"Unknown thesis '{thesis}'. Available: "
                          f"{', '.join(list_thesis_chains())}"),
        )
    entries: List[ThesisChainEntry] = []
    for imp in builder():
        status = "not_addressed"
        try:
            if imp.contradict_pred and imp.contradict_pred(packet):
                status = "contradicted"
            elif imp.confirm_pred and imp.confirm_pred(packet):
                status = "confirmed"
            elif imp.packet_field and imp.packet_field in packet:
                # Field is present but no pred triggered — neutral.
                status = "confirmed"
        except Exception:
            status = "not_addressed"
        entries.append(ThesisChainEntry(
            claim=imp.claim,
            partner_check=imp.partner_check,
            risk=imp.risk,
            status=status,
        ))

    not_addressed = sum(1 for e in entries
                        if e.status == "not_addressed")
    contradicted = sum(1 for e in entries
                       if e.status == "contradicted")
    confirmed = sum(1 for e in entries if e.status == "confirmed")
    high_unresolved = sum(
        1 for e in entries
        if e.risk == "high" and e.status != "confirmed"
    )

    if contradicted >= 1:
        note = (f"Thesis '{thesis}' has {contradicted} contradicted "
                "link(s). Partner: the chain breaks here — the "
                "headline doesn't survive.")
    elif high_unresolved >= 2:
        note = (f"Thesis '{thesis}': {high_unresolved} high-risk "
                "links not addressed. Partner: diligence these "
                "before IC; they are where the thesis lives or "
                "dies.")
    elif not_addressed >= 1:
        note = (f"Thesis '{thesis}': {not_addressed} links not "
                "yet addressed. Partner: tighten the chain — "
                "seller hasn't closed these loops.")
    else:
        note = (f"Thesis '{thesis}': chain is tight. Partner: "
                "proceed — the seller has addressed each downstream "
                "implication.")

    return ThesisChainReport(
        thesis=thesis,
        entries=entries,
        not_addressed_count=not_addressed,
        contradicted_count=contradicted,
        confirmed_count=confirmed,
        high_risk_unresolved=high_unresolved,
        partner_note=note,
    )


def render_thesis_chain_markdown(r: ThesisChainReport) -> str:
    lines = [
        f"# Thesis implications chain — `{r.thesis}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Confirmed: {r.confirmed_count}",
        f"- Not addressed: {r.not_addressed_count}",
        f"- Contradicted: {r.contradicted_count}",
        f"- High-risk unresolved: {r.high_risk_unresolved}",
        "",
        "| Status | Risk | Claim | Partner check |",
        "|---|---|---|---|",
    ]
    for e in r.entries:
        lines.append(
            f"| {e.status} | {e.risk} | {e.claim} | {e.partner_check} |"
        )
    return "\n".join(lines)
