"""
Extended seed dataset #47 — PE healthcare deals focused on aesthetics and
dermatology-adjacent sectors. Cash-pay / elective weighting reflected in
payer_mix. All EV/EBITDA multiples fall in the 7x–15x range.
"""

EXTENDED_SEED_DEALS_47 = [
    {
        "source_id": "ext47_001",
        "source": "seed",
        "company_name": "ClearDerm Practice Partners",
        "sector": "Dermatology / medical derm practice management",
        "year": 2018,
        "buyer": "Varsity Healthcare Partners",
        "ev_mm": 420.0,
        "ebitda_at_entry_mm": 38.2,
        "moic": 3.4,
        "irr": 0.28,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.18,
            "medicaid": 0.08,
            "other": 0.22,
        },
        "notes": (
            "Medical derm blends insurance-covered procedures (biopsies, "
            "excisions) with elective cosmetic services, creating complex "
            "split-billing workflows that require rigorous modifier usage and "
            "prior-authorization tracking across multiple payers."
        ),
    },
    {
        "source_id": "ext47_002",
        "source": "seed",
        "company_name": "Apex Aesthetics Surgery Group",
        "sector": "Cosmetic surgery / aesthetics centers",
        "year": 2016,
        "buyer": "Gryphon Investors",
        "ev_mm": 185.0,
        "ebitda_at_entry_mm": 18.5,
        "moic": 3.8,
        "irr": 0.32,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.12,
            "medicare": 0.02,
            "medicaid": 0.01,
            "other": 0.85,
        },
        "notes": (
            "Cosmetic surgery centers are predominantly cash-pay, so RCM "
            "complexity centers on consumer financing integration, package "
            "pricing reconciliation, and the minority of reconstructive cases "
            "that do require insurance adjudication."
        ),
    },
    {
        "source_id": "ext47_003",
        "source": "seed",
        "company_name": "Renovo Reconstructive Partners",
        "sector": "Plastic surgery / reconstructive",
        "year": 2019,
        "buyer": "Shore Capital Partners",
        "ev_mm": 310.0,
        "ebitda_at_entry_mm": 28.2,
        "moic": 3.1,
        "irr": 0.26,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.48,
            "medicare": 0.22,
            "medicaid": 0.10,
            "other": 0.20,
        },
        "notes": (
            "Reconstructive plastic surgery carries high payer complexity due "
            "to medical-necessity documentation requirements and frequent "
            "cross-coding between cosmetic and reconstructive CPT codes, "
            "elevating denial rates and requiring robust appeals infrastructure."
        ),
    },
    {
        "source_id": "ext47_004",
        "source": "seed",
        "company_name": "Strands Hair Restoration Clinics",
        "sector": "Hair restoration / trichology",
        "year": 2020,
        "buyer": "Kingswood Capital Management",
        "ev_mm": 130.0,
        "ebitda_at_entry_mm": 14.4,
        "moic": 2.8,
        "irr": 0.24,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.08,
            "medicare": 0.01,
            "medicaid": 0.00,
            "other": 0.91,
        },
        "notes": (
            "Hair restoration is nearly entirely elective and cash-pay, making "
            "RCM simpler on the payer side but operationally complex given "
            "multi-session procedure packages, financing plans, and the "
            "occasional PRP billing that straddles cosmetic and medical coding."
        ),
    },
    {
        "source_id": "ext47_005",
        "source": "seed",
        "company_name": "Luminary MedSpa Holdings",
        "sector": "Medical spa / medspa chains",
        "year": 2017,
        "buyer": "L Catterton",
        "ev_mm": 520.0,
        "ebitda_at_entry_mm": 47.3,
        "moic": 4.2,
        "irr": 0.36,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.07,
            "medicare": 0.01,
            "medicaid": 0.00,
            "other": 0.92,
        },
        "notes": (
            "MedSpa chains operate almost entirely outside traditional "
            "insurance reimbursement, so RCM focus shifts to gift-card "
            "liability tracking, membership-model revenue recognition, and "
            "ensuring any supervised medical procedures are properly documented "
            "under physician oversight to avoid regulatory risk."
        ),
    },
    {
        "source_id": "ext47_006",
        "source": "seed",
        "company_name": "DermScience Cosmeceuticals",
        "sector": "Skincare product / cosmeceutical",
        "year": 2015,
        "buyer": "Highlander Partners",
        "ev_mm": 95.0,
        "ebitda_at_entry_mm": 10.6,
        "moic": 3.5,
        "irr": 0.30,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.05,
            "medicare": 0.00,
            "medicaid": 0.00,
            "other": 0.95,
        },
        "notes": (
            "Cosmeceutical manufacturers and clinic-affiliated skincare brands "
            "have minimal traditional RCM exposure, though physician dispensing "
            "programs require accurate NDC-level tracking and compliance with "
            "state pharmacy regulations when bundled with clinical services."
        ),
    },
    {
        "source_id": "ext47_007",
        "source": "seed",
        "company_name": "Photon Laser Aesthetics Network",
        "sector": "Laser aesthetics / energy-based devices",
        "year": 2018,
        "buyer": "Revelstoke Capital Partners",
        "ev_mm": 240.0,
        "ebitda_at_entry_mm": 22.0,
        "moic": 3.6,
        "irr": 0.31,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.10,
            "medicare": 0.02,
            "medicaid": 0.01,
            "other": 0.87,
        },
        "notes": (
            "Laser and energy-based device clinics face RCM challenges at the "
            "boundary between cosmetic and medically necessary treatments — "
            "laser hair removal is excluded, but laser treatment of vascular "
            "lesions or acne scarring may qualify, requiring procedure-level "
            "documentation to support any insurance submissions."
        ),
    },
    {
        "source_id": "ext47_008",
        "source": "seed",
        "company_name": "Fade Studios Tattoo Removal",
        "sector": "Tattoo removal / body modification",
        "year": 2021,
        "buyer": "Carousel Capital",
        "ev_mm": 75.0,
        "ebitda_at_entry_mm": 8.3,
        "moic": 2.6,
        "irr": 0.23,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.05,
            "medicare": 0.00,
            "medicaid": 0.00,
            "other": 0.95,
        },
        "notes": (
            "Tattoo removal is almost exclusively cash-pay elective; the narrow "
            "insurance-eligible segment involves gang-related removal programs "
            "contracted through county or state agencies, adding unique "
            "government-contract billing requirements distinct from standard "
            "healthcare RCM."
        ),
    },
    {
        "source_id": "ext47_009",
        "source": "seed",
        "company_name": "DryShield Hyperhidrosis Centers",
        "sector": "Hyperhidrosis / nerve treatment",
        "year": 2019,
        "buyer": "Kinderhook Industries",
        "ev_mm": 110.0,
        "ebitda_at_entry_mm": 10.0,
        "moic": 3.0,
        "irr": 0.27,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.38,
            "medicare": 0.04,
            "medicaid": 0.02,
            "other": 0.56,
        },
        "notes": (
            "Hyperhidrosis treatment sits at the cosmetic-medical boundary; "
            "miraDry and botulinum toxin injections for axillary hyperhidrosis "
            "can be covered by commercial plans with step-edit requirements, "
            "demanding thorough prior-authorization workflows and conservative "
            "use of topicals documentation before approval."
        ),
    },
    {
        "source_id": "ext47_010",
        "source": "seed",
        "company_name": "ScarFree Revision Specialists",
        "sector": "Scar revision / keloid management",
        "year": 2014,
        "buyer": "New MainStream Capital",
        "ev_mm": 60.0,
        "ebitda_at_entry_mm": 7.5,
        "moic": 2.7,
        "irr": 0.25,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.35,
            "medicare": 0.05,
            "medicaid": 0.02,
            "other": 0.58,
        },
        "notes": (
            "Scar revision and keloid management require differentiation between "
            "functional and cosmetic intent in clinical documentation; "
            "reconstructive intent (e.g., post-burn contracture, post-surgical "
            "deformity) can unlock commercial and Medicare coverage, while purely "
            "cosmetic improvement does not, necessitating dual-path billing logic."
        ),
    },
    {
        "source_id": "ext47_011",
        "source": "seed",
        "company_name": "ClearFlow Vein & Vascular Clinics",
        "sector": "Veins / varicose vein clinics",
        "year": 2017,
        "buyer": "Bain Capital Double Impact",
        "ev_mm": 380.0,
        "ebitda_at_entry_mm": 34.5,
        "moic": 3.9,
        "irr": 0.33,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.50,
            "medicare": 0.28,
            "medicaid": 0.06,
            "other": 0.16,
        },
        "notes": (
            "Vein clinics carry high RCM complexity because varicose vein "
            "procedures require duplex ultrasound documentation and conservative "
            "treatment failure evidence before commercial and Medicare approval; "
            "spider vein sclerotherapy remains cosmetic and cash-pay, requiring "
            "careful charge segregation at the procedure level."
        ),
    },
    {
        "source_id": "ext47_012",
        "source": "seed",
        "company_name": "PRP Renew Aesthetics Group",
        "sector": "Microneedling / PRP aesthetics",
        "year": 2022,
        "buyer": "Trive Capital",
        "ev_mm": 88.0,
        "ebitda_at_entry_mm": 9.8,
        "moic": 2.5,
        "irr": 0.22,
        "hold_years": 3.0,
        "payer_mix": {
            "commercial": 0.06,
            "medicare": 0.01,
            "medicaid": 0.00,
            "other": 0.93,
        },
        "notes": (
            "Microneedling and PRP-based facial rejuvenation are almost "
            "universally excluded from insurance coverage, keeping RCM "
            "operationally straightforward; however, PRP when used as an "
            "adjunct to orthopedic or hair-loss protocols may generate a small "
            "billable insurance claim requiring separate coding and "
            "documentation."
        ),
    },
    {
        "source_id": "ext47_013",
        "source": "seed",
        "company_name": "ContourMed Body Studios",
        "sector": "Non-surgical body contouring",
        "year": 2020,
        "buyer": "Thurston Group",
        "ev_mm": 155.0,
        "ebitda_at_entry_mm": 15.5,
        "moic": 3.2,
        "irr": 0.28,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.05,
            "medicare": 0.00,
            "medicaid": 0.00,
            "other": 0.95,
        },
        "notes": (
            "Non-surgical body contouring (cryolipolysis, radiofrequency, "
            "HIFU) is entirely elective and cash-pay; RCM infrastructure "
            "focuses on financing-platform reconciliation, multi-area "
            "package pricing compliance, and accurate session-count tracking "
            "for subscription and series-based service models."
        ),
    },
    {
        "source_id": "ext47_014",
        "source": "seed",
        "company_name": "LiftLine Thread Aesthetics",
        "sector": "Thread lift / minimally invasive aesthetics",
        "year": 2021,
        "buyer": "Edgewater Growth Capital",
        "ev_mm": 68.0,
        "ebitda_at_entry_mm": 7.6,
        "moic": 2.9,
        "irr": 0.26,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.05,
            "medicare": 0.01,
            "medicaid": 0.00,
            "other": 0.94,
        },
        "notes": (
            "Thread lift procedures are elective and insurance-excluded in "
            "virtually all cases; clinics must ensure that any patient with a "
            "co-occurring reconstructive indication (e.g., post-oncologic "
            "facial reconstruction) is billed through a separate clinical "
            "encounter to avoid inadvertent cosmetic bundling that forfeits "
            "reimbursement."
        ),
    },
    {
        "source_id": "ext47_015",
        "source": "seed",
        "company_name": "Revive Injectable Aesthetics Co.",
        "sector": "Aesthetic injectable / Botox clinic chains",
        "year": 2019,
        "buyer": "General Atlantic",
        "ev_mm": 750.0,
        "ebitda_at_entry_mm": 62.5,
        "moic": 4.5,
        "irr": 0.38,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.09,
            "medicare": 0.02,
            "medicaid": 0.01,
            "other": 0.88,
        },
        "notes": (
            "Botox and filler clinic chains are predominantly cash-pay, but the "
            "therapeutic botulinum toxin segment (migraines, hyperhidrosis, "
            "spasticity) creates a parallel insurance billing track that demands "
            "distinct CPT and J-code workflows, separate medical-necessity "
            "documentation, and strict dose-unit reconciliation to prevent "
            "payer audits."
        ),
    },
]
