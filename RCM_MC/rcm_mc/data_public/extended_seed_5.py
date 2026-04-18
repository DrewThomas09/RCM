"""Extended seed batch 5 — deals 116-135.

Covers 2019-2024 vintage: behavioral health platforms, home infusion,
physician practice consolidation, dental DSOs, value-based care IPOs,
and large-scale hospital system M&A.
"""
from __future__ import annotations

EXTENDED_SEED_DEALS_5 = [
    # 116
    {
        "source_id": "seed_116",
        "source": "seed",
        "deal_name": "Acadia Healthcare – Behavioral Portfolio Add-ons 2021",
        "year": 2021,
        "buyer": "Acadia Healthcare",
        "seller": "Various regional operators",
        "ev_mm": 680.0,
        "ebitda_at_entry_mm": 72.0,
        "hold_years": 4.0,
        "realized_moic": 2.1,
        "realized_irr": 0.19,
        "payer_mix": {
            "medicare": 0.28, "medicaid": 0.38, "commercial": 0.24, "selfpay": 0.10
        },
        "notes": (
            "Behavioral health platform roll-up; Southeast concentration; "
            "benefits from mental health parity enforcement"
        ),
    },
    # 117
    {
        "source_id": "seed_117",
        "source": "seed",
        "deal_name": "Option Care Health – Walgreens Infusion Services Carve-out",
        "year": 2019,
        "buyer": "Option Care Health",
        "seller": "Walgreens Boots Alliance",
        "ev_mm": 580.0,
        "ebitda_at_entry_mm": 48.0,
        "hold_years": 3.5,
        "realized_moic": 2.8,
        "realized_irr": 0.24,
        "payer_mix": {
            "medicare": 0.35, "medicaid": 0.15, "commercial": 0.50, "selfpay": 0.00
        },
        "notes": (
            "Home infusion carve-out from Walgreens; merged with BioScrip to form Option Care Health; "
            "high commercial mix drives margin"
        ),
    },
    # 118
    {
        "source_id": "seed_118",
        "source": "seed",
        "deal_name": "USPI / Tenet Healthcare – ASC Add-on Cluster 2022",
        "year": 2022,
        "buyer": "United Surgical Partners International / Tenet Healthcare",
        "seller": "Various independent ASC owners",
        "ev_mm": 1200.0,
        "ebitda_at_entry_mm": 155.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.22, "medicaid": 0.05, "commercial": 0.73, "selfpay": 0.00
        },
        "notes": (
            "15-center ASC cluster; high commercial mix drives margin; "
            "TX-heavy footprint; ongoing accretion to Tenet"
        ),
    },
    # 119
    {
        "source_id": "seed_119",
        "source": "seed",
        "deal_name": "Smile Brands – Gryphon Investors LBO",
        "year": 2020,
        "buyer": "Gryphon Investors",
        "seller": "Smile Brands management",
        "ev_mm": 480.0,
        "ebitda_at_entry_mm": 55.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.05, "medicaid": 0.22, "commercial": 0.58, "selfpay": 0.15
        },
        "notes": (
            "Dental DSO LBO; 400+ practices; COVID disruption in year 1; "
            "West Coast concentration"
        ),
    },
    # 120
    {
        "source_id": "seed_120",
        "source": "seed",
        "deal_name": "Privia Health Group – IPO / Goldman Sachs / Blackstone Exit",
        "year": 2021,
        "buyer": "Public Market (IPO)",
        "seller": "Goldman Sachs / Blackstone",
        "ev_mm": 3200.0,
        "ebitda_at_entry_mm": 28.0,
        "hold_years": 4.5,
        "realized_moic": 1.8,
        "realized_irr": 0.22,
        "payer_mix": {
            "medicare": 0.42, "medicaid": 0.12, "commercial": 0.46, "selfpay": 0.00
        },
        "notes": (
            "VBC-aligned physician enablement platform; NASDAQ IPO ~$28/share; "
            "Mid-Atlantic heavy; managed care capitation model"
        ),
    },
    # 121
    {
        "source_id": "seed_121",
        "source": "seed",
        "deal_name": "Agilon Health – IPO / Clayton Dubilier & Rice Exit",
        "year": 2021,
        "buyer": "Public Market (IPO)",
        "seller": "Clayton Dubilier & Rice",
        "ev_mm": 5800.0,
        "ebitda_at_entry_mm": -85.0,
        "hold_years": 3.0,
        "realized_moic": 0.7,
        "realized_irr": -0.14,
        "payer_mix": {
            "medicare": 0.95, "medicaid": 0.02, "commercial": 0.03, "selfpay": 0.00
        },
        "notes": (
            "MA capitation model; membership ramp hit MLR headwinds 2022-23; "
            "CD&R partial exit at IPO; stock declined post-lockup"
        ),
    },
    # 122
    {
        "source_id": "seed_122",
        "source": "seed",
        "deal_name": "Kindred at Home – LHC Group Acquisition (Humana Stake)",
        "year": 2021,
        "buyer": "LHC Group",
        "seller": "Humana",
        "ev_mm": 2800.0,
        "ebitda_at_entry_mm": 210.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.70, "medicaid": 0.15, "commercial": 0.15, "selfpay": 0.00
        },
        "notes": (
            "Humana divested 60% stake in Kindred at Home to LHC Group; "
            "combined entity subsequently acquired by Optum 2022"
        ),
    },
    # 123
    {
        "source_id": "seed_123",
        "source": "seed",
        "deal_name": "Cano Health – SPAC / Jaws Acquisition Corp",
        "year": 2021,
        "buyer": "Jaws Acquisition Corp (SPAC)",
        "seller": "InTandem Capital Partners",
        "ev_mm": 4400.0,
        "ebitda_at_entry_mm": -42.0,
        "hold_years": 2.5,
        "realized_moic": 0.05,
        "realized_irr": -0.7,
        "payer_mix": {
            "medicare": 0.80, "medicaid": 0.12, "commercial": 0.08, "selfpay": 0.00
        },
        "notes": (
            "FL/TX capitation concentration; Chapter 11 filed 2024; "
            "near-total equity loss; Peter Thiel-backed SPAC vehicle"
        ),
    },
    # 124
    {
        "source_id": "seed_124",
        "source": "seed",
        "deal_name": "Envision Healthcare – Post-Reorganization Creditor Entity 2023",
        "year": 2023,
        "buyer": "New Envision creditor consortium",
        "seller": "KKR (pre-bankruptcy equity)",
        "ev_mm": 1200.0,
        "ebitda_at_entry_mm": 95.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.32, "medicaid": 0.18, "commercial": 0.50, "selfpay": 0.00
        },
        "notes": (
            "Post-Ch11 reorganization; NSA arbitration removed $1B+ revenue; "
            "creditors received equity in reorganized entity"
        ),
    },
    # 125
    {
        "source_id": "seed_125",
        "source": "seed",
        "deal_name": "LifeStance Health – IPO / TPG Capital Exit",
        "year": 2021,
        "buyer": "Public Market (IPO)",
        "seller": "TPG Capital",
        "ev_mm": 6900.0,
        "ebitda_at_entry_mm": -118.0,
        "hold_years": 3.0,
        "realized_moic": 0.45,
        "realized_irr": -0.28,
        "payer_mix": {
            "medicare": 0.12, "medicaid": 0.08, "commercial": 0.80, "selfpay": 0.00
        },
        "notes": (
            "Mental health roll-up; clinician attrition and de-novo losses hurt margin; "
            "stock declined ~75% from IPO price"
        ),
    },
    # 126
    {
        "source_id": "seed_126",
        "source": "seed",
        "deal_name": "US Renal Care – DaVita Acquisition (DOJ Blocked)",
        "year": 2020,
        "buyer": "DaVita",
        "seller": "Summit Health / US Renal Care shareholders",
        "ev_mm": 2200.0,
        "ebitda_at_entry_mm": 180.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.68, "medicaid": 0.18, "commercial": 0.14, "selfpay": 0.00
        },
        "notes": (
            "DOJ blocked on antitrust grounds 2022; US Renal ultimately sold to Summit Health; "
            "dialysis market concentration concern"
        ),
    },
    # 127
    {
        "source_id": "seed_127",
        "source": "seed",
        "deal_name": "Mednax Radiology Solutions – Radiology Partners Carve-out",
        "year": 2020,
        "buyer": "Radiology Partners",
        "seller": "Mednax",
        "ev_mm": 885.0,
        "ebitda_at_entry_mm": 88.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.40, "medicaid": 0.10, "commercial": 0.50, "selfpay": 0.00
        },
        "notes": (
            "Mednax radiology division carve-out to Radiology Partners (NMC-backed); "
            "national footprint; AI-assisted reads roll-in thesis"
        ),
    },
    # 128
    {
        "source_id": "seed_128",
        "source": "seed",
        "deal_name": "Ensemble Health Partners – Golden Gate Capital Minority Recap",
        "year": 2022,
        "buyer": "Golden Gate Capital",
        "seller": "Bon Secours Mercy Health",
        "ev_mm": 3500.0,
        "ebitda_at_entry_mm": 280.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Tech-enabled RCM services; minority recap at ~12.5x EBITDA; "
            "Midwest origins; technology-first revenue cycle platform"
        ),
    },
    # 129
    {
        "source_id": "seed_129",
        "source": "seed",
        "deal_name": "Netsmart Technologies – GI Partners LBO",
        "year": 2021,
        "buyer": "GI Partners",
        "seller": "GI Partners (recapitalization)",
        "ev_mm": 1950.0,
        "ebitda_at_entry_mm": 145.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Behavioral health EHR platform; ~$80M ARR; "
            "add-on integration of CareSuite and other specialty EHRs"
        ),
    },
    # 130
    {
        "source_id": "seed_130",
        "source": "seed",
        "deal_name": "Spring Health – General Catalyst Series D Growth Round",
        "year": 2022,
        "buyer": "General Catalyst",
        "seller": "Existing shareholders",
        "ev_mm": 2000.0,
        "ebitda_at_entry_mm": -55.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.02, "medicaid": 0.05, "commercial": 0.93, "selfpay": 0.00
        },
        "notes": (
            "Digital mental health; employer-sponsored EAP model; "
            "Series D at $2B valuation; high commercial concentration"
        ),
    },
    # 131
    {
        "source_id": "seed_131",
        "source": "seed",
        "deal_name": "Prospect Medical Holdings – CA Hospitals Distressed Sale",
        "year": 2023,
        "buyer": "KPC Medical Management",
        "seller": "Leonard Green & Partners",
        "ev_mm": 150.0,
        "ebitda_at_entry_mm": -40.0,
        "hold_years": 8.0,
        "realized_moic": 0.1,
        "realized_irr": -0.25,
        "payer_mix": {
            "medicare": 0.30, "medicaid": 0.48, "commercial": 0.15, "selfpay": 0.07
        },
        "notes": (
            "Distressed CA hospital system sale; Medicaid-heavy safety net; "
            "near-total equity loss for LGP; CA AG oversight required"
        ),
    },
    # 132
    {
        "source_id": "seed_132",
        "source": "seed",
        "deal_name": "ScionHealth – LTACH Carve-out from LifePoint / Apollo",
        "year": 2021,
        "buyer": "ScionHealth (Apollo-backed)",
        "seller": "LifePoint Health",
        "ev_mm": 800.0,
        "ebitda_at_entry_mm": 72.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.72, "medicaid": 0.12, "commercial": 0.16, "selfpay": 0.00
        },
        "notes": (
            "LTACH + community hospital carve-out from LifePoint; "
            "Apollo-backed; high Medicare dependency; KY-heavy footprint"
        ),
    },
    # 133
    {
        "source_id": "seed_133",
        "source": "seed",
        "deal_name": "Paradigm Oral Surgery – Cressey & Company Platform Creation",
        "year": 2020,
        "buyer": "Cressey & Company",
        "seller": "Founding oral surgeons",
        "ev_mm": 290.0,
        "ebitda_at_entry_mm": 32.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.04, "medicaid": 0.18, "commercial": 0.65, "selfpay": 0.13
        },
        "notes": (
            "Oral surgery DSO platform; de novo + tuck-in strategy; "
            "Midwest concentration; Cressey specialty-healthcare focus"
        ),
    },
    # 134
    {
        "source_id": "seed_134",
        "source": "seed",
        "deal_name": "Ovation Healthcare – Delphi Private Equity LBO",
        "year": 2022,
        "buyer": "Delphi Private Equity",
        "seller": "Ovation management",
        "ev_mm": 520.0,
        "ebitda_at_entry_mm": 52.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.45, "medicaid": 0.30, "commercial": 0.22, "selfpay": 0.03
        },
        "notes": (
            "Rural critical access + community hospital management; "
            "340B dependency; Southeast concentration; TN-based"
        ),
    },
    # 135
    {
        "source_id": "seed_135",
        "source": "seed",
        "deal_name": "National Oncology Ventures – US Oncology / McKesson Add-on",
        "year": 2023,
        "buyer": "US Oncology / McKesson",
        "seller": "General Atlantic",
        "ev_mm": 1100.0,
        "ebitda_at_entry_mm": 98.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.55, "medicaid": 0.08, "commercial": 0.37, "selfpay": 0.00
        },
        "notes": (
            "Oncology clinic roll-up via US Oncology network; "
            "drug margin supports EBITDA; TX-heavy; McKesson strategic distribution synergy"
        ),
    },
]
