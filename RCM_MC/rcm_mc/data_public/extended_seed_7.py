"""Extended seed batch 7 — deals 156-175.

Covers 2020-2024 vintage: specialty pharmacy, post-acute care,
urgent care consolidation, musculoskeletal PT/spine, digital health
infrastructure, and cross-border strategic transactions.
"""
from __future__ import annotations

EXTENDED_SEED_DEALS_7 = [
    # 156 — Optum / Change Healthcare (blocked then unwound)
    {
        "source_id": "seed_156",
        "source": "seed",
        "deal_name": "Change Healthcare – UnitedHealth Group / Optum Acquisition",
        "year": 2022,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "Change Healthcare shareholders (public)",
        "ev_mm": 13000.0,
        "ebitda_at_entry_mm": 680.0,
        "hold_years": 1.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "DOJ challenged; cleared by courts 2022; largest healthcare IT acquisition; "
            "HCIT network integration + clearinghouse synergies; ~19x EBITDA"
        ),
    },
    # 157 — Specialty Pharma: Shields Health Solutions / WBA
    {
        "source_id": "seed_157",
        "source": "seed",
        "deal_name": "Shields Health Solutions – Walgreens Boots Alliance Majority Stake",
        "year": 2021,
        "buyer": "Walgreens Boots Alliance",
        "seller": "Summit Partners / existing investors",
        "ev_mm": 1600.0,
        "ebitda_at_entry_mm": 105.0,
        "hold_years": None,
        "realized_moic": 3.2,
        "realized_irr": 0.28,
        "payer_mix": {
            "medicare": 0.38, "medicaid": 0.22, "commercial": 0.40, "selfpay": 0.00
        },
        "notes": (
            "Specialty pharmacy embedded in health systems; WBA acquired majority stake; "
            "Summit Partners strong return at ~15x entry"
        ),
    },
    # 158 — Viant Medical / Goldman Sachs (medical devices adjacent)
    {
        "source_id": "seed_158",
        "source": "seed",
        "deal_name": "Synchrony Health Services – Kindred + Genesis Post-Acute",
        "year": 2021,
        "buyer": "Synchrony Health management",
        "seller": "Kindred Healthcare / Genesis Healthcare",
        "ev_mm": 280.0,
        "ebitda_at_entry_mm": 24.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.65, "medicaid": 0.25, "commercial": 0.10, "selfpay": 0.00
        },
        "notes": (
            "Pharmacy + rehab carve-out from Kindred/Genesis; post-acute ancillary services; "
            "SNF-adjacent model"
        ),
    },
    # 159 — Tivity Health / Foley (digital fitness for seniors)
    {
        "source_id": "seed_159",
        "source": "seed",
        "deal_name": "Tivity Health – Foley & Lardner / Spire Capital LBO",
        "year": 2020,
        "buyer": "Spire Capital Partners",
        "seller": "Tivity Health shareholders (public)",
        "ev_mm": 660.0,
        "ebitda_at_entry_mm": 85.0,
        "hold_years": 3.0,
        "realized_moic": 2.3,
        "realized_irr": 0.19,
        "payer_mix": {
            "medicare": 0.82, "medicaid": 0.05, "commercial": 0.13, "selfpay": 0.00
        },
        "notes": (
            "SilverSneakers MA fitness benefit; take-private from Nasdaq; "
            "COVID disrupted gym utilization 2020; recovered via digital engagement"
        ),
    },
    # 160 — Surgical Care Affiliates / United Surgical (SCA Health / Bain)
    {
        "source_id": "seed_160",
        "source": "seed",
        "deal_name": "SCA Health – Bain Capital Secondary LBO",
        "year": 2022,
        "buyer": "Bain Capital",
        "seller": "UnitedHealth Group / Optum",
        "ev_mm": 3900.0,
        "ebitda_at_entry_mm": 340.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.20, "medicaid": 0.04, "commercial": 0.76, "selfpay": 0.00
        },
        "notes": (
            "Second LBO of SCA; Optum divested to Bain under antitrust pressure; "
            "~11.5x EBITDA; commercial-heavy ASC operator"
        ),
    },
    # 161 — Rural Health Group / New Bern Healthcare
    {
        "source_id": "seed_161",
        "source": "seed",
        "deal_name": "Lifepoint Health – Kindred Rehab Add-on Portfolio",
        "year": 2022,
        "buyer": "LifePoint Health / Apollo",
        "seller": "Kindred Healthcare",
        "ev_mm": 700.0,
        "ebitda_at_entry_mm": 62.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.72, "medicaid": 0.10, "commercial": 0.18, "selfpay": 0.00
        },
        "notes": (
            "IRF + LTACH portfolio add-on; LifePoint / Apollo post-acute strategy; "
            "high Medicare IRF dependency; SE geographic concentration"
        ),
    },
    # 162 — ATI Physical Therapy / HALO / Advent International
    {
        "source_id": "seed_162",
        "source": "seed",
        "deal_name": "ATI Physical Therapy – Advent International SPAC / Viant",
        "year": 2021,
        "buyer": "Public Market (SPAC) / Advent International",
        "seller": "Advent International (partial)",
        "ev_mm": 2550.0,
        "ebitda_at_entry_mm": 95.0,
        "hold_years": 2.0,
        "realized_moic": 0.3,
        "realized_irr": -0.38,
        "payer_mix": {
            "medicare": 0.20, "medicaid": 0.06, "commercial": 0.72, "selfpay": 0.02
        },
        "notes": (
            "PT SPAC merger with Halo SPAC; de-novo growth burn exceeded commercial "
            "margin recovery; stock declined >90% post-SPAC; near-total equity loss"
        ),
    },
    # 163 — DaVita / Paladina Health (primary care JV)
    {
        "source_id": "seed_163",
        "source": "seed",
        "deal_name": "Paladina Health – DaVita Primary Care Spin / Village MD",
        "year": 2020,
        "buyer": "Various (management buyout)",
        "seller": "DaVita",
        "ev_mm": 350.0,
        "ebitda_at_entry_mm": -15.0,
        "hold_years": 3.0,
        "realized_moic": 1.8,
        "realized_irr": 0.20,
        "payer_mix": {
            "medicare": 0.30, "medicaid": 0.10, "commercial": 0.60, "selfpay": 0.00
        },
        "notes": (
            "DaVita divested primary care division; VBC primary care subscription model; "
            "employer-sponsored market focus"
        ),
    },
    # 164 — Astrana Health (formerly ApolloMed) / Prospect acquisition
    {
        "source_id": "seed_164",
        "source": "seed",
        "deal_name": "Astrana Health – VBC Platform Expansion 2022",
        "year": 2022,
        "buyer": "Astrana Health (public)",
        "seller": "Various physician groups",
        "ev_mm": 830.0,
        "ebitda_at_entry_mm": 70.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.55, "medicaid": 0.25, "commercial": 0.20, "selfpay": 0.00
        },
        "notes": (
            "Capitation-based VBC platform; CA-heavy; "
            "dual-eligible + MA managed care concentration"
        ),
    },
    # 165 — Caliber Imaging / KKR (pathology)
    {
        "source_id": "seed_165",
        "source": "seed",
        "deal_name": "Pathgroup – Genoptix / Sonic Healthcare Pathology Add-on",
        "year": 2021,
        "buyer": "Sonic Healthcare",
        "seller": "Various pathology practices",
        "ev_mm": 340.0,
        "ebitda_at_entry_mm": 38.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.45, "medicaid": 0.10, "commercial": 0.45, "selfpay": 0.00
        },
        "notes": (
            "Pathology practice roll-up; Sonic Healthcare US expansion; "
            "anatomic pathology + clinical lab consolidation"
        ),
    },
    # 166 — GreenShield / Abri Health
    {
        "source_id": "seed_166",
        "source": "seed",
        "deal_name": "National Spine & Pain Centers – Sentinel Capital Platform",
        "year": 2021,
        "buyer": "Sentinel Capital Partners",
        "seller": "NSPC management",
        "ev_mm": 480.0,
        "ebitda_at_entry_mm": 50.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.35, "medicaid": 0.08, "commercial": 0.55, "selfpay": 0.02
        },
        "notes": (
            "Interventional pain + spine platform; Sentinel Capital; "
            "commercial concentration; 100+ clinic footprint"
        ),
    },
    # 167 — Steward Health Texas hospitals / Wadley Regional
    {
        "source_id": "seed_167",
        "source": "seed",
        "deal_name": "Steward Health Care – Texas Hospital Portfolio Sale",
        "year": 2024,
        "buyer": "Various (Stewardship Health / STHS)",
        "seller": "Steward Health Care (bankruptcy)",
        "ev_mm": 400.0,
        "ebitda_at_entry_mm": -60.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.32, "medicaid": 0.40, "commercial": 0.22, "selfpay": 0.06
        },
        "notes": (
            "Bankruptcy §363 sale of TX hospitals; distressed; high Medicaid; "
            "Leonard Green & Partners total loss; buyer assumes pension liabilities"
        ),
    },
    # 168 — Wellbe Senior Medical (Landmark Health)
    {
        "source_id": "seed_168",
        "source": "seed",
        "deal_name": "Landmark Health – UnitedHealth Group Acquisition",
        "year": 2021,
        "buyer": "UnitedHealth Group",
        "seller": "Landmark Health / WCAS",
        "ev_mm": 2500.0,
        "ebitda_at_entry_mm": 140.0,
        "hold_years": 5.0,
        "realized_moic": 3.5,
        "realized_irr": 0.29,
        "payer_mix": {
            "medicare": 0.88, "medicaid": 0.08, "commercial": 0.04, "selfpay": 0.00
        },
        "notes": (
            "Home-based primary care for complex elderly; Optum-acquired; "
            "WCAS strong return on MA capitation thesis; ~17.9x EBITDA"
        ),
    },
    # 169 — Global Medical Response / AMR
    {
        "source_id": "seed_169",
        "source": "seed",
        "deal_name": "Global Medical Response – KKR / Ardian Acquisition",
        "year": 2021,
        "buyer": "KKR / Ardian",
        "seller": "American Securities",
        "ev_mm": 6500.0,
        "ebitda_at_entry_mm": 580.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.35, "medicaid": 0.25, "commercial": 0.30, "selfpay": 0.10
        },
        "notes": (
            "Air + ground ambulance; KKR / Ardian $6.5B deal; NSA balance billing reform risk; "
            "~11.2x EBITDA; largest air medical transport operator"
        ),
    },
    # 170 — Sound Physicians / TPG
    {
        "source_id": "seed_170",
        "source": "seed",
        "deal_name": "Sound Physicians – TPG Capital Secondary Investment",
        "year": 2021,
        "buyer": "TPG Capital",
        "seller": "Optum / prior investors",
        "ev_mm": 2300.0,
        "ebitda_at_entry_mm": 165.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.38, "medicaid": 0.18, "commercial": 0.44, "selfpay": 0.00
        },
        "notes": (
            "Hospitalist / intensivist / nocturnist staffing platform; "
            "TPG secondary investment; NSA exposure on commercial splits"
        ),
    },
    # 171 — Bright Health / Alignment / carrier
    {
        "source_id": "seed_171",
        "source": "seed",
        "deal_name": "Bright Health Group – IPO / New Enterprise Associates Exit",
        "year": 2021,
        "buyer": "Public Market (IPO)",
        "seller": "New Enterprise Associates / existing investors",
        "ev_mm": 11000.0,
        "ebitda_at_entry_mm": -250.0,
        "hold_years": 2.0,
        "realized_moic": 0.02,
        "realized_irr": -0.86,
        "payer_mix": {
            "medicare": 0.70, "medicaid": 0.10, "commercial": 0.20, "selfpay": 0.00
        },
        "notes": (
            "MA carrier IPO; multi-state expansion imploded on MLR losses; "
            "exited individual markets; stock declined >95%; near-total loss"
        ),
    },
    # 172 — Encompass Health / Enhabit spinoff
    {
        "source_id": "seed_172",
        "source": "seed",
        "deal_name": "Enhabit Home Health & Hospice – Encompass Health Spin-off",
        "year": 2022,
        "buyer": "Public Market (spin-off)",
        "seller": "Encompass Health",
        "ev_mm": 1800.0,
        "ebitda_at_entry_mm": 120.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.75, "medicaid": 0.12, "commercial": 0.13, "selfpay": 0.00
        },
        "notes": (
            "Encompass spun home health & hospice segment; standalone public company; "
            "PDGM rate pressure pressured post-spin valuation"
        ),
    },
    # 173 — Fresenius Medical Care / NephroCare North America
    {
        "source_id": "seed_173",
        "source": "seed",
        "deal_name": "Fresenius Medical Care – NephroCare Dialysis Add-ons",
        "year": 2020,
        "buyer": "Fresenius Medical Care",
        "seller": "Independent dialysis operators",
        "ev_mm": 950.0,
        "ebitda_at_entry_mm": 88.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.72, "medicaid": 0.16, "commercial": 0.12, "selfpay": 0.00
        },
        "notes": (
            "Fresenius strategic consolidation of independent dialysis centers; "
            "ESRD payment reform headwinds; duopoly market dynamics"
        ),
    },
    # 174 — Array Behavioral Care / Genoa Healthcare (telepsych)
    {
        "source_id": "seed_174",
        "source": "seed",
        "deal_name": "Array Behavioral Care – Telepsychiatry Platform Growth",
        "year": 2021,
        "buyer": "Warburg Pincus",
        "seller": "Previous investors",
        "ev_mm": 380.0,
        "ebitda_at_entry_mm": 35.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.25, "medicaid": 0.45, "commercial": 0.30, "selfpay": 0.00
        },
        "notes": (
            "Telepsychiatry platform; hospital + ED contract model; "
            "Warburg Pincus; high Medicaid exposure via state behavioral health contracts"
        ),
    },
    # 175 — Acuitas Medical / Surgical Notes acquisition
    {
        "source_id": "seed_175",
        "source": "seed",
        "deal_name": "Surgical Notes – ASC Revenue Cycle SaaS Platform",
        "year": 2022,
        "buyer": "GTCR",
        "seller": "Surgical Notes management",
        "ev_mm": 290.0,
        "ebitda_at_entry_mm": 28.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "ASC-specific revenue cycle software; GTCR healthcare IT strategy; "
            "SaaS ARR base; add-on to broader RCM platform thesis"
        ),
    },
]
