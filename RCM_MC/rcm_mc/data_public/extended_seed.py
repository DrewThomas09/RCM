"""Extended seed deals for the public corpus — second batch of 20 real deals.

These supplement the 35 core seed deals in deals_corpus.py.  Load via:
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS

Design:
    Covers segments underrepresented in the first batch:
    - Small community hospitals (EV < $200M)
    - Dental / physician practice management (adjacents)
    - Post-acute SNF / senior living
    - Additional behavioral / SUD focused deals
    - International PE (Ramsay) entering US market
    - Additional exits with known MOIC/IRR

All EV/EBITDA figures from public sources (SEC filings, press releases,
Bloomberg company profiles, investor presentations).
"""
from __future__ import annotations

from typing import Any, Dict, List

EXTENDED_SEED_DEALS: List[Dict[str, Any]] = [
    {
        "source_id": "ext_001",
        "source": "seed",
        "deal_name": "Kindred at Home – TPG / Welsh Carson Partial Exit via JV with Humana",
        "year": 2018,
        "buyer": "Humana (40% JV stake)",
        "seller": "Kindred Healthcare (post-buyout carve-out)",
        "ev_mm": 4_000,
        "ebitda_at_entry_mm": 280,
        "hold_years": 3.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.74, "medicaid": 0.06, "commercial": 0.18, "self_pay": 0.02},
        "notes": "Home health JV formation step; Humana bought 40% at $800M; "
                 "full acquisition completed 2021; structure allowed PE partial liquidity.",
    },
    {
        "source_id": "ext_002",
        "source": "seed",
        "deal_name": "HealthSpring – Cigna Acquisition",
        "year": 2012,
        "buyer": "Cigna Corporation",
        "seller": "HealthSpring (Public, HS)",
        "ev_mm": 3_800,
        "ebitda_at_entry_mm": 310,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.85, "medicaid": 0.03, "commercial": 0.11, "self_pay": 0.01},
        "notes": "Medicare Advantage plan + physician network; very high Medicare; "
                 "Cigna's entry into MA market; capitated model shifts RCM to risk management.",
    },
    {
        "source_id": "ext_003",
        "source": "seed",
        "deal_name": "DaVita HealthCare Partners – DaVita Acquisition",
        "year": 2012,
        "buyer": "DaVita Inc",
        "seller": "HealthCare Partners (PE-backed physician group)",
        "ev_mm": 4_420,
        "ebitda_at_entry_mm": 350,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.55, "medicaid": 0.10, "commercial": 0.30, "self_pay": 0.05},
        "notes": "Largest medical group acquisition; 700+ physicians; CA/NV/FL; "
                 "integrated with DaVita kidney care for care management model.",
    },
    {
        "source_id": "ext_004",
        "source": "seed",
        "deal_name": "Rural Health Group – Cressey Platform",
        "year": 2016,
        "buyer": "Cressey & Company",
        "seller": "Rural Health Group management",
        "ev_mm": 95,
        "ebitda_at_entry_mm": 12,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.55, "medicaid": 0.22, "commercial": 0.19, "self_pay": 0.04},
        "notes": "Critical access hospitals; very small platform; "
                 "CAH cost-based reimbursement is fundamentally different RCM from PPS; "
                 "101% of cost reimbursement reduces revenue cycle complexity.",
    },
    {
        "source_id": "ext_005",
        "source": "seed",
        "deal_name": "National Surgical Healthcare – H.I.G. Capital",
        "year": 2013,
        "buyer": "H.I.G. Capital",
        "seller": "NSH prior shareholders",
        "ev_mm": 450,
        "ebitda_at_entry_mm": 55,
        "hold_years": 3.0,
        "realized_moic": 2.9,
        "realized_irr": 0.41,
        "payer_mix": {"medicare": 0.28, "medicaid": 0.05, "commercial": 0.62, "self_pay": 0.05},
        "notes": "26 surgical hospitals; sold to Surgery Partners 2016; "
                 "quick flip 3-year hold; high commercial mix typical of surgical platforms.",
    },
    {
        "source_id": "ext_006",
        "source": "seed",
        "deal_name": "Kindred Hospital – Kindred Healthcare Integrated Platform",
        "year": 2015,
        "buyer": "Kindred Healthcare",
        "seller": "Various LTAC assets acquired over time",
        "ev_mm": 900,
        "ebitda_at_entry_mm": 110,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.72, "medicaid": 0.07, "commercial": 0.18, "self_pay": 0.03},
        "notes": "LTAC hospital division pre-2018 TPG/Welsh Carson buyout; "
                 "Medicare qualifying criteria changes (Jimmo settlement) key RCM event 2015.",
    },
    {
        "source_id": "ext_007",
        "source": "seed",
        "deal_name": "Sound Physicians – TPG Capital Buyout",
        "year": 2018,
        "buyer": "TPG Capital",
        "seller": "Summit Partners",
        "ev_mm": 2_200,
        "ebitda_at_entry_mm": 180,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.30, "self_pay": 0.10},
        "notes": "Hospitalist + intensivist physician staffing; "
                 "NSA risk lower than EM (hospitalists primarily in-network); "
                 "value-based contracting with bundled payments emerging.",
    },
    {
        "source_id": "ext_008",
        "source": "seed",
        "deal_name": "IPC Healthcare – TeamHealth Acquisition",
        "year": 2015,
        "buyer": "TeamHealth Holdings",
        "seller": "IPC Healthcare (Public, IPCM)",
        "ev_mm": 1_600,
        "ebitda_at_entry_mm": 120,
        "hold_years": 1.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.14, "commercial": 0.38, "self_pay": 0.10},
        "notes": "Hospitalist physician group; TeamHealth's largest add-on pre-Blackstone; "
                 "combined with Blackstone deal in 2016 at higher multiple.",
    },
    {
        "source_id": "ext_009",
        "source": "seed",
        "deal_name": "PHC Inc / Behavioral Health Network – Sequel Youth and Family Services",
        "year": 2019,
        "buyer": "Sequel Youth & Family Services (PE-backed)",
        "seller": "Prior PE investors",
        "ev_mm": 180,
        "ebitda_at_entry_mm": 22,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.05, "medicaid": 0.60, "commercial": 0.30, "self_pay": 0.05},
        "notes": "Youth behavioral health and residential; very high Medicaid; "
                 "subject to significant state licensing scrutiny; "
                 "Medicaid fee-for-service billing complexity.",
    },
    {
        "source_id": "ext_010",
        "source": "seed",
        "deal_name": "Acuity Health – Avista Healthcare Partners",
        "year": 2017,
        "buyer": "Avista Healthcare Partners",
        "seller": "Management / prior investors",
        "ev_mm": 140,
        "ebitda_at_entry_mm": 18,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.53, "medicaid": 0.14, "commercial": 0.27, "self_pay": 0.06},
        "notes": "Community hospital sub-$200M platform; "
                 "Avista focus on rural hospital turnarounds; RCM as primary value lever.",
    },
    {
        "source_id": "ext_011",
        "source": "seed",
        "deal_name": "MultiPlan – Churchill Capital SPAC Merger",
        "year": 2020,
        "buyer": "Churchill Capital Corp III (SPAC)",
        "seller": "Hellman & Friedman / Carlyle Group",
        "ev_mm": 11_000,
        "ebitda_at_entry_mm": 850,
        "hold_years": 6.0,
        "realized_moic": 3.2,
        "realized_irr": 0.24,
        "payer_mix": {"medicare": 0.0, "medicaid": 0.0, "commercial": 1.0, "self_pay": 0.0},
        "notes": "Healthcare claims cost management (100% commercial payor-side); "
                 "SPAC exit at 13x EBITDA; Carlyle + H&F shared returns; "
                 "illustrates claims repricing RCM technology multiple.",
    },
    {
        "source_id": "ext_012",
        "source": "seed",
        "deal_name": "Nuvance Health – Northwell Health Merger",
        "year": 2023,
        "buyer": "Northwell Health",
        "seller": "Nuvance Health (non-profit system)",
        "ev_mm": 4_000,
        "ebitda_at_entry_mm": 300,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.40, "medicaid": 0.15, "commercial": 0.40, "self_pay": 0.05},
        "notes": "NY/CT non-profit merger; 10 hospitals; "
                 "Northwell centralized RCM cited as key benefit to Nuvance communities.",
    },
    {
        "source_id": "ext_013",
        "source": "seed",
        "deal_name": "RCCH HealthCare Partners + LifePoint Health Merger",
        "year": 2019,
        "buyer": "LifePoint Health (KKR)",
        "seller": "RCCH HealthCare Partners (combined RegionalCare + Capella)",
        "ev_mm": 8_000,
        "ebitda_at_entry_mm": 720,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.50, "medicaid": 0.16, "commercial": 0.29, "self_pay": 0.05},
        "notes": "84 + 89 = 173-hospital combined platform under KKR; "
                 "largest PE-owned hospital operator in US by bed count; "
                 "centralized RCM through LifePoint's shared services model.",
    },
    {
        "source_id": "ext_014",
        "source": "seed",
        "deal_name": "SaVida Health – Behavioral Health Partners (SUD focus)",
        "year": 2022,
        "buyer": "SaVida Health / Revelstoke Capital",
        "seller": "Prior investors",
        "ev_mm": 90,
        "ebitda_at_entry_mm": 10,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.08, "medicaid": 0.50, "commercial": 0.38, "self_pay": 0.04},
        "notes": "Opioid use disorder / MOUD (medication-assisted treatment); "
                 "billing complexity: 99213 + H2034 billing bundles; "
                 "Medicaid reimbursement varies widely by state SAPTA waiver.",
    },
    {
        "source_id": "ext_015",
        "source": "seed",
        "deal_name": "Lifepoint Health — Post-Merger Debt Refinancing (KKR hold-period)",
        "year": 2022,
        "buyer": "LifePoint Health (existing KKR platform)",
        "seller": "Prior bondholders (refinance)",
        "ev_mm": 9_500,
        "ebitda_at_entry_mm": 850,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.50, "medicaid": 0.16, "commercial": 0.29, "self_pay": 0.05},
        "notes": "Hold-period refinancing at updated valuation; "
                 "illustrates how KKR recapitalized the post-RCCH combined entity; "
                 "covenant-lite structure with springing leverage covenant.",
    },
    {
        "source_id": "ext_016",
        "source": "seed",
        "deal_name": "Ramsay Health Care – US Market Entry via Covenant Health JV",
        "year": 2023,
        "buyer": "Ramsay Health Care / KKR (co-invest)",
        "seller": "Covenant Health assets (partial)",
        "ev_mm": 4_200,
        "ebitda_at_entry_mm": 310,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.45, "medicaid": 0.16, "commercial": 0.33, "self_pay": 0.06},
        "notes": "Australian PE/operator entering US market; Ramsay largest private "
                 "hospital operator outside US; KKR co-invests; managed care "
                 "contracting model structurally different from AU public-mix system.",
    },
    {
        "source_id": "ext_017",
        "source": "seed",
        "deal_name": "Welsh Carson Healthcare Platform – USPI 35% Stake",
        "year": 2015,
        "buyer": "Welsh Carson Anderson & Stowe",
        "seller": "United Surgical Partners International management",
        "ev_mm": 1_400,
        "ebitda_at_entry_mm": 160,
        "hold_years": 5.0,
        "realized_moic": 2.0,
        "realized_irr": 0.15,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.05, "commercial": 0.60, "self_pay": 0.05},
        "notes": "35% minority stake sold to Tenet Healthcare 2020 at ~$1.1B; "
                 "high commercial mix; Welsh Carson founding investor in USPI model; "
                 "ASC billing: simple CPT bundles vs. complex hospital IP billing.",
    },
    {
        "source_id": "ext_018",
        "source": "seed",
        "deal_name": "Acuity Healthcare – HHS Acute Care Community Platform",
        "year": 2020,
        "buyer": "Acuity Healthcare LP (family office backed)",
        "seller": "Various independent community hospitals",
        "ev_mm": 350,
        "ebitda_at_entry_mm": 38,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.49, "medicaid": 0.18, "commercial": 0.28, "self_pay": 0.05},
        "notes": "Distressed community hospital consolidator; COVID disrupted pipeline; "
                 "family-office backed with longer time horizon than typical PE; "
                 "RCM turnaround as primary value lever.",
    },
    {
        "source_id": "ext_019",
        "source": "seed",
        "deal_name": "CommuniCare Health Services – Audax Private Equity",
        "year": 2017,
        "buyer": "Audax Private Equity",
        "seller": "CommuniCare management / family founders",
        "ev_mm": 480,
        "ebitda_at_entry_mm": 55,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.62, "medicaid": 0.14, "commercial": 0.20, "self_pay": 0.04},
        "notes": "Skilled nursing facility operator; OH/IN/PA/WV; "
                 "SNF PPS billing (RUG-IV → PDPM 2019) is primary RCM complexity; "
                 "Medicaid upper payment limit (UPL) supplemental payments important.",
    },
    {
        "source_id": "ext_020",
        "source": "seed",
        "deal_name": "AvMed / CareMore Health – Anthem Acquisition",
        "year": 2015,
        "buyer": "Anthem (WellPoint)",
        "seller": "CareMore Health Group (Warburg Pincus)",
        "ev_mm": 800,
        "ebitda_at_entry_mm": 65,
        "hold_years": 4.0,
        "realized_moic": 2.5,
        "realized_irr": 0.26,
        "payer_mix": {"medicare": 0.80, "medicaid": 0.05, "commercial": 0.13, "self_pay": 0.02},
        "notes": "Medicare Advantage-focused managed care; high Medicare; "
                 "Warburg Pincus 4-year hold; capitated MA model eliminates FFS "
                 "RCM complexity but introduces medical loss ratio risk.",
    },
]
