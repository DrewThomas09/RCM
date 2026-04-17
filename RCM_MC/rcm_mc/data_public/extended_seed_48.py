# extended_seed_48.py
# 15 PE healthcare deals covering staffing, education, consulting, and RCM-adjacent SaaS sectors.

EXTENDED_SEED_DEALS_48 = [
    # 1. Healthcare staffing / travel nurse agency
    {
        "source_id": "ext48_001",
        "source": "seed",
        "company_name": "TravelNurse Alliance Group",
        "sector": "Healthcare Staffing / Travel Nurse Agency",
        "year": 2016,
        "buyer": "Warburg Pincus",
        "ev_mm": 420.0,
        "ebitda_at_entry_mm": 38.2,          # EV/EBITDA ≈ 11.0x
        "moic": 3.4,
        "irr": 0.28,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.20,
            "medicaid": 0.15,
            "other": 0.10,
        },
        "notes": (
            "Travel nurse agencies face complex multi-state payroll and credentialing workflows "
            "that complicate W-2 vs. 1099 classification billing. Shift-based timekeeping must "
            "reconcile against facility invoicing to prevent revenue leakage."
        ),
    },
    # 2. Allied health staffing / therapy staffing
    {
        "source_id": "ext48_002",
        "source": "seed",
        "company_name": "AlliedTherapy Staffing Partners",
        "sector": "Allied Health Staffing / Therapy Staffing",
        "year": 2018,
        "buyer": "Blackstone Growth",
        "ev_mm": 310.0,
        "ebitda_at_entry_mm": 26.1,          # EV/EBITDA ≈ 11.9x
        "moic": 3.1,
        "irr": 0.26,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.48,
            "medicare": 0.28,
            "medicaid": 0.18,
            "other": 0.06,
        },
        "notes": (
            "Therapy staffing contracts span PT, OT, and SLP disciplines each carrying distinct "
            "CPT code sets and payer-specific documentation requirements. Per-visit contract "
            "reconciliation against facility census data is a persistent RCM challenge."
        ),
    },
    # 3. Physician recruiting / locum tenens
    {
        "source_id": "ext48_003",
        "source": "seed",
        "company_name": "LocumLink Physician Staffing",
        "sector": "Physician Recruiting / Locum Tenens",
        "year": 2015,
        "buyer": "KKR",
        "ev_mm": 580.0,
        "ebitda_at_entry_mm": 52.7,          # EV/EBITDA ≈ 11.0x
        "moic": 3.8,
        "irr": 0.31,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.60,
            "medicare": 0.22,
            "medicaid": 0.10,
            "other": 0.08,
        },
        "notes": (
            "Locum tenens placements require temporary credentialing at each facility, creating "
            "payer enrollment lags that delay billing authorization by 30–90 days. Accurate "
            "tracking of NPI-to-facility linkages is essential to avoid claim denials."
        ),
    },
    # 4. Medical education / CME provider
    {
        "source_id": "ext48_004",
        "source": "seed",
        "company_name": "PinnacleEd CME Solutions",
        "sector": "Medical Education / CME Provider",
        "year": 2017,
        "buyer": "Francisco Partners",
        "ev_mm": 185.0,
        "ebitda_at_entry_mm": 17.6,          # EV/EBITDA ≈ 10.5x
        "moic": 3.3,
        "irr": 0.30,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.20,
            "medicare": 0.05,
            "medicaid": 0.02,
            "other": 0.73,
        },
        "notes": (
            "CME providers bill pharmaceutical sponsors, health systems, and individual "
            "physicians under diverse fee structures that do not align with standard insurance "
            "billing workflows. Revenue recognition must differentiate grant-funded content from "
            "direct-pay registration fees."
        ),
    },
    # 5. Health literacy content / patient education SaaS
    {
        "source_id": "ext48_005",
        "source": "seed",
        "company_name": "ClearScript Patient Education Platform",
        "sector": "Health Literacy Content / Patient Education SaaS",
        "year": 2019,
        "buyer": "Vista Equity Partners",
        "ev_mm": 260.0,
        "ebitda_at_entry_mm": 22.6,          # EV/EBITDA ≈ 11.5x
        "moic": 3.6,
        "irr": 0.33,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.15,
            "medicare": 0.08,
            "medicaid": 0.05,
            "other": 0.72,
        },
        "notes": (
            "SaaS patient education platforms typically bill health systems and payers via "
            "enterprise subscription contracts, requiring multi-site license reconciliation. "
            "Usage-based tiers tied to patient volume create variable revenue that complicates "
            "ARR forecasting and billing automation."
        ),
    },
    # 6. Healthcare training / simulation center
    {
        "source_id": "ext48_006",
        "source": "seed",
        "company_name": "SimHealth Clinical Training Centers",
        "sector": "Healthcare Training / Simulation Center",
        "year": 2016,
        "buyer": "Bain Capital",
        "ev_mm": 155.0,
        "ebitda_at_entry_mm": 14.3,          # EV/EBITDA ≈ 10.8x
        "moic": 2.9,
        "irr": 0.25,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.10,
            "medicare": 0.04,
            "medicaid": 0.02,
            "other": 0.84,
        },
        "notes": (
            "Simulation centers derive revenue from hospital contracts, nursing school "
            "affiliations, and government grants, each with distinct invoicing cadences. "
            "Accurate cost-center allocation between simulation lab equipment depreciation and "
            "instructional labor is critical for margin visibility."
        ),
    },
    # 7. Revenue cycle education / coding certification
    {
        "source_id": "ext48_007",
        "source": "seed",
        "company_name": "CodeMaster RCM Education",
        "sector": "Revenue Cycle Education / Coding Certification",
        "year": 2014,
        "buyer": "General Atlantic",
        "ev_mm": 120.0,
        "ebitda_at_entry_mm": 11.4,          # EV/EBITDA ≈ 10.5x
        "moic": 3.5,
        "irr": 0.32,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.08,
            "medicare": 0.03,
            "medicaid": 0.02,
            "other": 0.87,
        },
        "notes": (
            "Coding certification bodies collect exam fees, annual renewal dues, and "
            "online courseware subscriptions under different revenue streams that require "
            "separate deferred revenue schedules. ICD-10 and CPT update cycles create "
            "periodic spikes in exam volume that must be reflected in billing projections."
        ),
    },
    # 8. Clinical documentation consulting
    {
        "source_id": "ext48_008",
        "source": "seed",
        "company_name": "DocuIntegrity CDI Advisors",
        "sector": "Clinical Documentation Consulting",
        "year": 2018,
        "buyer": "Carlyle Group",
        "ev_mm": 340.0,
        "ebitda_at_entry_mm": 29.6,          # EV/EBITDA ≈ 11.5x
        "moic": 3.2,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.30,
            "medicare": 0.38,
            "medicaid": 0.18,
            "other": 0.14,
        },
        "notes": (
            "CDI consulting engagements are billed on retainer plus performance-based fees "
            "tied to documented case-mix index improvement, creating contingency revenue "
            "recognition complexity. DRG query response rates must be tracked at the "
            "physician level to substantiate performance billing."
        ),
    },
    # 9. Healthcare compliance / regulatory consulting
    {
        "source_id": "ext48_009",
        "source": "seed",
        "company_name": "RegGuard Healthcare Compliance Group",
        "sector": "Healthcare Compliance / Regulatory Consulting",
        "year": 2017,
        "buyer": "TPG Capital",
        "ev_mm": 225.0,
        "ebitda_at_entry_mm": 20.0,          # EV/EBITDA ≈ 11.25x
        "moic": 3.0,
        "irr": 0.24,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.18,
            "medicare": 0.12,
            "medicaid": 0.08,
            "other": 0.62,
        },
        "notes": (
            "Compliance consulting firms bill hospital and payer clients under time-and-materials "
            "and fixed-fee project structures that require separate revenue recognition treatment. "
            "OIG work plan updates and CMS final rules drive episodic demand, creating lumpy "
            "backlog that complicates cash flow forecasting."
        ),
    },
    # 10. Medical staff credentialing / MSSP
    {
        "source_id": "ext48_010",
        "source": "seed",
        "company_name": "CredVerify Medical Staff Solutions",
        "sector": "Medical Staff Credentialing / MSSP",
        "year": 2020,
        "buyer": "GTCR",
        "ev_mm": 190.0,
        "ebitda_at_entry_mm": 17.3,          # EV/EBITDA ≈ 11.0x
        "moic": 2.7,
        "irr": 0.23,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.22,
            "medicare": 0.15,
            "medicaid": 0.08,
            "other": 0.55,
        },
        "notes": (
            "Credentialing outsourcing firms invoice hospitals on a per-provider or PEPM basis "
            "and must track privilege expiration dates to avoid billing for lapsed practitioners. "
            "Payer enrollment delays tied to credentialing create revenue holds that directly "
            "impact client cash collections."
        ),
    },
    # 11. Peer review / quality consulting
    {
        "source_id": "ext48_011",
        "source": "seed",
        "company_name": "QualityReview Physician Partners",
        "sector": "Peer Review / Quality Consulting",
        "year": 2015,
        "buyer": "Hellman & Friedman",
        "ev_mm": 95.0,
        "ebitda_at_entry_mm": 8.6,           # EV/EBITDA ≈ 11.0x
        "moic": 3.7,
        "irr": 0.34,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.25,
            "medicare": 0.30,
            "medicaid": 0.15,
            "other": 0.30,
        },
        "notes": (
            "Peer review organizations bill hospitals and payers per case review with additional "
            "fees for expedited turnaround, requiring SLA-based invoice tiering. Retrospective "
            "audits by payers of previously paid cases add receivables complexity when clawbacks "
            "are issued."
        ),
    },
    # 12. Case management outsourcing / utilization management
    {
        "source_id": "ext48_012",
        "source": "seed",
        "company_name": "CaseAxis UM Outsourcing",
        "sector": "Case Management Outsourcing / Utilization Management",
        "year": 2019,
        "buyer": "New Mountain Capital",
        "ev_mm": 475.0,
        "ebitda_at_entry_mm": 43.2,          # EV/EBITDA ≈ 11.0x
        "moic": 3.3,
        "irr": 0.29,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.40,
            "medicare": 0.30,
            "medicaid": 0.22,
            "other": 0.08,
        },
        "notes": (
            "Case management outsourcers contract with health plans on PMPM and per-authorization "
            "fee schedules, creating dual revenue streams that must be separately tracked against "
            "member eligibility rosters. Length-of-stay reductions tied to UM decisions affect "
            "both provider billing and payer fee calculations simultaneously."
        ),
    },
    # 13. Medical necessity review / UM platform
    {
        "source_id": "ext48_013",
        "source": "seed",
        "company_name": "NecessityIQ Review Platform",
        "sector": "Medical Necessity Review / UM Platform",
        "year": 2021,
        "buyer": "Insight Partners",
        "ev_mm": 520.0,
        "ebitda_at_entry_mm": 44.4,          # EV/EBITDA ≈ 11.7x
        "moic": 2.6,
        "irr": 0.22,
        "hold_years": 3.0,
        "payer_mix": {
            "commercial": 0.45,
            "medicare": 0.28,
            "medicaid": 0.20,
            "other": 0.07,
        },
        "notes": (
            "SaaS medical necessity platforms bill health plans per clinical decision supported "
            "and face regulatory scrutiny over InterQual/MCG criteria licensing that can affect "
            "contractual revenue caps. Denial rate reductions create performance-based revenue "
            "tiers that complicate GAAP revenue recognition under ASC 606."
        ),
    },
    # 14. Prior authorization / PA automation SaaS
    {
        "source_id": "ext48_014",
        "source": "seed",
        "company_name": "AuthBridge PA Automation",
        "sector": "Prior Authorization / PA Automation SaaS",
        "year": 2020,
        "buyer": "Thoma Bravo",
        "ev_mm": 780.0,
        "ebitda_at_entry_mm": 60.0,          # EV/EBITDA ≈ 13.0x
        "moic": 4.2,
        "irr": 0.37,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.50,
            "medicare": 0.25,
            "medicaid": 0.18,
            "other": 0.07,
        },
        "notes": (
            "PA automation platforms invoice providers and health systems on transaction volume "
            "tiers, where per-authorization fees vary by specialty and urgency, requiring "
            "granular usage metering. CMS e-PA mandates under the Interoperability Rule are "
            "expanding addressable volume but also compressing per-transaction pricing."
        ),
    },
    # 15. Denial prevention / claim scrubbing platform
    {
        "source_id": "ext48_015",
        "source": "seed",
        "company_name": "ScrubShield Claim Intelligence",
        "sector": "Denial Prevention / Claim Scrubbing Platform",
        "year": 2018,
        "buyer": "Veritas Capital",
        "ev_mm": 640.0,
        "ebitda_at_entry_mm": 54.0,          # EV/EBITDA ≈ 11.9x
        "moic": 3.9,
        "irr": 0.35,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.26,
            "medicaid": 0.16,
            "other": 0.06,
        },
        "notes": (
            "Claim scrubbing platforms price on a per-claim or percentage-of-collections basis, "
            "creating revenue volatility tied directly to client billing volumes and payer mix "
            "shifts. Edits targeting Medicare LCD/NCD compliance must be updated with each "
            "quarterly CMS release or clients face denial spikes that trigger SLA penalties."
        ),
    },
]
