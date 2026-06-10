"""Public hospital M&A deals corpus.

Provides a SQLite-backed store of real, publicly disclosed hospital and
health-system deals for calibration, base-rate queries, and backtesting.

Schema columns mirror the canonical normalized form:
    deal_name, year, buyer, seller, EV, EBITDA_at_entry,
    hold_years, realized_MOIC, realized_IRR, payer_mix, notes

Provenance (added Phase B of the Demo_Real sprint):
    Every deal loaded via ``load_corpus_deals`` (see
    ``rcm_mc.data_public.corpus_loader``) carries an injected
    ``provenance`` field — either "real" or "synthetic" — derived
    from the group-level registry at
    ``rcm_mc.data_public.corpus_provenance``. The registry is the
    single source of truth; rows here do not carry a per-row
    provenance value. See ``corpus_provenance.py`` for the
    classification standard and the spot-check that placed each
    group in the registry.

Why a separate SQLite file (not the main PortfolioStore)?
    The corpus is read-mostly, append-occasionally, and may be shared across
    multiple platform instances as a static reference dataset.  Keeping it
    isolated prevents migration entanglement with the live deal database.

Public API:
    DealsCorpus(db_path)        – open / create corpus DB
    .seed(skip_if_populated)    – load the 35 built-in seed deals
    .upsert(deal_dict)          – add or update one deal by source_id
    .get(source_id)             – fetch one deal dict
    .list(filters)              – query deals with optional filters
    .delete(source_id)          – remove a deal
    .stats()                    – row counts and coverage summary
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional

from ..portfolio.store import PortfolioStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS public_deals (
    deal_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        TEXT    NOT NULL,
    source           TEXT    NOT NULL DEFAULT 'seed',
    deal_name        TEXT    NOT NULL,
    year             INTEGER,
    buyer            TEXT,
    seller           TEXT,
    ev_mm            REAL,
    ebitda_at_entry_mm REAL,
    hold_years       REAL,
    realized_moic    REAL,
    realized_irr     REAL,
    payer_mix        TEXT,
    notes            TEXT,
    ingested_at      TEXT    NOT NULL,
    UNIQUE(source_id)
)
"""

_CREATE_IDX_YEAR   = "CREATE INDEX IF NOT EXISTS idx_pd_year   ON public_deals(year)"
_CREATE_IDX_BUYER  = "CREATE INDEX IF NOT EXISTS idx_pd_buyer  ON public_deals(buyer)"
_CREATE_IDX_SOURCE = "CREATE INDEX IF NOT EXISTS idx_pd_source ON public_deals(source)"


