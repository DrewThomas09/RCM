"""Extended seed 97: Community health clinic / FQHC / safety-net PE deals.

This module contains a curated set of 15 healthcare private equity
deal records focused on the community health clinic / Federally
Qualified Health Center (FQHC) / safety-net subsector. The theme
covers:

- Federally Qualified Health Centers (FQHCs) operating under
  Section 330 of the Public Health Service Act with HRSA (Health
  Resources and Services Administration) grant funding and Section
  330 grant awards supporting uninsured and underinsured care
  delivery, reimbursed by Medicare and Medicaid under the FQHC
  Prospective Payment System (PPS) rate methodology — a
  cost-based per-visit encounter rate distinct from fee-for-service
  physician reimbursement
- Community health centers (CHCs) delivering integrated primary
  care, behavioral health, dental, pharmacy, and enabling
  (transportation / interpreter / case-management) services to
  medically underserved populations in HRSA-designated Medically
  Underserved Areas (MUAs) and Medically Underserved Populations
  (MUPs), with a federally mandated sliding fee scale based on
  federal poverty level (FPL) discount tiers at or below 200% FPL
- FQHC Look-Alikes meeting Section 330 program requirements for
  HRSA look-alike designation without receiving Section 330 grant
  funding but retaining FQHC PPS reimbursement status, 340B Drug
  Pricing Program participation eligibility, and FTCA (Federal
  Tort Claims Act) medical malpractice coverage under look-alike
  status
- Safety-net clinics operating outside the Section 330 / FQHC
  framework but serving Medicaid-heavy and uninsured populations
  via state-charity-care programs, hospital-affiliated charity
  care arrangements, free-clinic 501(c)(3) charitable-care
  operations, and Medicaid-DSH (Disproportionate Share Hospital)
  cross-subsidy funding
- Charitable care network platforms consolidating free-clinic and
  sliding-fee-scale operations under 501(c)(3) charitable mission
  structures with philanthropic funding, state-grant program
  support, and limited commercial-insurance participation for
  wraparound revenue

Community health clinic / FQHC / safety-net economics are
distinguished by a Medicaid-heavy payer mix (45-68% Medicaid
reflecting the core safety-net patient population of Medicaid
expansion-state beneficiaries, CHIP-enrolled children, and
pregnancy-and-postpartum Medicaid coverage), a meaningful
Medicare segment (15-25% Medicare driven by dual-eligible
Medicare-Medicaid beneficiaries and traditional Medicare
beneficiaries in Medically Underserved Areas), a constrained
commercial segment (10-22% commercial reflecting the
employed-but-underinsured working-poor population and limited
commercial-payer contracting at FQHC PPS rates), and a large
self-pay / sliding-fee segment (8-20% self-pay reflecting the
uninsured population served under the Section 330 mandate and
sliding-fee-scale 0% - 100% sliding discount structure at or
below 200% FPL). The subsector faces specific regulatory and
reimbursement dynamics: (a) Section 330 of the Public Health
Service Act establishing FQHC program requirements including
governance by a patient-majority board (51% of governing
board members must be FQHC patients), provision of comprehensive
primary care with behavioral health and dental integration,
open access regardless of ability to pay, sliding fee scale for
patients at or below 200% FPL, HRSA-approved quality-assurance
plan, and UDS (Uniform Data System) annual reporting to HRSA on
patient demographics, service utilization, quality measures, and
financial performance; (b) FQHC Prospective Payment System (PPS)
reimbursement methodology under Medicare and Medicaid that pays
a cost-based per-visit encounter rate reflecting the FQHC's
historical reasonable cost per visit, with Medicare PPS rates
published annually by CMS and Medicaid PPS rates determined
by state Medicaid agency via base-year cost-report methodology
with annual MEI (Medicare Economic Index) inflation adjustment —
the FQHC PPS rate structure produces encounter rates of $180-
$280 per medical visit and $120-$220 per dental/behavioral-
health visit that are materially above Medicaid fee-for-service
rates for equivalent CPT code billing by non-FQHC providers
and create the fundamental FQHC reimbursement advantage; (c)
340B Drug Pricing Program participation for FQHCs and FQHC
Look-Alikes enabling the organization to purchase outpatient
pharmaceuticals at manufacturer-discount 340B pricing and bill
insurance at full contract rates, generating 340B margin that
cross-subsidizes uninsured care — with growing regulatory
and manufacturer-contract pressure on 340B eligibility and
contract-pharmacy arrangements; (d) HRSA look-alike designation
pathway for organizations meeting Section 330 program
requirements without receiving Section 330 grant funding, with
look-alikes retaining FQHC PPS reimbursement, 340B participation,
and FTCA malpractice coverage eligibility but operating without
federal grant revenue; (e) Federal Tort Claims Act (FTCA)
medical malpractice coverage for FQHC and FQHC look-alike
employees and certain contractors, replacing commercial medical
malpractice insurance and creating a material cost advantage;
(f) Uniform Data System (UDS) annual reporting to HRSA on
patient demographics, service utilization, clinical quality
measures, and financial performance — a standardized dataset
that drives HRSA performance evaluation, Section 330 grant
continuation, and quality-based supplemental payments under
some state Medicaid programs; (g) state Medicaid expansion
dynamics under the Affordable Care Act materially affecting
FQHC payer mix (Medicaid-expansion states produce FQHC
Medicaid mixes in the 55-68% range while non-expansion states
run 40-50% Medicaid with elevated 15-25% uninsured / sliding-
fee-scale mix); (h) the CMS Medicare PPS alternative-payment-
model (APM) pathway for FQHCs participating in ACO and Medicare
Advantage arrangements with shared-savings and capitated
payment structures distinct from the base PPS per-visit
reimbursement; (i) the post-2021 HRSA Section 330 grant
expansion under the American Rescue Plan Act (ARPA) providing
supplemental FQHC funding with continued base-funding
uncertainty in subsequent HRSA Bureau of Primary Health Care
(BPHC) appropriations cycles; and (j) the nonprofit-to-
for-profit conversion and management-services-organization
(MSO) structural complexity — traditional FQHCs are organized
as 501(c)(3) nonprofits with patient-majority governing
boards, so PE participation in the subsector operates through
MSO contracts, back-office services arrangements, real-estate
master leases, and specialty-services joint ventures with
nonprofit FQHC operating entities rather than direct equity
ownership of the Section 330 grantee. Value creation in PE-
backed FQHC-adjacent platforms centers on MSO back-office
scale (revenue-cycle, IT, HR, compliance, finance shared
services), 340B contract-pharmacy program optimization and
specialty-drug pipeline, Medicare and Medicaid PPS rate
rebasing and cost-report sophistication, HRSA look-alike
designation pathway and Section 330 grant application support,
UDS reporting optimization for quality-based supplemental
payments, specialty-care access partnerships (behavioral
health, dental, vision, specialty medical), and payer-
contracting support for commercial and Medicare Advantage
at-risk arrangements. Each record captures deal economics
(EV, EV/EBITDA, margins), return profile (MOIC, IRR, hold
period), payer mix, regional footprint, sponsor, realization
status, and a short deal narrative. These records are
synthesized for modeling, backtesting, and scenario analysis
use cases.
"""

