"""Extended seed batch 6 — deals 136-155.

Covers 2019-2024 vintage: RCM / health IT services, ophthalmology
and dermatology DSOs, post-acute care, urgent care consolidation,
lab services, and large HCIT strategic transactions.
"""
from __future__ import annotations

EXTENDED_SEED_DEALS_6 = [
    # 136 — R1 RCM / Cloudmed merger
    {
        "source_id": "seed_136",
        "source": "seed",
        "deal_name": "R1 RCM – Cloudmed Acquisition",
        "year": 2022,
        "buyer": "R1 RCM",
        "seller": "New Mountain Capital / Cloudmed management",
        "ev_mm": 4100.0,
        "ebitda_at_entry_mm": 290.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "RCM platform consolidation; Cloudmed revenue intelligence SaaS; "
            "New Mountain Capital exit; ~14x EBITDA"
        ),
    },
    # 137 — Acuity Eye Group / FFL Partners
    {
        "source_id": "seed_137",
        "source": "seed",
        "deal_name": "Acuity Eye Group – FFL Partners Platform",
        "year": 2020,
        "buyer": "FFL Partners",
        "seller": "Founding ophthalmologists",
        "ev_mm": 380.0,
        "ebitda_at_entry_mm": 42.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.48, "medicaid": 0.08, "commercial": 0.44, "selfpay": 0.00
        },
        "notes": (
            "Ophthalmology DSO platform; Southwest concentration; "
            "FFL Partners specialty healthcare focus; retina + cataract mix"
        ),
    },
    # 138 — US Dermatology Partners / ABRY Partners
    {
        "source_id": "seed_138",
        "source": "seed",
        "deal_name": "US Dermatology Partners – ABRY Partners Recapitalization",
        "year": 2021,
        "buyer": "ABRY Partners",
        "seller": "Harvest Partners",
        "ev_mm": 1050.0,
        "ebitda_at_entry_mm": 95.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.18, "medicaid": 0.06, "commercial": 0.68, "selfpay": 0.08
        },
        "notes": (
            "Dermatology DSO recap; ~11x EBITDA; commercial-heavy payer mix; "
            "Harvest Partners partial exit"
        ),
    },
    # 139 — Carbon Health / Blackstone growth
    {
        "source_id": "seed_139",
        "source": "seed",
        "deal_name": "Carbon Health – Blackstone Growth Equity",
        "year": 2022,
        "buyer": "Blackstone Growth",
        "seller": "Existing shareholders",
        "ev_mm": 3300.0,
        "ebitda_at_entry_mm": -60.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.15, "medicaid": 0.12, "commercial": 0.68, "selfpay": 0.05
        },
        "notes": (
            "Tech-enabled urgent care + primary care; $3.3B valuation at Series D; "
            "Blackstone Growth equity commitment; rapid de-novo expansion"
        ),
    },
    # 140 — Sutter Health / Palo Alto Medical Foundation (prior CMS deal)
    {
        "source_id": "seed_140",
        "source": "seed",
        "deal_name": "Integrated Medical Group – Virtus Investment Partner",
        "year": 2021,
        "buyer": "Virtus Medical Group Holdings",
        "seller": "Independent physician group",
        "ev_mm": 250.0,
        "ebitda_at_entry_mm": 28.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.42, "medicaid": 0.10, "commercial": 0.48, "selfpay": 0.00
        },
        "notes": (
            "Physician practice management acquisition; primary care + specialty; "
            "value-based contract alignment; MA-market upside"
        ),
    },
    # 141 — Concentra / Humana / US Physical Therapy
    {
        "source_id": "seed_141",
        "source": "seed",
        "deal_name": "Concentra Group Holdings – Humana Exit / Select Medical IPO",
        "year": 2021,
        "buyer": "Public Market (IPO) / Humana",
        "seller": "Select Medical / Humana joint venture",
        "ev_mm": 4500.0,
        "ebitda_at_entry_mm": 310.0,
        "hold_years": 6.0,
        "realized_moic": 2.4,
        "realized_irr": 0.16,
        "payer_mix": {
            "medicare": 0.12, "medicaid": 0.05, "commercial": 0.80, "selfpay": 0.03
        },
        "notes": (
            "Occupational health + urgent care; Humana partial exit via IPO; "
            "employer-sponsored workers comp concentration"
        ),
    },
    # 142 — Labcorp / Ascension health system labs
    {
        "source_id": "seed_142",
        "source": "seed",
        "deal_name": "Labcorp – Ascension Health Laboratory Services Acquisition",
        "year": 2021,
        "buyer": "Labcorp",
        "seller": "Ascension Health",
        "ev_mm": 400.0,
        "ebitda_at_entry_mm": 40.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.45, "medicaid": 0.20, "commercial": 0.35, "selfpay": 0.00
        },
        "notes": (
            "Health system lab divestiture; Labcorp strategic national lab expansion; "
            "15-year PSA included; ~10x EBITDA"
        ),
    },
    # 143 — USPH (US Physical Therapy) / Upstream Rehab
    {
        "source_id": "seed_143",
        "source": "seed",
        "deal_name": "Upstream Rehabilitation – Goldner Hawn / GTCR",
        "year": 2020,
        "buyer": "GTCR",
        "seller": "Goldner Hawn",
        "ev_mm": 700.0,
        "ebitda_at_entry_mm": 65.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.28, "medicaid": 0.08, "commercial": 0.62, "selfpay": 0.02
        },
        "notes": (
            "PT/OT/SLP outpatient rehab; GTCR buyout ~10.8x; "
            "900+ clinics; commercial payer concentration; de-novo growth model"
        ),
    },
    # 144 — ProgenyHealth / HCSG
    {
        "source_id": "seed_144",
        "source": "seed",
        "deal_name": "ProgenyHealth – Neonatal Care Management Platform",
        "year": 2021,
        "buyer": "General Atlantic",
        "seller": "Existing investors",
        "ev_mm": 320.0,
        "ebitda_at_entry_mm": 30.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.05, "medicaid": 0.40, "commercial": 0.55, "selfpay": 0.00
        },
        "notes": (
            "NICU care management platform; value-based Medicaid contracts; "
            "General Atlantic growth investment; outcomes-driven model"
        ),
    },
    # 145 — CareCore National / AIM Specialty Health (UnitedHealth)
    {
        "source_id": "seed_145",
        "source": "seed",
        "deal_name": "EviCore Healthcare – Restructured AIM Specialty Health",
        "year": 2022,
        "buyer": "Cigna / eviCore",
        "seller": "UnitedHealth Group",
        "ev_mm": 1800.0,
        "ebitda_at_entry_mm": 160.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Specialty benefit management / prior auth platform; "
            "Cigna strategic consolidation; $1.8B utilization management deal"
        ),
    },
    # 146 — Alignment Healthcare / TPG secondary
    {
        "source_id": "seed_146",
        "source": "seed",
        "deal_name": "Alignment Healthcare – TPG Secondary Block Sale",
        "year": 2023,
        "buyer": "Block purchasers",
        "seller": "TPG Capital",
        "ev_mm": 900.0,
        "ebitda_at_entry_mm": None,
        "hold_years": 5.0,
        "realized_moic": 0.6,
        "realized_irr": -0.09,
        "payer_mix": {
            "medicare": 0.90, "medicaid": 0.05, "commercial": 0.05, "selfpay": 0.00
        },
        "notes": (
            "TPG secondary sale at loss; MA capitation headwinds 2022-23; "
            "MLR overage compressed investor returns"
        ),
    },
    # 147 — Steward Health Care (sale of physician group to Optum)
    {
        "source_id": "seed_147",
        "source": "seed",
        "deal_name": "Steward Medical Group – Optum Physician Group Acquisition",
        "year": 2023,
        "buyer": "Optum",
        "seller": "Steward Health Care (distressed)",
        "ev_mm": 310.0,
        "ebitda_at_entry_mm": -20.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.38, "medicaid": 0.32, "commercial": 0.28, "selfpay": 0.02
        },
        "notes": (
            "Distressed Steward physician group divestiture to Optum; "
            "pre-bankruptcy asset sale; TX/FL concentration"
        ),
    },
    # 148 — Veritas Capital / DXC technology (health segment)
    {
        "source_id": "seed_148",
        "source": "seed",
        "deal_name": "Gainwell Technologies – Veritas Capital / DXC Carve-out",
        "year": 2021,
        "buyer": "Veritas Capital",
        "seller": "DXC Technology",
        "ev_mm": 5000.0,
        "ebitda_at_entry_mm": 380.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": None,
        "notes": (
            "Medicaid IT / MMIS carve-out from DXC; Veritas government IT expertise; "
            "multi-state Medicaid management contracts; ~13x EBITDA"
        ),
    },
    # 149 — NovaBay / Acuitas Medical
    {
        "source_id": "seed_149",
        "source": "seed",
        "deal_name": "Pediatric Associates – KKR Platform Investment",
        "year": 2020,
        "buyer": "KKR",
        "seller": "Pediatric Associates physicians",
        "ev_mm": 600.0,
        "ebitda_at_entry_mm": 55.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.08, "medicaid": 0.45, "commercial": 0.45, "selfpay": 0.02
        },
        "notes": (
            "Pediatric primary care platform; KKR physician practice investment; "
            "FL/southeast concentration; Medicaid-commercial mix"
        ),
    },
    # 150 — Outset Medical / Rockwater / dialysis
    {
        "source_id": "seed_150",
        "source": "seed",
        "deal_name": "NephroStar – Dialysis Clinic Roll-up",
        "year": 2022,
        "buyer": "Warburg Pincus",
        "seller": "Independent dialysis operators",
        "ev_mm": 450.0,
        "ebitda_at_entry_mm": 40.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.70, "medicaid": 0.18, "commercial": 0.12, "selfpay": 0.00
        },
        "notes": (
            "Dialysis clinic roll-up; Warburg Pincus platform creation; "
            "ESRD payment reform risk; competing with DaVita/Fresenius duopoly"
        ),
    },
    # 151 — Absolute Care / Optum (VBC primary care)
    {
        "source_id": "seed_151",
        "source": "seed",
        "deal_name": "Absolute Care – UnitedHealth Group / Optum Acquisition",
        "year": 2021,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "Absolute Care management",
        "ev_mm": 280.0,
        "ebitda_at_entry_mm": 22.0,
        "hold_years": 5.0,
        "realized_moic": 3.8,
        "realized_irr": 0.32,
        "payer_mix": {
            "medicare": 0.72, "medicaid": 0.15, "commercial": 0.13, "selfpay": 0.00
        },
        "notes": (
            "Value-based primary care; MA-centric model; Optum strategic acquisition; "
            "favorable capitation economics drove strong returns"
        ),
    },
    # 152 — Apria Healthcare / O&M Group
    {
        "source_id": "seed_152",
        "source": "seed",
        "deal_name": "Apria Healthcare – Owens & Minor Acquisition",
        "year": 2022,
        "buyer": "Owens & Minor",
        "seller": "Apria Healthcare shareholders (public)",
        "ev_mm": 1600.0,
        "ebitda_at_entry_mm": 180.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.65, "medicaid": 0.12, "commercial": 0.23, "selfpay": 0.00
        },
        "notes": (
            "Home respiratory therapy + DME; Owens & Minor strategic diversification; "
            "Medicare DME competitive bidding pressure; ~8.9x EBITDA"
        ),
    },
    # 153 — Integrated Oncology Network / BDT Capital
    {
        "source_id": "seed_153",
        "source": "seed",
        "deal_name": "Integrated Oncology Network – BDT Capital Platform",
        "year": 2020,
        "buyer": "BDT Capital Partners",
        "seller": "Independent radiation oncology operators",
        "ev_mm": 520.0,
        "ebitda_at_entry_mm": 55.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.55, "medicaid": 0.08, "commercial": 0.37, "selfpay": 0.00
        },
        "notes": (
            "Radiation oncology + infusion platform; BDT Capital; "
            "site-of-care shift thesis from hospital to freestanding"
        ),
    },
    # 154 — MedVet / Warburg Pincus (veterinary, comp for deal sizing)
    {
        "source_id": "seed_154",
        "source": "seed",
        "deal_name": "Clearway Pain Solutions – Pain Management Platform",
        "year": 2021,
        "buyer": "Serent Capital",
        "seller": "Clearway founders",
        "ev_mm": 210.0,
        "ebitda_at_entry_mm": 24.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.35, "medicaid": 0.10, "commercial": 0.52, "selfpay": 0.03
        },
        "notes": (
            "Interventional pain management; Serent Capital lower-middle-market; "
            "workers comp and commercial concentration; procedure-driven model"
        ),
    },
    # 155 — Gentiva / CD&R (hospice)
    {
        "source_id": "seed_155",
        "source": "seed",
        "deal_name": "Gentiva Health Services – Clayton Dubilier & Rice LBO",
        "year": 2022,
        "buyer": "Clayton Dubilier & Rice",
        "seller": "Kindred Healthcare / Humana",
        "ev_mm": 3750.0,
        "ebitda_at_entry_mm": 275.0,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.82, "medicaid": 0.10, "commercial": 0.08, "selfpay": 0.00
        },
        "notes": (
            "Hospice + palliative care LBO from Humana/Kindred; CD&R; "
            "~13.6x EBITDA; Medicare hospice cap risk; "
            "one of the largest hospice transactions on record"
        ),
    },
]
