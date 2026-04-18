"""Drug Shortage / Supply-Chain Risk Tracker.

Models drug shortage exposure for PE healthcare platforms with meaningful
pharmaceutical spend (oncology, infusion, hospital, anesthesia).
Tracks FDA shortage list, sole-source risk, GPO reliability, and
tariff / geopolitical exposure.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CriticalDrug:
    drug: str
    therapy_area: str
    shortage_status: str
    sole_source: bool
    annual_volume_doses: int
    substitution_available: bool
    platform_spend_mm: float
    days_on_hand: int


@dataclass
class SupplierConcentration:
    supplier: str
    category: str
    annual_spend_mm: float
    share_of_category: float
    country_of_manufacture: str
    audit_history: str
    risk_score: int


@dataclass
class GeoExposure:
    country: str
    product_categories: int
    spend_exposure_mm: float
    tariff_risk_pct: float
    geopolitical_risk: str
    diversification_score: int


@dataclass
class ShortagePlaybook:
    scenario: str
    probability_pct: float
    financial_impact_mm: float
    operational_impact: str
    mitigation_status: str
    lead_time_days: int


@dataclass
class GPOMetric:
    gpo_partner: str
    contracts_count: int
    annual_volume_mm: float
    on_time_fill_rate_pct: float
    backorder_rate_pct: float
    price_stability_pct: float


@dataclass
class DrugShortageResult:
    total_critical_drugs: int
    active_shortages: int
    total_platform_spend_mm: float
    sole_source_exposure_mm: float
    overall_supply_risk_score: int
    risk_tier: str
    drugs: List[CriticalDrug]
    suppliers: List[SupplierConcentration]
    geography: List[GeoExposure]
    playbooks: List[ShortagePlaybook]
    gpos: List[GPOMetric]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 106):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_drugs() -> List[CriticalDrug]:
    return [
        CriticalDrug("Carboplatin (Inj)", "Oncology", "FDA Shortage - resolved 2024", False, 48000, True, 3.85, 45),
        CriticalDrug("Cisplatin (Inj)", "Oncology", "FDA Shortage - active", False, 28500, True, 2.65, 28),
        CriticalDrug("Methotrexate (Rheum)", "Rheumatology", "stable", False, 185000, True, 1.45, 120),
        CriticalDrug("Fluorouracil (5-FU)", "Oncology", "FDA Shortage - active", False, 32000, True, 4.25, 35),
        CriticalDrug("Bupivacaine (Reg Anesthesia)", "Anesthesia", "stable", False, 245000, True, 0.95, 90),
        CriticalDrug("Propofol (Sedation)", "Anesthesia", "intermittent availability", False, 425000, True, 1.85, 62),
        CriticalDrug("Rocuronium (NMB)", "Anesthesia", "stable", False, 85000, True, 0.55, 95),
        CriticalDrug("Doxorubicin (Anthracycline)", "Oncology", "stable", False, 22000, True, 2.15, 108),
        CriticalDrug("Pegfilgrastim (Neulasta)", "Oncology Supportive", "stable - biosimilars", False, 18500, True, 12.55, 75),
        CriticalDrug("Dexmedetomidine", "ICU Sedation", "intermittent availability", False, 65000, True, 0.85, 48),
        CriticalDrug("Adenosine (Cardiac Stress)", "Cardiology", "stable", True, 12500, False, 0.45, 55),
        CriticalDrug("Amiodarone (Anti-Arrhythmic)", "Cardiology", "stable", False, 38000, True, 0.65, 88),
        CriticalDrug("Epinephrine (1:1000)", "Emergency", "rolling shortage", False, 485000, True, 0.95, 42),
        CriticalDrug("Lidocaine (Local)", "Multi-Use", "stable", False, 1250000, True, 0.45, 95),
        CriticalDrug("Regadenoson (Lexiscan)", "Cardiac Imaging", "stable", True, 8500, False, 1.25, 68),
    ]


def _build_suppliers() -> List[SupplierConcentration]:
    return [
        SupplierConcentration("Pfizer Hospira", "Injectables / Oncology", 28.5, 0.38, "US/PR/IT", "2x FDA 483s 2023-2024", 72),
        SupplierConcentration("Fresenius Kabi", "Sterile Injectables", 18.5, 0.24, "DE/AT/CN", "clean 3-yr", 42),
        SupplierConcentration("Baxter International", "IV Solutions / Hospital", 22.5, 0.58, "US/PR", "PR hurricane disruption 2023", 58),
        SupplierConcentration("Teva Pharmaceuticals", "Generics Oral", 12.5, 0.22, "IL/US/HU", "clean 2-yr", 45),
        SupplierConcentration("Mylan / Viatris", "Generics", 15.8, 0.28, "IN/US/DE", "clean 3-yr", 48),
        SupplierConcentration("Sandoz (Novartis)", "Biosimilars / Generics", 18.5, 0.32, "CH/DE/AT", "clean 3-yr", 35),
        SupplierConcentration("Amgen / Biosimilars", "Biologics", 32.5, 0.45, "US/PR/IE", "clean 3-yr", 28),
        SupplierConcentration("AstraZeneca", "Respiratory / Oncology", 21.5, 0.35, "UK/SE/US", "clean 3-yr", 32),
        SupplierConcentration("Merck", "Oncology / Vaccines", 38.5, 0.42, "US/IE/NL", "clean 3-yr", 25),
        SupplierConcentration("Sun Pharma", "Generics / Derm", 8.2, 0.15, "IN/US", "1x FDA Warning Letter 2023", 65),
    ]


def _build_geography() -> List[GeoExposure]:
    return [
        GeoExposure("United States", 42, 118.5, 0.00, "very low", 98),
        GeoExposure("European Union", 28, 68.5, 0.12, "low", 85),
        GeoExposure("China", 18, 28.5, 0.28, "elevated", 45),
        GeoExposure("India", 35, 42.5, 0.18, "moderate", 72),
        GeoExposure("Puerto Rico", 12, 38.5, 0.05, "hurricane risk", 62),
        GeoExposure("Ireland", 15, 28.5, 0.08, "low", 82),
        GeoExposure("Israel", 6, 8.5, 0.12, "moderate", 58),
        GeoExposure("Switzerland", 8, 12.5, 0.08, "low", 85),
    ]


def _build_playbooks() -> List[ShortagePlaybook]:
    return [
        ShortagePlaybook("China tariff escalation (sterile injectables)", 0.45, 8.5, "Price pass-through to payers (limited)", "in progress", 30),
        ShortagePlaybook("Puerto Rico hurricane (IV solutions)", 0.25, 12.5, "Inventory pre-positioning; alt suppliers", "drill complete", 14),
        ShortagePlaybook("Oncology 5-FU / Cisplatin critical shortage", 0.75, 15.8, "Compounding pharmacy partnership", "activated", 7),
        ShortagePlaybook("FDA Warning Letter - Teva or Sun", 0.32, 4.2, "Alternate NDC switching playbook", "standing", 3),
        ShortagePlaybook("GPO price renegotiation failure", 0.22, 5.8, "Secondary GPO contract activation", "evaluated", 30),
        ShortagePlaybook("Biosimilar supply interruption", 0.15, 6.5, "Reference product fallback; payer coordination", "standing", 21),
        ShortagePlaybook("DEA quota change (Schedule II/III)", 0.18, 2.8, "Prescriber rotation; state compact alternatives", "standing", 60),
    ]


def _build_gpos() -> List[GPOMetric]:
    return [
        GPOMetric("Vizient", 2850, 85.5, 0.96, 0.025, 0.94),
        GPOMetric("Premier", 1985, 62.5, 0.95, 0.028, 0.93),
        GPOMetric("HealthTrust", 1450, 48.5, 0.94, 0.032, 0.92),
        GPOMetric("Intalere", 685, 22.5, 0.93, 0.035, 0.91),
        GPOMetric("Captis / MedAssets", 845, 28.5, 0.92, 0.038, 0.90),
    ]


def compute_drug_shortage() -> DrugShortageResult:
    corpus = _load_corpus()

    drugs = _build_drugs()
    suppliers = _build_suppliers()
    geography = _build_geography()
    playbooks = _build_playbooks()
    gpos = _build_gpos()

    total_spend = sum(d.platform_spend_mm for d in drugs)
    active = sum(1 for d in drugs if "Shortage - active" in d.shortage_status or "intermittent" in d.shortage_status or "rolling" in d.shortage_status)
    sole_source_exp = sum(d.platform_spend_mm for d in drugs if d.sole_source)

    # Risk score 0-100
    weighted_playbook_impact = sum(p.probability_pct * p.financial_impact_mm for p in playbooks)
    supplier_risk = sum(s.risk_score * s.annual_spend_mm for s in suppliers) / sum(s.annual_spend_mm for s in suppliers) if suppliers else 0
    risk_score = min(100, int(supplier_risk * 0.5 + active * 4 + weighted_playbook_impact * 2))

    if risk_score >= 70:
        tier = "elevated"
    elif risk_score >= 50:
        tier = "moderate"
    else:
        tier = "low"

    return DrugShortageResult(
        total_critical_drugs=len(drugs),
        active_shortages=active,
        total_platform_spend_mm=round(total_spend, 2),
        sole_source_exposure_mm=round(sole_source_exp, 2),
        overall_supply_risk_score=risk_score,
        risk_tier=tier,
        drugs=drugs,
        suppliers=suppliers,
        geography=geography,
        playbooks=playbooks,
        gpos=gpos,
        corpus_deal_count=len(corpus),
    )
