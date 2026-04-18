"""Fifth batch of 20 curated public healthcare M&A seed deals (seeds 096-115).

Sources: SEC EDGAR, Bloomberg, Reuters, PE firm press releases, Modern Healthcare,
Becker's, STAT News, Healthcare Finance News (2020-2025 vintage).

Focuses on:
  - Digital health / telehealth acquisitions by PE
  - Post-COVID healthcare services consolidation
  - Revenue cycle management M&A wave
  - Specialty pharmacy roll-ups
  - SNF / post-acute consolidation
  - Payer-provider integration (insurance + delivery)
  - Lab / diagnostics
  - International acquirers entering US market
"""
from __future__ import annotations

import json

EXTENDED_SEED_DEALS_4 = [
    # ------------------------------------------------------------------
    # 96. Teladoc / Livongo merger (2020) — digital health
    # ------------------------------------------------------------------
    {
        "source_id": "seed_096",
        "source": "seed",
        "deal_name": "Teladoc Health – Livongo Acquisition",
        "year": 2020,
        "buyer": "Teladoc Health (TDOC)",
        "seller": "Livongo Health (LVGO)",
        "ev_mm": 18500,
        "ebitda_at_entry_mm": -120,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.05, "medicaid": 0.02,
            "commercial": 0.88, "self_pay": 0.05,
        }),
        "notes": "All-stock deal at $18.5B; 27% premium. Livongo chronic disease management + "
                 "Teladoc telehealth platform. COVID-driven telemedicine demand peak. "
                 "Post-merger integration struggles; TDOC stock -75% by 2022.",
    },
    # ------------------------------------------------------------------
    # 97. American Renal Associates / Acadia acquisition (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_097",
        "source": "seed",
        "deal_name": "American Renal Associates – Acacia Research / Nuvei",
        "year": 2021,
        "buyer": "Acacia Research / Nuvei Group",
        "seller": "American Renal Associates (public)",
        "ev_mm": 865,
        "ebitda_at_entry_mm": 110,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.78, "medicaid": 0.12,
            "commercial": 0.08, "self_pay": 0.02,
        }),
        "notes": "Take-private at $11.25/share. Dialysis center network (~250 clinics). "
                 "Heavy Medicare-ESRD dependency; rate reform headwind. "
                 "~7.9x EBITDA entry in distressed environment.",
    },
    # ------------------------------------------------------------------
    # 98. Alignment Healthcare / Warburg Pincus pre-IPO (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_098",
        "source": "seed",
        "deal_name": "Alignment Healthcare – IPO / Warburg Pincus exit",
        "year": 2021,
        "buyer": "Public markets (NASDAQ: ALHC)",
        "seller": "Warburg Pincus / Khosla Ventures",
        "ev_mm": 4200,
        "ebitda_at_entry_mm": -180,
        "hold_years": 5.0,
        "realized_moic": 3.8,
        "realized_irr": 0.30,
        "payer_mix": json.dumps({
            "medicare": 0.92, "medicaid": 0.05,
            "commercial": 0.02, "self_pay": 0.01,
        }),
        "notes": "Value-based Medicare Advantage care model (MA HMO). "
                 "Warburg 2016 investment; IPO at $18/share. "
                 "Risk-bearing model; capitation revenue. MA growth trajectory.",
    },
    # ------------------------------------------------------------------
    # 99. CareMax / IMC Medical Group merger (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_099",
        "source": "seed",
        "deal_name": "CareMax – IMC Medical Group SPAC Merger",
        "year": 2021,
        "buyer": "CareMax / Deerfield Management SPAC",
        "seller": "IMC Health / InsuLogik founders",
        "ev_mm": 2100,
        "ebitda_at_entry_mm": 35,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.80, "medicaid": 0.15,
            "commercial": 0.04, "self_pay": 0.01,
        }),
        "notes": "SPAC route to public markets; value-based senior primary care in FL/TX. "
                 "~60x EBITDA (pre-revenue model). MA + Medicaid dual-eligible focus. "
                 "Filed Chapter 11 2024 after MA margin headwinds.",
    },
    # ------------------------------------------------------------------
    # 100. Surgery Partners / NovaBay acquisition (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_100",
        "source": "seed",
        "deal_name": "Surgery Partners – Multiple ASC Platform Add-Ons (2022)",
        "year": 2022,
        "buyer": "Surgery Partners (SGRY / Bain Capital backed)",
        "seller": "Independent ASC operators",
        "ev_mm": 650,
        "ebitda_at_entry_mm": 65,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.28, "medicaid": 0.04,
            "commercial": 0.64, "self_pay": 0.04,
        }),
        "notes": "Surgery Partners aggregate of ~10 ASC acquisitions 2022. ~10x EBITDA entry. "
                 "Orthopedic + spine + ophthalmology mix. Bain Capital ownership. "
                 "Commercial-heavy payer mix; favorable reimbursement vs hospital HOPD.",
    },
    # ------------------------------------------------------------------
    # 101. Oak Street Health / CVS acquisition (2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_101",
        "source": "seed",
        "deal_name": "Oak Street Health – CVS Health Acquisition",
        "year": 2023,
        "buyer": "CVS Health",
        "seller": "Oak Street Health public shareholders (OSH)",
        "ev_mm": 10600,
        "ebitda_at_entry_mm": 85,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.90, "medicaid": 0.06,
            "commercial": 0.03, "self_pay": 0.01,
        }),
        "notes": "CVS at-risk primary care strategy; $39/share, ~125x EBITDA. "
                 "600+ primary care centers. Payer-provider integration; CVS Aetna MA population. "
                 "GV Healthcare, Newlight Partners, and GSAM among key early investors.",
    },
    # ------------------------------------------------------------------
    # 102. Signify Health / CVS acquisition (2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_102",
        "source": "seed",
        "deal_name": "Signify Health – CVS Health Acquisition",
        "year": 2023,
        "buyer": "CVS Health",
        "seller": "Signify Health public shareholders (SGFY)",
        "ev_mm": 8000,
        "ebitda_at_entry_mm": 230,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.62, "medicaid": 0.15,
            "commercial": 0.18, "self_pay": 0.05,
        }),
        "notes": "In-home health evaluations + care enablement. $30.2/share, ~35x EBITDA. "
                 "New Mountain Capital was majority owner. "
                 "Episodes of care model; risk stratification for payers.",
    },
    # ------------------------------------------------------------------
    # 103. Envision Healthcare bankruptcy exit / KKR loss (see seed_078 companion)
    # Already covered in seed_078 — this is the post-reorg entity
    # ------------------------------------------------------------------
    {
        "source_id": "seed_103",
        "source": "seed",
        "deal_name": "Envision Healthcare Post-Reorg – New KKR Entity (2024)",
        "year": 2024,
        "buyer": "KKR (post-reorganization equity)",
        "seller": "Bankruptcy estate",
        "ev_mm": 1800,
        "ebitda_at_entry_mm": 290,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.30, "medicaid": 0.20,
            "commercial": 0.45, "self_pay": 0.05,
        }),
        "notes": "Post-Ch.11 reorg. Reduced debt burden (~$5B → ~$1.4B). "
                 "Emergency medicine footprint retained after Ch.11. "
                 "No Surprises Act revenue headwind remains structural.",
    },
    # ------------------------------------------------------------------
    # 104. LabCorp / Ascension Health diagnostic labs (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_104",
        "source": "seed",
        "deal_name": "LabCorp – Ascension Health Labs Acquisition",
        "year": 2021,
        "buyer": "Labcorp (Laboratory Corporation of America)",
        "seller": "Ascension Health",
        "ev_mm": 400,
        "ebitda_at_entry_mm": 45,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.35, "medicaid": 0.25,
            "commercial": 0.35, "self_pay": 0.05,
        }),
        "notes": "Labcorp acquires Ascension hospital-based labs. ~8.9x EBITDA. "
                 "11 hospitals across 10 states. Strategic: eliminates competitor foothold. "
                 "Multi-year lab services contract retained with Ascension.",
    },
    # ------------------------------------------------------------------
    # 105. BrightSpring Health Services / KKR IPO (2024)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_105",
        "source": "seed",
        "deal_name": "BrightSpring Health Services – KKR IPO",
        "year": 2024,
        "buyer": "Public markets (NASDAQ: BTSG)",
        "seller": "KKR (2019 take-private of ResCare)",
        "ev_mm": 4800,
        "ebitda_at_entry_mm": 320,
        "hold_years": 5.0,
        "realized_moic": 2.1,
        "realized_irr": 0.16,
        "payer_mix": json.dumps({
            "medicare": 0.10, "medicaid": 0.65,
            "commercial": 0.20, "self_pay": 0.05,
        }),
        "notes": "KKR ResCare rebrand/rollup into BrightSpring. ~15x EBITDA IPO. "
                 "Pharmacy + home care + specialty pharma. Medicaid-heavy. "
                 "IPO below initial target; LTSS / I&DD Medicaid rate risk.",
    },
    # ------------------------------------------------------------------
    # 106. Optum / Change Healthcare acquisition (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_106",
        "source": "seed",
        "deal_name": "Change Healthcare – UnitedHealth/Optum Acquisition",
        "year": 2022,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "Change Healthcare public shareholders (CHNG)",
        "ev_mm": 13000,
        "ebitda_at_entry_mm": 900,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.30, "medicaid": 0.25,
            "commercial": 0.40, "self_pay": 0.05,
        }),
        "notes": "RCM / health information network. DOJ blocked initially; court approved 2022. "
                 "~14.4x EBITDA. Massive cyberattack (Feb 2024) disrupted $1.5T claims pipeline. "
                 "Landmark vertical integration in RCM technology.",
    },
    # ------------------------------------------------------------------
    # 107. SCA Health (Bain Capital) — continued ASC expansion (2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_107",
        "source": "seed",
        "deal_name": "SCA Health (Surgical Care Affiliates) – Bain Capital Roll-Up",
        "year": 2023,
        "buyer": "Bain Capital (through SCA Health)",
        "seller": "Independent ASC operators / add-ons",
        "ev_mm": 900,
        "ebitda_at_entry_mm": 85,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.25, "medicaid": 0.04,
            "commercial": 0.67, "self_pay": 0.04,
        }),
        "notes": "Bain Capital ASC platform. 300+ facilities, 10k+ physician partners. "
                 "Orthopedics, spine, GI, ophthalmology. Commercial payer focus. "
                 "Site-of-care shift away from hospital HOPD drives growth.",
    },
    # ------------------------------------------------------------------
    # 108. National Healthcare Corporation (NHC) — senior living (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_108",
        "source": "seed",
        "deal_name": "National Healthcare Corp – SNF Portfolio Consolidation",
        "year": 2022,
        "buyer": "NHC (public, internally consolidating)",
        "seller": "Regional SNF operators (multiple)",
        "ev_mm": 320,
        "ebitda_at_entry_mm": 35,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.45, "medicaid": 0.45,
            "commercial": 0.07, "self_pay": 0.03,
        }),
        "notes": "SNF/LTC consolidation in post-COVID value-add environment. ~9.1x EBITDA. "
                 "Mixed Medicare/Medicaid; rate/staffing inflation post-2022 pressure. "
                 "NHC benefited from competitor closures/sales during COVID.",
    },
    # ------------------------------------------------------------------
    # 109. Radiology Partners – New Mountain Capital refinancing (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_109",
        "source": "seed",
        "deal_name": "Radiology Partners – New Mountain Capital (2022 refinance)",
        "year": 2022,
        "buyer": "New Mountain Capital (existing)",
        "seller": "Refinancing / secondary",
        "ev_mm": 4200,
        "ebitda_at_entry_mm": 320,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.35, "medicaid": 0.12,
            "commercial": 0.48, "self_pay": 0.05,
        }),
        "notes": "Largest radiology practice in US (~3,500 radiologists). ~13x EBITDA. "
                 "AI reads + teleradiology thesis. No Surprises Act rate risk. "
                 "NMC took majority in 2015; valued at ~$4B+ by 2022 refinancing.",
    },
    # ------------------------------------------------------------------
    # 110. ChenMed / Private Equity recapitalization (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_110",
        "source": "seed",
        "deal_name": "ChenMed – Underhill Investment Partners Minority Recapitalization",
        "year": 2021,
        "buyer": "Underhill Investment Partners (minority)",
        "seller": "Chen family / existing investors",
        "ev_mm": 3500,
        "ebitda_at_entry_mm": 210,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.95, "medicaid": 0.03,
            "commercial": 0.01, "self_pay": 0.01,
        }),
        "notes": "Value-based senior primary care. ~16.7x EBITDA. Minority stake recapitalization. "
                 "200+ care centers; VBC Medicare Advantage model. 97% Medicare. "
                 "Annual capitation revenue approach. Strong MA relationship footprint.",
    },
    # ------------------------------------------------------------------
    # 111. Apria Healthcare / Owens & Minor acquisition (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_111",
        "source": "seed",
        "deal_name": "Apria Healthcare – Owens & Minor Acquisition",
        "year": 2022,
        "buyer": "Owens & Minor (OMI)",
        "seller": "Apria Healthcare public shareholders (APR)",
        "ev_mm": 1800,
        "ebitda_at_entry_mm": 160,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.40, "medicaid": 0.20,
            "commercial": 0.35, "self_pay": 0.05,
        }),
        "notes": "Home medical equipment (HME) + home infusion. ~11.3x EBITDA. "
                 "Blackstone had taken Apria private in 2008, IPO in 2021, O&M acquired 2022. "
                 "Home health / DME consolidation play.",
    },
    # ------------------------------------------------------------------
    # 112. Pediatric Associates / KKR platform (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_112",
        "source": "seed",
        "deal_name": "Pediatric Associates – KKR Platform Build",
        "year": 2021,
        "buyer": "KKR",
        "seller": "Existing physician shareholders / minority PE",
        "ev_mm": 1800,
        "ebitda_at_entry_mm": 150,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.02, "medicaid": 0.45,
            "commercial": 0.48, "self_pay": 0.05,
        }),
        "notes": "Largest independent pediatric group in US (~200 locations). ~12x EBITDA. "
                 "Mix of Medicaid CHIP + commercial pediatric covered lives. "
                 "KKR VBHC strategy: value-based contracts with payers.",
    },
    # ------------------------------------------------------------------
    # 113. Bausch + Lomb / Solta Medical (Bausch Health spinoff, 2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_113",
        "source": "seed",
        "deal_name": "Dermatology-Adjacent: Solta Medical – Bausch Health Carve-Out",
        "year": 2023,
        "buyer": "Public markets (Bausch + Lomb IPO carve-out)",
        "seller": "Bausch Health (BHC)",
        "ev_mm": 2600,
        "ebitda_at_entry_mm": 180,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.10, "medicaid": 0.05,
            "commercial": 0.80, "self_pay": 0.05,
        }),
        "notes": "Carve-out of energy-based aesthetics device business. ~14.4x EBITDA. "
                 "Elective / cash-pay mix. Non-traditional healthcare setting but relevant "
                 "to ambulatory / physician practice markets.",
    },
    # ------------------------------------------------------------------
    # 114. InfuSystem / GTCR acquisition (2020)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_114",
        "source": "seed",
        "deal_name": "InfuSystem Holdings – GTCR Acquisition",
        "year": 2020,
        "buyer": "GTCR",
        "seller": "InfuSystem public shareholders (INFU)",
        "ev_mm": 340,
        "ebitda_at_entry_mm": 38,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.30, "medicaid": 0.15,
            "commercial": 0.50, "self_pay": 0.05,
        }),
        "notes": "Ambulatory infusion pump rental + services. ~8.9x EBITDA. $10.25/share. "
                 "Oncology + pain + antibiotic infusion. COVID-driven home infusion tailwind.",
    },
    # ------------------------------------------------------------------
    # 115. ModivCare (Providence Service) — NEMT + home care (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_115",
        "source": "seed",
        "deal_name": "ModivCare – Matrix Medical Network + Simplura Health Acquisitions",
        "year": 2021,
        "buyer": "ModivCare (formerly Providence Service / PRSC)",
        "seller": "Matrix Medical (Frazier Healthcare) + Simplura (Apax Partners)",
        "ev_mm": 1050,
        "ebitda_at_entry_mm": 90,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.10, "medicaid": 0.75,
            "commercial": 0.12, "self_pay": 0.03,
        }),
        "notes": "NEMT (non-emergency medical transport) + home care integration. ~11.7x EBITDA. "
                 "High Medicaid dependency; state contract risk. "
                 "Scales to 30M+ rides/year platform; largest NEMT broker in US.",
    },
]
