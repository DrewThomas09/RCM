"""Hospital Anchor Contract Tracker.

Tracks hospital system contracts for hospital-based physician groups
(anesthesia, radiology, ED, hospitalist, pathology) — the "anchor
customer" base that drives portfolio revenue concentration.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class HospitalContract:
    deal: str
    hospital_system: str
    service_line: str
    contract_start: str
    contract_end: str
    contract_value_annual_m: float
    stipend_m: float
    guaranteed_compensation_m: float
    productivity_based_pct: float
    exclusivity: bool
    renewal_probability_pct: float


@dataclass
class RenewalSchedule:
    deal: str
    contract: str
    expires: str
    months_until_expiry: int
    revenue_at_risk_m: float
    renewal_status: str
    incumbent_advantage: str


@dataclass
class StipendEconomics:
    hospital_system: str
    service_line: str
    stipend_vs_productivity_ratio: float
    stipend_per_wrvu: float
    total_stipend_m: float
    benchmark_percentile: str
    trend: str


@dataclass
class HospitalCounterparty:
    hospital_system: str
    rating: str
    contracts_with_portfolio: int
    total_revenue_m: float
    geographic_markets: str
    strategic_direction: str
    financial_health: str


@dataclass
class ServiceLineConcentration:
    service_line: str
    portfolio_deals: int
    total_contracts: int
    revenue_m: float
    avg_contract_size_m: float
    weighted_renewal_prob: float
    typical_term_years: int


@dataclass
class AtRiskContract:
    deal: str
    hospital_system: str
    service_line: str
    risk_factors: str
    at_risk_revenue_m: float
    mitigation_strategy: str
    owner: str
    action_date: str


@dataclass
class HospitalResult:
    total_contracts: int
    total_contract_value_m: float
    total_stipend_m: float
    weighted_renewal_probability_pct: float
    exclusive_contracts: int
    contracts_expiring_12mo: int
    at_risk_revenue_m: float
    contracts: List[HospitalContract]
    renewals: List[RenewalSchedule]
    stipends: List[StipendEconomics]
    counterparties: List[HospitalCounterparty]
    service_lines: List[ServiceLineConcentration]
    at_risk: List[AtRiskContract]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_contracts() -> List[HospitalContract]:
    return [
        HospitalContract("USAP (Horizon)", "HCA (east Texas)", "Anesthesia", "2022-07-01", "2027-06-30",
                         28.5, 8.5, 12.0, 0.65, True, 0.88),
        HospitalContract("USAP (Horizon)", "Baylor Scott & White", "Anesthesia", "2021-01-01", "2026-12-31",
                         42.0, 12.5, 18.5, 0.62, True, 0.82),
        HospitalContract("USAP (Horizon)", "Methodist Houston", "Anesthesia", "2023-04-01", "2028-03-31",
                         35.0, 10.5, 15.0, 0.65, True, 0.85),
        HospitalContract("USAP (Horizon)", "Tenet (DFW)", "Anesthesia", "2022-09-01", "2027-08-31",
                         24.5, 8.0, 12.5, 0.60, True, 0.85),
        HospitalContract("USAP (Horizon)", "AdventHealth", "Anesthesia", "2020-12-01", "2025-12-31",
                         32.0, 9.5, 14.0, 0.62, True, 0.62),
        HospitalContract("RadPartners (Spruce)", "Kaiser (NoCal)", "Radiology", "2022-10-01", "2027-09-30",
                         38.5, 11.5, 14.5, 0.70, True, 0.85),
        HospitalContract("RadPartners (Spruce)", "Ascension", "Radiology", "2021-03-01", "2026-02-28",
                         52.0, 15.5, 18.0, 0.70, True, 0.78),
        HospitalContract("RadPartners (Spruce)", "CommonSpirit", "Radiology", "2023-01-01", "2028-12-31",
                         68.5, 20.5, 22.0, 0.65, True, 0.88),
        HospitalContract("RadPartners (Spruce)", "HCA", "Radiology", "2022-05-01", "2027-04-30",
                         85.0, 25.5, 25.0, 0.65, True, 0.85),
        HospitalContract("Envision (Horizon)", "HCA Florida", "Emergency Medicine", "2023-06-01", "2028-05-31",
                         115.0, 32.5, 40.0, 0.60, True, 0.82),
        HospitalContract("Envision (Horizon)", "Tenet", "Emergency Medicine", "2022-02-01", "2027-01-31",
                         82.0, 22.5, 28.5, 0.62, True, 0.82),
        HospitalContract("Envision (Horizon)", "UHS", "Emergency Medicine", "2021-08-01", "2026-07-31",
                         58.0, 16.5, 20.5, 0.62, True, 0.75),
        HospitalContract("Hospitalist Group (Sierra)", "HCA", "Hospitalist", "2022-11-01", "2027-10-31",
                         45.0, 12.5, 22.0, 0.52, True, 0.85),
        HospitalContract("Hospitalist Group (Sierra)", "CommonSpirit", "Hospitalist", "2023-05-01", "2028-04-30",
                         38.0, 10.5, 18.5, 0.52, True, 0.88),
        HospitalContract("Pediatrix (Meridian)", "Multi-hospital Florida", "NICU / Neonatology", "2021-06-01", "2026-05-31",
                         52.0, 14.5, 22.5, 0.55, True, 0.80),
        HospitalContract("Pediatrix (Meridian)", "HCA (Tri-State)", "NICU / Neonatology", "2022-09-01", "2027-08-31",
                         62.0, 18.5, 26.5, 0.55, True, 0.82),
        HospitalContract("Pediatrix (Meridian)", "Ascension (MI)", "NICU / Neonatology", "2023-03-01", "2028-02-28",
                         38.5, 11.5, 16.5, 0.55, True, 0.85),
        HospitalContract("PathGroup (Ridge)", "HCA (Southeast)", "Pathology", "2022-04-01", "2027-03-31",
                         28.5, 8.5, 12.0, 0.65, True, 0.85),
        HospitalContract("PathGroup (Ridge)", "CommonSpirit (Midwest)", "Pathology", "2023-01-01", "2027-12-31",
                         22.5, 6.5, 9.5, 0.65, True, 0.88),
    ]


def _build_renewals() -> List[RenewalSchedule]:
    return [
        RenewalSchedule("USAP (Horizon)", "USAP × AdventHealth Anesthesia", "2025-12-31", 8, 32.0,
                        "in negotiation — pressure", "long-standing incumbent (10+ yrs)"),
        RenewalSchedule("RadPartners (Spruce)", "RadPartners × Ascension Radiology", "2026-02-28", 10, 52.0,
                        "proposal submitted", "cross-platform economics + volume"),
        RenewalSchedule("Pediatrix (Meridian)", "Pediatrix × FL Hospitals NICU", "2026-05-31", 13, 52.0,
                        "negotiations started", "specialty expertise + regulatory barriers"),
        RenewalSchedule("Envision (Horizon)", "Envision × UHS ED", "2026-07-31", 15, 58.0,
                        "early-stage discussions", "market-wide ED coverage economics"),
        RenewalSchedule("USAP (Horizon)", "USAP × Baylor Scott & White Anesthesia", "2026-12-31", 20, 42.0,
                        "pre-negotiation", "major system; likely renews"),
        RenewalSchedule("Envision (Horizon)", "Envision × Tenet ED", "2027-01-31", 21, 82.0,
                        "pre-negotiation", "Tenet-Envision strategic relationship"),
        RenewalSchedule("USAP (Horizon)", "USAP × Tenet DFW Anesthesia", "2027-08-31", 28, 24.5,
                        "scheduled 2026-Q3 RFP", "long-standing"),
        RenewalSchedule("RadPartners (Spruce)", "RadPartners × HCA Radiology", "2027-04-30", 24, 85.0,
                        "pre-negotiation", "marquee HCA relationship"),
        RenewalSchedule("USAP (Horizon)", "USAP × HCA East TX Anesthesia", "2027-06-30", 26, 28.5,
                        "pre-negotiation", "regional scale + staffing"),
    ]


def _build_stipends() -> List[StipendEconomics]:
    return [
        StipendEconomics("HCA", "Anesthesia", 0.298, 28.5, 42.5, "P75", "stable"),
        StipendEconomics("HCA", "Radiology", 0.300, 32.5, 25.5, "P75", "stable"),
        StipendEconomics("HCA", "Emergency Medicine", 0.283, 42.5, 32.5, "P75", "stable"),
        StipendEconomics("HCA", "Hospitalist", 0.278, 38.5, 12.5, "P75", "stable"),
        StipendEconomics("HCA", "Pathology", 0.298, 25.5, 8.5, "P75", "stable"),
        StipendEconomics("CommonSpirit", "Radiology", 0.299, 30.5, 20.5, "P60", "stable"),
        StipendEconomics("CommonSpirit", "Hospitalist", 0.276, 36.5, 10.5, "P60", "slightly widening"),
        StipendEconomics("CommonSpirit", "Pathology", 0.289, 24.5, 6.5, "P60", "stable"),
        StipendEconomics("Ascension", "Radiology", 0.298, 32.0, 15.5, "P60", "stable"),
        StipendEconomics("Ascension", "NICU / Neonatology", 0.299, 68.5, 11.5, "P60", "stable"),
        StipendEconomics("Tenet", "Anesthesia", 0.327, 32.0, 8.0, "P75", "slightly widening"),
        StipendEconomics("Tenet", "Emergency Medicine", 0.274, 42.0, 22.5, "P75", "stable"),
        StipendEconomics("UHS", "Emergency Medicine", 0.285, 40.0, 16.5, "P60", "slightly widening"),
        StipendEconomics("AdventHealth", "Anesthesia", 0.297, 30.0, 9.5, "P60", "tightening (pressure)"),
        StipendEconomics("Kaiser NoCal", "Radiology", 0.299, 30.5, 11.5, "P50", "stable"),
        StipendEconomics("Baylor Scott & White", "Anesthesia", 0.298, 31.0, 12.5, "P60", "stable"),
        StipendEconomics("Methodist Houston", "Anesthesia", 0.300, 31.5, 10.5, "P60", "stable"),
    ]


def _build_counterparties() -> List[HospitalCounterparty]:
    return [
        HospitalCounterparty("HCA Healthcare", "BBB+ (S&P)", 5, 283.0, "National (186 hospitals)",
                             "growth + ASC focus", "strong — A+ credit trajectory"),
        HospitalCounterparty("Tenet Healthcare", "B+ (S&P)", 3, 164.5, "Multi-state (57 hospitals)",
                             "ASC/USPI focus; divesting hospitals", "stable — improving"),
        HospitalCounterparty("CommonSpirit Health", "A- (S&P)", 3, 128.5, "National (140+ hospitals)",
                             "operating improvement + integration", "strained — improving"),
        HospitalCounterparty("Ascension", "A+ (Moody's)", 2, 90.5, "National (140 hospitals)",
                             "post-breach recovery + digital", "stable"),
        HospitalCounterparty("Baylor Scott & White", "AA- (S&P)", 1, 42.0, "Texas (50+ hospitals)",
                             "integrated model + VBC", "strong"),
        HospitalCounterparty("AdventHealth", "AA- (S&P)", 1, 32.0, "FL + 8 states (50+ hospitals)",
                             "growth + digital", "strong"),
        HospitalCounterparty("Kaiser Permanente", "AA+ (S&P)", 1, 38.5, "8 states (39 hospitals + MGs)",
                             "vertically integrated model", "strong"),
        HospitalCounterparty("UHS (Universal Health)", "BB+ (S&P)", 1, 58.0, "Multi-state (27 hospitals + BH)",
                             "behavioral expansion + ED", "stable"),
        HospitalCounterparty("Methodist Houston", "AA (S&P)", 1, 35.0, "Houston metro (8 hospitals)",
                             "academic + quality-driven", "strong"),
        HospitalCounterparty("Multi-hospital Florida PedRx", "(various)", 1, 52.0, "FL (12 hospitals)",
                             "pediatric specialty care", "varies by counterparty"),
    ]


def _build_service_lines() -> List[ServiceLineConcentration]:
    return [
        ServiceLineConcentration("Anesthesia", 1, 5, 162.0, 32.4, 0.80, 5),
        ServiceLineConcentration("Radiology", 1, 4, 243.5, 60.9, 0.85, 5),
        ServiceLineConcentration("Emergency Medicine", 1, 3, 255.0, 85.0, 0.80, 5),
        ServiceLineConcentration("Hospitalist", 1, 2, 83.0, 41.5, 0.87, 5),
        ServiceLineConcentration("NICU / Neonatology", 1, 3, 152.5, 50.8, 0.82, 5),
        ServiceLineConcentration("Pathology", 1, 2, 51.0, 25.5, 0.87, 5),
    ]


def _build_at_risk() -> List[AtRiskContract]:
    return [
        AtRiskContract("USAP (Horizon)", "AdventHealth", "Anesthesia",
                       "Contract term ending Dec 2025; stipend increase pressure (+$2.5M requested)",
                       32.0, "Value-based proposal + efficiency improvements; executive-level engagement",
                       "Sr. Partner (Horizon)", "2025-09-01"),
        AtRiskContract("Envision (Horizon)", "UHS", "Emergency Medicine",
                       "2026-Q3 renewal; UHS internal RFP planned given payor mix challenges",
                       58.0, "RFP response prep + alternative compensation model",
                       "Sr. Partner (Horizon)", "2025-10-01"),
        AtRiskContract("Pediatrix (Meridian)", "Multi-hospital FL", "NICU",
                       "Hospital consolidation underway; some target hospitals may shift to incumbent",
                       18.5, "Proactive negotiation + pricing flexibility",
                       "Sr. Partner (Meridian)", "2025-11-15"),
        AtRiskContract("Envision (Horizon)", "Tenet", "Emergency Medicine",
                       "Strategic relationship with Tenet — renewal likely but subject to market-wide economics",
                       28.5, "Executive relationship management + data-driven value case",
                       "Sr. Partner (Horizon)", "2026-01-15"),
        AtRiskContract("RadPartners (Spruce)", "Ascension", "Radiology",
                       "Post-cyber-breach Ascension under financial pressure; stipend reductions possible",
                       12.0, "AI-enabled productivity story + retention pricing",
                       "Sr. Partner (Spruce)", "2025-09-15"),
    ]


def compute_hospital_anchor() -> HospitalResult:
    corpus = _load_corpus()
    contracts = _build_contracts()
    renewals = _build_renewals()
    stipends = _build_stipends()
    counterparties = _build_counterparties()
    service_lines = _build_service_lines()
    at_risk = _build_at_risk()

    total_value = sum(c.contract_value_annual_m for c in contracts)
    total_stipend = sum(c.stipend_m for c in contracts)
    wtd_renewal = sum(c.renewal_probability_pct * c.contract_value_annual_m for c in contracts) / total_value if total_value > 0 else 0
    exclusive = sum(1 for c in contracts if c.exclusivity)
    expiring_12mo = sum(1 for r in renewals if r.months_until_expiry <= 12)
    at_risk_rev = sum(a.at_risk_revenue_m for a in at_risk)

    return HospitalResult(
        total_contracts=len(contracts),
        total_contract_value_m=round(total_value, 1),
        total_stipend_m=round(total_stipend, 1),
        weighted_renewal_probability_pct=round(wtd_renewal, 4),
        exclusive_contracts=exclusive,
        contracts_expiring_12mo=expiring_12mo,
        at_risk_revenue_m=round(at_risk_rev, 1),
        contracts=contracts,
        renewals=renewals,
        stipends=stipends,
        counterparties=counterparties,
        service_lines=service_lines,
        at_risk=at_risk,
        corpus_deal_count=len(corpus),
    )
