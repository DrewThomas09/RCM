"""Platform Maturity / Exit Readiness Scorecard.

Evaluates platform readiness for different exit paths: strategic sale,
sponsor-to-sponsor, IPO, continuation vehicle, dividend recap. Identifies
gaps and produces a weighted maturity score with remediation plan.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class MaturityDimension:
    dimension: str
    current_score: int
    ipo_ready_threshold: int
    strategic_threshold: int
    s2s_threshold: int
    gap_to_ipo: int
    notes: str


@dataclass
class ExitPath:
    path: str
    readiness_score: int
    timing_months: int
    expected_ev_mm: float
    expected_multiple: float
    advantages: str
    risks: str


@dataclass
class RemediationAction:
    area: str
    action: str
    priority: str
    cost_mm: float
    timeline_months: int
    score_uplift: int


@dataclass
class FinancialProfile:
    metric: str
    current: str
    ipo_benchmark: str
    strategic_benchmark: str
    gap: str


@dataclass
class ExitComps:
    comp_deal: str
    sector: str
    exit_year: int
    ev_mm: float
    ebitda_multiple: float
    exit_path: str


@dataclass
class PlatformMaturityResult:
    overall_maturity_score: int
    recommended_exit_path: str
    time_to_exit_months: int
    expected_exit_ev_mm: float
    dimensions: List[MaturityDimension]
    exit_paths: List[ExitPath]
    remediations: List[RemediationAction]
    financial: List[FinancialProfile]
    comps: List[ExitComps]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 103):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_dimensions() -> List[MaturityDimension]:
    items = [
        ("Financial Reporting Maturity", 75, 90, 80, 72, "Big 4 audit in place; GAAP quarterly; need SOX 404-ready"),
        ("Revenue Predictability (Recurring %)", 78, 85, 72, 65, "Strong, but 12% long-tail churn in smaller contracts"),
        ("Management Team Depth", 72, 85, 75, 68, "CFO transitioning; COO solid; need Chief Legal Officer"),
        ("Customer/Payer Concentration", 68, 85, 70, 65, "Top payer at 22% — below risk threshold but monitoring"),
        ("Data &amp; Tech Infrastructure", 82, 90, 78, 72, "Consolidated EHR complete; analytics platform ramping"),
        ("Compliance / Legal", 85, 92, 85, 80, "Clean audit trail; no active DOJ/OIG matters"),
        ("Clinical Quality Metrics", 78, 85, 78, 72, "Top-quartile on 6 of 8 HEDIS measures"),
        ("ESG / Impact Narrative", 65, 80, 70, 60, "SDOH reporting in progress; no greenwashing exposure"),
        ("International / Growth Optionality", 72, 85, 75, 70, "US-only; 3 near-shore expansion opportunities"),
        ("Brand / Market Position", 75, 88, 78, 72, "Top-3 player in target markets; strong provider NPS"),
    ]
    rows = []
    for dim, cur, ipo, strat, s2s, notes in items:
        rows.append(MaturityDimension(
            dimension=dim, current_score=cur,
            ipo_ready_threshold=ipo, strategic_threshold=strat, s2s_threshold=s2s,
            gap_to_ipo=ipo - cur, notes=notes,
        ))
    return rows


def _build_exit_paths() -> List[ExitPath]:
    return [
        ExitPath("IPO (S-1 filing)", 72, 18, 3850.0, 14.5,
                 "Maximum headline value; long-term currency for M&A",
                 "Market timing; long drag time; lock-up periods; quarterly scrutiny"),
        ExitPath("Strategic Acquisition", 82, 9, 3250.0, 12.5,
                 "Synergy-enhanced price; faster close; cash at close",
                 "Limited buyer universe; anti-trust risk; strategic overlap"),
        ExitPath("Sponsor-to-Sponsor (LBO)", 88, 6, 2950.0, 11.5,
                 "Fast execution; continuity for management; certainty",
                 "Buyer underwriting base rate; highly financing-dependent"),
        ExitPath("Continuation Vehicle (CV)", 85, 4, 2750.0, 11.0,
                 "Extend hold; tax-advantaged rollover for existing LPs",
                 "GP/LP alignment; valuation independence; LPAC approval"),
        ExitPath("Dividend Recap", 92, 3, 0.0, 0.0,
                 "No ownership change; returns cash to LPs; preserves upside",
                 "Increases leverage; interest expense headwind; rating downgrade"),
        ExitPath("Minority Sale / Partial Exit", 82, 5, 950.0, 12.0,
                 "Partial liquidity; maintains control; lower transaction cost",
                 "Valuation ceiling for full exit; governance complexity"),
    ]


def _build_remediations() -> List[RemediationAction]:
    return [
        RemediationAction("Financial Reporting", "Implement SOX 404 readiness (internal controls audit)",
                          "critical for IPO", 2.4, 9, 8),
        RemediationAction("Management Team", "Hire Chief Legal Officer from public-co experience",
                          "high", 0.85, 4, 5),
        RemediationAction("Payer Diversification", "2nd-payer contract ramp to reduce top-payer to <18%",
                          "high", 1.2, 12, 6),
        RemediationAction("ESG Reporting", "Build SDOH outcomes measurement + TCFD-aligned reporting",
                          "medium", 0.65, 8, 7),
        RemediationAction("Investor Relations", "Stand up IR function + rehearse analyst day",
                          "critical for IPO", 1.5, 6, 4),
        RemediationAction("Audit History", "Extend to 3-year GAAP-audited track record",
                          "critical for IPO", 0.45, 18, 6),
        RemediationAction("Cyber / Data Posture", "SOC 2 Type II + HITRUST certification",
                          "medium", 0.95, 9, 3),
        RemediationAction("Tax Structure", "Pre-exit check-the-box review; tax-efficient structure",
                          "high", 0.55, 4, 2),
    ]


def _build_financial() -> List[FinancialProfile]:
    return [
        FinancialProfile("LTM Revenue ($M)", "$485M", ">$400M", ">$250M", "exceeds IPO threshold"),
        FinancialProfile("Revenue Growth YoY", "+18%", ">+20%", ">+15%", "just below IPO sweet spot"),
        FinancialProfile("LTM EBITDA Margin", "22.4%", ">22%", ">18%", "at IPO benchmark"),
        FinancialProfile("Free Cash Flow Conversion", "72%", ">75%", ">65%", "slight gap to IPO"),
        FinancialProfile("Net Debt / LTM EBITDA", "4.2x", "<3.5x", "<5.5x", "need paydown for IPO"),
        FinancialProfile("Gross Margin", "58.5%", ">55%", ">50%", "at IPO benchmark"),
        FinancialProfile("Net Revenue Retention", "108%", ">110%", ">100%", "slight gap to premium IPO"),
        FinancialProfile("Operating Cash Flow ($M)", "$112M", ">$100M", ">$50M", "exceeds IPO threshold"),
    ]


def _build_comps(corpus: List[dict]) -> List[ExitComps]:
    # Synthesize realistic comp deals from corpus
    realized = [d for d in corpus if d.get("status") in ("Realized", "Exited") and d.get("moic")]
    comps = []
    for d in realized[:12]:
        path = "strategic" if (d.get("moic") or 0) >= 2.5 else ("sponsor-to-sponsor" if (d.get("moic") or 0) >= 1.8 else "dividend recap / partial")
        name = d.get("company_name") or d.get("deal_name") or ""
        comps.append(ExitComps(
            comp_deal=name[:40],
            sector=d.get("sector", ""),
            exit_year=(d.get("year") or 2020) + int(d.get("hold_years") or 4),
            ev_mm=d.get("ev_mm") or 0,
            ebitda_multiple=d.get("ev_ebitda") or 0,
            exit_path=path,
        ))
    return comps


def compute_platform_maturity() -> PlatformMaturityResult:
    corpus = _load_corpus()

    dimensions = _build_dimensions()
    exit_paths = _build_exit_paths()
    remediations = _build_remediations()
    financial = _build_financial()
    comps = _build_comps(corpus)

    # Overall maturity = weighted average
    overall = sum(d.current_score for d in dimensions) / len(dimensions) if dimensions else 0

    # Recommend path with highest readiness * expected EV
    best = max(exit_paths, key=lambda p: p.readiness_score * max(p.expected_ev_mm, 1))
    recommended_path = best.path
    time_to_exit = best.timing_months
    expected_ev = best.expected_ev_mm

    return PlatformMaturityResult(
        overall_maturity_score=round(overall),
        recommended_exit_path=recommended_path,
        time_to_exit_months=time_to_exit,
        expected_exit_ev_mm=expected_ev,
        dimensions=dimensions,
        exit_paths=exit_paths,
        remediations=remediations,
        financial=financial,
        comps=comps,
        corpus_deal_count=len(corpus),
    )