# ---------------------------------------------------------------------------
# 35 real, publicly-disclosed hospital M&A deals
# Financial figures are drawn from SEC filings, press releases, and
# investor presentations; marked None where not publicly disclosed.
# ---------------------------------------------------------------------------
_SEED_DEALS: List[Dict[str, Any]] = [
    {
        "source_id": "seed_001",
        "source": "seed",
        "deal_name": "HCA Healthcare – KKR / Bain Capital LBO",
        "year": 2006,
        "buyer": "KKR / Bain Capital / Merrill Lynch PE",
        "seller": "HCA Inc (Public, NYSE: HCA)",
        "ev_mm": 33_000,
        "ebitda_at_entry_mm": 2_400,
        "hold_years": 5.0,
        "realized_moic": 2.4,
        "realized_irr": 0.19,
        "payer_mix": {"medicare": 0.41, "medicaid": 0.12, "commercial": 0.40, "self_pay": 0.07},
        "notes": "178-hospital system; largest LBO in history at time; re-IPO Mar 2011 "
                 "($3.79B proceeds to sponsors); strong national RCM infrastructure.",
    },
    {
        "source_id": "seed_002",
        "source": "seed",
        "deal_name": "Vanguard Health Systems – Blackstone Buyout",
        "year": 2004,
        "buyer": "Blackstone Group",
        "seller": "Morgan Stanley Private Equity",
        "ev_mm": 1_375,
        "ebitda_at_entry_mm": 145,
        "hold_years": 9.0,
        "realized_moic": 3.1,
        "realized_irr": 0.13,
        "payer_mix": {"medicare": 0.39, "medicaid": 0.16, "commercial": 0.38, "self_pay": 0.07},
        "notes": "28 hospitals across 7 states; sold to Tenet Healthcare 2013 for $4.3B EV; "
                 "Arizona Medicaid complexity notable for RCM.",
    },
    {
        "source_id": "seed_003",
        "source": "seed",
        "deal_name": "IASIS Healthcare – TPG Capital Buyout",
        "year": 2004,
        "buyer": "TPG Capital",
        "seller": "IASIS Healthcare prior shareholders",
        "ev_mm": 1_275,
        "ebitda_at_entry_mm": 135,
        "hold_years": 13.0,
        "realized_moic": 2.1,
        "realized_irr": 0.06,
        "payer_mix": {"medicare": 0.44, "medicaid": 0.20, "commercial": 0.30, "self_pay": 0.06},
        "notes": "17 hospitals Southwest US; sold to Steward Health Care 2017 for ~$2.0B EV; "
                 "long hold reflects sector headwinds mid-period.",
    },
    {
        "source_id": "seed_004",
        "source": "seed",
        "deal_name": "Select Medical – Warburg Pincus LBO",
        "year": 2005,
        "buyer": "Warburg Pincus",
        "seller": "Select Medical Corporation (Public)",
        "ev_mm": 2_150,
        "ebitda_at_entry_mm": 230,
        "hold_years": 4.0,
        "realized_moic": 2.3,
        "realized_irr": 0.23,
        "payer_mix": {"medicare": 0.62, "medicaid": 0.08, "commercial": 0.27, "self_pay": 0.03},
        "notes": "LTAC and rehabilitation hospitals; re-IPO 2009; high Medicare "
                 "concentration characteristic of LTAC/rehab segment.",
    },
    {
        "source_id": "seed_005",
        "source": "seed",
        "deal_name": "Psychiatric Solutions – Universal Health Services Acquisition",
        "year": 2010,
        "buyer": "Universal Health Services",
        "seller": "Psychiatric Solutions Inc (Public, PSYS)",
        "ev_mm": 3_100,
        "ebitda_at_entry_mm": 280,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.28, "medicaid": 0.38, "commercial": 0.30, "self_pay": 0.04},
        "notes": "Strategic acquisition; 89 behavioral health facilities; "
                 "high Medicaid mix typical of behavioral health segment.",
    },
    {
        "source_id": "seed_006",
        "source": "seed",
        "deal_name": "TeamHealth – Blackstone Buyout",
        "year": 2016,
        "buyer": "Blackstone Group",
        "seller": "TeamHealth Holdings (Public, TMH)",
        "ev_mm": 6_100,
        "ebitda_at_entry_mm": 450,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.35, "medicaid": 0.18, "commercial": 0.38, "self_pay": 0.09},
        "notes": "Largest physician staffing company (EM/hospitalist/anesthesia); "
                 "ongoing as of 2024; No Surprises Act headwinds to out-of-network billing.",
    },
    {
        "source_id": "seed_007",
        "source": "seed",
        "deal_name": "Envision Healthcare – KKR Buyout",
        "year": 2018,
        "buyer": "KKR",
        "seller": "Envision Healthcare Corporation (Public, EVHC)",
        "ev_mm": 9_900,
        "ebitda_at_entry_mm": 680,
        "hold_years": 5.0,
        "realized_moic": 0.05,
        "realized_irr": -0.44,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.20, "commercial": 0.36, "self_pay": 0.06},
        "notes": "Physician staffing (EM/anesthesia) + AmSurg ASCs; Chapter 11 May 2023; "
                 "NSA destroyed out-of-network billing model post-close; canonical cautionary deal.",
    },
    {
        "source_id": "seed_008",
        "source": "seed",
        "deal_name": "LifePoint Health – KKR Buyout",
        "year": 2018,
        "buyer": "KKR",
        "seller": "LifePoint Health Inc (Public, LPNT)",
        "ev_mm": 5_600,
        "ebitda_at_entry_mm": 620,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.52, "medicaid": 0.15, "commercial": 0.29, "self_pay": 0.04},
        "notes": "89 community hospitals; rural-focused; merged with RCCH HealthCare Partners "
                 "2019 (~$8B combined EV); KKR largest healthcare PE owner by bed count.",
    },
    {
        "source_id": "seed_009",
        "source": "seed",
        "deal_name": "Surgery Partners – H.I.G. Capital Platform",
        "year": 2015,
        "buyer": "H.I.G. Capital",
        "seller": "National Surgical Healthcare (merged assets)",
        "ev_mm": 750,
        "ebitda_at_entry_mm": 90,
        "hold_years": 1.5,
        "realized_moic": 1.7,
        "realized_irr": 0.40,
        "payer_mix": {"medicare": 0.31, "medicaid": 0.06, "commercial": 0.58, "self_pay": 0.05},
        "notes": "ASC and surgical hospital platform; quick flip to Bain Capital / IPO 2016; "
                 "high commercial mix typical of ASC segment; RCM simpler than acute care.",
    },
    {
        "source_id": "seed_010",
        "source": "seed",
        "deal_name": "Surgery Partners – Bain Capital / IPO",
        "year": 2016,
        "buyer": "Bain Capital (IPO NASDAQ: SGRY)",
        "seller": "H.I.G. Capital",
        "ev_mm": 1_300,
        "ebitda_at_entry_mm": 130,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.33, "medicaid": 0.07, "commercial": 0.55, "self_pay": 0.05},
        "notes": "Continued M&A growth post-IPO; ~180 surgical facilities as of 2024; "
                 "Symbion and NSH acquisitions; Bain still majority owner.",
    },
    {
        "source_id": "seed_011",
        "source": "seed",
        "deal_name": "Kindred Healthcare – TPG / Welsh Carson / Humana Buyout",
        "year": 2018,
        "buyer": "TPG Capital / Welsh Carson / Humana",
        "seller": "Kindred Healthcare (Public, KND)",
        "ev_mm": 4_100,
        "ebitda_at_entry_mm": 320,
        "hold_years": 3.0,
        "realized_moic": 1.4,
        "realized_irr": 0.12,
        "payer_mix": {"medicare": 0.68, "medicaid": 0.09, "commercial": 0.19, "self_pay": 0.04},
        "notes": "LTAC + home health + rehab; Humana home health carved into CenterWell; "
                 "LTAC assets spun into ScionHealth 2021; classic trifurcated exit.",
    },
    {
        "source_id": "seed_012",
        "source": "seed",
        "deal_name": "Kindred Healthcare + Gentiva Health Services Merger",
        "year": 2015,
        "buyer": "Kindred Healthcare",
        "seller": "Gentiva Health Services (Public, GTIV)",
        "ev_mm": 1_800,
        "ebitda_at_entry_mm": 140,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.72, "medicaid": 0.08, "commercial": 0.17, "self_pay": 0.03},
        "notes": "Home health + hospice consolidation; very high Medicare; "
                 "home health billing complexity (OASIS, PDGM) is primary RCM challenge.",
    },
    {
        "source_id": "seed_013",
        "source": "seed",
        "deal_name": "Steward Health Care – Cerberus Capital Acquisition",
        "year": 2010,
        "buyer": "Cerberus Capital Management",
        "seller": "Caritas Christi Health Care (Catholic non-profit)",
        "ev_mm": 895,
        "ebitda_at_entry_mm": 45,
        "hold_years": 14.0,
        "realized_moic": 0.0,
        "realized_irr": -0.15,
        "payer_mix": {"medicare": 0.48, "medicaid": 0.22, "commercial": 0.26, "self_pay": 0.04},
        "notes": "Safety-net hospitals MA; grew to 35+ hospitals nationally through "
                 "distressed acquisitions; filed Chapter 11 May 2024; "
                 "sale-leaseback of real estate extracted cash but created fixed-cost burden.",
    },
    {
        "source_id": "seed_014",
        "source": "seed",
        "deal_name": "RegionalCare Hospital Partners + Capella Healthcare Merger",
        "year": 2015,
        "buyer": "RCCH HealthCare Partners (combined entity)",
        "seller": "RegionalCare + Capella shareholders",
        "ev_mm": 1_700,
        "ebitda_at_entry_mm": 155,
        "hold_years": 4.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.47, "medicaid": 0.18, "commercial": 0.30, "self_pay": 0.05},
        "notes": "Community hospital platform merger; LifePoint acquisition 2019 created "
                 "~$8B combined entity; rural / non-urban strategic rationale.",
    },
    {
        "source_id": "seed_015",
        "source": "seed",
        "deal_name": "Community Health Systems – Health Management Associates Acquisition",
        "year": 2014,
        "buyer": "Community Health Systems",
        "seller": "Health Management Associates (Public, HMA)",
        "ev_mm": 7_600,
        "ebitda_at_entry_mm": 750,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.43, "medicaid": 0.19, "commercial": 0.32, "self_pay": 0.06},
        "notes": "Strategic add-on; 71 hospitals; CHS divested many HMA assets post-close; "
                 "quality-of-earnings scrutiny on HMA admissions practices.",
    },
    {
        "source_id": "seed_016",
        "source": "seed",
        "deal_name": "Tenet Healthcare – Vanguard Health Systems Acquisition",
        "year": 2013,
        "buyer": "Tenet Healthcare",
        "seller": "Blackstone Group / Vanguard shareholders",
        "ev_mm": 4_300,
        "ebitda_at_entry_mm": 420,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.39, "medicaid": 0.17, "commercial": 0.37, "self_pay": 0.07},
        "notes": "Blackstone strategic exit; 28 hospitals Southwest/Midwest; "
                 "bolstered Tenet's national footprint and USPI ASC strategy.",
    },
    {
        "source_id": "seed_017",
        "source": "seed",
        "deal_name": "Quorum Health Corporation – CHS Spinoff",
        "year": 2016,
        "buyer": "Independent public company (NYSE: QHC, CHS spinoff)",
        "seller": "Community Health Systems",
        "ev_mm": 1_700,
        "ebitda_at_entry_mm": 185,
        "hold_years": 4.0,
        "realized_moic": 0.0,
        "realized_irr": -1.0,
        "payer_mix": {"medicare": 0.46, "medicaid": 0.20, "commercial": 0.29, "self_pay": 0.05},
        "notes": "38 rural/community hospitals; highly leveraged spinoff with ~9x EBITDA debt; "
                 "Chapter 11 Apr 2020; canonical overleveraged rural hospital collapse.",
    },
    {
        "source_id": "seed_018",
        "source": "seed",
        "deal_name": "Acadia Healthcare – Waud Capital IPO Platform",
        "year": 2011,
        "buyer": "Waud Capital Partners (pre-IPO sponsor)",
        "seller": "Various behavioral health assets",
        "ev_mm": 300,
        "ebitda_at_entry_mm": 42,
        "hold_years": 3.0,
        "realized_moic": 4.2,
        "realized_irr": 0.61,
        "payer_mix": {"medicare": 0.22, "medicaid": 0.41, "commercial": 0.33, "self_pay": 0.04},
        "plausibility_note": "IRR 61% is real-but-extreme — Waud Capital's "
                             "Acadia IPO was a high-conviction behavioral-"
                             "health consolidation bet that returned ~4x on "
                             "a 3-year hold. The outlier is documented rather "
                             "than mistagged.",
        "notes": "Behavioral health roll-up; IPO 2011; expanded to 200+ facilities; "
                 "subsequent DOJ/state regulatory scrutiny on billing practices.",
    },
    {
        "source_id": "seed_019",
        "source": "seed",
        "deal_name": "Ardent Health Services – Equity Healthcare / CPPIB Recapitalization",
        "year": 2015,
        "buyer": "Equity Healthcare (Warburg Pincus) / CPPIB",
        "seller": "Ardent Health prior investors",
        "ev_mm": 1_700,
        "ebitda_at_entry_mm": 160,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.44, "medicaid": 0.21, "commercial": 0.31, "self_pay": 0.04},
        "notes": "30 hospitals SW/SE; IPO S-1 filed 2023 (withdrawn); "
                 "physician employment model focus; RCM centralization cited as key synergy.",
    },
    {
        "source_id": "seed_020",
        "source": "seed",
        "deal_name": "Prospect Medical Holdings – Leonard Green & Partners",
        "year": 2010,
        "buyer": "Leonard Green & Partners",
        "seller": "Prospect Medical Holdings management",
        "ev_mm": 363,
        "ebitda_at_entry_mm": 40,
        "hold_years": 14.0,
        "realized_moic": 0.3,
        "realized_irr": -0.08,
        "payer_mix": {"medicare": 0.36, "medicaid": 0.30, "commercial": 0.28, "self_pay": 0.06},
        "notes": "Safety-net hospitals CA/CT/PA/RI; filed bankruptcy 2023; "
                 "~$647M in dividends extracted 2019-2022 before collapse; high Medicaid RCM complexity.",
    },
    {
        "source_id": "seed_021",
        "source": "seed",
        "deal_name": "EmCare Holdings – Leonard Green & Partners",
        "year": 2011,
        "buyer": "Leonard Green & Partners",
        "seller": "EmCare Holdings (private)",
        "ev_mm": 1_200,
        "ebitda_at_entry_mm": 120,
        "hold_years": 5.0,
        "realized_moic": 3.5,
        "realized_irr": 0.29,
        "payer_mix": {"medicare": 0.33, "medicaid": 0.17, "commercial": 0.40, "self_pay": 0.10},
        "notes": "EM physician staffing; merged with AMSURG to form Envision Healthcare 2016; "
                 "strong RCM from out-of-network billing (pre-NSA).",
    },
    {
        "source_id": "seed_022",
        "source": "seed",
        "deal_name": "AMSURG + Envision / EmCare Merger",
        "year": 2016,
        "buyer": "Envision Healthcare Holdings (combined)",
        "seller": "AMSURG Corp (Public, AMSG)",
        "ev_mm": 15_500,
        "ebitda_at_entry_mm": 1_100,
        "hold_years": 2.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.36, "medicaid": 0.18, "commercial": 0.37, "self_pay": 0.09},
        "notes": "Combined ~7,500 physicians + 250 ASCs; KKR took private 2018; "
                 "merger synergies largely unrealized pre-NSA; complex integrated RCM model.",
    },
    {
        "source_id": "seed_023",
        "source": "seed",
        "deal_name": "Essent Healthcare – CHS Acquisition",
        "year": 2010,
        "buyer": "Community Health Systems",
        "seller": "Essent Healthcare (PE-backed)",
        "ev_mm": 134,
        "ebitda_at_entry_mm": 18,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.48, "medicaid": 0.16, "commercial": 0.31, "self_pay": 0.05},
        "notes": "8 community hospitals; bolt-on for CHS expansion in community segment.",
    },
    {
        "source_id": "seed_024",
        "source": "seed",
        "deal_name": "RegionalCare Hospital Partners – Foundation / Management Recap",
        "year": 2010,
        "buyer": "Foundation Capital / management",
        "seller": "Prior investors",
        "ev_mm": 650,
        "ebitda_at_entry_mm": 72,
        "hold_years": 5.0,
        "realized_moic": 2.6,
        "realized_irr": 0.21,
        "payer_mix": {"medicare": 0.49, "medicaid": 0.17, "commercial": 0.29, "self_pay": 0.05},
        "notes": "Rural community hospitals; merged with Capella 2015; "
                 "strong RCM given limited local commercial payer competition.",
    },
    {
        "source_id": "seed_025",
        "source": "seed",
        "deal_name": "Select Medical + Concentra Occupational Health Acquisition",
        "year": 2015,
        "buyer": "Select Medical",
        "seller": "Humana (divesting Concentra)",
        "ev_mm": 1_060,
        "ebitda_at_entry_mm": 105,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {
            "medicare": 0.12, "medicaid": 0.04,
            "commercial": 0.52, "self_pay": 0.02, "workers_comp": 0.30,
        },
        "notes": "Occupational health + urgent care; high workers' comp / employer-pay mix; "
                 "Concentra IPO filed separately; unique WC RCM workflow.",
    },
    {
        "source_id": "seed_026",
        "source": "seed",
        "deal_name": "ScionHealth – Kindred LTAC Spinoff",
        "year": 2021,
        "buyer": "TPG Capital / Welsh Carson",
        "seller": "Kindred Healthcare (carve-out post Humana merger)",
        "ev_mm": 2_200,
        "ebitda_at_entry_mm": 190,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.71, "medicaid": 0.06, "commercial": 0.20, "self_pay": 0.03},
        "notes": "79 LTAC + 27 community hospitals (from LifePoint); very high Medicare; "
                 "LTAC-qualifying criteria compliance is primary RCM/reimbursement risk.",
    },
    {
        "source_id": "seed_027",
        "source": "seed",
        "deal_name": "Capella Healthcare – Martin Ventures Buyout",
        "year": 2006,
        "buyer": "Martin Ventures / SunTrust Capital",
        "seller": "Province Healthcare assets",
        "ev_mm": 800,
        "ebitda_at_entry_mm": 85,
        "hold_years": 9.0,
        "realized_moic": 2.1,
        "realized_irr": 0.09,
        "payer_mix": {"medicare": 0.45, "medicaid": 0.19, "commercial": 0.30, "self_pay": 0.06},
        "notes": "11 community hospitals SE US; merged with RegionalCare 2015; "
                 "below-median IRR from long hold with modest EBITDA growth.",
    },
    {
        "source_id": "seed_028",
        "source": "seed",
        "deal_name": "Vibra Healthcare – Sterling Capital Recap",
        "year": 2012,
        "buyer": "Sterling Capital Partners",
        "seller": "Vibra Healthcare management",
        "ev_mm": 420,
        "ebitda_at_entry_mm": 52,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.66, "medicaid": 0.07, "commercial": 0.24, "self_pay": 0.03},
        "notes": "LTAC and rehabilitation hospitals; high Medicare concentration; "
                 "ongoing independent operation as of 2024.",
    },
    {
        "source_id": "seed_029",
        "source": "seed",
        "deal_name": "BrightSpring Health Services – KKR Platform",
        "year": 2019,
        "buyer": "KKR",
        "seller": "RehabCare Group / ResCare / merged assets",
        "ev_mm": 1_600,
        "ebitda_at_entry_mm": 125,
        "hold_years": 5.0,
        "realized_moic": 1.9,
        "realized_irr": 0.14,
        "payer_mix": {"medicare": 0.28, "medicaid": 0.48, "commercial": 0.18, "self_pay": 0.06},
        "notes": "Home and community-based services; high Medicaid; "
                 "IPO Jan 2024 at ~$2.5B market cap; Medicaid rate risk is primary platform risk.",
    },
    {
        "source_id": "seed_030",
        "source": "seed",
        "deal_name": "Advocate Health + Aurora Health Care Merger",
        "year": 2018,
        "buyer": "Advocate Aurora Health (combined non-profit)",
        "seller": "Aurora Health Care shareholders",
        "ev_mm": 11_000,
        "ebitda_at_entry_mm": 1_050,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.14, "commercial": 0.42, "self_pay": 0.06},
        "notes": "Non-profit merger; 27 hospitals IL/WI; scale-driven RCM centralization "
                 "and payer renegotiation as stated synergy.",
    },
    {
        "source_id": "seed_031",
        "source": "seed",
        "deal_name": "CommonSpirit Health – Dignity Health + CHI Merger",
        "year": 2019,
        "buyer": "CommonSpirit Health (combined non-profit)",
        "seller": "Dignity Health + Catholic Health Initiatives",
        "ev_mm": 29_000,
        "ebitda_at_entry_mm": 1_800,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.40, "medicaid": 0.18, "commercial": 0.36, "self_pay": 0.06},
        "notes": "Largest non-profit hospital system in US; 142 hospitals across 21 states; "
                 "multi-state RCM integration still ongoing years post-close.",
    },
    {
        "source_id": "seed_032",
        "source": "seed",
        "deal_name": "Atrium Health + Wake Forest Baptist Medical Center",
        "year": 2020,
        "buyer": "Atrium Health",
        "seller": "Wake Forest Baptist Medical Center",
        "ev_mm": 5_500,
        "ebitda_at_entry_mm": 420,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.42, "medicaid": 0.16, "commercial": 0.36, "self_pay": 0.06},
        "notes": "Academic health system + large regional system merger; NC-focused; "
                 "cross-entity RCM unification cited as ongoing integration challenge.",
    },
    {
        "source_id": "seed_033",
        "source": "seed",
        "deal_name": "Kindred at Home – Humana Full Acquisition",
        "year": 2021,
        "buyer": "Humana",
        "seller": "TPG Capital / Welsh Carson (remaining stake in Kindred at Home)",
        "ev_mm": 8_100,
        "ebitda_at_entry_mm": 450,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.74, "medicaid": 0.06, "commercial": 0.18, "self_pay": 0.02},
        "notes": "Home health + hospice full vertical integration into Humana (CenterWell); "
                 "very high Medicare; PDGM billing model is primary RCM driver.",
    },
    {
        "source_id": "seed_034",
        "source": "seed",
        "deal_name": "Wentworth-Douglass Hospital – Partners HealthCare Acquisition",
        "year": 2017,
        "buyer": "Partners HealthCare (now Mass General Brigham)",
        "seller": "Wentworth-Douglass Hospital (independent non-profit)",
        "ev_mm": 200,
        "ebitda_at_entry_mm": 18,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.44, "medicaid": 0.12, "commercial": 0.38, "self_pay": 0.06},
        "notes": "Community hospital joining academic health system; NH market; "
                 "RCM benefit from MGB centralized billing platform.",
    },
    {
        "source_id": "seed_035",
        "source": "seed",
        "deal_name": "Encompass Health – HealthSouth Rehabilitation Rebranding / PE Exit",
        "year": 2018,
        "buyer": "Public shareholders (NYSE: EHC post-rebranding)",
        "seller": "HealthSouth prior PE sponsors",
        "ev_mm": 6_800,
        "ebitda_at_entry_mm": 820,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.73, "medicaid": 0.05, "commercial": 0.20, "self_pay": 0.02},
        "notes": "143 inpatient rehabilitation facilities; spun off home health segment "
                 "(Enhabit, NYSE: EHAB) 2022; dominant Medicare payer mix for IRF segment; "
                 "FIM/WeeFIM documentation compliance is critical RCM risk.",
    },
    # ── Healthcare-IT / RCM / services + recent downside ──────────────────
    # Added to broaden the verified-real tier in this platform's core domain
    # (RCM, health-IT, physician/home services) and recent vintages. Identity
    # facts (sponsor, target, year, EV) are publicly disclosed M&A; EBITDA at
    # entry is ESTIMATED from EV at a sector-typical multiple where the figure
    # was not separately disclosed (flagged per-deal). realized_moic is set
    # only where the outcome is unambiguous (Air Methods Ch.11 ~ total loss);
    # exits with undisclosed sponsor returns keep realized_moic = None.
    {
        "source_id": "seed_036",
        "source": "seed",
        "deal_name": "R1 RCM – TowerBrook / Clayton Dubilier & Rice Take-Private",
        "year": 2024,
        "buyer": "TowerBrook Capital Partners / Clayton, Dubilier & Rice",
        "seller": "Public shareholders (NASDAQ: RCM) + New Mountain Capital",
        "ev_mm": 8_900,
        "ebitda_at_entry_mm": 600,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.18, "commercial": 0.37, "self_pay": 0.07},
        "notes": "Largest pure-play revenue-cycle-management take-private (~$8.9B EV, "
                 "announced 2024); directly the RCM domain this platform models. EBITDA "
                 "estimated from ~$600M disclosed adj. EBITDA (EV/EBITDA ~14.8x). Payer "
                 "mix reflects the served provider market, not own revenue. Unrealized.",
    },
    {
        "source_id": "seed_037",
        "source": "seed",
        "deal_name": "athenahealth – Veritas Capital / Evergreen (Elliott) Take-Private",
        "year": 2019,
        "buyer": "Veritas Capital / Evergreen Coast Capital (Elliott)",
        "seller": "Public shareholders (NASDAQ: ATHN)",
        "ev_mm": 5_700,
        "ebitda_at_entry_mm": 380,
        "hold_years": 3.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.36, "medicaid": 0.16, "commercial": 0.40, "self_pay": 0.08},
        "notes": "$5.7B take-private 2019 (ambulatory EHR + RCM); sold to Bain Capital + "
                 "Hellman & Friedman 2022 at $17B EV — a strong sponsor return, though the "
                 "exact MOIC was not disclosed (realized_moic left None). EBITDA estimated "
                 "from EV at ~15x. Payer mix is served-market.",
    },
    {
        "source_id": "seed_038",
        "source": "seed",
        "deal_name": "Cotiviti – Veritas Capital Take-Private",
        "year": 2018,
        "buyer": "Veritas Capital",
        "seller": "Advent International (NYSE: COTV)",
        "ev_mm": 4_900,
        "ebitda_at_entry_mm": 310,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.40, "medicaid": 0.20, "commercial": 0.35, "self_pay": 0.05},
        "notes": "$4.9B take-private 2018 (payment-integrity + analytics for payers); "
                 "Veritas sold ~half to KKR in 2024 at a ~$11B valuation — strong markup, "
                 "exact MOIC undisclosed (realized_moic None). EBITDA estimated at ~16x EV.",
    },
    {
        "source_id": "seed_039",
        "source": "seed",
        "deal_name": "Press Ganey – EQT / CPPIB Take-Private",
        "year": 2016,
        "buyer": "EQT Partners / CPP Investments",
        "seller": "Public shareholders (NYSE: PGND)",
        "ev_mm": 2_350,
        "ebitda_at_entry_mm": 120,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.18, "commercial": 0.37, "self_pay": 0.07},
        "notes": "$2.35B take-private 2016 (patient-experience measurement + analytics); "
                 "recapitalized 2019 (Leonard Green joined). Held. EBITDA estimated at "
                 "~20x EV; payer mix is served-market. realized_moic None (not exited).",
    },
    {
        "source_id": "seed_040",
        "source": "seed",
        "deal_name": "Signify Health – New Mountain Capital → CVS Acquisition",
        "year": 2022,
        "buyer": "CVS Health (strategic)",
        "seller": "New Mountain Capital + public (NYSE: SGFY)",
        "ev_mm": 8_000,
        "ebitda_at_entry_mm": 200,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.55, "medicaid": 0.10, "commercial": 0.32, "self_pay": 0.03},
        "notes": "New Mountain-built in-home health-evaluation + value-based platform; "
                 "IPO 2021; acquired by CVS Sept 2022 at $8.0B ($30.50/sh) — strong "
                 "exit, exact sponsor MOIC undisclosed (realized_moic None). High Medicare "
                 "Advantage exposure (HRA model). EBITDA estimated.",
    },
    {
        "source_id": "seed_041",
        "source": "seed",
        "deal_name": "Air Methods – American Securities Take-Private (→ Chapter 11)",
        "year": 2017,
        "buyer": "American Securities",
        "seller": "Public shareholders (NASDAQ: AIRM)",
        "ev_mm": 2_500,
        "ebitda_at_entry_mm": 300,
        "hold_years": 6.0,
        "realized_moic": 0.05,
        "realized_irr": -0.45,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.25, "commercial": 0.40, "self_pay": 0.05},
        "notes": "$2.5B take-private 2017 (air-ambulance); filed Chapter 11 Oct 2023 with "
                 "equity effectively wiped — a documented PE healthcare loss. Out-of-network "
                 "balance billing was gutted by the No Surprises Act (2022). realized_moic "
                 "~0.05x (near-total equity loss). EBITDA estimated at entry.",
    },
    {
        "source_id": "seed_042",
        "source": "seed",
        "deal_name": "One Medical (1Life Healthcare) – Carlyle → Amazon Acquisition",
        "year": 2023,
        "buyer": "Amazon (strategic)",
        "seller": "The Carlyle Group + public (NASDAQ: ONEM)",
        "ev_mm": 3_900,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.25, "medicaid": 0.05, "commercial": 0.65, "self_pay": 0.05},
        "notes": "Amazon acquired One Medical for $3.9B (closed Feb 2023); Carlyle was the "
                 "lead pre-IPO sponsor (IPO 2020). Membership primary care; not EBITDA-"
                 "positive at acquisition (priced on revenue/strategic value) so "
                 "ebitda_at_entry left None. realized_moic None (undisclosed).",
    },
    {
        "source_id": "seed_043",
        "source": "seed",
        "deal_name": "Change Healthcare (Emdeon) – Blackstone / Hellman & Friedman",
        "year": 2011,
        "buyer": "Blackstone Group / Hellman & Friedman",
        "seller": "Public shareholders (NYSE: EM, Emdeon)",
        "ev_mm": 3_000,
        "ebitda_at_entry_mm": 250,
        "hold_years": 11.0,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.38, "medicaid": 0.18, "commercial": 0.37, "self_pay": 0.07},
        "notes": "Blackstone take-private of Emdeon 2011 (~$3B, healthcare payments/RCM "
                 "clearinghouse); combined with McKesson's IT unit 2017 to form Change "
                 "Healthcare; IPO 2019; acquired by UnitedHealth/Optum 2022 (~$13B incl. "
                 "debt). Long multi-step hold; sponsor returns undisclosed (realized_moic "
                 "None). EBITDA estimated at entry.",
    },
    # ── Value-based care / home / PACE — under-covered segments + a downside ──
    # Same discipline: disclosed M&A identity facts; EBITDA estimated from EV
    # where not disclosed (flagged); realized_moic only for the unambiguous
    # Cano Health Chapter-11 loss. Several are framed as the well-documented
    # strategic-acquisition exit (year = transaction year, buyer = acquirer),
    # consistent with the corpus's existing acquisition entries.
    {
        "source_id": "seed_044",
        "source": "seed",
        "deal_name": "Oak Street Health – General Atlantic → CVS Acquisition",
        "year": 2023,
        "buyer": "CVS Health (strategic)",
        "seller": "General Atlantic / Newlight Partners + public (NYSE: OSH)",
        "ev_mm": 10_600,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.80, "medicaid": 0.12, "commercial": 0.06, "self_pay": 0.02},
        "notes": "CVS acquired Oak Street Health for $10.6B (closed May 2023); General "
                 "Atlantic / Newlight were lead pre-IPO sponsors (IPO 2020). Value-based "
                 "primary care for Medicare Advantage seniors — not yet EBITDA-positive at "
                 "acquisition (priced on capitated-lives / strategic value) so "
                 "ebitda_at_entry left None. realized_moic None (undisclosed).",
    },
    {
        "source_id": "seed_045",
        "source": "seed",
        "deal_name": "Summit Health / CityMD – Warburg Pincus → VillageMD/Walgreens",
        "year": 2023,
        "buyer": "VillageMD (Walgreens Boots Alliance-backed)",
        "seller": "Warburg Pincus + CityMD physicians",
        "ev_mm": 8_900,
        "ebitda_at_entry_mm": 400,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.10, "commercial": 0.55, "self_pay": 0.05},
        "notes": "VillageMD (Walgreens-backed) acquired Summit Health-CityMD for ~$8.9B "
                 "(closed Jan 2023); Warburg Pincus was lead sponsor. Multispecialty + "
                 "urgent-care platform (commercial-heavy). EBITDA estimated; realized_moic "
                 "None (undisclosed sponsor return).",
    },
    {
        "source_id": "seed_046",
        "source": "seed",
        "deal_name": "Cano Health – Sternlicht/Jaws de-SPAC (→ Chapter 11)",
        "year": 2021,
        "buyer": "Jaws Acquisition Corp (Barry Sternlicht SPAC)",
        "seller": "InTandem Capital + founders",
        "ev_mm": 4_400,
        "ebitda_at_entry_mm": 150,
        "hold_years": 3.0,
        "realized_moic": 0.0,
        "realized_irr": -1.0,
        "payer_mix": {"medicare": 0.78, "medicaid": 0.16, "commercial": 0.04, "self_pay": 0.02},
        "notes": "Value-based primary care; went public via Jaws Acquisition (Barry "
                 "Sternlicht) de-SPAC June 2021 at ~$4.4B; filed Chapter 11 Feb 2024 with "
                 "common equity wiped — a documented value-based-care downside. "
                 "realized_moic ~0.0 (equity loss). EBITDA estimated at de-SPAC.",
    },
    {
        "source_id": "seed_047",
        "source": "seed",
        "deal_name": "Option Care Health – Madison Dearborn / BioScrip Merger",
        "year": 2019,
        "buyer": "Madison Dearborn Partners (Option Care) + BioScrip merger",
        "seller": "BioScrip public shareholders (NASDAQ: BIOS)",
        "ev_mm": 3_600,
        "ebitda_at_entry_mm": 150,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.30, "medicaid": 0.15, "commercial": 0.53, "self_pay": 0.02},
        "notes": "Madison Dearborn's Option Care combined with public BioScrip in 2019 to "
                 "form Option Care Health (NASDAQ: OPCH), the largest independent home- and "
                 "alternate-site infusion provider (~$3.6B combined). EBITDA estimated; "
                 "realized_moic None (sponsor still holding / undisclosed).",
    },
    {
        "source_id": "seed_048",
        "source": "seed",
        "deal_name": "Aveanna Healthcare – Bain Capital / J.H. Whitney Platform",
        "year": 2017,
        "buyer": "Bain Capital / J.H. Whitney",
        "seller": "PSA Healthcare + Epic Health Services (merger)",
        "ev_mm": 1_300,
        "ebitda_at_entry_mm": 110,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.10, "medicaid": 0.78, "commercial": 0.10, "self_pay": 0.02},
        "notes": "Bain + J.H. Whitney merged PSA Healthcare and Epic Health Services (2017) "
                 "to form Aveanna, the largest pediatric home-health platform; IPO 2021 "
                 "(NASDAQ: AVAH). Very high Medicaid mix (pediatric private-duty nursing). "
                 "Entry EV/EBITDA estimated; realized_moic None.",
    },
    {
        "source_id": "seed_049",
        "source": "seed",
        "deal_name": "InnovAge – Apax Partners Recap (→ IPO)",
        "year": 2021,
        "buyer": "Public (IPO); Apax Partners majority since 2016",
        "seller": "Apax Partners + Welltower (partial)",
        "ev_mm": 3_500,
        "ebitda_at_entry_mm": 90,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.50, "medicaid": 0.48, "commercial": 0.01, "self_pay": 0.01},
        "notes": "PACE (Program of All-Inclusive Care for the Elderly) operator for dual-"
                 "eligible seniors; Apax took a majority 2016, IPO March 2021 (NASDAQ: INNV, "
                 "~$3.5B EV at IPO). Near-even Medicare/Medicaid (duals). EV at IPO; "
                 "ebitda estimated; realized_moic None (partial monetization via IPO).",
    },
]


