"""Seeking Chartis Module Index.

Consolidated directory of every analytical module in Seeking Chartis —
searchable catalog with category, description, deal lifecycle phase,
primary persona, and route. The index is the platform's own map of itself.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class Module:
    name: str
    route: str
    category: str
    lifecycle_phase: str
    primary_persona: str
    description: str
    corpus_dependent: bool


@dataclass
class CategoryRollup:
    category: str
    module_count: int
    lifecycle_phases: str
    example_modules: str


@dataclass
class PhaseRollup:
    phase: str
    module_count: int
    primary_output: str


@dataclass
class PersonaUsage:
    persona: str
    module_count: int
    top_modules: str


@dataclass
class ModuleIndexResult:
    total_modules: int
    categories: int
    modules: List[Module]
    category_rollups: List[CategoryRollup]
    phase_rollups: List[PhaseRollup]
    persona_usage: List[PersonaUsage]
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


def _build_modules() -> List[Module]:
    m = [
        # Sourcing & Sector Analysis
        Module("Deal Origination", "/deal-origination", "Sourcing", "sourcing", "principal",
               "Active M&A pipeline, banker relationship matrix, sector whitespace, win/loss analysis", True),
        Module("Sponsor Heatmap", "/sponsor-heatmap", "Sourcing", "sourcing", "associate",
               "Sponsor × sector performance grid — who wins in which sector", True),
        Module("Base-Rate Engine", "/base-rates", "Sourcing", "diligence", "associate",
               "P25/P50/P75/P90 percentile cuts across EV/EBITDA, margin, MOIC, IRR — filterable", True),
        Module("Market Rates", "/market-rates", "Sourcing", "diligence", "associate",
               "MOIC/IRR percentiles by sector, payer mix, and hold period", True),
        Module("MSA Concentration", "/msa-concentration", "Sourcing", "diligence", "associate",
               "HHI / CR3 / CR5 concentration analysis; whitespace scoring by MSA", True),
        Module("CMS Data Browser", "/cms-data-browser", "Data", "diligence", "analyst",
               "20 curated CMS datasets (PFS, OPPS, MS-DRG, HCRIS, MA), API status", False),
        Module("CMS Sources", "/cms-sources", "Data", "diligence", "analyst",
               "High-level CMS data source catalog (companion to CMS Data Browser)", False),
        # Diligence & Screening
        Module("Red-Flag Scanner", "/redflag-scanner", "Diligence", "diligence", "associate",
               "Rule-based red-flag screening against corpus benchmarks", True),
        Module("Value Backtester", "/backtester", "Diligence", "diligence", "associate",
               "Predicted MOIC vs realized base rates; lever attribution", True),
        Module("Anti-Trust Screener", "/antitrust-screener", "Diligence", "diligence", "principal",
               "HSR thresholds, HHI, market overlap, FTC case law, remediation matrix", True),
        Module("Payer Concentration", "/payer-concentration", "Diligence", "diligence", "associate",
               "CR1/CR3/CR5 payer concentration, HHI, renewal calendar, denials, NSA exposure", True),
        Module("FWA Detection", "/fraud-detection", "Diligence", "diligence", "associate",
               "Billing anomalies, upcoding risk, Stark/AKS referral patterns, compliance events", True),
        Module("Drug Shortage", "/drug-shortage", "Diligence", "diligence", "analyst",
               "FDA shortage list, supplier concentration, geographic / tariff exposure", True),
        Module("Cyber Risk", "/cyber-risk", "Diligence", "diligence", "principal",
               "NIST CSF maturity, incident history, ransomware prep, HIPAA/HITRUST compliance", True),
        Module("AI Operating Model", "/ai-operating-model", "Diligence", "diligence", "associate",
               "AI initiative portfolio, vendor landscape, model governance, ROI by bucket", True),
        Module("Health Equity Scorecard", "/health-equity", "Diligence", "diligence", "associate",
               "CMS Health Equity Index, SDOH screening, equity investment ROI, disparity flags", True),
        Module("Physician Labor Market", "/physician-labor", "Diligence", "diligence", "associate",
               "Supply/demand by specialty, wage inflation, NP/PA extender, burnout, HPSA", True),
        # Sector-Specific Analyzers (sample highlight)
        Module("Physician Comp Plan", "/phys-comp-plan", "Sector", "diligence", "analyst",
               "MD/NP/PA comp plan design, RVU productivity, quality bonus structure", True),
        Module("Locum Workforce", "/locum-tracker", "Sector", "portfolio", "associate",
               "Contract clinician spend, coverage gaps, permanent conversion pipeline", True),
        Module("MA Contracts", "/ma-contracts", "Sector", "portfolio", "associate",
               "MA plan economics, bid/bench/rebate, RAF optimization, Stars, V28", True),
        Module("340B Drug Pricing", "/drug-pricing-340b", "Sector", "portfolio", "associate",
               "Covered entity eligibility, ceiling price spread, contract pharmacy, audits", True),
        Module("ACO Economics", "/aco-economics", "Sector", "portfolio", "principal",
               "MSSP/REACH/MA capitation, shared savings, quality scoring", True),
        Module("Roll-Up Economics", "/rollup-economics", "Value Creation", "diligence", "principal",
               "Multiple arbitrage, add-on cadence, synergy capture, debt capacity", True),
        Module("De Novo Expansion", "/denovo-expansion", "Value Creation", "portfolio", "associate",
               "Greenfield buildout, market expansion queue, ramp curves, lease/buy NPV", True),
        Module("PMI Playbook", "/pmi-playbook", "Value Creation", "portfolio", "principal",
               "Post-merger integration workstreams, synergy capture, risk register", True),
        Module("Direct Employer", "/direct-employer", "Value Creation", "portfolio", "associate",
               "Centers of Excellence, on-site clinics, ERISA structure, RFP pipeline", True),
        Module("CIN Analyzer", "/cin-analyzer", "Value Creation", "portfolio", "associate",
               "Clinical Integration Network: providers, contracts, quality, compliance", True),
        Module("ZBB Tracker", "/zbb-tracker", "Value Creation", "portfolio", "associate",
               "Zero-based budgeting cost rebuild, savings initiatives, vendor rationalization", True),
        # Capital & Finance
        Module("Capital Call Pacing", "/capital-pacing", "Capital", "portfolio", "principal",
               "Fund-level cashflow, J-curve, DPI/TVPI/RVPI evolution, vintage comparison", True),
        Module("Covenant Headroom", "/covenant-headroom", "Capital", "portfolio", "principal",
               "Covenant compliance matrix, stress scenarios, cure rights, amort schedule", True),
        Module("Direct Lending", "/direct-lending", "Capital", "portfolio", "principal",
               "Private credit facility portfolio, market spreads, default trends, portfolio marks", True),
        Module("REIT / SLB", "/reit-analyzer", "Capital", "portfolio", "principal",
               "Real estate monetization, cap rate comps, rent coverage, REIT buyer landscape", True),
        Module("Platform Maturity", "/platform-maturity", "Capital", "exit", "principal",
               "Exit readiness scorecard, 6 exit paths, remediation roadmap", True),
        # IC / Committee
        Module("IC Memo Generator", "/ic-memo-gen", "IC", "diligence", "principal",
               "Standardized IC memo: thesis, findings, levers, risks, scenarios, structure", True),
        # Sponsor League / Performance
        Module("Sponsor League", "/sponsor-league", "Performance", "sourcing", "associate",
               "Sponsor track record rankings across sectors and vintages", True),
        Module("Exit Timing", "/exit-timing", "Performance", "exit", "principal",
               "Hold period analysis, exit market timing indicators", True),
        Module("Telehealth Economics", "/telehealth-econ", "Sector", "diligence", "associate",
               "Visit-level P&L, provider productivity, state parity, PHE cliff, DTC comps", True),
        Module("HCIT Platform", "/hcit-platform", "Sector", "diligence", "associate",
               "SaaS metrics: ARR/NRR/LTV/CAC, Rule of 40, TAM penetration, comps", True),
        Module("Biosimilars", "/biosimilars", "Sector", "portfolio", "associate",
               "LoE waves, ASP+6% economics, provider margin, interchangeable status", True),
        Module("Trial Site Econ", "/trial-site-econ", "Sector", "diligence", "associate",
               "Clinical trial site P&L, therapeutic area mix, phase economics, sponsors", True),
    ]
    return m


def _build_categories(modules: List[Module]) -> List[CategoryRollup]:
    from collections import Counter
    cats: dict = {}
    for m in modules:
        cats.setdefault(m.category, []).append(m)
    rows = []
    for cat, ms in cats.items():
        phases = sorted(set(m.lifecycle_phase for m in ms))
        examples = ", ".join(m.name for m in ms[:3])
        rows.append(CategoryRollup(
            category=cat,
            module_count=len(ms),
            lifecycle_phases=" / ".join(phases),
            example_modules=examples,
        ))
    return sorted(rows, key=lambda c: c.module_count, reverse=True)


def _build_phases(modules: List[Module]) -> List[PhaseRollup]:
    outputs = {
        "sourcing": "deal pipeline, sector whitespace, competitive intel",
        "diligence": "IC memo inputs, risk flags, value creation plan",
        "portfolio": "value creation tracking, quarterly reporting, operating cadence",
        "exit": "exit readiness, buyer landscape, return modeling",
    }
    from collections import Counter
    phase_counts = Counter(m.lifecycle_phase for m in modules)
    rows = []
    for phase, count in phase_counts.most_common():
        rows.append(PhaseRollup(phase=phase, module_count=count, primary_output=outputs.get(phase, "—")))
    return rows


def _build_personas(modules: List[Module]) -> List[PersonaUsage]:
    from collections import Counter
    persona_modules: dict = {}
    for m in modules:
        persona_modules.setdefault(m.primary_persona, []).append(m)
    rows = []
    for persona, ms in persona_modules.items():
        top = ", ".join(mm.name for mm in ms[:5])
        rows.append(PersonaUsage(persona=persona, module_count=len(ms), top_modules=top))
    return sorted(rows, key=lambda p: p.module_count, reverse=True)


def compute_module_index() -> ModuleIndexResult:
    corpus = _load_corpus()
    modules = _build_modules()
    categories = _build_categories(modules)
    phases = _build_phases(modules)
    personas = _build_personas(modules)

    return ModuleIndexResult(
        total_modules=len(modules),
        categories=len(categories),
        modules=modules,
        category_rollups=categories,
        phase_rollups=phases,
        persona_usage=personas,
        corpus_deal_count=len(corpus),
    )
