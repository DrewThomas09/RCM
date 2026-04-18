"""Extended seed batch 8 — deals 176-195.

Covers 2020-2024 vintage: SNF/LTACH/IRF post-acute consolidation,
women's health, addiction treatment, veterinary (comp for sizing),
oncology, and notable PE-to-PE secondary transactions.
"""
from __future__ import annotations

EXTENDED_SEED_DEALS_8 = [
    # 176 — Diversicare Healthcare / Prescient Health
    {
        "source_id": "seed_176",
        "source": "seed",
        "deal_name": "Diversicare Healthcare – PE Recapitalization",
        "year": 2022,
        "buyer": "Diversicare management / LP investors",
        "seller": "Public shareholders",
        "ev_mm": 320.0,
        "ebitda_at_entry_mm": 35.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.30, "medicaid": 0.55, "commercial": 0.12, "selfpay": 0.03
        },
        "notes": (
            "SNF operator take-private; high Medicaid concentration; "
            "staffing cost inflation and minimum wage risk; Southeast-heavy"
        ),
    },
    # 177 — Evolent Health / NIA (National Imaging Associates)
    {
        "source_id": "seed_177",
        "source": "seed",
        "deal_name": "Evolent Health – National Imaging Associates Acquisition",
        "year": 2023,
        "buyer": "Evolent Health",
        "seller": "Magellan Health / Centene",
        "ev_mm": 975.0,
        "ebitda_at_entry_mm": 68.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Specialty care management + imaging prior auth; Evolent strategic; "
            "utilization management platform expansion; ~14x EBITDA"
        ),
    },
    # 178 — InfuSystem / GTCR secondary
    {
        "source_id": "seed_178",
        "source": "seed",
        "deal_name": "InfuSystem – GTCR Secondary Buyout",
        "year": 2021,
        "buyer": "GTCR",
        "seller": "Bain Capital Double Impact",
        "ev_mm": 600.0,
        "ebitda_at_entry_mm": 52.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.30, "medicaid": 0.10, "commercial": 0.60, "selfpay": 0.00
        },
        "notes": (
            "Ambulatory infusion services; GTCR secondary buyout; "
            "chemotherapy + pain management infusion; commercial-heavy"
        ),
    },
    # 179 — Hazel Health / Equity Community Care
    {
        "source_id": "seed_179",
        "source": "seed",
        "deal_name": "Hazel Health – School-Based Health Platform Growth",
        "year": 2022,
        "buyer": "Owl Ventures",
        "seller": "Existing investors",
        "ev_mm": 500.0,
        "ebitda_at_entry_mm": -8.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.00, "medicaid": 0.60, "commercial": 0.35, "selfpay": 0.05
        },
        "notes": (
            "School-based telehealth; Medicaid-funded student health services; "
            "Owl Ventures Series C; 28-state expansion"
        ),
    },
    # 180 — Amedisys / UnitedHealth Group merger
    {
        "source_id": "seed_180",
        "source": "seed",
        "deal_name": "Amedisys – UnitedHealth Group / Optum Acquisition",
        "year": 2023,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "Amedisys shareholders (public)",
        "ev_mm": 3300.0,
        "ebitda_at_entry_mm": 168.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.78, "medicaid": 0.12, "commercial": 0.10, "selfpay": 0.00
        },
        "notes": (
            "Largest home health acquisition; DOJ challenged + cleared; "
            "~19.6x EBITDA; Optum home-based care strategy anchor"
        ),
    },
    # 181 — Behavioral Health Group / Webster Equity
    {
        "source_id": "seed_181",
        "source": "seed",
        "deal_name": "Behavioral Health Group – Webster Equity Platform LBO",
        "year": 2020,
        "buyer": "Webster Equity Partners",
        "seller": "BHG management",
        "ev_mm": 400.0,
        "ebitda_at_entry_mm": 45.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.10, "medicaid": 0.55, "commercial": 0.30, "selfpay": 0.05
        },
        "notes": (
            "Opioid addiction treatment (OTP) platform; Medicaid-heavy; "
            "SAMHSA compliance requirements; Webster Equity specialty behavior focus"
        ),
    },
    # 182 — CenterWell Senior Primary Care (Humana)
    {
        "source_id": "seed_182",
        "source": "seed",
        "deal_name": "CenterWell Senior Primary Care – Humana Internal Build",
        "year": 2021,
        "buyer": "Humana (internal)",
        "seller": "Various acquired practices",
        "ev_mm": 1800.0,
        "ebitda_at_entry_mm": -75.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.90, "medicaid": 0.05, "commercial": 0.05, "selfpay": 0.00
        },
        "notes": (
            "Humana de-novo + acquired MA-centric primary care network; "
            "capitation model; investment in member health outcomes"
        ),
    },
    # 183 — GI Alliance / Ares Management
    {
        "source_id": "seed_183",
        "source": "seed",
        "deal_name": "GI Alliance – Ares Management / HGGC Acquisition",
        "year": 2021,
        "buyer": "Ares Management / HGGC",
        "seller": "HarbourVest Partners",
        "ev_mm": 2800.0,
        "ebitda_at_entry_mm": 220.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.32, "medicaid": 0.05, "commercial": 0.63, "selfpay": 0.00
        },
        "notes": (
            "GI physician practice management; ~12.7x EBITDA; "
            "commercial-heavy; colonoscopy + IBD procedure volume"
        ),
    },
    # 184 — Prognocis / Bizmatics (health IT EHR)
    {
        "source_id": "seed_184",
        "source": "seed",
        "deal_name": "WRS Health / Bizmatics – Ambulatory EHR Roll-up",
        "year": 2022,
        "buyer": "Thoma Bravo",
        "seller": "Bizmatics management",
        "ev_mm": 380.0,
        "ebitda_at_entry_mm": 38.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Ambulatory EHR platform roll-up; Thoma Bravo healthcare IT thesis; "
            "SaaS ARR base; specialty-specific workflow differentiation"
        ),
    },
    # 185 — VillageMD / Walgreens
    {
        "source_id": "seed_185",
        "source": "seed",
        "deal_name": "VillageMD – Walgreens Boots Alliance Majority Stake",
        "year": 2021,
        "buyer": "Walgreens Boots Alliance",
        "seller": "Village Practice Management (existing investors)",
        "ev_mm": 5200.0,
        "ebitda_at_entry_mm": -120.0,
        "hold_years": 3.0,
        "realized_moic": 0.3,
        "realized_irr": -0.37,
        "payer_mix": {
            "medicare": 0.28, "medicaid": 0.15, "commercial": 0.57, "selfpay": 0.00
        },
        "notes": (
            "Clinic-in-pharmacy model; Walgreens majority stake at $5.2B; "
            "unit economics failed at scale; WBA divested 2024 at steep loss"
        ),
    },
    # 186 — Maven Clinic / General Atlantic
    {
        "source_id": "seed_186",
        "source": "seed",
        "deal_name": "Maven Clinic – Women's Health Platform Series E",
        "year": 2022,
        "buyer": "General Atlantic",
        "seller": "Existing investors",
        "ev_mm": 1000.0,
        "ebitda_at_entry_mm": -20.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.02, "medicaid": 0.10, "commercial": 0.88, "selfpay": 0.00
        },
        "notes": (
            "Digital women's health; maternity + fertility benefits platform; "
            "employer-sponsored; General Atlantic Series E at $1B valuation"
        ),
    },
    # 187 — Signify Health realized exit (New Mountain Capital, via CVS/Aetna acquisition)
    # Phase 6 Bug #1 fix: buyer was "CVS Health / Aetna" (the
    # strategic acquirer). The realized_moic 4.5 / realized_irr 0.46
    # belong to New Mountain Capital (the exiting PE sponsor,
    # explicitly named in the seller field). Sponsor-ledger
    # attribution moves to NMC; CVS context preserved in notes.
    {
        "source_id": "seed_187",
        "source": "seed",
        "deal_name": "Signify Health – CVS Health / Aetna Acquisition",
        "year": 2023,
        "buyer": "New Mountain Capital",
        "seller": "New Mountain Capital / public shareholders",
        "ev_mm": 8000.0,
        "ebitda_at_entry_mm": 180.0,
        "hold_years": 4.0,
        "realized_moic": 4.5,
        "realized_irr": 0.46,
        "payer_mix": {
            "medicare": 0.85, "medicaid": 0.08, "commercial": 0.07, "selfpay": 0.00
        },
        "notes": (
            "Home-based assessments + provider enablement; "
            "CVS Health / Aetna was the strategic acquirer at $8B; "
            "New Mountain Capital is the exiting PE sponsor realizing "
            "this MOIC/IRR. ACKO/SDOH integration thesis; "
            "~44x EBITDA premium."
        ),
    },
    # 188 — Tenet Healthcare / USPI secondary
    {
        "source_id": "seed_188",
        "source": "seed",
        "deal_name": "Tenet Healthcare – USPI Control Stake Acquisition",
        "year": 2021,
        "buyer": "Tenet Healthcare",
        "seller": "Welsh Carson / USPI minority shareholders",
        "ev_mm": 1800.0,
        "ebitda_at_entry_mm": 200.0,
        "hold_years": 5.0,
        "realized_moic": 2.2,
        "realized_irr": 0.17,
        "payer_mix": {
            "medicare": 0.22, "medicaid": 0.06, "commercial": 0.72, "selfpay": 0.00
        },
        "notes": (
            "Tenet acquired remaining USPI minority; ~9x EBITDA; "
            "commercial ASC concentration; Welsh Carson realized strong return"
        ),
    },
    # 189 — Nexus Health / Kelso (IRF)
    {
        "source_id": "seed_189",
        "source": "seed",
        "deal_name": "Nexus Health Systems – Kelso & Company IRF Platform",
        "year": 2021,
        "buyer": "Kelso & Company",
        "seller": "Nexus management",
        "ev_mm": 540.0,
        "ebitda_at_entry_mm": 55.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.70, "medicaid": 0.10, "commercial": 0.20, "selfpay": 0.00
        },
        "notes": (
            "Inpatient rehabilitation + LTACH platform; Kelso; "
            "Medicare IRF classification compliance risk; national expansion"
        ),
    },
    # 190 — 1Life Healthcare / Amazon (One Medical)
    {
        "source_id": "seed_190",
        "source": "seed",
        "deal_name": "One Medical (1Life Healthcare) – Amazon Acquisition",
        "year": 2023,
        "buyer": "Amazon",
        "seller": "1Life Healthcare shareholders (public)",
        "ev_mm": 3900.0,
        "ebitda_at_entry_mm": -110.0,
        "hold_years": 3.0,
        "realized_moic": 1.5,
        "realized_irr": 0.15,
        "payer_mix": {
            "medicare": 0.10, "medicaid": 0.05, "commercial": 0.85, "selfpay": 0.00
        },
        "notes": (
            "Membership-based primary care; Amazon acquisition; "
            "employer benefit + Prime integration; loss-making at acquisition"
        ),
    },
    # 191 — Solstice Health / Nuance (AI/clinical documentation)
    {
        "source_id": "seed_191",
        "source": "seed",
        "deal_name": "Nuance Communications – Microsoft Acquisition",
        "year": 2022,
        "buyer": "Microsoft",
        "seller": "Nuance shareholders (public)",
        "ev_mm": 19700.0,
        "ebitda_at_entry_mm": 310.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "AI clinical documentation / Dragon Medical; Microsoft $19.7B deal; "
            "healthcare AI + ambient voice documentation thesis; ~63x EBITDA"
        ),
    },
    # 192 — CareDx / transplant management
    {
        "source_id": "seed_192",
        "source": "seed",
        "deal_name": "Cotiviti – Veritas Capital Secondary LBO",
        "year": 2022,
        "buyer": "Veritas Capital",
        "seller": "Veritas (recap)",
        "ev_mm": 15000.0,
        "ebitda_at_entry_mm": 1100.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Payer analytics + risk adjustment platform; Veritas $15B recapitalization; "
            "~13.6x EBITDA; government + commercial payer client base"
        ),
    },
    # 193 — Carrum Health / episode-based surgery
    {
        "source_id": "seed_193",
        "source": "seed",
        "deal_name": "Carrum Health – Episode-Based Surgery Platform",
        "year": 2022,
        "buyer": "Health Assurance Acquisition / health system partners",
        "seller": "Carrum founders",
        "ev_mm": 220.0,
        "ebitda_at_entry_mm": -5.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.08, "medicaid": 0.02, "commercial": 0.90, "selfpay": 0.00
        },
        "notes": (
            "Value-based surgery benefit management; bundled payment model; "
            "employer-sponsored; commercial-only concentration"
        ),
    },
    # 194 — National Mentor / Centerstone
    {
        "source_id": "seed_194",
        "source": "seed",
        "deal_name": "ResCare / BrightSpring Health Services – KKR IPO",
        "year": 2024,
        "buyer": "Public Market (IPO)",
        "seller": "KKR",
        "ev_mm": 2800.0,
        "ebitda_at_entry_mm": 260.0,
        "hold_years": 6.0,
        "realized_moic": 1.4,
        "realized_irr": 0.06,
        "payer_mix": {
            "medicare": 0.25, "medicaid": 0.60, "commercial": 0.15, "selfpay": 0.00
        },
        "notes": (
            "Home + community-based services; KKR IPO at ~10.8x; "
            "high Medicaid; Medicaid rate reform and minimum wage exposure"
        ),
    },
    # 195 — Pearl Health / Andreessen
    {
        "source_id": "seed_195",
        "source": "seed",
        "deal_name": "Pearl Health – Primary Care ACO-REACH Platform",
        "year": 2022,
        "buyer": "a16z / General Catalyst",
        "seller": "Existing investors",
        "ev_mm": 380.0,
        "ebitda_at_entry_mm": -12.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.95, "medicaid": 0.03, "commercial": 0.02, "selfpay": 0.00
        },
        "notes": (
            "ACO REACH primary care enablement; a16z / GC investment; "
            "Medicare FFS to value conversion model; risk adjustment dependency"
        ),
    },
]
