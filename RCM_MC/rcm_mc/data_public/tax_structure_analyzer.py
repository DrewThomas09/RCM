"""Tax Structure Analyzer for PE Exits.

Detailed tax-structuring scorecard for PE healthcare platform exits.
Covers F-reorg, 338(h)(10), 336(e), check-the-box, UBTI blockers,
tax-free rollovers, continuation-vehicle tax treatment, and state
tax diligence.

Complements /tax-structure (higher-level) with exit-specific
mechanics and scenario after-tax IRR math.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class StructureOption:
    structure: str
    description: str
    tax_treatment: str
    gain_recognition: str
    typical_scenario: str
    complexity: str


@dataclass
class AfterTaxScenario:
    structure: str
    gross_proceeds_mm: float
    federal_tax_mm: float
    state_tax_mm: float
    other_adjustments_mm: float
    after_tax_proceeds_mm: float
    after_tax_moic: float
    after_tax_irr: float


@dataclass
class RolloverMechanics:
    rollover_type: str
    typical_structure: str
    tax_deferred: bool
    lock_up_months: int
    typical_rollover_pct: float
    notes: str


@dataclass
class BlockerStructure:
    blocker_type: str
    purpose: str
    jurisdiction: str
    annual_cost_k: float
    affected_investors: str


@dataclass
class StateTaxDiligence:
    state: str
    relevant_tax: str
    rate: float
    apportionment_method: str
    notable_items: str


@dataclass
class SOR_Consideration:
    topic: str
    relevance: str
    diligence_action: str
    timeline_pre_close_days: int


@dataclass
class TaxStructureResult:
    recommended_structure: str
    estimated_tax_savings_mm: float
    after_tax_moic_uplift: float
    recommended_jurisdiction: str
    structures: List[StructureOption]
    after_tax_scenarios: List[AfterTaxScenario]
    rollovers: List[RolloverMechanics]
    blockers: List[BlockerStructure]
    state_diligence: List[StateTaxDiligence]
    sor_items: List[SOR_Consideration]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 116):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_structures() -> List[StructureOption]:
    return [
        StructureOption("Stock Sale (§1001)", "Straight stock purchase — seller recognizes capital gain",
                        "capital gain (seller); carryover basis (buyer)", "full recognition at sale",
                        "Default option when no stepped-up basis required", "low"),
        StructureOption("338(h)(10) Election", "Stock sale treated as asset sale for tax purposes; buyer gets step-up",
                        "ordinary/capital mix (seller); stepped-up basis (buyer)", "full seller recognition",
                        "When buyer wants step-up and seller is C-corp with minimal depreciated assets", "medium"),
        StructureOption("§336(e) Election", "Similar to 338(h)(10) but available for S-corp and LLC purchases",
                        "deemed asset sale treatment; step-up for buyer", "full seller recognition",
                        "Common for S-corp / partnership exits", "medium"),
        StructureOption("F-Reorganization", "Tax-free reorganization; convert entity form pre-close",
                        "no recognition at conversion; sale treated separately", "deferred",
                        "Single-owner S-corp or QSub restructuring pre-sale", "high"),
        StructureOption("Asset Sale (§1060)", "Direct asset purchase — straightforward step-up",
                        "ordinary/capital per asset class", "full seller recognition (double tax if C-corp)",
                        "When seller is LLC/partnership; buyer wants basis step-up", "low"),
        StructureOption("Stock-for-Stock (§368)", "Tax-free merger; seller receives buyer equity",
                        "no recognition at close; deferred until shareholder sale", "deferred",
                        "Strategic acquisitions by public buyers", "high"),
        StructureOption("QSBS (§1202) Exclusion", "Up to $10M or 10x basis gain exclusion for qualified stock",
                        "capital gain excluded for qualifying sellers", "5-year hold required",
                        "Founders with qualifying small business stock", "medium"),
        StructureOption("Installment Sale (§453)", "Seller receives note; recognition over payment period",
                        "installment basis (seller)", "deferred over term",
                        "Earnouts, contingent consideration; defers but not eliminates tax", "medium"),
        StructureOption("CV Rollover (Tax-Free)", "Continuation vehicle with §721 rollover treatment",
                        "no recognition on rolled portion; new entry basis",
                        "deferred indefinitely for rollover portion", "GP-led CV with LP rollover option", "medium"),
        StructureOption("Up-C / Tax Receivable Agreement (TRA)", "Pre-IPO restructure: C-corp holds LLC interests + TRA",
                        "step-up at IPO; TRA payments deductible",
                        "TRA pays 85% of tax benefit to pre-IPO holders",
                        "Pre-IPO preparation; monetizes tax attributes", "high"),
    ]


def _build_scenarios() -> List[AfterTaxScenario]:
    return [
        AfterTaxScenario("Stock Sale (baseline)", 485.0, 96.4, 28.5, 0.0, 360.1, 2.62, 0.216),
        AfterTaxScenario("338(h)(10) Election", 485.0, 102.8, 30.2, 0.0, 352.0, 2.56, 0.211),
        AfterTaxScenario("F-Reorg + Asset Sale", 485.0, 94.2, 26.8, 0.0, 364.0, 2.64, 0.218),
        AfterTaxScenario("Stock-for-Stock (tax-free)", 485.0, 0.0, 0.0, 0.0, 485.0, 3.52, 0.290),
        AfterTaxScenario("QSBS Exclusion (50% of proceeds)", 485.0, 48.2, 14.3, 0.0, 422.5, 3.07, 0.252),
        AfterTaxScenario("Earnout + Installment (50% deferred)", 485.0, 48.2, 14.3, 0.0, 422.5, 3.07, 0.252),
        AfterTaxScenario("CV Rollover (100% tax-free on rolled)", 485.0, 0.0, 0.0, 0.0, 485.0, 3.52, 0.290),
        AfterTaxScenario("Hybrid: 60% stock sale + 40% rollover", 485.0, 57.8, 17.1, 0.0, 410.1, 2.98, 0.245),
    ]


def _build_rollovers() -> List[RolloverMechanics]:
    return [
        RolloverMechanics("Management Rollover (§351)", "Pre-close C-corp rollover in exchange for buyer stock",
                          True, 36, 0.05, "Typical 5% of sale proceeds; drag-along rights"),
        RolloverMechanics("LLC / Partnership Rollover (§721)", "Sellers contribute to new LLC; defer gain",
                          True, 24, 0.08, "Typical 5-10% rollover for seller management"),
        RolloverMechanics("Stock-for-Stock Merger (§368(a))", "Target shareholders exchange for buyer stock",
                          True, 6, 0.95, "Requires 80%+ consideration in stock"),
        RolloverMechanics("Continuation Vehicle (§721)", "Rolled portion contributed to new LLC holding vehicle",
                          True, 36, 0.42, "Tax-deferred rollover maintained through CV structure"),
        RolloverMechanics("Earnout Structure (§453)", "Contingent consideration; tax recognition at receipt",
                          False, 24, 0.00, "Installment method; deferred but not eliminated"),
        RolloverMechanics("Phantom / Stock Appreciation Rights", "Cash-based incentive tied to stock value",
                          False, 0, 0.0, "Ordinary income at vest; not capital gains"),
    ]


def _build_blockers() -> List[BlockerStructure]:
    return [
        BlockerStructure("Corporate Blocker (Delaware C-Corp)", "Prevent UBTI flow-through to tax-exempt LPs",
                         "Delaware", 25.0, "Endowments, foundations, pension funds"),
        BlockerStructure("Cayman Blocker (Exempt Company)", "Non-US tax treatment for non-US investors",
                         "Cayman Islands", 45.0, "Non-US institutional LPs"),
        BlockerStructure("Irish / Luxembourg Holding Co", "EU tax-efficient structure",
                         "Ireland / Luxembourg", 85.0, "Non-US institutional + tax-efficient debt"),
        BlockerStructure("REIT Subsidiary", "Qualify dividends for §199A deduction; REIT distributions",
                         "Delaware", 65.0, "Real estate holdings; SNF/Senior Living platforms"),
        BlockerStructure("Single-Member LLC (§761 election)", "Check-the-box treatment; tax-transparent",
                         "Various states", 8.0, "Most PE fund investors"),
        BlockerStructure("Domestic Partnership (Feeder)", "Tax-transparent pass-through for US LPs",
                         "Delaware", 12.0, "Standard US LP partnership"),
    ]


def _build_state_diligence() -> List[StateTaxDiligence]:
    return [
        StateTaxDiligence("California", "Corporate Franchise Tax", 0.0884, "single sales factor apportionment",
                          "High-tax state; apportionment method can drive tax"),
        StateTaxDiligence("New York", "Corporate Franchise Tax", 0.0765, "single sales factor",
                          "Multi-state apportionment complex; NY MTA surcharge"),
        StateTaxDiligence("Texas", "Franchise Tax (Margin Tax)", 0.00375, "single sales factor",
                          "Low rate; minimum $1M revenue threshold"),
        StateTaxDiligence("Florida", "Corporate Income Tax", 0.055, "apportionment",
                          "Standard rate; no individual income tax attractive to rollovers"),
        StateTaxDiligence("Illinois", "Corporate Income + Replacement Tax", 0.095, "single sales factor",
                          "One of highest-burden states; replacement tax on pass-through"),
        StateTaxDiligence("Pennsylvania", "Corporate Net Income Tax", 0.0899, "apportionment",
                          "Healthcare-adjacent (Medicaid) considerations"),
        StateTaxDiligence("Ohio", "Commercial Activity Tax (CAT)", 0.0026, "gross receipts",
                          "Gross-receipts tax applies to healthcare revenues"),
        StateTaxDiligence("New Jersey", "Corporate Business Tax", 0.091, "three-factor + surtax",
                          "Complex structure; BAIT election may help"),
        StateTaxDiligence("Massachusetts", "Corporate Excise Tax", 0.08, "single sales factor",
                          "Net-worth + income tax; healthcare-specific nexus rules"),
        StateTaxDiligence("Oregon", "Corporate Activity Tax (CAT)", 0.0057, "gross receipts",
                          "Applies to healthcare gross receipts"),
        StateTaxDiligence("Washington", "Business & Occupation Tax", 0.015, "classification-based",
                          "B&O tax on gross receipts; healthcare services classified"),
        StateTaxDiligence("Nevada", "No Corporate Income Tax", 0.0, "N/A",
                          "Favorable for holding structures; physical nexus concerns"),
    ]


def _build_sor_items() -> List[SOR_Consideration]:
    return [
        SOR_Consideration("F-Reorg Pre-Close", "Required if converting S-corp structure before stock sale",
                          "Tax counsel opinion; IRS PLR potentially", 120),
        SOR_Consideration("338(h)(10) Election", "Joint election with buyer; filed with buyer's return",
                          "Determine election; model asset-by-asset step-up", 60),
        SOR_Consideration("Section 1202 Eligibility", "5-year hold + original issuance requirements",
                          "Certify QSBS status pre-close; document holding", 30),
        SOR_Consideration("State Tax Nexus Analysis", "Multi-state apportionment impact",
                          "State-by-state review; registration status", 60),
        SOR_Consideration("NOL / Tax Attribute Survival", "§382 limitation on NOLs post-acquisition",
                          "Quantify NOL value; structure to preserve if material", 45),
        SOR_Consideration("International Tax Structure", "If acquiring non-US ops, CFC / GILTI analysis",
                          "Coordinated tax counsel engagement", 75),
        SOR_Consideration("Management Rollover Mechanics", "§351 / §721 rollover structuring",
                          "Coordinate with management for rollover docs", 45),
        SOR_Consideration("Section 280G Golden Parachute", "Parachute payments to officers / directors",
                          "Valuation testing; shareholder approval", 30),
        SOR_Consideration("Tax Receivable Agreement (TRA)", "Pre-IPO structure for tax benefit monetization",
                          "Structure pre-IPO; negotiate TRA percentage", 180),
        SOR_Consideration("CV Rollover (§721)", "Continuation vehicle tax-deferred rollover",
                          "LPA amendment; fairness opinion", 90),
    ]


def compute_tax_structure_analyzer() -> TaxStructureResult:
    corpus = _load_corpus()

    structures = _build_structures()
    scenarios = _build_scenarios()
    rollovers = _build_rollovers()
    blockers = _build_blockers()
    state_dil = _build_state_diligence()
    sor = _build_sor_items()

    # Find best scenario (highest after-tax MOIC)
    best = max(scenarios, key=lambda s: s.after_tax_moic)
    baseline = next((s for s in scenarios if s.structure == "Stock Sale (baseline)"), scenarios[0])
    savings = best.after_tax_proceeds_mm - baseline.after_tax_proceeds_mm
    moic_uplift = best.after_tax_moic - baseline.after_tax_moic

    return TaxStructureResult(
        recommended_structure=best.structure,
        estimated_tax_savings_mm=round(savings, 2),
        after_tax_moic_uplift=round(moic_uplift, 3),
        recommended_jurisdiction="Delaware (Corporate Blocker) + Cayman (non-US LP Blocker)",
        structures=structures,
        after_tax_scenarios=scenarios,
        rollovers=rollovers,
        blockers=blockers,
        state_diligence=state_dil,
        sor_items=sor,
        corpus_deal_count=len(corpus),
    )
