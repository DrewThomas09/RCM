"""Extended seed 81: Dental DSO, oral surgery, and orthodontics PE deals.

This module contains a curated set of 15 healthcare private equity deal
records focused on the dental services landscape. The theme covers:

- General dental DSOs (multi-state practice platforms)
- Oral and maxillofacial surgery specialty groups
- Orthodontic platforms (adult/teen clear aligners, traditional braces)
- Pediatric dental chains (Medicaid-heavy and commercial)
- Endodontic specialty rollups (root canals, microsurgery)

Dental economics are distinguished by a commercial-dominant payer mix
(dental benefits rather than medical insurance), meaningful self-pay
exposure from elective/cosmetic services (aligners, implants, veneers),
and limited Medicare participation. Pediatric dental is the exception
where Medicaid CHIP programs drive a majority of volume. Value creation
in PE-backed DSOs centers on de novo growth, same-store yield from
hygiene recall and implant attach rates, specialty in-sourcing, and
regional density roll-ups.

Each record captures deal economics (EV, EV/EBITDA, margins), return
profile (MOIC, IRR, hold period), payer mix, regional footprint, sponsor,
realization status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis use cases.
"""

EXTENDED_SEED_DEALS_81 = [
    {
        "company_name": "Cascade Dental Partners",
        "sector": "Dental DSO",
        "buyer": "Audax",
        "year": 2018,
        "region": "Northeast",
        "ev_mm": 480.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 38.4,
        "ebitda_margin": 0.22,
        "revenue_mm": 174.55,
        "hold_years": 5.0,
        "moic": 2.6,
        "irr": 0.2106,
        "status": "Realized",
        "payer_mix": {"commercial": 0.62, "medicare": 0.03, "medicaid": 0.10, "self_pay": 0.25},
        "comm_pct": 0.62,
        "deal_narrative": (
            "Multi-state general dental DSO with 180+ affiliated offices across "
            "New England and Mid-Atlantic. Value creation driven by specialty "
            "in-sourcing (endo, perio, implants) and same-store hygiene recall "
            "improvement that lifted EBITDA margins by ~400 bps during hold."
        ),
    },
    {
        "company_name": "BrightSmile Orthodontics",
        "sector": "Orthodontics",
        "buyer": "Shore Capital",
        "year": 2020,
        "region": "Southeast",
        "ev_mm": 165.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 11.79,
        "ebitda_margin": 0.25,
        "revenue_mm": 47.16,
        "hold_years": 3.5,
        "moic": 1.9,
        "irr": 0.2013,
        "status": "Active",
        "payer_mix": {"commercial": 0.48, "medicare": 0.01, "medicaid": 0.11, "self_pay": 0.40},
        "comm_pct": 0.48,
        "deal_narrative": (
            "Regional orthodontic platform combining traditional bracket work "
            "with Invisalign-heavy adult aligner programs across Florida, Georgia, "
            "and the Carolinas. Self-pay financing plans and DSO-style marketing "
            "engine drove case-start volume growth of roughly 18% CAGR post-close."
        ),
    },
    {
        "company_name": "Heartland Oral Surgery Associates",
        "sector": "Oral Surgery",
        "buyer": "Welsh Carson",
        "year": 2016,
        "region": "Midwest",
        "ev_mm": 720.0,
        "ev_ebitda": 11.8,
        "ebitda_mm": 61.02,
        "ebitda_margin": 0.225,
        "revenue_mm": 271.2,
        "hold_years": 6.5,
        "moic": 3.2,
        "irr": 0.196,
        "status": "Realized",
        "payer_mix": {"commercial": 0.58, "medicare": 0.08, "medicaid": 0.09, "self_pay": 0.25},
        "comm_pct": 0.58,
        "deal_narrative": (
            "Integrated oral and maxillofacial surgery MSO with wisdom-teeth, "
            "dental implant, and full-arch reconstruction lines across 12 Midwestern "
            "states. Platform leveraged in-office anesthesia capability and "
            "referral-network density to compound revenue at mid-teens organically "
            "plus 30+ bolt-ons during hold."
        ),
    },
    {
        "company_name": "SunnyKids Pediatric Dental",
        "sector": "Pediatric Dental",
        "buyer": "Varsity",
        "year": 2021,
        "region": "Southwest",
        "ev_mm": 95.0,
        "ev_ebitda": 15.5,
        "ebitda_mm": 6.13,
        "ebitda_margin": 0.27,
        "revenue_mm": 22.7,
        "hold_years": 3.0,
        "moic": 1.7,
        "irr": 0.1935,
        "status": "Active",
        "payer_mix": {"commercial": 0.18, "medicare": 0.00, "medicaid": 0.74, "self_pay": 0.08},
        "comm_pct": 0.18,
        "deal_narrative": (
            "Medicaid-focused pediatric dental chain concentrated in Texas and "
            "Arizona, serving underserved CHIP populations through a hub-and-spoke "
            "de novo model. Growth thesis centers on state-level Medicaid rate "
            "stability and a ~25-office annual de novo cadence."
        ),
    },
    {
        "company_name": "Pinnacle Endodontic Specialists",
        "sector": "Endodontics",
        "buyer": "Nautic",
        "year": 2017,
        "region": "West",
        "ev_mm": 225.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 19.57,
        "ebitda_margin": 0.21,
        "revenue_mm": 93.19,
        "hold_years": 6.0,
        "moic": 2.8,
        "irr": 0.1872,
        "status": "Realized",
        "payer_mix": {"commercial": 0.60, "medicare": 0.04, "medicaid": 0.06, "self_pay": 0.30},
        "comm_pct": 0.60,
        "deal_narrative": (
            "West Coast endodontic specialty rollup featuring microsurgery and "
            "GentleWave technology. Platform built referral density with 2,400+ "
            "general-dentist partners and realized >3.0x by sale to a strategic "
            "dental specialty platform in 2023."
        ),
    },
    {
        "company_name": "Meridian Oral & Facial Surgery",
        "sector": "Oral Surgery",
        "buyer": "Frazier",
        "year": 2019,
        "region": "West",
        "ev_mm": 175.0,
        "ev_ebitda": 13.2,
        "ebitda_mm": 13.26,
        "ebitda_margin": 0.213,
        "revenue_mm": 62.25,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1792,
        "status": "Active",
        "payer_mix": {"commercial": 0.55, "medicare": 0.12, "medicaid": 0.08, "self_pay": 0.25},
        "comm_pct": 0.55,
        "deal_narrative": (
            "Pacific Northwest oral surgery group focused on All-on-X full-arch "
            "implant protocols and corrective jaw surgery. Post-close thesis "
            "includes expansion of surgeon-led implant centers and cross-referral "
            "from affiliated general dental partners in Washington and Oregon."
        ),
    },
    {
        "company_name": "ClearPath Aligner Network",
        "sector": "Orthodontics",
        "buyer": "Silversmith",
        "year": 2020,
        "region": "Southeast",
        "ev_mm": 135.0,
        "ev_ebitda": 12.8,
        "ebitda_mm": 10.55,
        "ebitda_margin": 0.23,
        "revenue_mm": 45.87,
        "hold_years": 4.0,
        "moic": 1.9,
        "irr": 0.1741,
        "status": "Active",
        "payer_mix": {"commercial": 0.42, "medicare": 0.00, "medicaid": 0.06, "self_pay": 0.52},
        "comm_pct": 0.42,
        "deal_narrative": (
            "Adult-focused orthodontic platform built around clear aligner therapy "
            "with hybrid doctor-led and teledentistry channels. Self-pay financing "
            "programs and targeted CAC optimization lifted clinic-level contribution "
            "margins from 19% to 24% during the first 24 months post-close."
        ),
    },
    {
        "company_name": "Summit Dental Holdings",
        "sector": "Dental DSO",
        "buyer": "Webster Equity",
        "year": 2017,
        "region": "National",
        "ev_mm": 830.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 61.48,
        "ebitda_margin": 0.24,
        "revenue_mm": 256.17,
        "hold_years": 6.0,
        "moic": 3.0,
        "irr": 0.2009,
        "status": "Realized",
        "payer_mix": {"commercial": 0.65, "medicare": 0.03, "medicaid": 0.09, "self_pay": 0.23},
        "comm_pct": 0.65,
        "deal_narrative": (
            "National general dental platform with 420+ offices at exit spanning "
            "25 states. Value creation driven by central services scale "
            "(procurement, RCM, marketing), specialty in-sourcing of ortho and "
            "implants, and a disciplined de novo program that added ~40 offices "
            "annually during hold."
        ),
    },
    {
        "company_name": "Atlantic Endodontic Partners",
        "sector": "Endodontics",
        "buyer": "Harren",
        "year": 2019,
        "region": "Northeast",
        "ev_mm": 155.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 12.92,
        "ebitda_margin": 0.19,
        "revenue_mm": 68.0,
        "hold_years": 5.0,
        "moic": 2.3,
        "irr": 0.1813,
        "status": "Active",
        "payer_mix": {"commercial": 0.63, "medicare": 0.05, "medicaid": 0.07, "self_pay": 0.25},
        "comm_pct": 0.63,
        "deal_narrative": (
            "Northeast endodontic specialty group serving Boston, New York, and "
            "Philadelphia metros. Platform differentiated by same-day root canal "
            "capacity and a tightly integrated referral portal with general "
            "dental practices."
        ),
    },
    {
        "company_name": "LittleTeeth Pediatric Dental",
        "sector": "Pediatric Dental",
        "buyer": "Cressey",
        "year": 2021,
        "region": "Southeast",
        "ev_mm": 125.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 8.93,
        "ebitda_margin": 0.24,
        "revenue_mm": 37.21,
        "hold_years": 3.0,
        "moic": 1.6,
        "irr": 0.1696,
        "status": "Active",
        "payer_mix": {"commercial": 0.26, "medicare": 0.00, "medicaid": 0.66, "self_pay": 0.08},
        "comm_pct": 0.26,
        "deal_narrative": (
            "Southeastern pediatric dental chain combining Medicaid-heavy core "
            "locations with ortho and specialty in-sourcing. Early hold focused "
            "on integrating two regional tuck-ins in Florida and Tennessee and "
            "standardizing hospital-based sedation workflows."
        ),
    },
    {
        "company_name": "BraceWorks Orthodontic Group",
        "sector": "Orthodontics",
        "buyer": "Silversmith",
        "year": 2022,
        "region": "West",
        "ev_mm": 82.0,
        "ev_ebitda": 13.8,
        "ebitda_mm": 5.94,
        "ebitda_margin": 0.20,
        "revenue_mm": 29.7,
        "hold_years": 2.5,
        "moic": 1.4,
        "irr": 0.1441,
        "status": "Held",
        "payer_mix": {"commercial": 0.50, "medicare": 0.00, "medicaid": 0.12, "self_pay": 0.38},
        "comm_pct": 0.50,
        "deal_narrative": (
            "Pacific-region orthodontic platform serving a mix of teen bracket "
            "and adult aligner patients in California and Nevada. Operator-led "
            "thesis centers on consolidating fragmented mom-and-pop ortho "
            "practices within 30-minute drive-time clusters."
        ),
    },
    {
        "company_name": "Legacy Oral Surgery Group",
        "sector": "Oral Surgery",
        "buyer": "Frazier",
        "year": 2018,
        "region": "Northeast",
        "ev_mm": 205.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 13.67,
        "ebitda_margin": 0.255,
        "revenue_mm": 53.61,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.1979,
        "status": "Exited",
        "payer_mix": {"commercial": 0.54, "medicare": 0.15, "medicaid": 0.06, "self_pay": 0.25},
        "comm_pct": 0.54,
        "deal_narrative": (
            "Boutique oral and maxillofacial surgery platform focused on full-arch "
            "implant reconstruction and corrective jaw procedures. Exit to a larger "
            "strategic dental specialty platform delivered 2.7x MOIC driven by "
            "procedure-mix shift into higher-acuity implant cases."
        ),
    },
    {
        "company_name": "Horizon Dental Services",
        "sector": "Dental DSO",
        "buyer": "Welsh Carson",
        "year": 2019,
        "region": "National",
        "ev_mm": 395.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 30.38,
        "ebitda_margin": 0.24,
        "revenue_mm": 126.58,
        "hold_years": 5.0,
        "moic": 2.5,
        "irr": 0.2011,
        "status": "Active",
        "payer_mix": {"commercial": 0.60, "medicare": 0.03, "medicaid": 0.12, "self_pay": 0.25},
        "comm_pct": 0.60,
        "deal_narrative": (
            "Multi-brand DSO platform with approximately 220 offices operating under "
            "three regional brands. Integration playbook focused on back-office "
            "consolidation (RCM, HR, procurement) and specialty in-sourcing "
            "to capture ortho and implant revenue that historically leaked to "
            "external referrals."
        ),
    },
    {
        "company_name": "Sterling Pediatric Dental Group",
        "sector": "Pediatric Dental",
        "buyer": "Cressey",
        "year": 2016,
        "region": "Midwest",
        "ev_mm": 245.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 23.33,
        "ebitda_margin": 0.225,
        "revenue_mm": 103.69,
        "hold_years": 6.0,
        "moic": 3.8,
        "irr": 0.2492,
        "status": "Realized",
        "payer_mix": {"commercial": 0.30, "medicare": 0.00, "medicaid": 0.62, "self_pay": 0.08},
        "comm_pct": 0.30,
        "deal_narrative": (
            "Midwest pediatric dental platform built through 70+ acquisitions plus "
            "a steady de novo program across Ohio, Michigan, Illinois, and Indiana. "
            "Exit realized 3.8x MOIC after state Medicaid rate resets and same-store "
            "volume recovery post-COVID materially lifted EBITDA in years 4-6."
        ),
    },
    {
        "company_name": "Apex Dental Alliance",
        "sector": "Dental DSO",
        "buyer": "TA Associates",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 540.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 49.09,
        "ebitda_margin": 0.235,
        "revenue_mm": 208.89,
        "hold_years": 5.5,
        "moic": 3.5,
        "irr": 0.2558,
        "status": "Realized",
        "payer_mix": {"commercial": 0.63, "medicare": 0.03, "medicaid": 0.10, "self_pay": 0.24},
        "comm_pct": 0.63,
        "deal_narrative": (
            "Southeastern dental DSO platform combining general dentistry with "
            "strong specialty offerings (ortho, endo, oral surgery) under a shared "
            "services model. Delivered top-quartile 3.5x MOIC via disciplined "
            "bolt-on cadence (45+ transactions) and same-store revenue CAGR "
            "in the high single digits."
        ),
    },
]
