"""Physician Labor Market Tracker.

Models physician supply/demand by specialty — critical for PE platforms
with clinician-dependent revenue. Covers wage inflation, retirement cliff,
NP/PA substitution, burnout attrition.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class SpecialtySupply:
    specialty: str
    active_physicians: int
    annual_grad_supply: int
    annual_retirements: int
    net_annual_change: int
    median_age: int
    projected_2030_shortage: int
    wage_inflation_ltm_pct: float


@dataclass
class WageGrowth:
    specialty: str
    median_comp_2019_k: float
    median_comp_2024_k: float
    cagr_pct: float
    locum_premium_pct: float
    signing_bonus_median_k: float


@dataclass
class NPPAExtenders:
    category: str
    fte_supply: int
    productivity_vs_md: float
    cost_ratio_vs_md: float
    scope_of_practice: str
    state_practice_authority: int


@dataclass
class BurnoutIndex:
    specialty: str
    burnout_rate_pct: float
    attrition_3yr_pct: float
    reduced_hours_pct: float
    retention_investment_pmpy_k: float


@dataclass
class GeographicGap:
    region_type: str
    physician_per_100k: int
    shortage_severity: str
    hpsa_score: int
    loan_repayment_available: bool


@dataclass
class LaborResult:
    total_active_physicians: int
    avg_median_age: float
    specialties_in_shortage: int
    blended_wage_inflation_pct: float
    specialties: List[SpecialtySupply]
    wages: List[WageGrowth]
    extenders: List[NPPAExtenders]
    burnout: List[BurnoutIndex]
    geography: List[GeographicGap]
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


def _build_specialties() -> List[SpecialtySupply]:
    items = [
        ("Primary Care / Family Med", 120000, 3950, 5850, -1900, 53, 48000, 0.062),
        ("Internal Medicine", 155000, 8200, 7500, 700, 55, 25000, 0.055),
        ("Pediatrics", 65000, 3150, 2850, 300, 51, 8500, 0.048),
        ("Psychiatry", 48500, 1850, 2200, -350, 58, 22000, 0.088),
        ("Anesthesiology", 52000, 1825, 2650, -825, 52, 15500, 0.072),
        ("Emergency Medicine", 48000, 2450, 2200, 250, 48, 5500, 0.068),
        ("Radiology", 42000, 1350, 2150, -800, 54, 18500, 0.074),
        ("OB/GYN", 42500, 1325, 1950, -625, 52, 8500, 0.058),
        ("Cardiology", 32500, 950, 1450, -500, 56, 9500, 0.065),
        ("Orthopedic Surgery", 28500, 775, 1200, -425, 54, 7500, 0.068),
        ("Gastroenterology", 18500, 525, 825, -300, 55, 5500, 0.075),
        ("Dermatology", 14500, 525, 485, 40, 52, 1500, 0.055),
        ("Ophthalmology", 22000, 475, 875, -400, 55, 5500, 0.048),
        ("Urology", 14500, 350, 625, -275, 56, 3500, 0.062),
        ("Hospitalist", 58000, 2850, 2200, 650, 45, 2500, 0.085),
    ]
    rows = []
    for s, ap, gs, ret, nc, age, short, wage in items:
        rows.append(SpecialtySupply(
            specialty=s, active_physicians=ap, annual_grad_supply=gs,
            annual_retirements=ret, net_annual_change=nc, median_age=age,
            projected_2030_shortage=short, wage_inflation_ltm_pct=wage,
        ))
    return rows


def _build_wages() -> List[WageGrowth]:
    items = [
        ("Primary Care / Family Med", 238, 285, 0.037, 0.68, 45),
        ("Psychiatry", 251, 320, 0.050, 0.82, 65),
        ("Hospitalist", 245, 312, 0.049, 0.82, 55),
        ("Anesthesiology", 398, 485, 0.040, 0.65, 85),
        ("Emergency Medicine", 325, 395, 0.039, 0.72, 75),
        ("Radiology", 422, 510, 0.039, 0.68, 85),
        ("Cardiology", 465, 575, 0.043, 0.58, 125),
        ("Orthopedic Surgery", 512, 640, 0.046, 0.52, 145),
        ("Gastroenterology", 455, 560, 0.043, 0.55, 115),
        ("Dermatology", 395, 485, 0.042, 0.48, 85),
    ]
    rows = []
    for s, old, new, cagr, loc, sign in items:
        rows.append(WageGrowth(
            specialty=s, median_comp_2019_k=old, median_comp_2024_k=new,
            cagr_pct=cagr, locum_premium_pct=loc, signing_bonus_median_k=sign,
        ))
    return rows


def _build_extenders() -> List[NPPAExtenders]:
    return [
        NPPAExtenders("Nurse Practitioner (Primary Care)", 234000, 0.78, 0.48, "full (most states)", 27),
        NPPAExtenders("Physician Assistant (All)", 168000, 0.72, 0.52, "collaborative (all states)", 0),
        NPPAExtenders("CRNA (Nurse Anesthetist)", 58000, 0.92, 0.62, "full in 17 states, collab elsewhere", 17),
        NPPAExtenders("CNM (Nurse Midwife)", 14500, 0.85, 0.58, "full (most states)", 32),
        NPPAExtenders("Psych NP", 28500, 0.85, 0.52, "full (23 states)", 23),
        NPPAExtenders("Acute Care NP (Hospitalist)", 32500, 0.75, 0.55, "hospital-based", 0),
        NPPAExtenders("Derm PA (Cosmetic/Medical)", 8500, 0.68, 0.55, "collaborative", 0),
        NPPAExtenders("Ortho PA (Surgical)", 12500, 0.70, 0.55, "collaborative", 0),
    ]


def _build_burnout() -> List[BurnoutIndex]:
    return [
        BurnoutIndex("Emergency Medicine", 0.65, 0.22, 0.28, 8.5),
        BurnoutIndex("Critical Care", 0.62, 0.20, 0.32, 7.2),
        BurnoutIndex("Internal Medicine", 0.55, 0.18, 0.25, 5.8),
        BurnoutIndex("Family Medicine", 0.52, 0.16, 0.22, 5.2),
        BurnoutIndex("OB/GYN", 0.54, 0.17, 0.24, 6.5),
        BurnoutIndex("Radiology", 0.48, 0.12, 0.18, 4.5),
        BurnoutIndex("Psychiatry", 0.42, 0.14, 0.32, 3.8),
        BurnoutIndex("Anesthesiology", 0.38, 0.10, 0.15, 3.5),
        BurnoutIndex("Dermatology", 0.32, 0.08, 0.14, 2.5),
        BurnoutIndex("Orthopedic Surgery", 0.35, 0.09, 0.12, 3.2),
    ]


def _build_geography() -> List[GeographicGap]:
    return [
        GeographicGap("Urban Core (population >1M)", 385, "no shortage", 0, False),
        GeographicGap("Urban Suburban", 265, "no shortage", 0, False),
        GeographicGap("Mid-Size Metro (250k-1M)", 215, "mild shortage", 12, False),
        GeographicGap("Small Metro (50k-250k)", 165, "moderate shortage", 17, True),
        GeographicGap("Rural (non-metro)", 98, "severe shortage", 22, True),
        GeographicGap("Frontier / Remote", 52, "critical shortage", 24, True),
        GeographicGap("Tribal / Indian Health Service", 88, "severe shortage", 23, True),
        GeographicGap("Inner-City Underserved", 142, "moderate shortage", 19, True),
    ]


def compute_physician_labor() -> LaborResult:
    corpus = _load_corpus()

    specialties = _build_specialties()
    wages = _build_wages()
    extenders = _build_extenders()
    burnout = _build_burnout()
    geography = _build_geography()

    total_active = sum(s.active_physicians for s in specialties)
    avg_age = sum(s.median_age * s.active_physicians for s in specialties) / total_active if total_active else 0
    shortage = sum(1 for s in specialties if s.projected_2030_shortage > 5000)
    blended_wage = sum(s.wage_inflation_ltm_pct * s.active_physicians for s in specialties) / total_active if total_active else 0

    return LaborResult(
        total_active_physicians=total_active,
        avg_median_age=round(avg_age, 1),
        specialties_in_shortage=shortage,
        blended_wage_inflation_pct=round(blended_wage, 4),
        specialties=specialties,
        wages=wages,
        extenders=extenders,
        burnout=burnout,
        geography=geography,
        corpus_deal_count=len(corpus),
    )
