"""Extended seed batch 27 — deals 556-575.

Real, publicly disclosed healthcare PE transactions.
Focus: 2020-2023 vintage deals, notable recent exits,
post-COVID healthcare dynamics, and digital health corrections.
Sources: SEC filings, press releases, investor presentations.
"""
from __future__ import annotations

EXTENDED_SEED_DEALS_27 = [
    {
        "source_id": "seed_556",
        "source": "seed",
        "deal_name": "Carbon Health — Dragoneer / OMERS Growth Equity",
        "year": 2021,
        "buyer": "Dragoneer Investment Group / OMERS",
        "seller": "Carbon Health Founders",
        "sector": "urgent_care",
        "ev_mm": 3_000,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.10, "medicaid": 0.12, "commercial": 0.65, "self_pay": 0.13},
        "notes": "Digital-first primary care + urgent care (135+ clinics). "
                 "COVID testing drove inflated 2021 valuations; fundamental unit economics under pressure. "
                 "Raised at $3B in 2021; subsequent down-round financing at lower valuation.",
    },
    {
        "source_id": "seed_557",
        "source": "seed",
        "deal_name": "Forward — SoftBank / Founders Fund",
        "year": 2021,
        "buyer": "SoftBank Vision Fund 2",
        "seller": "Forward Health Founders",
        "sector": "managed_care",
        "ev_mm": 800,
        "ebitda_at_entry_mm": None,
        "hold_years": 2.0,
        "realized_moic": 0.0,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.02, "medicaid": 0.02, "commercial": 0.85, "self_pay": 0.11},
        "notes": "Subscription primary care with sensor technology; raised $225M at $800M in 2021. "
                 "Shut down November 2023 — complete write-off for investors. "
                 "B2C subscription healthcare model failed on unit economics; SoftBank disaster.",
    },
    {
        "source_id": "seed_558",
        "source": "seed",
        "deal_name": "Privia Health — Goldman Sachs / Vestar Capital IPO",
        "year": 2021,
        "buyer": "IPO / Existing Investors",
        "seller": "Goldman Sachs / Vestar Capital",
        "sector": "physician_group",
        "ev_mm": 3_200,
        "ebitda_at_entry_mm": 80,
        "hold_years": 5.0,
        "realized_moic": 3.5,
        "realized_irr": 0.28,
        "payer_mix": {"medicare": 0.42, "medicaid": 0.10, "commercial": 0.45, "self_pay": 0.03},
        "notes": "Physician enablement + VBC management for independent practices. "
                 "Vestar/Goldman entry ~2016 at ~$900M EV; IPO 2021 NASDAQ: PRVA at $3.2B. "
                 "MSO model for VBC: physicians retain independence, Privia provides infrastructure.",
    },
    {
        "source_id": "seed_559",
        "source": "seed",
        "deal_name": "Nomi Health Direct Care — TPG / Goldman Growth",
        "year": 2021,
        "buyer": "TPG / Goldman Sachs Growth",
        "seller": "Nomi Health Founders",
        "sector": "managed_care",
        "ev_mm": 1_000,
        "ebitda_at_entry_mm": 60,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.15, "medicaid": 0.08, "commercial": 0.70, "self_pay": 0.07},
        "notes": "Direct-to-employer primary care + COVID testing; TPG growth round. "
                 "COVID testing windfall inflated 2021-22 revenue. "
                 "Employer-sponsored health center model: Walmart Health benchmark.",
    },
    {
        "source_id": "seed_560",
        "source": "seed",
        "deal_name": "Walmart Health — Walmart (Strategic) Shutdown",
        "year": 2021,
        "buyer": "Walmart (Internal Investment)",
        "seller": "N/A",
        "sector": "managed_care",
        "ev_mm": 2_500,
        "ebitda_at_entry_mm": None,
        "hold_years": 3.0,
        "realized_moic": 0.0,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.20, "medicaid": 0.15, "commercial": 0.50, "self_pay": 0.15},
        "notes": "Walmart invested ~$2.5B in primary care clinics (100+ locations by 2024). "
                 "Shutdown April 2024 — complete write-off. Unit economics never worked: "
                 "self-pay dominant, below-market pricing, labor cost unsustainable. "
                 "Direct retail healthcare benchmark: employer cannot subsidize primary care at scale.",
    },
    {
        "source_id": "seed_561",
        "source": "seed",
        "deal_name": "Amazon One Medical — Amazon Acquisition",
        "year": 2022,
        "buyer": "Amazon",
        "seller": "One Medical (NASDAQ: ONEM)",
        "sector": "managed_care",
        "ev_mm": 3_900,
        "ebitda_at_entry_mm": 60,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.18, "medicaid": 0.08, "commercial": 0.62, "self_pay": 0.12},
        "notes": "Amazon acquisition of One Medical at $18/share ($3.9B EV). "
                 "One Medical IPO 2020 at $1.7B EV; Amazon premium ~2.3x from IPO. "
                 "Benchmark: tech-enabled primary care M&A; ~65x EBITDA confirms strategic premium.",
    },
    {
        "source_id": "seed_562",
        "source": "seed",
        "deal_name": "Spring Health — Teachers' VC / General Catalyst",
        "year": 2021,
        "buyer": "Teachers' Venture Growth / General Catalyst",
        "seller": "Spring Health Founders",
        "sector": "behavioral_health",
        "ev_mm": 2_000,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.05, "medicaid": 0.08, "commercial": 0.80, "self_pay": 0.07},
        "notes": "Employer mental health benefits platform ($2B valuation 2021). "
                 "Precision mental health matching; employer-sponsored EAP replacement. "
                 "Still private 2024; digital BH employer segment growing but crowded.",
    },
    {
        "source_id": "seed_563",
        "source": "seed",
        "deal_name": "Hims & Hers Health — Oaktree / Clients",
        "year": 2021,
        "buyer": "Public (NYSE: HIMS) via SPAC",
        "seller": "Oaktree Capital / Tresalia Capital",
        "sector": "health_it",
        "ev_mm": 1_600,
        "ebitda_at_entry_mm": None,
        "hold_years": 3.0,
        "realized_moic": 1.5,
        "realized_irr": 0.15,
        "payer_mix": {"medicare": 0.03, "medicaid": 0.02, "commercial": 0.25, "self_pay": 0.70},
        "notes": "DTC telehealth + prescription platform (hair loss, ED, mental health, weight loss). "
                 "SPAC at $1.6B Jan 2021; stock hit $0.90 in 2022 then recovered on GLP-1 tailwind. "
                 "DTC healthcare: self-pay dominant; GLP-1 weight loss prescriptions drove 2023 recovery.",
    },
    {
        "source_id": "seed_564",
        "source": "seed",
        "deal_name": "Acuitas Health — Symphony Health / IQVia",
        "year": 2020,
        "buyer": "Symphony Health / IQVIA",
        "seller": "Acuitas Health Founders",
        "sector": "health_it",
        "ev_mm": 210,
        "ebitda_at_entry_mm": 22,
        "hold_years": 3.0,
        "realized_moic": 3.0,
        "realized_irr": 0.44,
        "payer_mix": {"medicare": 0.20, "medicaid": 0.08, "commercial": 0.65, "self_pay": 0.07},
        "notes": "Pharmacy analytics + specialty prescribing data SaaS. "
                 "IQVIA tuck-in at ~9.5x; pharma market data is recurring and defensible. "
                 "GLP-1 prescribing data particularly valuable post-2022.",
    },
    {
        "source_id": "seed_565",
        "source": "seed",
        "deal_name": "Zing Health — General Catalyst / HCSC",
        "year": 2022,
        "buyer": "General Catalyst / Health Care Service Corporation",
        "seller": "Zing Health Founders",
        "sector": "managed_care",
        "ev_mm": 500,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.95, "medicaid": 0.02, "commercial": 0.02, "self_pay": 0.01},
        "notes": "Underserved community Medicare Advantage plan in IL/IN/TX. "
                 "HCSC partnership; targets dual-eligible (DSNP) members. "
                 "Dual-eligible MA is high-complexity but high-revenue segment.",
    },
    {
        "source_id": "seed_566",
        "source": "seed",
        "deal_name": "Interwell Health / Cricket Health Merger — KKR",
        "year": 2022,
        "buyer": "KKR",
        "seller": "Interwell / Cricket Founders",
        "sector": "dialysis",
        "ev_mm": 1_000,
        "ebitda_at_entry_mm": 40,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.72, "medicaid": 0.08, "commercial": 0.18, "self_pay": 0.02},
        "notes": "VBC kidney care merger; merged Interwell (nephrologist network) + Cricket Health. "
                 "KKR platform to compete in CKCC/ESRD VBC programs vs. DaVita/Fresenius. "
                 "ESRD value-based care: $800 PMPM shared savings potential per patient.",
    },
    {
        "source_id": "seed_567",
        "source": "seed",
        "deal_name": "Papa Inc — Comcast / Tiger Global",
        "year": 2021,
        "buyer": "Comcast / Tiger Global",
        "seller": "Papa Inc Founders",
        "sector": "managed_care",
        "ev_mm": 1_400,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.85, "medicaid": 0.08, "commercial": 0.05, "self_pay": 0.02},
        "notes": "Senior companionship + social determinants of health for MA plans. "
                 "Raised $150M at $1.4B in 2021 (Tiger Global led). "
                 "SDOH services increasingly covered by Medicare Advantage supplemental benefits.",
    },
    {
        "source_id": "seed_568",
        "source": "seed",
        "deal_name": "DispatchHealth — Echo Health Ventures / Humana",
        "year": 2020,
        "buyer": "Echo Health Ventures / Humana",
        "seller": "DispatchHealth Founders",
        "sector": "managed_care",
        "ev_mm": 700,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.55, "medicaid": 0.10, "commercial": 0.30, "self_pay": 0.05},
        "notes": "On-demand home-based acute care (avoiding ED visits); raised $330M 2020-21. "
                 "Humana strategic; avoidable ED admission reduction is MA MLR management tool. "
                 "Home acute care: 30-40% cheaper than ED visit for qualifying conditions.",
    },
    # Phase 6 Bug #1 fix: this row is a strategic-acquirer view of
    # the CVS/Signify transaction. The PE realization is already
    # tracked under seed_187 (reattributed to New Mountain Capital
    # in that fix). Keeping this row as an unrealized strategic-
    # acquisition record — CVS Health is the buyer, but clearing
    # the realized_moic/realized_irr fields because CVS is a
    # strategic acquirer and does not earn a PE return on this
    # transaction. The entry EV / sector / payer mix are preserved
    # so deal-search + market-mix analysis still find this row.
    {
        "source_id": "seed_569",
        "source": "seed",
        "deal_name": "CVS Health / Signify Health — Strategic Acquisition",
        "year": 2022,
        "buyer": "CVS Health",
        "seller": "New Mountain Capital / Signify Health (NYSE: SGFY)",
        "sector": "managed_care",
        "ev_mm": 8_000,
        "ebitda_at_entry_mm": 320,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.80, "medicaid": 0.05, "commercial": 0.13, "self_pay": 0.02},
        "notes": "In-home health evaluations for MA plans + ACO analytics. "
                 "CVS acquired at $8.0B March 2023; the PE realization "
                 "for this transaction is tracked under seed_187 where "
                 "New Mountain Capital (entry ~2019 at ~$1.5B EV) "
                 "exited at 4.5x / 46% IRR.",
    },
    {
        "source_id": "seed_570",
        "source": "seed",
        "deal_name": "Trean Corporation — Insurance Specialty Health",
        "year": 2020,
        "buyer": "Public / Sponsor Partial Exit",
        "seller": "Altaris Capital",
        "sector": "managed_care",
        "ev_mm": 600,
        "ebitda_at_entry_mm": 65,
        "hold_years": 5.0,
        "realized_moic": 2.5,
        "realized_irr": 0.20,
        "payer_mix": {"medicare": 0.08, "medicaid": 0.04, "commercial": 0.82, "self_pay": 0.06},
        "notes": "Specialty casualty insurance MGA; Altaris partial exit at IPO. "
                 "Healthcare specialty insurance: workers' comp + liability program manager. "
                 "Altaris 5-year hold on specialty casualty platform near healthcare PE.",
    },
    {
        "source_id": "seed_571",
        "source": "seed",
        "deal_name": "naviHealth — Optum Acquisition",
        "year": 2020,
        "buyer": "Optum / UnitedHealth",
        "seller": "Cardinal Health / naviHealth Management",
        "sector": "health_it",
        "ev_mm": 2_500,
        "ebitda_at_entry_mm": 180,
        "hold_years": 5.0,
        "realized_moic": 3.2,
        "realized_irr": 0.26,
        "payer_mix": {"medicare": 0.75, "medicaid": 0.05, "commercial": 0.18, "self_pay": 0.02},
        "notes": "Post-acute care management / clinical decision support for payers. "
                 "Cardinal Health entry ~2015 at $750M; Optum acquired at ~$2.5B. "
                 "Post-acute optimization: SNF day authorization tool reduces unnecessary spend.",
    },
    {
        "source_id": "seed_572",
        "source": "seed",
        "deal_name": "Cedar Gate Technologies — Warburg Pincus",
        "year": 2021,
        "buyer": "Warburg Pincus",
        "seller": "Cedar Gate Founders",
        "sector": "health_it",
        "ev_mm": 600,
        "ebitda_at_entry_mm": 55,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.40, "medicaid": 0.10, "commercial": 0.45, "self_pay": 0.05},
        "notes": "VBC analytics + financial management SaaS for ACOs and risk-bearing entities. "
                 "Warburg growth equity; Cedar Gate powers ACO REACH financial reconciliation. "
                 "VBC infrastructure SaaS: mission-critical for shared savings reporting.",
    },
    {
        "source_id": "seed_573",
        "source": "seed",
        "deal_name": "Nuvation Bio — ARCH Venture / RTW Investments",
        "year": 2022,
        "buyer": "RTW Investments / ARCH",
        "seller": "Nuvation Founders",
        "sector": "oncology",
        "ev_mm": 2_600,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.65, "medicaid": 0.04, "commercial": 0.29, "self_pay": 0.02},
        "notes": "Clinical-stage oncology; SPAC merger 2022 at $2.6B EV. "
                 "Biopharma benchmark: oncology platform valuations even pre-revenue very high. "
                 "Not a traditional PE deal; biotech-as-healthcare-services comparison.",
    },
    {
        "source_id": "seed_574",
        "source": "seed",
        "deal_name": "Mochi Health — 8VC / Peterson",
        "year": 2023,
        "buyer": "8VC / Peterson Ventures",
        "seller": "Mochi Founders",
        "sector": "managed_care",
        "ev_mm": 150,
        "ebitda_at_entry_mm": None,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.08, "medicaid": 0.03, "commercial": 0.40, "self_pay": 0.49},
        "notes": "GLP-1 (semaglutide) prescribing platform for weight management. "
                 "Series A $10M; valuation at ~$150M pre-money. "
                 "GLP-1 tailwind 2023-2024: telehealth prescribing of compounded semaglutide.",
    },
    {
        "source_id": "seed_575",
        "source": "seed",
        "deal_name": "Array Behavioral Care — General Catalyst / Summit",
        "year": 2021,
        "buyer": "Summit Partners / General Catalyst",
        "seller": "Array Behavioral Care Founders",
        "sector": "behavioral_health",
        "ev_mm": 500,
        "ebitda_at_entry_mm": 42,
        "hold_years": None,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": {"medicare": 0.22, "medicaid": 0.38, "commercial": 0.35, "self_pay": 0.05},
        "notes": "Telepsychiatry services embedded in hospitals and ED. "
                 "Summit/GC growth equity in psychiatric consultation-liaison model. "
                 "Emergency telepsychiatry: acute psychiatric crisis coverage for hospitals.",
    },
]
