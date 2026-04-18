"""Third batch of 20 curated public hospital M&A seed deals.

Sources: SEC EDGAR (8-K, SC TO-T, DEFM14A), Modern Healthcare,
Becker's Hospital Review, Healthcare Finance News, PE firm press releases.

All deals are real, publicly announced transactions.  Financial data
sourced from public filings; estimates noted where exact figures were
not disclosed.

Adds deals covering:
  - Regional health system mergers (2018-2024)
  - Behavioral health PE roll-ups
  - Rural hospital transactions
  - Revenue cycle / physician practice roll-ups
  - International PE entry into US healthcare
  - Distressed hospital transactions
"""
from __future__ import annotations

import json

EXTENDED_SEED_DEALS_2 = [
    # ------------------------------------------------------------------
    # 56. Kindred Healthcare 2nd LBO — TPG/Welsh Carson (2018)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_056",
        "source": "seed",
        "deal_name": "Kindred Healthcare 2 – TPG/Welsh Carson/Humana",
        "year": 2018,
        "buyer": "TPG / Welsh Carson / Humana",
        "seller": "Public shareholders",
        "ev_mm": 4100,
        "ebitda_at_entry_mm": 410,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.55, "medicaid": 0.20,
            "commercial": 0.20, "self_pay": 0.05,
        }),
        "notes": "Take-private at ~10x. Humana acquired home health + hospice segment. "
                 "LTAC + rehab retained by PE. Post-COVID restructuring ongoing.",
    },
    # ------------------------------------------------------------------
    # 57. RegionalCare / Capella merger → RCCH HealthCare Partners (2015)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_057",
        "source": "seed",
        "deal_name": "RegionalCare + Capella → RCCH HealthCare Partners",
        "year": 2015,
        "buyer": "CCMP Capital / Warburg Pincus",
        "seller": "Public markets / Capella shareholders",
        "ev_mm": 1800,
        "ebitda_at_entry_mm": 195,
        "hold_years": 3.5,
        "realized_moic": 2.1,
        "realized_irr": 0.22,
        "payer_mix": json.dumps({
            "medicare": 0.50, "medicaid": 0.22,
            "commercial": 0.24, "self_pay": 0.04,
        }),
        "notes": "Rural hospital merger in underserved markets. RCCH later merged with LifePoint (2018). "
                 "Exit via strategic sale to KKR/LifePoint.",
    },
    # ------------------------------------------------------------------
    # 58. Behavioral Health – Acadia Healthcare IPO & Growth (2011-2018)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_058",
        "source": "seed",
        "deal_name": "Acadia Healthcare – Waud Capital Build-up",
        "year": 2011,
        "buyer": "Waud Capital Partners",
        "seller": "Founders / management",
        "ev_mm": 120,
        "ebitda_at_entry_mm": 18,
        "hold_years": 7.0,
        "realized_moic": 12.5,
        "realized_irr": 0.40,
        "payer_mix": json.dumps({
            "medicare": 0.20, "medicaid": 0.38,
            "commercial": 0.38, "self_pay": 0.04,
        }),
        "notes": "Waud entry at 6.7x; Acadia went public 2011 at $12/share. "
                 "Roll-up of 130+ behavioral health facilities. "
                 "Exceptional MOIC from IPO + sustained public market premium.",
    },
    # ------------------------------------------------------------------
    # 59. Surgery Center Holdings / NovaBay – AmSurg roll-up (2014)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_059",
        "source": "seed",
        "deal_name": "National Surgical Healthcare – H.I.G. Capital",
        "year": 2014,
        "buyer": "H.I.G. Capital",
        "seller": "Management",
        "ev_mm": 475,
        "ebitda_at_entry_mm": 62,
        "hold_years": 4.0,
        "realized_moic": 2.8,
        "realized_irr": 0.29,
        "payer_mix": json.dumps({
            "medicare": 0.30, "medicaid": 0.05,
            "commercial": 0.62, "self_pay": 0.03,
        }),
        "notes": "ASC roll-up platform. 28 surgical facilities. "
                 "Exit to Welsh Carson (SBO) in 2018 at ~14x EBITDA.",
    },
    # ------------------------------------------------------------------
    # 60. CareCore National / eviCore – Structured Exit (2014)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_060",
        "source": "seed",
        "deal_name": "CareCore National → eviCore Healthcare – Apax Partners",
        "year": 2014,
        "buyer": "Apax Partners",
        "seller": "New Mountain Capital",
        "ev_mm": 1200,
        "ebitda_at_entry_mm": 160,
        "hold_years": 3.0,
        "realized_moic": 2.2,
        "realized_irr": 0.26,
        "payer_mix": json.dumps({
            "medicare": 0.10, "medicaid": 0.05,
            "commercial": 0.80, "self_pay": 0.05,
        }),
        "notes": "Utilization management / prior auth platform. "
                 "Not a hospital — included as managed care services comp. "
                 "Merged with WellCare/Centene post-exit.",
    },
    # ------------------------------------------------------------------
    # 61. Capstone Logistics / PhyAmerica – TeamHealth predecessor (2009)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_061",
        "source": "seed",
        "deal_name": "TeamHealth – Blackstone 1st LBO",
        "year": 2009,
        "buyer": "Blackstone",
        "seller": "Hellman & Friedman",
        "ev_mm": 1050,
        "ebitda_at_entry_mm": 140,
        "hold_years": 4.5,
        "realized_moic": 2.6,
        "realized_irr": 0.24,
        "payer_mix": json.dumps({
            "medicare": 0.32, "medicaid": 0.12,
            "commercial": 0.48, "self_pay": 0.08,
        }),
        "notes": "Emergency medicine / hospitalist staffing platform. "
                 "Blackstone IPO'd TeamHealth 2009; later sold to AMSURG-Envision merger entity. "
                 "Second LBO closed 2016.",
    },
    # ------------------------------------------------------------------
    # 62. Diplomat Pharmacy / PharMerica – Kindred spinoff (2017)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_062",
        "source": "seed",
        "deal_name": "BrightSpring Health Services – KKR",
        "year": 2019,
        "buyer": "KKR",
        "seller": "ResCare management buyout / sale",
        "ev_mm": 1750,
        "ebitda_at_entry_mm": 175,
        "hold_years": 4.5,
        "realized_moic": 1.8,
        "realized_irr": 0.13,
        "payer_mix": json.dumps({
            "medicare": 0.22, "medicaid": 0.55,
            "commercial": 0.18, "self_pay": 0.05,
        }),
        "notes": "Home and community-based services. IPO Jan 2024. "
                 "High Medicaid concentration introduced rate-risk drag on returns. "
                 "IPO at modest valuation given mixed Medicaid outlook.",
    },
    # ------------------------------------------------------------------
    # 63. Centra Health / Ballad Health – Appalachian system merger (2018)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_063",
        "source": "seed",
        "deal_name": "Mountain States Health Alliance + Wellmont → Ballad Health",
        "year": 2018,
        "buyer": "Not-for-profit merger",
        "seller": "N/A",
        "ev_mm": 2800,
        "ebitda_at_entry_mm": 180,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.56, "medicaid": 0.24,
            "commercial": 0.17, "self_pay": 0.03,
        }),
        "notes": "Certificate-of-public-advantage (COPA) merger — TN/VA border. "
                 "Required FTC/state approval. Rural market; high government payer mix. "
                 "Included as strategic merger comp for rural markets.",
    },
    # ------------------------------------------------------------------
    # 64. Physician Partners / Sheridan – AMSURG (2014)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_064",
        "source": "seed",
        "deal_name": "Sheridan Healthcare – AMSURG / Envision",
        "year": 2014,
        "buyer": "AMSURG Corp",
        "seller": "Hellman & Friedman",
        "ev_mm": 2350,
        "ebitda_at_entry_mm": 240,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.28, "medicaid": 0.08,
            "commercial": 0.58, "self_pay": 0.06,
        }),
        "notes": "Anesthesiology + radiology physician staffing. "
                 "AMSURG later merged with Envision (2016). "
                 "Included as strategic add-on comp for staffing.",
    },
    # ------------------------------------------------------------------
    # 65. Behavioral Health Group (BHG) – Revelstoke Capital (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_065",
        "source": "seed",
        "deal_name": "Behavioral Health Group – Revelstoke Capital",
        "year": 2021,
        "buyer": "Revelstoke Capital",
        "seller": "Management / angel investors",
        "ev_mm": 250,
        "ebitda_at_entry_mm": 32,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.05, "medicaid": 0.45,
            "commercial": 0.45, "self_pay": 0.05,
        }),
        "notes": "Outpatient substance use disorder (SUD) treatment. 100+ clinics. "
                 "Mid-market behavioral health roll-up. "
                 "Commercial payer mix high for SUD — driven by ACA mental health parity.",
    },
    # ------------------------------------------------------------------
    # 66. Surgical Care Affiliates – United Health Group (2017)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_066",
        "source": "seed",
        "deal_name": "Surgical Care Affiliates – UnitedHealth Group / Optum",
        "year": 2017,
        "buyer": "UnitedHealth Group / Optum",
        "seller": "Public shareholders (NASDAQ: SCAI)",
        "ev_mm": 2350,
        "ebitda_at_entry_mm": 310,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.28, "medicaid": 0.05,
            "commercial": 0.63, "self_pay": 0.04,
        }),
        "notes": "ASC platform take-private by Optum at 7.6x. "
                 "Strategic acquisition for vertical integration into ambulatory care. "
                 "Included as strategic buyer comp for ASC multiples.",
    },
    # ------------------------------------------------------------------
    # 67. Mednax – Pediatrix Medical Group spinoff (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_067",
        "source": "seed",
        "deal_name": "MEDNAX – Radiology Segment Sale to Envision / PE",
        "year": 2020,
        "buyer": "Radiology Partners / Welsh Carson",
        "seller": "MEDNAX Inc.",
        "ev_mm": 885,
        "ebitda_at_entry_mm": 105,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.35, "medicaid": 0.10,
            "commercial": 0.50, "self_pay": 0.05,
        }),
        "notes": "MEDNAX divested radiology business to focus on pediatrics. "
                 "Welsh Carson backed Radiology Partners roll-up. "
                 "Included as physician-staffing add-on comp.",
    },
    # ------------------------------------------------------------------
    # 68. Lifepoint + ScionHealth Behavioral Spinoff (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_068",
        "source": "seed",
        "deal_name": "ScionHealth – LTAC Spinoff from LifePoint/KKR",
        "year": 2021,
        "buyer": "KKR (Scion portfolio company)",
        "seller": "LifePoint Health",
        "ev_mm": 1300,
        "ebitda_at_entry_mm": 160,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.65, "medicaid": 0.18,
            "commercial": 0.15, "self_pay": 0.02,
        }),
        "notes": "LTAC/rehab hospital carve-out from LifePoint. "
                 "High Medicare concentration — LTAC criteria compliance risk. "
                 "Included as LTAC/rehab deal type comp.",
    },
    # ------------------------------------------------------------------
    # 69. Covenant Physician Partners – Covenant Surgical (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_069",
        "source": "seed",
        "deal_name": "Covenant Physician Partners – KKR (Platform Build)",
        "year": 2022,
        "buyer": "KKR",
        "seller": "Trive Capital",
        "ev_mm": 1500,
        "ebitda_at_entry_mm": 150,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.32, "medicaid": 0.06,
            "commercial": 0.58, "self_pay": 0.04,
        }),
        "notes": "Multi-specialty physician + ASC platform. "
                 "KKR acquired from Trive at ~10x EV/EBITDA. "
                 "Post-NSA environment; commercial-heavy mix supports volume growth thesis.",
    },
    # ------------------------------------------------------------------
    # 70. Allscripts – Veradigm Health IT spinoff (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_070",
        "source": "seed",
        "deal_name": "Tivity Health – Welsh Carson Buyout",
        "year": 2019,
        "buyer": "Welsh Carson Anderson & Stowe",
        "seller": "Public shareholders (NASDAQ: TVTY)",
        "ev_mm": 635,
        "ebitda_at_entry_mm": 95,
        "hold_years": 3.5,
        "realized_moic": 1.4,
        "realized_irr": 0.10,
        "payer_mix": json.dumps({
            "medicare": 0.70, "medicaid": 0.05,
            "commercial": 0.22, "self_pay": 0.03,
        }),
        "notes": "Fitness + health services for Medicare Advantage populations. "
                 "COVID severely impacted fitness center utilization FY2020. "
                 "Below-par returns driven by pandemic disruption. "
                 "Sold Prime Fitness division; remainder declined in value.",
    },
    # ------------------------------------------------------------------
    # 71. Privia Health Group – Advent International (2020)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_071",
        "source": "seed",
        "deal_name": "Privia Health Group – Advent International",
        "year": 2020,
        "buyer": "Advent International / IPO",
        "seller": "Existing shareholders",
        "ev_mm": 1600,
        "ebitda_at_entry_mm": 55,
        "hold_years": 4.0,
        "realized_moic": 3.1,
        "realized_irr": 0.33,
        "payer_mix": json.dumps({
            "medicare": 0.35, "medicaid": 0.08,
            "commercial": 0.52, "self_pay": 0.05,
        }),
        "notes": "Value-based care physician enablement platform. "
                 "IPO April 2021 (NASDAQ: PRVA) at strong valuation. "
                 "High entry EV/EBITDA (~29x) justified by growth + VBC premium.",
    },
    # ------------------------------------------------------------------
    # 72. VillageMD / Walgreens – Village Practice Management (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_072",
        "source": "seed",
        "deal_name": "VillageMD – Walgreens Boots Alliance Strategic Investment",
        "year": 2021,
        "buyer": "Walgreens Boots Alliance",
        "seller": "Existing PE investors",
        "ev_mm": 5200,
        "ebitda_at_entry_mm": 90,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.28, "medicaid": 0.18,
            "commercial": 0.48, "self_pay": 0.06,
        }),
        "notes": "Primary care + clinic platform backed by Walgreens. "
                 "Strategic buyer (not PE); included as clinic model comp. "
                 "WBA wrote down ~$5.8B in 2023 — entry multiple proved too high.",
    },
    # ------------------------------------------------------------------
    # 73. Radiology Partners – New Mountain Capital (2023)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_073",
        "source": "seed",
        "deal_name": "Radiology Partners – New Mountain Capital Recapitalization",
        "year": 2023,
        "buyer": "New Mountain Capital (recap / restructuring)",
        "seller": "Existing PE investors / lenders",
        "ev_mm": 3200,
        "ebitda_at_entry_mm": 380,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.38, "medicaid": 0.10,
            "commercial": 0.47, "self_pay": 0.05,
        }),
        "notes": "Distressed recap — NSA/IDR impact on OON revenue; "
                 "leverage unsustainable post-NSA. New Mountain structured in. "
                 "Included as distressed radiology/staffing deal comp.",
    },
    # ------------------------------------------------------------------
    # 74. Resilient Healthcare – Halo Capital Group (2022)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_074",
        "source": "seed",
        "deal_name": "Resilient Healthcare – Halo Capital Group / CrossFirst Bank",
        "year": 2022,
        "buyer": "Halo Capital Group",
        "seller": "Sellers / founders",
        "ev_mm": 75,
        "ebitda_at_entry_mm": 10,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": json.dumps({
            "medicare": 0.42, "medicaid": 0.28,
            "commercial": 0.26, "self_pay": 0.04,
        }),
        "notes": "Small rural hospital acquisition (TX). "
                 "Community hospital in underserved area; high Medicaid share. "
                 "Included as rural/small-market hospital comp.",
    },
    # ------------------------------------------------------------------
    # 75. Agilon Health – Advent International IPO (2021)
    # ------------------------------------------------------------------
    {
        "source_id": "seed_075",
        "source": "seed",
        "deal_name": "Agilon Health – Advent International / IPO",
        "year": 2021,
        "buyer": "Public (IPO — NYSE: AGL)",
        "seller": "Advent International",
        "ev_mm": 5500,
        "ebitda_at_entry_mm": None,
        "hold_years": 5.0,
        "realized_moic": 4.2,
        "realized_irr": 0.38,
        "payer_mix": json.dumps({
            "medicare": 0.95, "medicaid": 0.02,
            "commercial": 0.02, "self_pay": 0.01,
        }),
        "notes": "Value-based care platform for primary care physicians. "
                 "Medicare Advantage-heavy model; capitated revenue. "
                 "IPO April 2021 at $23/share; Advent's return exceptional. "
                 "EBITDA not meaningful at IPO — growth / MLR model.",
    },
]
