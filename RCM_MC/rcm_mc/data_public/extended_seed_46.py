"""Extended seed deals – batch 46.

Covers dental and ophthalmic subspecialties with distinct RCM/billing
complexity profiles spanning DSOs, dental labs, vision retail, and
surgical and medical ophthalmology niches.
"""

EXTENDED_SEED_DEALS_46 = [
    {
        "source_id": "ext46_001",
        "source": "seed",
        "company_name": "BrightSmile Pediatric Dentistry & Orthodontics",
        "sector": "Pediatric Dentistry / Orthodontics",
        "year": 2018,
        "buyer": "Shore Capital Partners",
        "ev_mm": 195.0,
        "ebitda_at_entry_mm": 19.5,
        "moic": 3.4,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.50,
            "medicare": 0.02,
            "medicaid": 0.40,
            "other": 0.08,
        },
        "notes": (
            "Pediatric dental practices must navigate dual billing streams: medical "
            "dental codes (CDT) for diagnostic and preventive services under Medicaid "
            "CHIP programs alongside orthodontic records codes (D8080) with banding "
            "fees spread across contract periods, requiring installment-payment "
            "tracking in the RCM system. Medicaid prior-authorization for orthodontic "
            "treatment demands Handicapping Labio-lingual Deviation (HLD) index "
            "scoring, and denials for incomplete index documentation are the leading "
            "source of write-offs in this sector."
        ),
    },
    {
        "source_id": "ext46_002",
        "source": "seed",
        "company_name": "Summit Oral & Maxillofacial Surgery Partners",
        "sector": "Oral Surgery / Maxillofacial",
        "year": 2016,
        "buyer": "Heartwood Partners",
        "ev_mm": 280.0,
        "ebitda_at_entry_mm": 26.0,
        "moic": 3.6,
        "irr": 0.31,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.62,
            "medicare": 0.14,
            "medicaid": 0.16,
            "other": 0.08,
        },
        "notes": (
            "Oral and maxillofacial surgery occupies a billing gray zone between "
            "dental and medical payers: procedures such as impacted wisdom tooth "
            "removal (CDT D7240) may be billed under dental benefits or, when "
            "performed in a hospital setting under general anesthesia, under medical "
            "CPT codes (41899), triggering dual-eligibility coordination challenges. "
            "Anesthesia billing requires a separate CRNA or MD anesthesia claim with "
            "base units plus time units, and payer inconsistency on whether the "
            "surgeon or anesthesiologist's claim is primary drives frequent denial "
            "cycles requiring manual adjudication."
        ),
    },
    {
        "source_id": "ext46_003",
        "source": "seed",
        "company_name": "RootCause Endodontics Network",
        "sector": "Endodontics / Root Canal",
        "year": 2019,
        "buyer": "Riverside Partners",
        "ev_mm": 160.0,
        "ebitda_at_entry_mm": 16.0,
        "moic": 3.2,
        "irr": 0.28,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.68,
            "medicare": 0.03,
            "medicaid": 0.22,
            "other": 0.07,
        },
        "notes": (
            "Endodontic practices bill root canal therapy under CDT codes D3310–D3330 "
            "differentiated by tooth type (anterior, premolar, molar), and incorrect "
            "tooth-classification coding is a leading cause of payer downcoding that "
            "reduces reimbursement by 15–25% per claim without a denial flag. Many "
            "commercial dental plans impose separate annual maximums or frequency "
            "limitations on endodontic retreatment (D3346–D3348), requiring real-time "
            "benefit verification to avoid balance-billing disputes with patients."
        ),
    },
    {
        "source_id": "ext46_004",
        "source": "seed",
        "company_name": "PerioCare Implant & Periodontic Centers",
        "sector": "Periodontics / Implant Dentistry",
        "year": 2017,
        "buyer": "Gauge Capital",
        "ev_mm": 220.0,
        "ebitda_at_entry_mm": 22.0,
        "moic": 3.3,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.58,
            "medicare": 0.05,
            "medicaid": 0.18,
            "other": 0.19,
        },
        "notes": (
            "Periodontal practices generate high patient out-of-pocket balances because "
            "most dental plans exclude implants (D6010–D6067) entirely or cap annual "
            "implant benefits below procedure cost, requiring in-house financing "
            "and third-party patient-financing integration in the RCM workflow. Scaling "
            "and root planing (D4341/D4342) is frequently subject to frequency edits "
            "requiring radiographic and probing-depth documentation to substantiate "
            "medical necessity, and insurers routinely downgrade full-mouth treatment "
            "to a partial-mouth benefit when quadrant separation is not clearly recorded."
        ),
    },
    {
        "source_id": "ext46_005",
        "source": "seed",
        "company_name": "DentalFirst DSO General Practice Group",
        "sector": "Dental Service Organization (DSO) General Practice",
        "year": 2015,
        "buyer": "Ares Management",
        "ev_mm": 820.0,
        "ebitda_at_entry_mm": 74.0,
        "moic": 3.8,
        "irr": 0.33,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.04,
            "medicaid": 0.35,
            "other": 0.06,
        },
        "notes": (
            "DSO general-practice platforms consolidate billing across dozens of "
            "dental offices under a single TIN or group NPI, but legacy single-office "
            "CDT billing habits and payer-contract fee schedules negotiated at the "
            "site level create a fragmented charge-master environment that requires "
            "systematic normalization post-acquisition. Medicaid dental carve-outs "
            "through managed-care dental organizations (MCDOs) require each acquired "
            "office to re-credential under the DSO's group provider agreement, creating "
            "a revenue gap of 60–120 days per de novo or acquired location."
        ),
    },
    {
        "source_id": "ext46_006",
        "source": "seed",
        "company_name": "PrecisionCraft Dental Lab & CAD/CAM Prosthetics",
        "sector": "Dental Lab / CAD/CAM Prosthetics",
        "year": 2014,
        "buyer": "Sheridan Capital Partners",
        "ev_mm": 115.0,
        "ebitda_at_entry_mm": 11.5,
        "moic": 3.0,
        "irr": 0.26,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.44,
            "medicare": 0.08,
            "medicaid": 0.28,
            "other": 0.20,
        },
        "notes": (
            "Dental laboratory revenue is primarily B2B—billed to dentist practices "
            "rather than payers—but outsourced lab cases for federally qualified health "
            "centers and Medicaid clinics require CDT lab-fee codes (D9985) and "
            "case-tracking documentation to support the referring dentist's claim. "
            "The shift to CAD/CAM milling introduces materials-cost variability that "
            "must be reconciled against fixed-fee lab invoices when supporting payer "
            "audits of prosthetic procedure fees submitted by client offices."
        ),
    },
    {
        "source_id": "ext46_007",
        "source": "seed",
        "company_name": "ClearVision Optical Retail Group",
        "sector": "Vision / Optical Retail",
        "year": 2020,
        "buyer": "Apax Partners",
        "ev_mm": 640.0,
        "ebitda_at_entry_mm": 58.0,
        "moic": 3.5,
        "irr": 0.30,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.52,
            "medicare": 0.18,
            "medicaid": 0.20,
            "other": 0.10,
        },
        "notes": (
            "Optical retail chains bill a hybrid of professional exam services (CPT "
            "92004/92014) and vision-benefit product claims (frames and lenses under "
            "VSP, EyeMed, or Davis Vision networks), with each payer imposing separate "
            "fee schedules, frame allowances, and lens-upgrade co-pay structures that "
            "require point-of-sale RCM integration to prevent undercollection. Medicare "
            "covers routine exams only when medically necessary (e.g., for diabetic "
            "eye disease under CPT 92250), and misrouting routine exams to Medicare "
            "generates denials that are the highest-volume coding error in this sector."
        ),
    },
    {
        "source_id": "ext46_008",
        "source": "seed",
        "company_name": "SpectraLens Contact Lens Specialty Clinics",
        "sector": "Contact Lens Specialty",
        "year": 2021,
        "buyer": "Vistria Group",
        "ev_mm": 130.0,
        "ebitda_at_entry_mm": 13.0,
        "moic": 2.8,
        "irr": 0.24,
        "hold_years": 3.5,
        "payer_mix": {
            "commercial": 0.60,
            "medicare": 0.10,
            "medicaid": 0.14,
            "other": 0.16,
        },
        "notes": (
            "Contact lens specialty practices separately bill the fitting fee (CPT "
            "92310–92317 based on lens type) and the contact lens materials under "
            "vision-benefit plans that impose annual contact lens allowances distinct "
            "from spectacle-lens benefits, requiring parallel benefit-verification "
            "workflows for each product type. Specialty scleral and rigid gas-permeable "
            "lenses billed to medical plans (e.g., for keratoconus) require an ICD-10 "
            "medical-necessity diagnosis and prior authorization from commercial payers, "
            "substantially increasing administrative cost per unit relative to soft lens "
            "dispensing."
        ),
    },
    {
        "source_id": "ext46_009",
        "source": "seed",
        "company_name": "LuminanceVision Low Vision Rehab Network",
        "sector": "Low Vision Rehabilitation",
        "year": 2013,
        "buyer": "Consonance Capital Partners",
        "ev_mm": 72.0,
        "ebitda_at_entry_mm": 8.0,
        "moic": 2.9,
        "irr": 0.27,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.28,
            "medicare": 0.48,
            "medicaid": 0.18,
            "other": 0.06,
        },
        "notes": (
            "Low vision rehabilitation services are billed under CPT 97003 (OT "
            "evaluation) and 92065 (orthoptic/pleoptic training) with Medicare "
            "covering therapeutic services under the outpatient rehabilitation "
            "benefit subject to therapy-cap thresholds and KX-modifier exceptions, "
            "requiring meticulous functional-limitation documentation in each progress "
            "note to withstand ADR audits. Low-vision aids and optical devices are "
            "billed separately as DME under HCPCS V2600-series codes, creating a "
            "split-billing workflow where the same patient encounter generates both "
            "a therapy claim and a DME claim through separate billing pathways."
        ),
    },
    {
        "source_id": "ext46_010",
        "source": "seed",
        "company_name": "ClearSight Refractive Surgery & LASIK Centers",
        "sector": "Refractive Surgery / LASIK",
        "year": 2018,
        "buyer": "KKR",
        "ev_mm": 480.0,
        "ebitda_at_entry_mm": 44.0,
        "moic": 4.0,
        "irr": 0.35,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.15,
            "medicare": 0.05,
            "medicaid": 0.02,
            "other": 0.78,
        },
        "notes": (
            "Refractive surgery centers operate largely outside traditional insurance "
            "reimbursement because LASIK and PRK are elective procedures excluded "
            "from most commercial and government payer contracts, making the 'other' "
            "category—primarily self-pay and employer vision-benefit discounts—the "
            "dominant revenue stream. The RCM challenge centers on financing-product "
            "integration (CareCredit, Alphaeon), package-price versus per-eye billing "
            "reconciliation, and post-op enhancement billing, where some contracts "
            "include lifetime enhancement coverage that must be tracked to avoid "
            "double-billing complications."
        ),
    },
    {
        "source_id": "ext46_011",
        "source": "seed",
        "company_name": "CornealCare Anterior Segment Specialists",
        "sector": "Cornea / Anterior Segment",
        "year": 2017,
        "buyer": "Frazier Healthcare Partners",
        "ev_mm": 210.0,
        "ebitda_at_entry_mm": 21.0,
        "moic": 3.3,
        "irr": 0.29,
        "hold_years": 4.5,
        "payer_mix": {
            "commercial": 0.46,
            "medicare": 0.38,
            "medicaid": 0.10,
            "other": 0.06,
        },
        "notes": (
            "Corneal transplant surgery (PKP, DSAEK, DMEK) generates complex split-"
            "billing between the surgeon's professional fee (CPT 65710–65757) and the "
            "corneal tissue acquisition fee, which is separately reimbursed by Medicare "
            "under a flat add-on amount and by commercial payers at varying invoice-"
            "based rates, requiring tissue-registry invoice reconciliation within the "
            "RCM workflow to prevent undercollection. Dry eye disease management "
            "revenue—increasingly via LipiFlow or intense-pulsed-light devices—is "
            "largely non-covered by payers, demanding a self-pay pricing and consent "
            "process that must be operationally distinct from the insured visit workflow."
        ),
    },
    {
        "source_id": "ext46_012",
        "source": "seed",
        "company_name": "NeurOptix Neuro-Ophthalmology Associates",
        "sector": "Neuro-Ophthalmology",
        "year": 2016,
        "buyer": "Nautic Partners",
        "ev_mm": 145.0,
        "ebitda_at_entry_mm": 14.5,
        "moic": 3.1,
        "irr": 0.27,
        "hold_years": 5.0,
        "payer_mix": {
            "commercial": 0.44,
            "medicare": 0.42,
            "medicaid": 0.08,
            "other": 0.06,
        },
        "notes": (
            "Neuro-ophthalmology practices bill at the intersection of ophthalmology "
            "and neurology fee schedules, where the same visual-field test (CPT 92083) "
            "is reimbursed at different rates depending on whether it is submitted "
            "under the ophthalmology or neurology specialty taxonomy, creating a "
            "deliberate taxonomy-management requirement in provider enrollment. "
            "Diagnostic imaging such as orbital MRI (CPT 70553) ordered and interpreted "
            "by the same neuro-ophthalmologist requires separate professional and "
            "technical component billing with -26 and -TC modifiers, and payer "
            "policies on global vs. split billing vary by contract, elevating the "
            "risk of systematic under-reimbursement without active contract-edit monitoring."
        ),
    },
    {
        "source_id": "ext46_013",
        "source": "seed",
        "company_name": "VisionKids Pediatric Ophthalmology & Strabismus Group",
        "sector": "Pediatric Ophthalmology / Strabismus",
        "year": 2019,
        "buyer": "Lee Equity Partners",
        "ev_mm": 175.0,
        "ebitda_at_entry_mm": 17.5,
        "moic": 3.5,
        "irr": 0.31,
        "hold_years": 4.0,
        "payer_mix": {
            "commercial": 0.50,
            "medicare": 0.03,
            "medicaid": 0.42,
            "other": 0.05,
        },
        "notes": (
            "Pediatric ophthalmology practices rely heavily on Medicaid for strabismus "
            "surgery (CPT 67311–67340) and amblyopia management, where EPSDT mandates "
            "coverage but Medicaid managed-care plans impose prior-authorization "
            "requirements and surgery-facility credentialing that extend scheduling "
            "timelines and create revenue-cycle lag. Vision therapy billed for amblyopia "
            "(CPT 92065) is excluded by many commercial plans or subjected to strict "
            "visit-number caps, requiring proactive benefit verification and patient "
            "financial counseling to prevent surprise balances that drive bad-debt write-offs."
        ),
    },
    {
        "source_id": "ext46_014",
        "source": "seed",
        "company_name": "OcuOnco Ophthalmic Oncology Centers",
        "sector": "Ocular Oncology",
        "year": 2015,
        "buyer": "New Enterprise Associates",
        "ev_mm": 95.0,
        "ebitda_at_entry_mm": 9.5,
        "moic": 3.2,
        "irr": 0.28,
        "hold_years": 5.5,
        "payer_mix": {
            "commercial": 0.48,
            "medicare": 0.36,
            "medicaid": 0.10,
            "other": 0.06,
        },
        "notes": (
            "Ocular oncology centers bill radiation-based treatments such as episcleral "
            "plaque brachytherapy (CPT 77778) under both ophthalmic and radiation "
            "oncology fee schedules, requiring co-management billing coordination "
            "between the ophthalmologist and radiation physicist that must be explicitly "
            "documented in a co-management agreement to avoid Medicare split-billing "
            "denials. Proton beam therapy for uveal melanoma at academic centers "
            "requires pre-authorization under most commercial contracts and Medicare "
            "Advantage plans, and the documentation packet—including ocular pathology, "
            "tumor measurement, and treatment planning records—must be assembled within "
            "tight authorization windows to prevent revenue delay."
        ),
    },
    {
        "source_id": "ext46_015",
        "source": "seed",
        "company_name": "OculoPlastics & Orbital Reconstructive Surgery Group",
        "sector": "Ophthalmic Plastic Surgery / Oculoplastics",
        "year": 2022,
        "buyer": "Warburg Pincus",
        "ev_mm": 340.0,
        "ebitda_at_entry_mm": 31.0,
        "moic": 2.6,
        "irr": 0.23,
        "hold_years": 3.0,
        "payer_mix": {
            "commercial": 0.55,
            "medicare": 0.28,
            "medicaid": 0.08,
            "other": 0.09,
        },
        "notes": (
            "Oculoplastic practices must rigorously distinguish functional from cosmetic "
            "procedures in their coding: upper-lid blepharoplasty (CPT 15822/15823) "
            "is reimbursable when visual-field testing documents superior-field "
            "obstruction exceeding 30%, but payers routinely request the Humphrey "
            "visual-field printout as a claim attachment, and missing attachments are "
            "the single largest denial driver. Botulinum toxin injections for blepharospasm "
            "(J0585/J0587) are billed under the medical benefit at drug-acquisition "
            "cost plus an administration fee, requiring buy-and-bill drug-inventory "
            "reconciliation and J-code unit accuracy to avoid payer-initiated drug "
            "audits and recoupment demands."
        ),
    },
]