EXTENDED_SEED_DEALS_97 = [
    {
        "company_name": "Cardinal Community Health Network",
        "sector": "FQHC Network",
        "buyer": "Welsh, Carson, Anderson & Stowe",
        "year": 2018,
        "region": "Southeast",
        "ev_mm": 485.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 82.45,
        "ebitda_margin": 0.17,
        "revenue_mm": 485.00,
        "hold_years": 5.5,
        "moic": 2.7,
        "irr": 0.2032,
        "status": "Realized",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.58, "medicare": 0.20, "self_pay": 0.08},
        "comm_pct": 0.14,
        "deal_narrative": (
            "Southeast FQHC management-services-organization (MSO) "
            "platform supporting 12 affiliated Section 330 grantee "
            "community health centers across Florida, Georgia, and "
            "North Carolina with 68 clinical delivery sites serving "
            "420,000 unique patients annually under HRSA Section "
            "330 grant funding. MSO contract structure with each "
            "nonprofit FQHC operating entity provides revenue-cycle "
            "management, 340B contract-pharmacy administration, IT / "
            "EHR services, HR / credentialing, finance / UDS (Uniform "
            "Data System) reporting, and HRSA compliance support "
            "while each FQHC retains its patient-majority governing "
            "board and Section 330 grantee status. Long hold grew "
            "340B contract-pharmacy network from 38 to 124 "
            "contract pharmacies capturing pharmacy-margin cross-"
            "subsidy, optimized Medicare and Medicaid PPS "
            "(Prospective Payment System) rate cost-report "
            "methodology producing rate increases of 14-18% over "
            "the base-year rate at each affiliate, supported two "
            "affiliates through HRSA look-alike designation "
            "pathway, and exited to a strategic FQHC MSO platform "
            "at 2.7x MOIC on the demonstrated sliding-fee-scale "
            "safety-net operating model."
        ),
    },
    {
        "company_name": "Meadowlark FQHC Services Group",
        "sector": "FQHC Network",
        "buyer": "Bain Capital Double Impact",
        "year": 2019,
        "region": "Midwest",
        "ev_mm": 285.0,
        "ev_ebitda": 13.0,
        "ebitda_mm": 48.45,
        "ebitda_margin": 0.17,
        "revenue_mm": 285.00,
        "hold_years": 5.0,
        "moic": 2.4,
        "irr": 0.1920,
        "status": "Realized",
        "payer_mix": {"commercial": 0.12, "medicaid": 0.60, "medicare": 0.18, "self_pay": 0.10},
        "comm_pct": 0.12,
        "deal_narrative": (
            "Midwest FQHC MSO platform supporting 8 Section 330 "
            "grantee community health centers across Ohio, Indiana, "
            "and Michigan with 42 clinical sites serving 240,000 "
            "unique patients in HRSA-designated Medically Underserved "
            "Areas (MUAs). Service lines include integrated primary "
            "care, behavioral health (SBIRT screening and "
            "counseling), dental, vision, and enabling services "
            "(transportation, interpreter, case-management) per "
            "Section 330 comprehensive-services requirements. Long "
            "hold navigated state Medicaid expansion dynamics "
            "driving Medicaid mix expansion from 52% to 60% at Ohio "
            "and Michigan affiliates, captured 340B Drug Pricing "
            "Program margin on outpatient specialty pharmacy, "
            "supported UDS (Uniform Data System) reporting "
            "infrastructure for HRSA-required annual submission "
            "on patient demographics / service utilization / "
            "clinical quality measures / financial performance, "
            "and exited to a strategic nonprofit health system "
            "affiliated with FQHC MSO operations at 2.4x MOIC."
        ),
    },
    {
        "company_name": "Salt Flats Community Health Alliance",
        "sector": "Community Health Center",
        "buyer": "Linden Capital Partners",
        "year": 2020,
        "region": "West",
        "ev_mm": 195.0,
        "ev_ebitda": 12.5,
        "ebitda_mm": 31.20,
        "ebitda_margin": 0.16,
        "revenue_mm": 195.00,
        "hold_years": 4.5,
        "moic": 2.1,
        "irr": 0.1836,
        "status": "Active",
        "payer_mix": {"commercial": 0.16, "medicaid": 0.54, "medicare": 0.22, "self_pay": 0.08},
        "comm_pct": 0.16,
        "deal_narrative": (
            "West community health center MSO platform supporting "
            "6 Section 330 grantee CHCs across Utah, Nevada, and "
            "Arizona with 34 clinical sites delivering comprehensive "
            "primary care to 180,000 unique patients in rural and "
            "frontier HRSA-designated Medically Underserved Areas. "
            "Mid-hold navigates the post-2021 ARPA (American Rescue "
            "Plan Act) supplemental HRSA Section 330 grant funding "
            "environment with base-funding uncertainty in "
            "subsequent HRSA Bureau of Primary Health Care (BPHC) "
            "appropriations cycles, manages Arizona / Nevada "
            "Medicaid expansion dynamics producing elevated "
            "Medicaid mix at 54-58% across the portfolio, operates "
            "the federally mandated sliding fee scale producing "
            "0% - 100% discount tiers for patients at or below "
            "200% federal poverty level (FPL), and supports two "
            "affiliates on the HRSA look-alike designation pathway "
            "for program-compliance operations without Section 330 "
            "grant funding receipt. Sponsor targeting sale to a "
            "regional FQHC consolidator at a compressed mid-teens "
            "multiple."
        ),
    },
    {
        "company_name": "Birchwood Safety-Net Partners",
        "sector": "Safety-Net Clinic",
        "buyer": "Shore Capital Partners",
        "year": 2019,
        "region": "Mid-Atlantic",
        "ev_mm": 125.0,
        "ev_ebitda": 11.5,
        "ebitda_mm": 18.75,
        "ebitda_margin": 0.15,
        "revenue_mm": 125.00,
        "hold_years": 5.5,
        "moic": 2.2,
        "irr": 0.1570,
        "status": "Realized",
        "payer_mix": {"commercial": 0.18, "medicaid": 0.52, "medicare": 0.16, "self_pay": 0.14},
        "comm_pct": 0.18,
        "deal_narrative": (
            "Mid-Atlantic safety-net clinic platform with 28 primary "
            "care and behavioral health delivery sites across "
            "Virginia, Maryland, Pennsylvania, and DC operating "
            "outside the Section 330 / FQHC framework but serving "
            "Medicaid-heavy and uninsured populations via state-"
            "charity-care programs, hospital-affiliated charity-"
            "care arrangements, and state-grant program support. "
            "Service mix delivers integrated primary care, "
            "behavioral health counseling, SUD (substance use "
            "disorder) treatment, and limited specialty access "
            "(cardiology / endocrinology consult). Long hold "
            "navigated Virginia Medicaid expansion (2019) "
            "producing Medicaid mix expansion from 42% to 52% "
            "and reducing uninsured / sliding-fee-scale burden, "
            "built state-charity-care-program reimbursement "
            "optimization infrastructure, and exited to a "
            "nonprofit-affiliated FQHC MSO at 2.2x MOIC on the "
            "state-program-dependent safety-net reimbursement "
            "thesis."
        ),
    },
    {
        "company_name": "Juniper Look-Alike Health Partners",
        "sector": "Look-Alike FQHC",
        "buyer": "Audax Private Equity",
        "year": 2020,
        "region": "Southwest",
        "ev_mm": 165.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 28.05,
        "ebitda_margin": 0.17,
        "revenue_mm": 165.00,
        "hold_years": 4.5,
        "moic": 2.0,
        "irr": 0.1702,
        "status": "Active",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.56, "medicare": 0.18, "self_pay": 0.12},
        "comm_pct": 0.14,
        "deal_narrative": (
            "Southwest FQHC Look-Alike platform with 18 clinical "
            "delivery sites across Texas, Oklahoma, and New Mexico "
            "operating under HRSA look-alike designation meeting "
            "Section 330 program requirements (patient-majority "
            "governing board, comprehensive primary care with "
            "behavioral health and dental integration, open access "
            "regardless of ability to pay, sliding fee scale at or "
            "below 200% FPL, HRSA-approved quality-assurance plan, "
            "UDS reporting) without receiving Section 330 grant "
            "funding but retaining FQHC PPS (Prospective Payment "
            "System) reimbursement status, 340B Drug Pricing "
            "Program participation eligibility, and FTCA (Federal "
            "Tort Claims Act) medical malpractice coverage. Mid-"
            "hold navigates the non-expansion-state Texas / "
            "Oklahoma Medicaid environment producing elevated "
            "self-pay / sliding-fee-scale mix versus expansion-"
            "state peers, optimizes 340B contract-pharmacy "
            "network, and pursues HRSA Section 330 grant "
            "application pathway for two affiliates."
        ),
    },
    {
        "company_name": "Applewood FQHC Back-Office Services",
        "sector": "FQHC Network",
        "buyer": "New Mountain Capital",
        "year": 2017,
        "region": "National",
        "ev_mm": 625.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 112.50,
        "ebitda_margin": 0.18,
        "revenue_mm": 625.00,
        "hold_years": 6.0,
        "moic": 3.1,
        "irr": 0.2106,
        "status": "Realized",
        "payer_mix": {"commercial": 0.12, "medicaid": 0.62, "medicare": 0.18, "self_pay": 0.08},
        "comm_pct": 0.12,
        "deal_narrative": (
            "National FQHC back-office services / MSO platform "
            "supporting 28 Section 330 grantee community health "
            "centers across 14 states with 180 clinical delivery "
            "sites serving 820,000 unique patients. MSO contract "
            "structure provides shared-services revenue-cycle "
            "management (FQHC PPS-specific billing for Medicare "
            "and Medicaid encounter-rate reimbursement), 340B "
            "contract-pharmacy administration, EHR hosting and "
            "optimization (athenahealth / NextGen / eClinicalWorks "
            "ambulatory platforms common in the FQHC market), HR "
            "and credentialing shared services, finance and UDS "
            "reporting infrastructure, and HRSA compliance "
            "support. Long 6-year hold grew from 18 to 28 "
            "affiliated FQHCs, built 340B contract-pharmacy "
            "network to 340 contract pharmacies, supported 4 "
            "affiliates through HRSA look-alike-to-Section-330 "
            "grantee conversion pathway, achieved Medicaid PPS "
            "rate rebasing producing 12-22% rate increases at 8 "
            "affiliates, and exited to a strategic nonprofit "
            "health system with FQHC MSO operations at 3.1x MOIC."
        ),
    },
    {
        "company_name": "Cottonwood Charitable Care Network",
        "sector": "Charitable Care Network",
        "buyer": "Bain Capital Double Impact",
        "year": 2021,
        "region": "Midwest",
        "ev_mm": 85.0,
        "ev_ebitda": 11.0,
        "ebitda_mm": 11.05,
        "ebitda_margin": 0.13,
        "revenue_mm": 85.00,
        "hold_years": 3.5,
        "moic": 1.5,
        "irr": 0.1227,
        "status": "Active",
        "payer_mix": {"commercial": 0.10, "medicaid": 0.48, "medicare": 0.22, "self_pay": 0.20},
        "comm_pct": 0.10,
        "deal_narrative": (
            "Midwest charitable care network platform consolidating "
            "14 free-clinic and sliding-fee-scale 501(c)(3) "
            "charitable-care operations across Minnesota, Wisconsin, "
            "Iowa, and Missouri serving 58,000 unique patients "
            "annually under a charitable-mission structure with "
            "philanthropic funding, state-grant program support, "
            "and limited commercial-insurance participation for "
            "wraparound revenue. Service mix delivers primary "
            "care, behavioral health, medication-assistance "
            "pharmacy support (via 340B contract-pharmacy "
            "arrangements with affiliated FQHCs), and enabling "
            "services (case-management / interpreter / "
            "transportation). Mid-hold navigating the "
            "fundamentally margin-constrained charitable-care "
            "economics with 48% Medicaid mix and 20% self-pay / "
            "sliding-fee-scale uninsured burden, building "
            "philanthropic-development infrastructure, and "
            "supporting 3 of 14 operating entities on the HRSA "
            "look-alike designation pathway for FQHC PPS "
            "reimbursement access."
        ),
    },
    {
        "company_name": "Ironwood Community Health Services",
        "sector": "Community Health Center",
        "buyer": "Gryphon Investors",
        "year": 2018,
        "region": "Northeast",
        "ev_mm": 345.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 55.20,
        "ebitda_margin": 0.16,
        "revenue_mm": 345.00,
        "hold_years": 5.5,
        "moic": 2.6,
        "irr": 0.1926,
        "status": "Realized",
        "payer_mix": {"commercial": 0.18, "medicaid": 0.56, "medicare": 0.18, "self_pay": 0.08},
        "comm_pct": 0.18,
        "deal_narrative": (
            "Northeast community health center MSO platform "
            "supporting 10 Section 330 grantee CHCs across "
            "Massachusetts, Connecticut, Rhode Island, and New "
            "York with 62 clinical delivery sites serving 320,000 "
            "unique patients in HRSA-designated Medically "
            "Underserved Areas and among Medically Underserved "
            "Populations (MUPs). Service mix delivers integrated "
            "primary care (family medicine, internal medicine, "
            "pediatrics, OB/GYN), behavioral health "
            "(comprehensive outpatient counseling and MAT for "
            "opioid use disorder), dental, vision, and enabling "
            "services. Long hold benefited from the "
            "strongest-in-nation Medicaid expansion coverage in "
            "Massachusetts / Connecticut markets, captured 340B "
            "Drug Pricing Program margin on specialty pharmacy "
            "(HIV, oncology, hepatitis C treatment), optimized "
            "Massachusetts MassHealth and Connecticut HUSKY "
            "Medicaid PPS rate cost-report methodology producing "
            "rate increases averaging 16% at affiliates, and "
            "exited to a strategic nonprofit health system FQHC "
            "affiliate operator at 2.6x MOIC."
        ),
    },
    {
        "company_name": "Riverside Safety-Net Health",
        "sector": "Safety-Net Clinic",
        "buyer": "Council Capital",
        "year": 2019,
        "region": "West",
        "ev_mm": 75.0,
        "ev_ebitda": 10.5,
        "ebitda_mm": 9.75,
        "ebitda_margin": 0.13,
        "revenue_mm": 75.00,
        "hold_years": 5.0,
        "moic": 1.8,
        "irr": 0.1248,
        "status": "Realized",
        "payer_mix": {"commercial": 0.12, "medicaid": 0.50, "medicare": 0.20, "self_pay": 0.18},
        "comm_pct": 0.12,
        "deal_narrative": (
            "West Coast safety-net clinic platform with 14 primary "
            "care delivery sites across California, Oregon, and "
            "Washington operating outside the Section 330 / FQHC "
            "framework but serving Medicaid-heavy and uninsured "
            "populations. Service mix delivers primary care, "
            "behavioral health, limited specialty access, and "
            "medication-assisted treatment for opioid use "
            "disorder. Long hold navigated California Medi-Cal / "
            "Oregon Health Plan / Washington Apple Health "
            "Medicaid-expansion-state payer-mix dynamics, "
            "operated a state-charity-care-equivalent sliding-"
            "fee-scale structure modeled on FQHC program "
            "requirements without formal HRSA designation, "
            "supported 2 of 14 sites through HRSA look-alike "
            "designation application (1 approved, 1 pending at "
            "exit), and exited to a regional FQHC MSO platform "
            "at 1.8x MOIC on the constrained margin profile of "
            "non-designated safety-net operations."
        ),
    },
    {
        "company_name": "Magnolia FQHC Revenue Cycle Services",
        "sector": "FQHC Network",
        "buyer": "Great Hill Partners",
        "year": 2020,
        "region": "Southeast",
        "ev_mm": 225.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 45.00,
        "ebitda_margin": 0.20,
        "revenue_mm": 225.00,
        "hold_years": 4.0,
        "moic": 1.9,
        "irr": 0.1750,
        "status": "Active",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.54, "medicare": 0.22, "self_pay": 0.10},
        "comm_pct": 0.14,
        "deal_narrative": (
            "Southeast FQHC revenue-cycle services platform "
            "supporting 22 Section 330 grantee community health "
            "centers across Tennessee, Alabama, Mississippi, "
            "Louisiana, Georgia, and South Carolina (predominantly "
            "Medicaid-non-expansion states producing elevated "
            "self-pay / sliding-fee-scale mix). Service offering "
            "is FQHC-specific revenue-cycle management including "
            "FQHC PPS (Prospective Payment System) encounter-rate "
            "billing for Medicare and Medicaid, 340B Drug Pricing "
            "Program contract-pharmacy claims processing, sliding "
            "fee scale patient-responsibility calculation at or "
            "below 200% federal poverty level (FPL) discount tiers, "
            "and UDS (Uniform Data System) reporting support for "
            "HRSA annual submission. Mid-hold growing affiliate "
            "base via non-expansion-state FQHC pursuit, "
            "navigating Louisiana Medicaid expansion (2016) and "
            "pending expansion activity in Mississippi / Alabama / "
            "Georgia / Tennessee / South Carolina legislative "
            "sessions, and targeting sale to a strategic "
            "healthcare RCM platform at a compressed multiple."
        ),
    },
    {
        "company_name": "Sequoia FQHC Management Group",
        "sector": "FQHC Network",
        "buyer": "TPG Rise Fund",
        "year": 2017,
        "region": "West",
        "ev_mm": 545.0,
        "ev_ebitda": 14.0,
        "ebitda_mm": 98.10,
        "ebitda_margin": 0.18,
        "revenue_mm": 545.00,
        "hold_years": 6.5,
        "moic": 3.0,
        "irr": 0.1818,
        "status": "Realized",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.60, "medicare": 0.20, "self_pay": 0.06},
        "comm_pct": 0.14,
        "deal_narrative": (
            "West Coast FQHC MSO platform supporting 14 Section "
            "330 grantee community health centers across "
            "California, Oregon, and Washington (three of the "
            "strongest Medicaid-expansion states nationally) with "
            "92 clinical delivery sites serving 580,000 unique "
            "patients. Service mix centered on California Medi-Cal "
            "Managed Care / Oregon Coordinated Care Organization "
            "(CCO) / Washington Apple Health Managed Care "
            "Medicaid-managed-care contracting, FQHC PPS wrap-"
            "payment methodology reconciling managed-care payments "
            "to FQHC PPS encounter rates, and 340B contract-"
            "pharmacy administration capturing specialty-drug "
            "margin on HIV / oncology / hepatitis C. Long 6.5-year "
            "hold grew from 8 to 14 affiliated FQHCs, built "
            "340B contract-pharmacy network to 168 contract "
            "pharmacies, optimized California Medi-Cal PPS rate "
            "cost-report methodology producing rate increases "
            "averaging 18% at affiliates, supported 3 affiliates "
            "through HRSA look-alike-to-Section-330 grantee "
            "conversion, and exited to a strategic Kaiser-"
            "affiliated community-health operator at 3.0x MOIC."
        ),
    },
    {
        "company_name": "Alder Community Health Partners",
        "sector": "Community Health Center",
        "buyer": "Charlesbank Capital Partners",
        "year": 2022,
        "region": "Mid-Atlantic",
        "ev_mm": 155.0,
        "ev_ebitda": 13.5,
        "ebitda_mm": 24.80,
        "ebitda_margin": 0.16,
        "revenue_mm": 155.00,
        "hold_years": 3.0,
        "moic": 1.5,
        "irr": 0.1447,
        "status": "Active",
        "payer_mix": {"commercial": 0.16, "medicaid": 0.58, "medicare": 0.18, "self_pay": 0.08},
        "comm_pct": 0.16,
        "deal_narrative": (
            "Mid-Atlantic community health center platform "
            "supporting 5 Section 330 grantee CHCs across "
            "Pennsylvania, New Jersey, Delaware, and Maryland "
            "with 26 clinical delivery sites serving 140,000 "
            "unique patients. Service mix delivers comprehensive "
            "primary care, behavioral health, MAT (medication-"
            "assisted treatment) for opioid use disorder — a "
            "material service line given the Mid-Atlantic opioid "
            "crisis concentration — dental, and enabling services. "
            "Early hold acquired post-2022 multiple reset "
            "navigating HRSA Section 330 grant base-funding "
            "uncertainty in the post-ARPA (American Rescue Plan "
            "Act) supplemental-funding wind-down environment, "
            "340B Drug Pricing Program regulatory and "
            "manufacturer-contract pressure on contract-pharmacy "
            "arrangements, and state Medicaid agency PPS rate "
            "rebasing cycles in Pennsylvania and New Jersey. "
            "Sponsor pursuing value creation via UDS (Uniform "
            "Data System) quality-reporting optimization and "
            "340B specialty-drug pipeline expansion."
        ),
    },
    {
        "company_name": "Prairie Safety-Net Alliance",
        "sector": "Safety-Net Clinic",
        "buyer": "Webster Equity Partners",
        "year": 2018,
        "region": "Midwest",
        "ev_mm": 115.0,
        "ev_ebitda": 12.0,
        "ebitda_mm": 16.10,
        "ebitda_margin": 0.14,
        "revenue_mm": 115.00,
        "hold_years": 5.5,
        "moic": 2.3,
        "irr": 0.1646,
        "status": "Realized",
        "payer_mix": {"commercial": 0.14, "medicaid": 0.50, "medicare": 0.22, "self_pay": 0.14},
        "comm_pct": 0.14,
        "deal_narrative": (
            "Midwest safety-net clinic alliance with 18 primary "
            "care and behavioral health delivery sites across "
            "Illinois, Indiana, Wisconsin, and Kentucky operating "
            "in a mix of state-charity-care program structures "
            "and hospital-affiliated charity-care arrangements. "
            "Service mix delivers primary care, behavioral health, "
            "limited specialty access via affiliated-hospital "
            "referral relationships, and MAT for opioid use "
            "disorder. Long hold navigated Kentucky (2014) / "
            "Indiana (2015) / Illinois (2014) Medicaid expansion "
            "timing differentials versus Wisconsin "
            "non-expansion status, supported 6 of 18 sites "
            "through HRSA look-alike designation application "
            "(4 approved by exit, 2 pending), captured "
            "state-charity-care-program reimbursement across "
            "Illinois Charity Care Bureau / Indiana Hospital "
            "Assessment Fee / Kentucky state programs, and "
            "exited to a strategic FQHC MSO at 2.3x MOIC on "
            "the FQHC-designation-pathway value-creation "
            "thesis."
        ),
    },
    {
        "company_name": "Highland Look-Alike Health Network",
        "sector": "Look-Alike FQHC",
        "buyer": "Nautic Partners",
        "year": 2021,
        "region": "Northeast",
        "ev_mm": 245.0,
        "ev_ebitda": 15.0,
        "ebitda_mm": 41.65,
        "ebitda_margin": 0.17,
        "revenue_mm": 245.00,
        "hold_years": 3.5,
        "moic": 1.6,
        "irr": 0.1418,
        "status": "Active",
        "payer_mix": {"commercial": 0.20, "medicaid": 0.54, "medicare": 0.18, "self_pay": 0.08},
        "comm_pct": 0.20,
        "deal_narrative": (
            "Northeast FQHC Look-Alike platform with 22 clinical "
            "delivery sites across New York, New Jersey, "
            "Connecticut, and Massachusetts operating under HRSA "
            "look-alike designation with FQHC PPS (Prospective "
            "Payment System) reimbursement status, 340B Drug "
            "Pricing Program participation, and FTCA (Federal "
            "Tort Claims Act) medical malpractice coverage but "
            "without Section 330 grant funding receipt. Service "
            "mix delivers integrated primary care, behavioral "
            "health with SBIRT screening, dental, and MAT for "
            "opioid use disorder. Mid-hold acquired at peak 2021 "
            "healthcare services multiples, navigating 340B "
            "Drug Pricing Program regulatory pressure "
            "(HRSA-manufacturer contract-pharmacy disputes, "
            "restrictive-dispense manufacturer policies at "
            "Eli Lilly / Sanofi / AstraZeneca / Boehringer "
            "Ingelheim / Novartis / Merck limiting "
            "contract-pharmacy eligibility), pursuing 4 "
            "affiliates on the Section 330 grantee conversion "
            "pathway to shift from look-alike-only to full "
            "Section 330 grantee status, and optimizing UDS "
            "reporting for clinical-quality-measure "
            "performance."
        ),
    },
    {
        "company_name": "Evergreen Community Care Holdings",
        "sector": "Community Health Center",
        "buyer": "Great Point Partners",
        "year": 2016,
        "region": "National",
        "ev_mm": 825.0,
        "ev_ebitda": 14.5,
        "ebitda_mm": 148.50,
        "ebitda_margin": 0.18,
        "revenue_mm": 825.00,
        "hold_years": 6.5,
        "moic": 3.4,
        "irr": 0.2035,
        "status": "Realized",
        "payer_mix": {"commercial": 0.16, "medicaid": 0.62, "medicare": 0.16, "self_pay": 0.06},
        "comm_pct": 0.16,
        "deal_narrative": (
            "National community health center MSO platform acquired "
            "early in the post-ACA FQHC growth cycle, scaled to "
            "support 34 Section 330 grantee CHCs across 18 states "
            "with 245 clinical delivery sites serving 1.2 million "
            "unique patients. MSO contract structure delivers "
            "comprehensive shared-services support: FQHC-specific "
            "revenue-cycle management (FQHC PPS encounter-rate "
            "billing), 340B contract-pharmacy network "
            "administration, EHR hosting (athenahealth / NextGen / "
            "eClinicalWorks / OCHIN Epic community-FQHC Epic "
            "instance), HR / credentialing / compliance, "
            "finance / UDS reporting, and HRSA compliance support "
            "for Section 330 grant continuation. Long 6.5-year "
            "hold grew from 18 to 34 affiliated FQHCs, built 340B "
            "contract-pharmacy network to 560 contract "
            "pharmacies, supported 12 affiliates through Section "
            "330 grant expansion cycles and 4 affiliates through "
            "look-alike-to-grantee conversion, achieved Medicaid "
            "PPS rate rebasing at 14 affiliates producing rate "
            "increases averaging 16-20%, captured material "
            "340B specialty-drug margin on HIV / oncology / "
            "hepatitis C pipelines, navigated the 2017-2022 "
            "regulatory cycle on HRSA / CMS / state Medicaid "
            "FQHC program evolution, and exited to a strategic "
            "diversified healthcare-services platform at 3.4x "
            "MOIC on the most scaled FQHC MSO exit in the cycle."
        ),
    },
]
