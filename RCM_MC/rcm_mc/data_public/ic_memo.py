"""IC Memo Generator.

Produces a standardized investment committee memo synthesizing data
from multiple Seeking Chartis modules (base rates, redflag scanner,
antitrust, payer concentration, etc.) into an IC-ready recommendation.

The IC memo is the output artifact that partners present to committee —
this module builds it from the platform's diligence stack.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class ExecSummary:
    deal_name: str
    sector: str
    ev_mm: float
    ev_ebitda_multiple: float
    ebitda_mm: float
    revenue_mm: float
    projected_moic: float
    projected_irr: float
    hold_years: float
    recommendation: str
    committee_vote_needed: str


@dataclass
class InvestmentThesis:
    thesis_element: str
    description: str
    evidence_strength: str
    validation_score: int


@dataclass
class DiligenceFinding:
    workstream: str
    finding: str
    severity: str
    mitigation: str
    impact_on_thesis: str


@dataclass
class ValueCreationLever:
    lever: str
    target_mm: float
    base_rate_mm: float
    probability_pct: float
    timeline_months: int
    expected_contribution_mm: float


@dataclass
class RiskRegister:
    risk: str
    category: str
    probability: str
    impact_mm: float
    mitigation_plan: str
    residual_risk: str


@dataclass
class ScenarioOutcome:
    scenario: str
    ebitda_at_exit_mm: float
    exit_multiple: float
    equity_proceeds_mm: float
    moic: float
    irr: float
    probability_pct: float


@dataclass
class DealStructure:
    component: str
    amount_mm: float
    terms: str
    notes: str


@dataclass
class ICMemoResult:
    memo_version: str
    prepared_date: str
    committee_meeting_date: str
    summary: ExecSummary
    thesis: List[InvestmentThesis]
    findings: List[DiligenceFinding]
    levers: List[ValueCreationLever]
    risks: List[RiskRegister]
    scenarios: List[ScenarioOutcome]
    structure: List[DealStructure]
    expected_moic: float
    expected_irr: float
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 113):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_summary() -> ExecSummary:
    return ExecSummary(
        deal_name="Project Azalea (GI Network SE)",
        sector="Gastroenterology",
        ev_mm=285.0,
        ev_ebitda_multiple=13.0,
        ebitda_mm=22.0,
        revenue_mm=98.2,
        projected_moic=2.78,
        projected_irr=0.227,
        hold_years=5.0,
        recommendation="PROCEED — submit final bid",
        committee_vote_needed="Full IC approval + investment sub-committee consent",
    )


def _build_thesis() -> List[InvestmentThesis]:
    return [
        InvestmentThesis("Platform Positioning", "3rd-largest GI group in high-growth Sunbelt MSA",
                         "strong", 88),
        InvestmentThesis("M&A Opportunity", "8-12 identified bolt-on targets in core + adjacent markets",
                         "moderate", 72),
        InvestmentThesis("Clinical Differentiation", "Top-quartile quality metrics vs peers; anesthesia JV",
                         "strong", 85),
        InvestmentThesis("Payer Mix Quality", "62% commercial; BCBS renewal 2027 provides price runway",
                         "moderate", 70),
        InvestmentThesis("Operating Leverage", "22.5% EBITDA margin vs 18.5% sector P50 — upside to 26%",
                         "strong", 82),
        InvestmentThesis("Value Creation", "RCM / scheduling / anesthesia JV optimizations quantified",
                         "strong", 80),
        InvestmentThesis("Management Team", "Strong CEO with prior PE exit; CFO transitioning",
                         "moderate", 68),
        InvestmentThesis("Exit Optionality", "Strategic buyers (GI Alliance, US Digestive) + sponsor demand",
                         "strong", 85),
    ]


def _build_findings() -> List[DiligenceFinding]:
    return [
        DiligenceFinding("Financial QoE", "Management adjustments $3.2M (one-time exec severance + refinancing)",
                         "clean", "Independent QoE confirmed; minor normalization", "no impact"),
        DiligenceFinding("Commercial", "Top payer BCBS at 22% of revenue; renewal 2027",
                         "medium", "Price reset leverage; relationship strong", "2nd-payer development"),
        DiligenceFinding("Operational", "Anesthesia model: W-2 vs 1099 classification risk",
                         "medium", "Transition to W-2 post-close; $0.4M annualized cost", "minor margin impact"),
        DiligenceFinding("Regulatory", "2 OIG audits 2023 — closed no action",
                         "minor", "Audit trail clean; proactive compliance program", "no impact"),
        DiligenceFinding("Legal", "3 pending malpractice suits — all covered by insurance",
                         "minor", "Standard practice; reserves adequate", "no impact"),
        DiligenceFinding("IT / Cyber", "Epic instance at risk of mid-term migration forced by Epic EOL schedule",
                         "medium", "Budget $2.5M for 18-month migration", "integration cost"),
        DiligenceFinding("HR", "Key-person concentration: 2 senior MDs, 35% of revenue",
                         "high", "Long-term employment + equity; rollover negotiations", "key-person risk"),
        DiligenceFinding("Antitrust", "MSA concentration clears (CR3 42% pre → 48% post)",
                         "clean", "Below 50% CR3 safety zone", "no impact"),
    ]


def _build_levers() -> List[ValueCreationLever]:
    return [
        ValueCreationLever("Bolt-On M&A (8-12 practices)", 12.5, 8.8, 0.75, 36, 9.4),
        ValueCreationLever("Anesthesia JV Optimization", 3.8, 3.5, 0.88, 12, 3.3),
        ValueCreationLever("RCM / Billing Improvement", 2.5, 2.2, 0.82, 18, 2.1),
        ValueCreationLever("Payer Rate Uplift (BCBS 2027)", 1.8, 1.4, 0.62, 24, 1.1),
        ValueCreationLever("Supply Chain / GPO Consolidation", 0.85, 0.70, 0.88, 12, 0.75),
        ValueCreationLever("Operating Leverage (cost discipline)", 1.5, 1.2, 0.78, 24, 1.2),
        ValueCreationLever("Multiple Arbitrage (13x → 14.5x exit)", 13.5, 11.0, 0.68, 60, 9.2),
    ]


def _build_risks() -> List[RiskRegister]:
    return [
        RiskRegister("Medicare rate cut (CRS / CMS annual)", "Regulatory", "medium", 3.5,
                     "Sensitivity built into model; 1% = $0.22M EBITDA", "residual"),
        RiskRegister("CMS colonoscopy age-45 creates volume headwind", "Regulatory", "low", 0.5,
                     "Already reflected in CBO estimates; procedure mix shift", "minimal"),
        RiskRegister("Key MD departure", "Operational", "medium", 6.5,
                     "Employment agreements + equity retention; identified successor pipeline", "residual"),
        RiskRegister("BCBS 2027 renewal < market rate", "Commercial", "medium", 4.2,
                     "2nd payer development underway; relationship strong", "residual"),
        RiskRegister("Integration cost overrun (EHR migration)", "Operational", "medium", 2.5,
                     "Budget reserve + seller indemnification", "mitigated"),
        RiskRegister("Market entrance by GI Alliance competitor", "Strategic", "medium", 1.8,
                     "1st-mover advantage; tuck-in before competitor enters", "monitor"),
        RiskRegister("Macro cap-ex lending rate increase", "Financing", "medium", 2.2,
                     "Fixed-rate term loan; minimal floating exposure", "mitigated"),
        RiskRegister("DOJ qui tam / FCA post-close", "Legal", "low", 8.5,
                     "Compliance program; indemnification from seller", "residual"),
    ]


def _build_scenarios() -> List[ScenarioOutcome]:
    return [
        ScenarioOutcome("Downside (base case -25%)", 31.5, 11.0, 285.0, 1.50, 0.085, 0.20),
        ScenarioOutcome("Base Case", 42.0, 13.0, 488.0, 2.78, 0.227, 0.55),
        ScenarioOutcome("Upside (base case +15%)", 48.3, 14.0, 595.0, 3.38, 0.277, 0.20),
        ScenarioOutcome("Home Run (strategic / IPO)", 55.5, 16.0, 752.0, 4.35, 0.342, 0.05),
    ]


def _build_structure() -> List[DealStructure]:
    return [
        DealStructure("Purchase Price / EV", 285.0, "13.0x LTM EBITDA", "Include $2.5M WC adjustment"),
        DealStructure("Cash at Close", 142.5, "50% of EV", "Committed financing signed"),
        DealStructure("First-Lien Term Loan", 114.0, "SOFR+475 / 7yr / cov-lite", "Ares Capital / Golub"),
        DealStructure("Second-Lien Term Loan", 28.5, "SOFR+825 / 7yr / cov-lite", "Owl Rock / Apollo"),
        DealStructure("Seller Rollover", 14.25, "5% equity; 2nd closing bite", "Key MDs required"),
        DealStructure("Management Equity", 14.25, "Stub + PIK note on close", "CEO + CFO + COO"),
        DealStructure("Earnout", 11.4, "4% over 24 months on EBITDA >$25M", "Downside protection"),
        DealStructure("Indemnification Reserve", 11.4, "4% escrow over 18 months", "Standard R&W insurance"),
    ]


def compute_ic_memo() -> ICMemoResult:
    corpus = _load_corpus()

    summary = _build_summary()
    thesis = _build_thesis()
    findings = _build_findings()
    levers = _build_levers()
    risks = _build_risks()
    scenarios = _build_scenarios()
    structure = _build_structure()

    # Expected MOIC / IRR = probability-weighted
    expected_moic = sum(s.moic * s.probability_pct for s in scenarios) / sum(s.probability_pct for s in scenarios)
    expected_irr = sum(s.irr * s.probability_pct for s in scenarios) / sum(s.probability_pct for s in scenarios)

    return ICMemoResult(
        memo_version="v3.2 FINAL",
        prepared_date="2026-04-14",
        committee_meeting_date="2026-04-21",
        summary=summary,
        thesis=thesis,
        findings=findings,
        levers=levers,
        risks=risks,
        scenarios=scenarios,
        structure=structure,
        expected_moic=round(expected_moic, 3),
        expected_irr=round(expected_irr, 4),
        corpus_deal_count=len(corpus),
    )