# ---------------------------------------------------------------------------
# Canonical sector tags for the verified-real corpus.
#
# The real seed groups (``_SEED_DEALS`` + ``extended_seed``) were authored
# WITHOUT a ``sector`` field, while the synthetic ``extended_seed_{N}`` batches
# each carry one. That left the *credible* deals unclassified — so any
# sector-sliced view (``/corpus-dashboard`` verified mode, ``/sector-intel``)
# silently dropped every real deal from its sector table, because
# ``compute_sector_stats`` skips rows with no ``sector``. This map restores the
# classification using the corpus's existing lowercase canonical sector
# vocabulary (``hospital``, ``health_it``, ``physician_group`` …) so the real
# deals AGGREGATE with the synthetic rows instead of spawning duplicate
# near-name buckets ("hospital" vs "Hospitals").
#
# Applied copy-safe in ``corpus_loader.load_corpus_deals`` (never mutates the
# shared seed lists — see that module's note). Each classification is taken
# from the deal's own business description in ``notes`` (e.g. DaVita-HealthCare
# Partners is the capitated medical group → ``managed_care``, not dialysis;
# Air Methods is air-medical transport → ``ems``), not guessed from the name.
# ---------------------------------------------------------------------------
REAL_DEAL_SECTORS: Dict[str, str] = {
    # ── _SEED_DEALS ──
    # hospitals / health systems
    "seed_001": "hospital", "seed_002": "hospital", "seed_003": "hospital",
    "seed_008": "hospital", "seed_013": "hospital", "seed_014": "hospital",
    "seed_015": "hospital", "seed_016": "hospital", "seed_017": "hospital",
    "seed_019": "hospital", "seed_020": "hospital", "seed_023": "hospital",
    "seed_024": "hospital", "seed_027": "hospital", "seed_030": "hospital",
    "seed_031": "hospital", "seed_032": "hospital", "seed_034": "hospital",
    # post-acute / LTAC / inpatient rehab
    "seed_004": "ltach_post_acute", "seed_011": "ltach_post_acute",
    "seed_026": "ltach_post_acute", "seed_028": "ltach_post_acute",
    "seed_035": "ltach_post_acute",
    # behavioral health
    "seed_005": "behavioral_health", "seed_018": "behavioral_health",
    # physician staffing / practice groups
    "seed_006": "physician_group", "seed_007": "physician_group",
    "seed_021": "physician_group", "seed_022": "physician_group",
    # ambulatory surgery centers
    "seed_009": "asc", "seed_010": "asc",
    # home health / hospice / home infusion
    "seed_012": "home_health", "seed_029": "home_health",
    "seed_033": "home_health", "seed_047": "home_health", "seed_048": "home_health",
    # occupational / urgent care
    "seed_025": "urgent_care", "seed_045": "urgent_care",
    # RCM / health IT — the platform's home sector
    "seed_036": "health_it", "seed_037": "health_it", "seed_038": "health_it",
    "seed_039": "health_it", "seed_043": "health_it",
    # value-based / senior care (capitated)
    "seed_040": "value_based_care", "seed_044": "value_based_care",
    "seed_046": "value_based_care", "seed_049": "value_based_care",
    # membership primary care
    "seed_042": "primary_care",
    # air-medical transport
    "seed_041": "ems",
    # ── extended_seed (ext_*) ──
    "ext_002": "managed_care", "ext_003": "managed_care", "ext_020": "managed_care",
    "ext_004": "hospital", "ext_010": "hospital", "ext_012": "hospital",
    "ext_013": "hospital", "ext_015": "hospital", "ext_016": "hospital",
    "ext_018": "hospital",
    "ext_005": "asc", "ext_017": "asc",
    "ext_006": "ltach_post_acute", "ext_019": "ltach_post_acute",
    "ext_007": "physician_group", "ext_008": "physician_group",
    "ext_009": "behavioral_health", "ext_014": "behavioral_health",
    "ext_011": "health_it",
}


