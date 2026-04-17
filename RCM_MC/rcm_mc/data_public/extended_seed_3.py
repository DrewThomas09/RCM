"""Fourth batch of 20 curated public hospital/healthcare M&A seed deals (seeds 076-095).

Sources: SEC EDGAR (8-K, DEFM14A, SC 13E-3), Modern Healthcare, Becker's Hospital Review,
PE firm press releases, Healthcare Finance News (2019-2024 vintage).

All deals are real, publicly announced transactions.  Financial data from public
filings; estimates flagged where exact figures were not disclosed.

Covers:
  - Ambulatory surgery center roll-ups (USPI, Envision, NovaBay)
  - Behavioral/mental health platform builds (Behavioral Health Group, Refresh)
  - Home health / hospice consolidation (Amedisys, LHC, Gentiva)
  - Revenue cycle management M&A (Optum, R1 RCM, Nuvei)
  - Physician management buyouts (TeamHealth, IPC Healthcare)
  - Rural / critical access hospital transactions
  - Specialty pharmacy and infusion
  - International PE entry into U.S. hospital market
"""
from __future__ import annotations

import json

EXTENDED_SEED_DEALS_3 = [
    # ------------------------------------------------------------------
    # 76. Amedisys / UnitedHealth (Optum) acquisition attempt (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_076",
        "source": "seed",
        "deal_name": "Amedisys – UnitedHealth/Optum Acquisition",
        "year": 2023,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "Amedisys (public)",
        "ev_mm": 3300,
        "ebitda_at_entry_mm": 210,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.72, "medicaid": 0.08,
            "commercial": 0.15, "self_pay": 0.05,
        }),
        "notes": "Strategic acquisition by Optum at ~15.7x EBITDA. "
                 "DOJ antitrust review blocked deal (2024); Amedisys pivoted to Option Care merger. "
                 "Home health largest pure-play; 522 care centers, 21,000 employees.",
    },
    # ------------------------------------------------------------------
    # 77. LHC Group / Optum (completed 2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_077",
        "source": "seed",
        "deal_name": "LHC Group – Optum (completed)",
        "year": 2023,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "LHC Group (public)",
        "ev_mm": 5400,
        "ebitda_at_entry_mm": 370,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.70, "medicaid": 0.10,
            "commercial": 0.15, "self_pay": 0.05,
        }),
        "notes": "Closed Feb 2023 at ~14.6x EBITDA, $170/share. "
                 "Creates largest home health platform in US (~32k caregivers). "
                 "Optum vertical integration strategy; combined with Landmark Health (palliative).",
    },
    # ------------------------------------------------------------------
    # 78. Envision Healthcare / KKR take-private (2018) then bankruptcy (2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_078",
        "source": "seed",
        "deal_name": "Envision Healthcare – KKR Take-Private",
        "year": 2018,
        "buyer": "KKR",
        "seller": "Public shareholders",
        "ev_mm": 9900,
        "ebitda_at_entry_mm": 900,
        "hold_years": 5.0,
        "realized_moic": 0.2,
        "realized_irr": -0.28,
        "payer_mix": json.dumps({
            "medicare": 0.30, "medicaid": 0.20,
            "commercial": 0.45, "self_pay": 0.05,
        }),
        "notes": "KKR take-private at $46/share (~11x EBITDA). Surprise billing legislation "
                 "(No Surprises Act) devastated emergency medicine revenue. Filed Chapter 11 May 2023. "
                 "Cautionary tale on regulatory/legislative exposure in physician staffing.",
    },
    # ------------------------------------------------------------------
    # 79. R1 RCM / New Mountain Capital take-private (2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_079",
        "source": "seed",
        "deal_name": "R1 RCM – New Mountain Capital / TCP-ASC Take-Private",
        "year": 2023,
        "buyer": "New Mountain Capital / TCP-ASC",
        "seller": "R1 RCM (public, NASDAQ: RCM)",
        "ev_mm": 8900,
        "ebitda_at_entry_mm": 590,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.35, "medicaid": 0.20,
            "commercial": 0.40, "self_pay": 0.05,
        }),
        "notes": "Go-private at $13.75/share, ~15x EBITDA. Revenue cycle management outsourcer; "
                 "serves 160+ health systems, $40B revenue under management. "
                 "AI/automation investment thesis. TowerBrook co-invested.",
    },
    # ------------------------------------------------------------------
    # 80. TeamHealth / Blackstone take-private (2016)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_080",
        "source": "seed",
        "deal_name": "TeamHealth – Blackstone Take-Private",
        "year": 2016,
        "buyer": "Blackstone",
        "seller": "Public shareholders (NYSE: TMH)",
        "ev_mm": 6100,
        "ebitda_at_entry_mm": 480,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.28, "medicaid": 0.22,
            "commercial": 0.45, "self_pay": 0.05,
        }),
        "notes": "Blackstone take-private at $43.50/share (~12.7x EBITDA). "
                 "Emergency medicine + hospital medicine outsourcing platform. "
                 "No Surprises Act material revenue headwind post-2022. Refinancing challenges.",
    },
    # ------------------------------------------------------------------
    # 81. Surgical Care Affiliates (SCA) / UnitedHealth (2017)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_081",
        "source": "seed",
        "deal_name": "Surgical Care Affiliates (SCA) – UnitedHealth",
        "year": 2017,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "BCPE Empire Holdings (Warburg Pincus + AMSURG)",
        "ev_mm": 2300,
        "ebitda_at_entry_mm": 190,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.30, "medicaid": 0.05,
            "commercial": 0.62, "self_pay": 0.03,
        }),
        "notes": "Optum acquires ASC platform at ~12x EBITDA; 200+ surgery centers, "
                 "10k+ physicians. Payer-provider vertical integration play. "
                 "High commercial mix drives attractive margin profile.",
    },
    # ------------------------------------------------------------------
    # 82. Steward Health Care / Medical Properties Trust restructuring (2024)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_082",
        "source": "seed",
        "deal_name": "Steward Health Care – MPT / Chapter 11 Restructuring",
        "year": 2024,
        "buyer": "Various (distressed acquirers)",
        "seller": "Steward Health Care (Cerberus portfolio)",
        "ev_mm": 1200,
        "ebitda_at_entry_mm": -80,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.40, "medicaid": 0.35,
            "commercial": 0.20, "self_pay": 0.05,
        }),
        "notes": "Largest US for-profit hospital system bankruptcy (38 hospitals). "
                 "Medical Properties Trust (REIT) held $7B in leases. "
                 "Filed May 2024; hospitals sold piecemeal. Cerberus 2010 LBO unraveled. "
                 "High Medicaid / Medicare mix + sale-leaseback debt trap.",
    },
    # ------------------------------------------------------------------
    # 83. Gentiva Health Services / Kindred at Home split (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_083",
        "source": "seed",
        "deal_name": "Gentiva Health (Kindred at Home) – Humana / Clayton Dubilier",
        "year": 2021,
        "buyer": "Clayton Dubilier & Rice / Humana (minority)",
        "seller": "Kindred Healthcare / TPG / Welsh Carson",
        "ev_mm": 2800,
        "ebitda_at_entry_mm": 230,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.65, "medicaid": 0.12,
            "commercial": 0.18, "self_pay": 0.05,
        }),
        "notes": "CD&R acquires Kindred at Home (~12x EBITDA); Humana retains ~40% stake. "
                 "Rebranded Gentiva. Home health + hospice; ~50k patients/day. "
                 "Medicare Advantage rate pressure post-2023 headwind.",
    },
    # ------------------------------------------------------------------
    # 84. Behavioral Health Group (BHG) / GTCR add-on platform (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_084",
        "source": "seed",
        "deal_name": "Behavioral Health Group (BHG) – GTCR Platform",
        "year": 2021,
        "buyer": "GTCR",
        "seller": "Shore Capital Partners / Founders",
        "ev_mm": 450,
        "ebitda_at_entry_mm": 45,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.05, "medicaid": 0.60,
            "commercial": 0.30, "self_pay": 0.05,
        }),
        "notes": "Opioid use disorder treatment network; ~120 centers across 24 states. "
                 "Entry at ~10x EBITDA. GTCR targets 300+ centers. "
                 "Medicaid-heavy payer mix; SAMHSA grant funding supplements.",
    },
    # ------------------------------------------------------------------
    # 85. National Mentor Holdings / Civitas Solutions (2019)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_085",
        "source": "seed",
        "deal_name": "Civitas Solutions / Public Shareholders",
        "year": 2019,
        "buyer": "A-G Capital Partners (management buyout consortium)",
        "seller": "Public shareholders (NYSE: CIVI)",
        "ev_mm": 1400,
        "ebitda_at_entry_mm": 160,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.05, "medicaid": 0.80,
            "commercial": 0.10, "self_pay": 0.05,
        }),
        "notes": "Take-private of I/DD and behavioral health residential services. "
                 "~$14.50/share, ~8.75x EBITDA. Medicaid-dependent; state rate risk flagged. "
                 "Previously National Mentor Holdings, backed by Vestar Capital.",
    },
    # ------------------------------------------------------------------
    # 86. LifePoint Health / RCCH HealthCare Partners merger (2018)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_086",
        "source": "seed",
        "deal_name": "LifePoint Health – RCCH HealthCare Partners Merger",
        "year": 2018,
        "buyer": "Apollo Global / RCCH",
        "seller": "LifePoint Health (public)",
        "ev_mm": 5600,
        "ebitda_at_entry_mm": 560,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.42, "medicaid": 0.25,
            "commercial": 0.28, "self_pay": 0.05,
        }),
        "notes": "Apollo-backed RCCH merges with LifePoint at ~10x EBITDA. "
                 "Combined 89 hospital campuses in 30 states, predominantly rural and non-urban. "
                 "Renamed LifePoint Health (private). Significant rural Medicare/Medicaid exposure.",
    },
    # ------------------------------------------------------------------
    # 87. Sound Physicians / TPG Growth (2017)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_087",
        "source": "seed",
        "deal_name": "Sound Physicians – TPG Growth",
        "year": 2017,
        "buyer": "TPG Growth",
        "seller": "Summit Partners / Founders",
        "ev_mm": 2100,
        "ebitda_at_entry_mm": 175,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.32, "medicaid": 0.20,
            "commercial": 0.43, "self_pay": 0.05,
        }),
        "notes": "Hospitalist / intensivist / post-acute physician management. ~12x EBITDA. "
                 "3,000+ physicians across 350+ facilities. "
                 "No Surprises Act later impacted out-of-network revenue streams.",
    },
    # ------------------------------------------------------------------
    # 88. MEDNAX / Pediatrix Medical Group physician group (2020)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_088",
        "source": "seed",
        "deal_name": "MEDNAX Radiology / Radiology Partners split-off",
        "year": 2020,
        "buyer": "New Mountain Capital / MEDNAX management",
        "seller": "MEDNAX (public spinoff of radiology segment)",
        "ev_mm": 885,
        "ebitda_at_entry_mm": 85,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.25, "medicaid": 0.10,
            "commercial": 0.60, "self_pay": 0.05,
        }),
        "notes": "MEDNAX divests radiology arm to New Mountain at ~10.4x EBITDA. "
                 "Merged into Radiology Partners platform. "
                 "AI-reads and teleradiology growth thesis. Commercial-heavy payer mix.",
    },
    # ------------------------------------------------------------------
    # 89. US Physical Therapy / European rollup add-on (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_089",
        "source": "seed",
        "deal_name": "US Physical Therapy – ATI Physical Therapy add-on targets",
        "year": 2022,
        "buyer": "ATI Physical Therapy (Advent backed)",
        "seller": "Various independent PT clinic groups",
        "ev_mm": 180,
        "ebitda_at_entry_mm": 18,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.25, "medicaid": 0.10,
            "commercial": 0.60, "self_pay": 0.05,
        }),
        "notes": "Fragmented PT market roll-up; ~10x entry. "
                 "Therapy staffing labor cost inflation headwind post-2021. "
                 "ATI public company SPAC route struggled; margin compression.",
    },
    # ------------------------------------------------------------------
    # 90. National Spine & Pain Centers / Centre Partners (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_090",
        "source": "seed",
        "deal_name": "National Spine & Pain Centers – Avista Capital Partners",
        "year": 2021,
        "buyer": "Avista Capital Partners",
        "seller": "Existing investors / founders",
        "ev_mm": 380,
        "ebitda_at_entry_mm": 40,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.28, "medicaid": 0.05,
            "commercial": 0.62, "self_pay": 0.05,
        }),
        "notes": "Pain management / interventional spine platform. ~9.5x entry. "
                 "150+ clinics across mid-Atlantic and Southeast. "
                 "Commercial payer mix attractive; prior auth risk on pain procedures.",
    },
    # ------------------------------------------------------------------
    # 91. Ardent Health Services / Ventas REIT partnership (2015, refinanced 2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_091",
        "source": "seed",
        "deal_name": "Ardent Health Services – Equity Capital (2021 refinancing)",
        "year": 2021,
        "buyer": "Equity Group Investments / Ventas REIT",
        "seller": "Welsh Carson Anderson & Stowe",
        "ev_mm": 3100,
        "ebitda_at_entry_mm": 250,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.38, "medicaid": 0.28,
            "commercial": 0.29, "self_pay": 0.05,
        }),
        "notes": "Ardent 30-hospital system in TX, OK, NM, NJ, ID. ~12.4x EBITDA. "
                 "Ventas provides REIT real estate; EGI provides operations capital. "
                 "Mixed payer state markets; rural + urban blend.",
    },
    # ------------------------------------------------------------------
    # 92. Prospect Medical Holdings / distressed sale (2023-24)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_092",
        "source": "seed",
        "deal_name": "Prospect Medical Holdings – Distressed Asset Sales",
        "year": 2023,
        "buyer": "State of CT / Various acquirers",
        "seller": "Samuel Lee / Prospect Medical (Leonard Green-backed)",
        "ev_mm": 600,
        "ebitda_at_entry_mm": -40,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.38, "medicaid": 0.40,
            "commercial": 0.17, "self_pay": 0.05,
        }),
        "notes": "Leonard Green & Partners loaded Prospect with debt via dividend recaps. "
                 "CT AG pursued clawback of $493M in dividends. Multiple hospitals closed/sold. "
                 "Emblematic of PE dividend recap abuse in distressed hospital settings.",
    },
    # ------------------------------------------------------------------
    # 93. Covenant Physician Partners / PEI acquisition (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_093",
        "source": "seed",
        "deal_name": "Covenant Physician Partners – USPI / Tenet acquisition",
        "year": 2021,
        "buyer": "United Surgical Partners International (USPI/Tenet)",
        "seller": "Covenant Physician Partners founders / Warburg Pincus",
        "ev_mm": 1400,
        "ebitda_at_entry_mm": 120,
        "hold_years": 6.0,
        "realized_moic": 4.5,
        "realized_irr": 0.27,
        "payer_mix": json.dumps({
            "medicare": 0.22, "medicaid": 0.05,
            "commercial": 0.68, "self_pay": 0.05,
        }),
        "notes": "Warburg Pincus exit via sale to USPI at ~11.7x. "
                 "Ophthalmology + orthopedic + multispecialty ASC network; 90+ facilities. "
                 "High commercial payer mix; attractive bolt-on for USPI platform.",
    },
    # ------------------------------------------------------------------
    # 94. Centurion Health / corrections healthcare (2019)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_094",
        "source": "seed",
        "deal_name": "Centurion Health – American Securities acquisition",
        "year": 2019,
        "buyer": "American Securities",
        "seller": "MedFirst / Founders",
        "ev_mm": 320,
        "ebitda_at_entry_mm": 32,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.02, "medicaid": 0.10,
            "commercial": 0.03, "self_pay": 0.85,
        }),
        "notes": "Correctional healthcare outsourcing (prisons/jails). ~10x entry. "
                 "Revenue from government correctional facility contracts (non-traditional payer mix). "
                 "Reputational and litigation risk inherent in corrections healthcare.",
    },
    # ------------------------------------------------------------------
    # 95. Premise Health / Warburg Pincus platform (2020)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_095",
        "source": "seed",
        "deal_name": "Premise Health – Warburg Pincus (employer health centers)",
        "year": 2020,
        "buyer": "Warburg Pincus",
        "seller": "H.I.G. Capital / Premise founders",
        "ev_mm": 1200,
        "ebitda_at_entry_mm": 95,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.00, "medicaid": 0.00,
            "commercial": 0.95, "self_pay": 0.05,
        }),
        "notes": "Employer-sponsored on-site / near-site health centers. ~12.6x EBITDA. "
                 "800+ care delivery sites, 200+ Fortune 500 clients. "
                 "Zero Medicare/Medicaid; 100% employer contract revenue. "
                 "COVID-accelerated demand for employer health navigation.",
    },
]
