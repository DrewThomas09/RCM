"""Extended seed 85: Fertility, IVF, and women's health PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on fertility, IVF, reproductive endocrinology, and
adjacent women's-health subsectors. The theme covers:

- Reproductive endocrinology & infertility (REI) physician practice
  management platforms consolidating IVF clinics and embryology labs
- Standalone egg-freezing and elective fertility-preservation clinics
  serving the cash-pay millennial and Gen-Z demographic
- OB/GYN women's-health MSOs with fertility ancillary build-outs
- Employer-sponsored fertility benefit platforms (Progyny-style carve-
  outs, managed fertility benefit administrators)
- Donor egg / sperm banking and cryopreservation infrastructure

Fertility economics are distinguished by a predominantly cash-pay and
self-insured employer-benefit payer mix, rapid mandate-state expansion
(21+ states with some form of IVF coverage mandate as of 2024), single
embryo transfer (SET) utilization driving per-cycle success metrics,
PGT-A (preimplantation genetic testing for aneuploidy) attach-rate
economics, and donor-cycle and egg-banking ancillary revenue. Value
creation in PE-backed fertility platforms centers on cycle volume per
REI physician, lab throughput and embryology staffing productivity,
PGT-A and ICSI attach rates, Progyny and Carrot network contracting,
employer direct-contracting, donor cycle mix, and de novo satellite
clinic expansion into under-penetrated MSAs.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_85 = [
    {
        "company_name": "Pinnacle Fertility Partners",
        "sector": "Fertility / IVF",
        "buyer": "Webster Equity",
        "year": 2019,
        "region": "National",
        "ev_mm": 565.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 38.97,
        "ebitda_margin": 0.25,
        "revenue_mm": 155.88,
        "hold_years": 5.0,
        "moic": 2.9,
        "irr": 0.2373,
        "status": "Realized",
        "payer_mix": {"commercial": 0.52, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.45},
        "comm_pct": 0.52,
        "deal_narrative": (
            "National REI and IVF platform consolidating 28 clinics across 14 states "
            "with integrated embryology labs. Hold period captured the Progyny and "
            "Carrot employer-benefit network expansion, lifted PGT-A attach rates "
            "from 55% to 78% of retrievals, and scaled single embryo transfer "
            "utilization to 85% of fresh cycles. Exit thesis realized on cash-pay "
            "egg-banking build-out and mandate-state cycle volume tailwinds."
        ),
    },
    {
        "company_name": "Aurora Reproductive Medicine",
        "sector": "Reproductive Endocrinology",
        "buyer": "TA Associates",
        "year": 2018,
        "region": "Northeast",
        "ev_mm": 395.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 29.26,
        "ebitda_margin": 0.24,
        "revenue_mm": 121.92,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.1979,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.42},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Northeast REI platform spanning Massachusetts, New York, Connecticut, "
            "and New Jersey with 14 clinics and 4 embryology labs. Value creation "
            "levered state-mandate coverage (MA, NY, NJ, CT) that drove commercial "
            "insured cycle volume, Progyny in-network contracting that lifted "
            "employer-sponsored referrals, and donor egg bank expansion supporting "
            "premium cash-pay cycles at exit to a strategic women's-health acquirer."
        ),
    },
    {
        "company_name": "Bloom Fertility Benefits",
        "sector": "Fertility Benefits",
        "buyer": "Warburg Pincus",
        "year": 2020,
        "region": "National",
        "ev_mm": 720.0,
        "ev_ebitda": 17.0,
        "ebitda_mm": 42.35,
        "ebitda_margin": 0.22,
        "revenue_mm": 192.5,
        "hold_years": 4.5,
        "moic": 2.6,
        "irr": 0.2363,
        "status": "Active",
        "payer_mix": {"commercial": 0.68, "medicare": 0.00, "medicaid": 0.02, "self_pay": 0.30},
        "comm_pct": 0.68,
        "deal_narrative": (
            "Employer-sponsored fertility benefit platform administering IVF, egg "
            "freezing, and donor cycle coverage for Fortune 500 self-insured plan "
            "sponsors. Growth thesis scaled employer-client count from 140 to 420 "
            "during hold, captured share from Progyny and Carrot through deeper "
            "clinical-pathway management, and expanded into Gen-Z egg-freezing "
            "benefit design with per-cycle cash-pay rails for non-covered lives."
        ),
    },
    {
        "company_name": "SeedLine Egg Freezing Co",
        "sector": "Egg Freezing",
        "buyer": "Silversmith",
        "year": 2022,
        "region": "West",
        "ev_mm": 145.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 12.08,
        "ebitda_margin": 0.19,
        "revenue_mm": 63.58,
        "hold_years": 3.0,
        "moic": 1.7,
        "irr": 0.1935,
        "status": "Active",
        "payer_mix": {"commercial": 0.43, "medicare": 0.00, "medicaid": 0.02, "self_pay": 0.55},
        "comm_pct": 0.43,
        "deal_narrative": (
            "Premium direct-to-consumer egg freezing operator with boutique clinics "
            "in Los Angeles, San Francisco, and Seattle serving the millennial and "
            "Gen-Z cash-pay demographic. Thesis executes on financing-partner "
            "rails for multi-cycle packages, employer-benefit contracting with "
            "tech-sector plan sponsors, and egg-banking cold-storage monetization "
            "through annual cryopreservation fees that generate annuity revenue."
        ),
    },
    {
        "company_name": "Harbor Women's Health MSO",
        "sector": "OB/GYN Women's Health",
        "buyer": "Shore Capital",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 215.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 18.70,
        "ebitda_margin": 0.18,
        "revenue_mm": 103.89,
        "hold_years": 3.5,
        "moic": 1.8,
        "irr": 0.1829,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.05, "medicaid": 0.05, "self_pay": 0.30},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Southeast OB/GYN women's-health MSO across Florida, Georgia, and North "
            "Carolina with an emerging REI fertility ancillary service line. Value "
            "creation thesis targets fertility clinic tuck-ins to capture self-pay "
            "IVF cycle revenue, PGT-A lab partnership economics, and single embryo "
            "transfer protocol standardization across the platform, plus donor "
            "cycle referral pathways into adjacent reproductive medicine practices."
        ),
    },
    {
        "company_name": "Continental IVF Group",
        "sector": "Fertility / IVF",
        "buyer": "KKR",
        "year": 2017,
        "region": "National",
        "ev_mm": 810.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 52.26,
        "ebitda_margin": 0.26,
        "revenue_mm": 201.0,
        "hold_years": 6.0,
        "moic": 3.2,
        "irr": 0.2139,
        "status": "Realized",
        "payer_mix": {"commercial": 0.50, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.47},
        "comm_pct": 0.50,
        "deal_narrative": (
            "National IVF and REI platform scaled from 22 to 58 clinics across 19 "
            "states during hold, with a proprietary embryology lab network and "
            "PGT-A pipeline. Long-hold value creation delivered on employer-benefit "
            "platform contracting with Progyny, Maven, and Carrot, egg-banking "
            "annuity revenue, and single embryo transfer success-rate leadership "
            "that supported 26% margin and a 3.2x MOIC to a strategic acquirer."
        ),
    },
    {
        "company_name": "Mosaic Donor Cycles Network",
        "sector": "Fertility / IVF",
        "buyer": "Nautic",
        "year": 2020,
        "region": "National",
        "ev_mm": 175.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 14.0,
        "ebitda_margin": 0.20,
        "revenue_mm": 70.0,
        "hold_years": 4.0,
        "moic": 2.0,
        "irr": 0.1892,
        "status": "Active",
        "payer_mix": {"commercial": 0.43, "medicare": 0.00, "medicaid": 0.02, "self_pay": 0.55},
        "comm_pct": 0.43,
        "deal_narrative": (
            "National donor egg and sperm banking platform with cryopreservation "
            "hubs and REI clinic distribution partnerships. Hold thesis executes "
            "donor-cycle volume scaling, frozen-donor inventory depth targeting "
            "LGBTQ+ and single-intended-parent cash-pay demographics, and deeper "
            "employer benefit platform integrations where Progyny and Carrot cover "
            "donor-assisted IVF cycles with pass-through egg acquisition fees."
        ),
    },
    {
        "company_name": "Sapphire Fertility Institute",
        "sector": "Reproductive Endocrinology",
        "buyer": "Cressey",
        "year": 2016,
        "region": "West",
        "ev_mm": 325.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 25.0,
        "ebitda_margin": 0.23,
        "revenue_mm": 108.70,
        "hold_years": 6.5,
        "moic": 3.4,
        "irr": 0.2072,
        "status": "Realized",
        "payer_mix": {"commercial": 0.48, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.49},
        "comm_pct": 0.48,
        "deal_narrative": (
            "West Coast REI platform across California, Nevada, and Arizona with 11 "
            "clinics and integrated embryology labs. Long hold delivered on "
            "California-market cash-pay cycle volume tailwinds, PGT-A attach-rate "
            "scaling to 80% of retrievals, single embryo transfer protocol adoption "
            "improving take-home baby rates, and egg banking ancillary revenue that "
            "underwrote a 3.4x MOIC realization to a strategic fertility acquirer."
        ),
    },
    {
        "company_name": "Meadowbrook OB/GYN Partners",
        "sector": "OB/GYN Women's Health",
        "buyer": "Audax",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 280.0,
        "ev_ebitda": 12.8,
        "ebitda_mm": 21.88,
        "ebitda_margin": 0.20,
        "revenue_mm": 109.40,
        "hold_years": 5.0,
        "moic": 2.3,
        "irr": 0.1811,
        "status": "Realized",
        "payer_mix": {"commercial": 0.55, "medicare": 0.05, "medicaid": 0.08, "self_pay": 0.32},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Midwest OB/GYN women's-health platform across Illinois, Indiana, and "
            "Ohio with a fertility ancillary service line built out during hold. "
            "Value creation added three REI fertility clinic tuck-ins, launched "
            "an egg freezing program targeting professional women cash-pay "
            "demographics, and developed an employer direct-contracting channel "
            "for fertility benefit services independent of Progyny network rails."
        ),
    },
    {
        "company_name": "NovaGenesis Fertility",
        "sector": "Fertility / IVF",
        "buyer": "Thomas H Lee",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 460.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 32.86,
        "ebitda_margin": 0.24,
        "revenue_mm": 136.92,
        "hold_years": 5.5,
        "moic": 2.8,
        "irr": 0.2059,
        "status": "Realized",
        "payer_mix": {"commercial": 0.47, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.50},
        "comm_pct": 0.47,
        "deal_narrative": (
            "Southeast IVF platform with 19 clinics across Florida, Georgia, Texas, "
            "and the Carolinas and three centralized embryology labs. Thesis "
            "delivered on cash-pay cycle mix in non-mandate states, PGT-A attach "
            "rates above 75%, donor cycle volume scaling, and Progyny and Carrot "
            "in-network contracting that converted employer-sponsored fertility "
            "benefit demand into reliable multi-cycle patient lifetime value."
        ),
    },
    {
        "company_name": "Lyra Egg Bank",
        "sector": "Egg Freezing",
        "buyer": "Harren",
        "year": 2023,
        "region": "Northeast",
        "ev_mm": 72.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 6.86,
        "ebitda_margin": 0.17,
        "revenue_mm": 40.35,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1441,
        "status": "Held",
        "payer_mix": {"commercial": 0.42, "medicare": 0.00, "medicaid": 0.03, "self_pay": 0.55},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Northeast egg freezing and fertility preservation clinic operator "
            "headquartered in New York City with satellite clinics in Boston and "
            "Washington DC. Early hold focused on cash-pay multi-cycle package "
            "pricing, annual cryopreservation storage-fee annuity scaling, and "
            "tech-sector employer benefit contracting where fertility preservation "
            "coverage (without full IVF) is increasingly standard for Gen-Z talent."
        ),
    },
    {
        "company_name": "Clearwater Reproductive Health",
        "sector": "Reproductive Endocrinology",
        "buyer": "New Mountain",
        "year": 2021,
        "region": "Pacific",
        "ev_mm": 310.0,
        "ev_ebitda": 13.2,
        "ebitda_mm": 23.48,
        "ebitda_margin": 0.22,
        "revenue_mm": 106.73,
        "hold_years": 3.5,
        "moic": 1.9,
        "irr": 0.2013,
        "status": "Active",
        "payer_mix": {"commercial": 0.53, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.44},
        "comm_pct": 0.53,
        "deal_narrative": (
            "Pacific Northwest REI platform with 9 clinics across Washington, "
            "Oregon, and Northern California. Hold thesis executes Progyny and "
            "Carrot network expansion, single embryo transfer protocol adoption "
            "to improve live-birth metrics, PGT-A lab insourcing to capture "
            "previously outsourced margin, and de novo satellite clinic rollout "
            "into under-penetrated secondary MSAs like Boise and Spokane."
        ),
    },
    {
        "company_name": "Kindred Fertility Benefit Co",
        "sector": "Fertility Benefits",
        "buyer": "Frazier",
        "year": 2022,
        "region": "National",
        "ev_mm": 195.0,
        "ev_ebitda": 14.2,
        "ebitda_mm": 13.73,
        "ebitda_margin": 0.21,
        "revenue_mm": 65.38,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.66, "medicare": 0.00, "medicaid": 0.02, "self_pay": 0.32},
        "comm_pct": 0.66,
        "deal_narrative": (
            "Challenger employer-sponsored fertility benefit platform targeting "
            "the mid-market 1,000-10,000 lives segment under-served by Progyny "
            "and Carrot. Growth thesis executes employer direct-sales into "
            "regional plan sponsors, curated REI clinic network contracting with "
            "bundled single embryo transfer and PGT-A pricing, and fertility "
            "preservation (egg freezing) benefit design for Gen-Z workforce pull."
        ),
    },
    {
        "company_name": "Concordia Women's Fertility Network",
        "sector": "OB/GYN Women's Health",
        "buyer": "Lee Equity",
        "year": 2020,
        "region": "Southwest",
        "ev_mm": 235.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 18.80,
        "ebitda_margin": 0.19,
        "revenue_mm": 98.95,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1792,
        "status": "Active",
        "payer_mix": {"commercial": 0.50, "medicare": 0.05, "medicaid": 0.10, "self_pay": 0.35},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Southwest women's-health MSO with integrated OB/GYN, gynecology, and "
            "REI fertility service lines across Texas, Arizona, and New Mexico. "
            "Hold thesis builds out fertility ancillary revenue via embryology lab "
            "JVs, PGT-A attach-rate scaling, cash-pay egg freezing program launch, "
            "and single embryo transfer protocol standardization across the "
            "platform to elevate success rates and Progyny in-network eligibility."
        ),
    },
    {
        "company_name": "Helix Fertility Holdings",
        "sector": "Fertility / IVF",
        "buyer": "Welsh Carson",
        "year": 2017,
        "region": "National",
        "ev_mm": 640.0,
        "ev_ebitda": 14.8,
        "ebitda_mm": 43.24,
        "ebitda_margin": 0.25,
        "revenue_mm": 172.96,
        "hold_years": 6.0,
        "moic": 3.0,
        "irr": 0.2009,
        "status": "Realized",
        "payer_mix": {"commercial": 0.51, "medicare": 0.01, "medicaid": 0.02, "self_pay": 0.46},
        "comm_pct": 0.51,
        "deal_narrative": (
            "National fertility and IVF platform with 36 REI clinics and 6 "
            "centralized embryology labs at exit, scaled from 18 clinics at entry. "
            "Long-hold value creation executed on Progyny and Carrot in-network "
            "contracting, PGT-A and ICSI attach-rate optimization, donor-cycle "
            "volume growth, egg-banking cryostorage annuity revenue, and state-"
            "mandate tailwinds that supported a 3.0x MOIC realization at exit."
        ),
    },
]