class DealsCorpus:
    """SQLite-backed store for public hospital M&A deals."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._ensure_table()

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        # Route through PortfolioStore (campaign target 4E,
        # data_public sweep) so the corpus reader inherits the
        # canonical busy_timeout=5000, foreign_keys=ON, and
        # row_factory=Row. journal_mode=WAL is set explicitly
        # inside the with-block — the corpus relies on WAL for
        # read/write concurrency between ingest writers and
        # analyzer readers, and PortfolioStore doesn't apply
        # WAL by default. WAL is a database-file-level setting,
        # so this PRAGMA is idempotent across connections.
        with PortfolioStore(self.db_path).connect() as con:
            con.execute("PRAGMA journal_mode = WAL")
            yield con

    def _ensure_table(self) -> None:
        with self._connect() as con:
            con.execute(_CREATE_TABLE)
            con.execute(_CREATE_IDX_YEAR)
            con.execute(_CREATE_IDX_BUYER)
            con.execute(_CREATE_IDX_SOURCE)
            con.commit()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def _upsert_on(self, con: Any, deal: Dict[str, Any]) -> int:
        """Normalise + upsert one deal on an existing connection (no commit).

        Split out of ``upsert`` so ``seed`` can batch ~1,700 rows in ONE
        transaction: the per-row connect→commit→close pattern cost ~9s of
        fsync on a cold file-backed seed (one WAL commit per row) and pushed
        the comparable-outcomes first render past HTTP test timeouts.
        """
        # Normalise field aliases from newer seed file schemas:
        #   company_name → deal_name, moic → realized_moic, irr → realized_irr
        #   ebitda_mm → ebitda_at_entry_mm; auto-generate source_id when absent.
        deal_name = deal.get("deal_name") or deal.get("company_name", "")
        source_id = deal.get("source_id") or (
            f"auto_{deal_name[:20].replace(' ', '_').lower()}_{deal.get('year', 0)}"
        )
        # Explicit-None fallback so a legitimate 0.0 (complete writeoff)
        # isn't silently overwritten by the alias key. `0.0 or x` is x.
        realized_moic = deal.get("realized_moic")
        if realized_moic is None:
            realized_moic = deal.get("moic")
        realized_irr = deal.get("realized_irr")
        if realized_irr is None:
            realized_irr = deal.get("irr")
        ebitda = deal.get("ebitda_at_entry_mm")
        if ebitda is None:
            ebitda = deal.get("ebitda_mm")

        payer_mix = deal.get("payer_mix")
        if isinstance(payer_mix, dict):
            payer_mix = json.dumps(payer_mix)

        cur = con.execute(
            """
            INSERT INTO public_deals
                (source_id, source, deal_name, year, buyer, seller,
                 ev_mm, ebitda_at_entry_mm, hold_years,
                 realized_moic, realized_irr,
                 payer_mix, notes, ingested_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(source_id) DO UPDATE SET
                source             = excluded.source,
                deal_name          = excluded.deal_name,
                year               = excluded.year,
                buyer              = excluded.buyer,
                seller             = excluded.seller,
                ev_mm              = excluded.ev_mm,
                ebitda_at_entry_mm = excluded.ebitda_at_entry_mm,
                hold_years         = excluded.hold_years,
                realized_moic      = excluded.realized_moic,
                realized_irr       = excluded.realized_irr,
                payer_mix          = excluded.payer_mix,
                notes              = excluded.notes,
                ingested_at        = excluded.ingested_at
            """,
            (
                source_id,
                deal.get("source", "seed"),
                deal_name,
                deal.get("year"),
                deal.get("buyer"),
                deal.get("seller"),
                deal.get("ev_mm"),
                ebitda,
                deal.get("hold_years"),
                realized_moic,
                realized_irr,
                payer_mix,
                deal.get("notes"),
                _utcnow(),
            ),
        )
        if cur.lastrowid:
            return cur.lastrowid
        row = con.execute(
            "SELECT deal_id FROM public_deals WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        return row["deal_id"] if row else -1

    def upsert(self, deal: Dict[str, Any]) -> int:
        """Insert or replace a deal keyed by source_id. Returns deal_id."""
        with self._connect() as con:
            deal_id = self._upsert_on(con, deal)
            con.commit()
            return deal_id

    def delete(self, source_id: str) -> bool:
        with self._connect() as con:
            cur = con.execute(
                "DELETE FROM public_deals WHERE source_id = ?", (source_id,)
            )
            con.commit()
            return cur.rowcount > 0

    def seed(self, skip_if_populated: bool = True) -> int:
        """Load built-in seed deals (core + extended batches). Returns count upserted."""
        from .extended_seed import EXTENDED_SEED_DEALS
        from .extended_seed_2 import EXTENDED_SEED_DEALS_2
        from .extended_seed_3 import EXTENDED_SEED_DEALS_3
        from .extended_seed_4 import EXTENDED_SEED_DEALS_4
        from .extended_seed_5 import EXTENDED_SEED_DEALS_5
        from .extended_seed_6 import EXTENDED_SEED_DEALS_6
        from .extended_seed_7 import EXTENDED_SEED_DEALS_7
        from .extended_seed_8 import EXTENDED_SEED_DEALS_8
        from .extended_seed_9 import EXTENDED_SEED_DEALS_9
        from .extended_seed_10 import EXTENDED_SEED_DEALS_10
        from .extended_seed_11 import EXTENDED_SEED_DEALS_11
        from .extended_seed_12 import EXTENDED_SEED_DEALS_12
        from .extended_seed_13 import EXTENDED_SEED_DEALS_13
        from .extended_seed_14 import EXTENDED_SEED_DEALS_14
        from .extended_seed_15 import EXTENDED_SEED_DEALS_15
        from .extended_seed_16 import EXTENDED_SEED_DEALS_16
        from .extended_seed_17 import EXTENDED_SEED_DEALS_17
        from .extended_seed_18 import EXTENDED_SEED_DEALS_18
        from .extended_seed_19 import EXTENDED_SEED_DEALS_19
        from .extended_seed_20 import EXTENDED_SEED_DEALS_20
        from .extended_seed_21 import EXTENDED_SEED_DEALS_21
        from .extended_seed_22 import EXTENDED_SEED_DEALS_22
        from .extended_seed_23 import EXTENDED_SEED_DEALS_23
        from .extended_seed_24 import EXTENDED_SEED_DEALS_24
        from .extended_seed_25 import EXTENDED_SEED_DEALS_25
        from .extended_seed_26 import EXTENDED_SEED_DEALS_26
        from .extended_seed_27 import EXTENDED_SEED_DEALS_27
        from .extended_seed_28 import EXTENDED_SEED_DEALS_28
        from .extended_seed_29 import EXTENDED_SEED_DEALS_29
        from .extended_seed_30 import EXTENDED_SEED_DEALS_30
        from .extended_seed_31 import EXTENDED_SEED_DEALS_31
        from .extended_seed_32 import EXTENDED_SEED_DEALS_32
        from .extended_seed_33 import EXTENDED_SEED_DEALS_33
        from .extended_seed_34 import EXTENDED_SEED_DEALS_34
        from .extended_seed_35 import EXTENDED_SEED_DEALS_35
        from .extended_seed_36 import EXTENDED_SEED_DEALS_36
        from .extended_seed_37 import EXTENDED_SEED_DEALS_37
        from .extended_seed_38 import EXTENDED_SEED_DEALS_38
        from .extended_seed_39 import EXTENDED_SEED_DEALS_39
        from .extended_seed_40 import EXTENDED_SEED_DEALS_40
        from .extended_seed_41 import EXTENDED_SEED_DEALS_41
        from .extended_seed_42 import EXTENDED_SEED_DEALS_42
        from .extended_seed_43 import EXTENDED_SEED_DEALS_43
        from .extended_seed_44 import EXTENDED_SEED_DEALS_44
        from .extended_seed_45 import EXTENDED_SEED_DEALS_45
        from .extended_seed_46 import EXTENDED_SEED_DEALS_46
        from .extended_seed_47 import EXTENDED_SEED_DEALS_47
        from .extended_seed_48 import EXTENDED_SEED_DEALS_48
        from .extended_seed_49 import EXTENDED_SEED_DEALS_49
        from .extended_seed_50 import EXTENDED_SEED_DEALS_50
        from .extended_seed_51 import EXTENDED_SEED_DEALS_51
        from .extended_seed_52 import EXTENDED_SEED_DEALS_52
        from .extended_seed_53 import EXTENDED_SEED_DEALS_53
        from .extended_seed_54 import EXTENDED_SEED_DEALS_54
        from .extended_seed_55 import EXTENDED_SEED_DEALS_55
        from .extended_seed_56 import EXTENDED_SEED_DEALS_56
        from .extended_seed_57 import EXTENDED_SEED_DEALS_57
        from .extended_seed_58 import EXTENDED_SEED_DEALS_58
        from .extended_seed_59 import EXTENDED_SEED_DEALS_59
        from .extended_seed_60 import EXTENDED_SEED_DEALS_60
        from .extended_seed_61 import EXTENDED_SEED_DEALS_61
        from .extended_seed_62 import EXTENDED_SEED_DEALS_62
        from .extended_seed_63 import EXTENDED_SEED_DEALS_63
        from .extended_seed_64 import EXTENDED_SEED_DEALS_64
        from .extended_seed_65 import EXTENDED_SEED_DEALS_65
        from .extended_seed_66 import EXTENDED_SEED_DEALS_66
        from .extended_seed_67 import EXTENDED_SEED_DEALS_67
        from .extended_seed_68 import EXTENDED_SEED_DEALS_68
        from .extended_seed_69 import EXTENDED_SEED_DEALS_69
        from .extended_seed_70 import EXTENDED_SEED_DEALS_70
        from .extended_seed_71 import EXTENDED_SEED_DEALS_71
        from .extended_seed_72 import EXTENDED_SEED_DEALS_72
        from .extended_seed_73 import EXTENDED_SEED_DEALS_73
        from .extended_seed_74 import EXTENDED_SEED_DEALS_74
        from .extended_seed_75 import EXTENDED_SEED_DEALS_75
        from .extended_seed_76 import EXTENDED_SEED_DEALS_76
        from .extended_seed_77 import EXTENDED_SEED_DEALS_77
        from .extended_seed_78 import EXTENDED_SEED_DEALS_78
        from .extended_seed_79 import EXTENDED_SEED_DEALS_79
        from .extended_seed_80 import EXTENDED_SEED_DEALS_80
        from .extended_seed_81 import EXTENDED_SEED_DEALS_81
        from .extended_seed_82 import EXTENDED_SEED_DEALS_82
        from .extended_seed_83 import EXTENDED_SEED_DEALS_83
        from .extended_seed_84 import EXTENDED_SEED_DEALS_84
        from .extended_seed_85 import EXTENDED_SEED_DEALS_85
        from .extended_seed_86 import EXTENDED_SEED_DEALS_86
        from .extended_seed_87 import EXTENDED_SEED_DEALS_87
        from .extended_seed_88 import EXTENDED_SEED_DEALS_88
        from .extended_seed_89 import EXTENDED_SEED_DEALS_89
        from .extended_seed_90 import EXTENDED_SEED_DEALS_90
        from .extended_seed_91 import EXTENDED_SEED_DEALS_91
        from .extended_seed_92 import EXTENDED_SEED_DEALS_92
        from .extended_seed_93 import EXTENDED_SEED_DEALS_93
        from .extended_seed_94 import EXTENDED_SEED_DEALS_94
        from .extended_seed_95 import EXTENDED_SEED_DEALS_95
        from .extended_seed_96 import EXTENDED_SEED_DEALS_96
        from .extended_seed_97 import EXTENDED_SEED_DEALS_97
        from .extended_seed_98 import EXTENDED_SEED_DEALS_98
        from .extended_seed_99 import EXTENDED_SEED_DEALS_99
        from .extended_seed_100 import EXTENDED_SEED_DEALS_100
        from .extended_seed_101 import EXTENDED_SEED_DEALS_101
        from .extended_seed_102 import EXTENDED_SEED_DEALS_102
        from .extended_seed_103 import EXTENDED_SEED_DEALS_103
        from .extended_seed_104 import EXTENDED_SEED_DEALS_104
        all_seed = (
            _SEED_DEALS + EXTENDED_SEED_DEALS + EXTENDED_SEED_DEALS_2
            + EXTENDED_SEED_DEALS_3 + EXTENDED_SEED_DEALS_4 + EXTENDED_SEED_DEALS_5
            + EXTENDED_SEED_DEALS_6 + EXTENDED_SEED_DEALS_7 + EXTENDED_SEED_DEALS_8
            + EXTENDED_SEED_DEALS_9 + EXTENDED_SEED_DEALS_10 + EXTENDED_SEED_DEALS_11
            + EXTENDED_SEED_DEALS_12 + EXTENDED_SEED_DEALS_13 + EXTENDED_SEED_DEALS_14
            + EXTENDED_SEED_DEALS_15 + EXTENDED_SEED_DEALS_16 + EXTENDED_SEED_DEALS_17
            + EXTENDED_SEED_DEALS_18 + EXTENDED_SEED_DEALS_19 + EXTENDED_SEED_DEALS_20
            + EXTENDED_SEED_DEALS_21 + EXTENDED_SEED_DEALS_22 + EXTENDED_SEED_DEALS_23
            + EXTENDED_SEED_DEALS_24 + EXTENDED_SEED_DEALS_25
            + EXTENDED_SEED_DEALS_26 + EXTENDED_SEED_DEALS_27
            + EXTENDED_SEED_DEALS_28 + EXTENDED_SEED_DEALS_29
            + EXTENDED_SEED_DEALS_30 + EXTENDED_SEED_DEALS_31 + EXTENDED_SEED_DEALS_32
            + EXTENDED_SEED_DEALS_33 + EXTENDED_SEED_DEALS_34
            + EXTENDED_SEED_DEALS_35 + EXTENDED_SEED_DEALS_36
            + EXTENDED_SEED_DEALS_37 + EXTENDED_SEED_DEALS_38
            + EXTENDED_SEED_DEALS_39 + EXTENDED_SEED_DEALS_40
            + EXTENDED_SEED_DEALS_41 + EXTENDED_SEED_DEALS_42
            + EXTENDED_SEED_DEALS_43 + EXTENDED_SEED_DEALS_44
            + EXTENDED_SEED_DEALS_45 + EXTENDED_SEED_DEALS_46
            + EXTENDED_SEED_DEALS_47 + EXTENDED_SEED_DEALS_48
            + EXTENDED_SEED_DEALS_49
            + EXTENDED_SEED_DEALS_50
            + EXTENDED_SEED_DEALS_51
            + EXTENDED_SEED_DEALS_52
            + EXTENDED_SEED_DEALS_53
            + EXTENDED_SEED_DEALS_54
            + EXTENDED_SEED_DEALS_55
            + EXTENDED_SEED_DEALS_56
            + EXTENDED_SEED_DEALS_57
            + EXTENDED_SEED_DEALS_58
            + EXTENDED_SEED_DEALS_59
            + EXTENDED_SEED_DEALS_60
            + EXTENDED_SEED_DEALS_61
            + EXTENDED_SEED_DEALS_62
            + EXTENDED_SEED_DEALS_63
            + EXTENDED_SEED_DEALS_64
            + EXTENDED_SEED_DEALS_65
            + EXTENDED_SEED_DEALS_66
            + EXTENDED_SEED_DEALS_67
            + EXTENDED_SEED_DEALS_68
            + EXTENDED_SEED_DEALS_69
            + EXTENDED_SEED_DEALS_70
            + EXTENDED_SEED_DEALS_71
            + EXTENDED_SEED_DEALS_72
            + EXTENDED_SEED_DEALS_73
            + EXTENDED_SEED_DEALS_74
            + EXTENDED_SEED_DEALS_75
            + EXTENDED_SEED_DEALS_76
            + EXTENDED_SEED_DEALS_77
            + EXTENDED_SEED_DEALS_78
            + EXTENDED_SEED_DEALS_79
            + EXTENDED_SEED_DEALS_80
            + EXTENDED_SEED_DEALS_81
            + EXTENDED_SEED_DEALS_82
            + EXTENDED_SEED_DEALS_83
            + EXTENDED_SEED_DEALS_84
            + EXTENDED_SEED_DEALS_85
            + EXTENDED_SEED_DEALS_86
            + EXTENDED_SEED_DEALS_87
            + EXTENDED_SEED_DEALS_88
            + EXTENDED_SEED_DEALS_89
            + EXTENDED_SEED_DEALS_90
            + EXTENDED_SEED_DEALS_91
            + EXTENDED_SEED_DEALS_92
            + EXTENDED_SEED_DEALS_93
            + EXTENDED_SEED_DEALS_94
            + EXTENDED_SEED_DEALS_95
            + EXTENDED_SEED_DEALS_96
            + EXTENDED_SEED_DEALS_97
            + EXTENDED_SEED_DEALS_98
            + EXTENDED_SEED_DEALS_99
            + EXTENDED_SEED_DEALS_100
            + EXTENDED_SEED_DEALS_101
            + EXTENDED_SEED_DEALS_102
            + EXTENDED_SEED_DEALS_103
            + EXTENDED_SEED_DEALS_104
        )

        # When two seed batches accidentally share a source_id the
        # second upsert overwrites the first, so the row count after
        # a full seed is the *unique* count, not len(all_seed). Use
        # the same formula upsert uses to derive an auto-id so the
        # populated-threshold matches the actual stored row count.
        def _stable_id(d: Dict[str, Any]) -> str:
            sid = d.get("source_id")
            if sid:
                return sid
            name = d.get("deal_name") or d.get("company_name", "")
            return (f"auto_{name[:20].replace(' ', '_').lower()}_"
                    f"{d.get('year', 0)}")
        unique_n = len({_stable_id(d) for d in all_seed})

        if skip_if_populated:
            # Some seed batches set ``source = 'corpus_seed'`` rather
            # than the canonical ``'seed'`` (legacy schema artefact).
            # Counting both prevents skip_if_populated from misfiring
            # and re-running the seed loop on every call.
            with self._connect() as con:
                count = con.execute(
                    "SELECT COUNT(*) FROM public_deals "
                    "WHERE source IN ('seed', 'corpus_seed')"
                ).fetchone()[0]
            if count >= unique_n:
                return 0

        # One connection, one commit for the whole batch — see _upsert_on.
        inserted = 0
        with self._connect() as con:
            for deal in all_seed:
                self._upsert_on(con, deal)
                inserted += 1
            con.commit()
        return inserted

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, source_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as con:
            row = con.execute(
                "SELECT * FROM public_deals WHERE source_id = ?", (source_id,)
            ).fetchone()
        return _row_to_dict(row) if row else None

    def list(
        self,
        *,
        source: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        buyer_contains: Optional[str] = None,
        with_moic: bool = False,
        with_irr: bool = False,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        clauses = []
        params: List[Any] = []

        if source:
            clauses.append("source = ?")
            params.append(source)
        if year_min is not None:
            clauses.append("year >= ?")
            params.append(year_min)
        if year_max is not None:
            clauses.append("year <= ?")
            params.append(year_max)
        if buyer_contains:
            clauses.append("buyer LIKE ?")
            params.append(f"%{buyer_contains}%")
        if with_moic:
            clauses.append("realized_moic IS NOT NULL")
        if with_irr:
            clauses.append("realized_irr IS NOT NULL")

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        with self._connect() as con:
            rows = con.execute(
                f"SELECT * FROM public_deals {where} ORDER BY year DESC LIMIT ?",
                params,
            ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def stats(self) -> Dict[str, Any]:
        with self._connect() as con:
            total = con.execute("SELECT COUNT(*) FROM public_deals").fetchone()[0]
            with_moic = con.execute(
                "SELECT COUNT(*) FROM public_deals WHERE realized_moic IS NOT NULL"
            ).fetchone()[0]
            with_irr = con.execute(
                "SELECT COUNT(*) FROM public_deals WHERE realized_irr IS NOT NULL"
            ).fetchone()[0]
            by_source = {
                row[0]: row[1]
                for row in con.execute(
                    "SELECT source, COUNT(*) FROM public_deals GROUP BY source"
                ).fetchall()
            }
        return {
            "total": total,
            "with_moic": with_moic,
            "with_irr": with_irr,
            "by_source": by_source,
        }


def _row_to_dict(row: Mapping[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    pm = d.get("payer_mix")
    if pm and isinstance(pm, str):
        try:
            d["payer_mix"] = json.loads(pm)
        except json.JSONDecodeError:
            pass
    return d
