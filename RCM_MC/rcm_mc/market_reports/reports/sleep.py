"""Sleep — sleep-disordered-breathing diagnosis and CPAP/DME therapy.

Deals-only pattern (no vendored sleep-lab census — AASM accreditation lists
aren't vendored). Authored around the two forces that define the sector: the
payer-driven site-of-service shift from the attended in-lab polysomnogram to the
home sleep apnea test (HSAT), which is a structural price cut on the diagnostic
side, and the adherence-gated CPAP/DME resupply annuity, which is where the
durable margin lives. Live SOURCED figures come from ``sleep_deep_dive()``.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver, default_connections,
    live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="sleep",
    name="Sleep",
    care_setting="Ambulatory",
    naics="621498",
    one_line_def=(
        "Diagnosis and treatment of sleep-disordered breathing (chiefly "
        "obstructive sleep apnea) and other sleep disorders — attended in-lab "
        "polysomnography vs. home sleep apnea testing (HSAT), the sleep-"
        "physician interpretation, and the downstream CPAP/DME therapy and "
        "adherence management."),
    tam_headline=TamHeadline(
        value=9.0, unit="$B", growth_pct=5.0, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Modeled US clinical sleep economy — diagnostic testing (in-lab "
            "PSG + HSAT) plus PAP/DME therapy and resupply. Industry estimates "
            "and CMS utilization put testing + therapy services in the high-"
            "single-digit $B. The site-of-service shift from in-lab to home is "
            "deflationary on diagnostics while DME resupply grows — a mix "
            "story, not a pure-volume one. ILLUSTRATIVE."),
    ),
    executive_summary=[
        "The whole sector is being re-priced by a site-of-service shift: payers "
        "and Medicare now steer sleep-apnea testing from the expensive attended "
        "in-lab polysomnogram to the cheap home sleep apnea test (HSAT). In-lab "
        "bed volume and revenue are structurally shrinking — the lab-heavy "
        "model is a melting ice cube.",
        "The durable annuity is CPAP DME resupply, not the diagnostic study. "
        "Diagnosis is a low-frequency event; masks, tubing, and filters "
        "resupply on a recurring schedule and are gated by documented "
        "adherence — the recurring, high-margin base a buyer underwrites.",
        "Reimbursement is adherence-gated. Medicare's CPAP coverage requires a "
        "qualifying AHI plus a 90-day compliance demonstration (objective usage "
        "data) to keep paying — so adherence management IS the revenue engine, "
        "and non-adherence is denied and recouped revenue.",
        "Vertical integration (test → interpret → dispense DME) is the value "
        "play, but it collides head-on with Stark/Anti-Kickback: a physician "
        "who orders the study and also profits from the CPAP is the textbook "
        "self-referral fact pattern.",
        "The Philips Respironics recall (2021) froze device supply, shifted "
        "share to ResMed, and left an adherence/replacement overhang the whole "
        "channel is still working through — a live diligence factor on any "
        "DME-integrated sleep asset.",
        "Demand is large and under-diagnosed (OSA prevalence tracks obesity and "
        "aging), but GLP-1 weight-loss drugs are a genuine two-sided wildcard — "
        "expanding screening today while potentially shrinking the severe-OSA "
        "population over a long hold.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Primary-care / ENT / cardiology referral or screening (STOP-BANG)",
            "Sleep-physician evaluation + testing decision (in-lab vs HSAT)",
            "Study performed & scored (attended PSG or home test)",
            "Physician interpretation + therapy prescription",
            "DME dispense & setup (PAP device, mask fitting)",
            "90-day adherence monitoring (objective usage download)",
            "Recurring mask/consumable resupply — the annuity",
        ],
        sites_of_care=[
            "Hospital-based sleep lab (HOPD)",
            "Independent diagnostic testing facility (IDTF) / freestanding lab",
            "Physician-office sleep testing",
            "The patient's home (HSAT)",
            "DME / telehealth layer managing therapy remotely",
        ],
        money_flow=(
            "Two revenue streams paid two ways. The diagnostic study is billed "
            "under the Medicare Physician Fee Schedule and commercial "
            "equivalents — a professional (interpretation) component and a "
            "technical/facility component, higher for an attended in-lab "
            "polysomnogram (CPT 95810/95811) than for a home study (95806 / "
            "HCPCS G0399) — and payers increasingly require the cheaper home "
            "test first, compressing lab revenue. The therapy stream is DME: "
            "PAP devices are a Medicare capped-rental (paid monthly over ~13 "
            "months, then owned), and continued payment past the trial requires "
            "documented adherence; the recurring resupply of masks and "
            "consumables is a separate, higher-frequency DME annuity. Prior "
            "authorization and adherence documentation gate both."),
        key_players=(
            "A fragmented provider base — hospital sleep programs, independent "
            "labs/IDTFs, and sleep-physician practices — sits between two "
            "concentrated ends: device makers upstream (ResMed and Philips "
            "Respironics dominate PAP; Inspire Medical for hypoglossal-nerve-"
            "stimulation implants) and DME/telehealth distributors downstream. "
            "Vertically-integrated sleep-plus-DME operators and digital "
            "adherence platforms (value-based sleep management) are the roll-up "
            "and disruption vectors."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("In-lab attended polysomnography (PSG)",
                    "declining share; higher-revenue study",
                    "INDUSTRY · sleep-medicine utilization"),
            Segment("Home sleep apnea testing (HSAT)",
                    "fast-growing, payer-preferred",
                    "GOV · CMS / commercial coverage policy"),
            Segment("PAP devices + capped-rental therapy",
                    "the initial therapy stream",
                    "GOV · Medicare DME capped-rental"),
            Segment("CPAP resupply (masks / consumables)",
                    "the recurring annuity",
                    "ILLUSTRATIVE · DME resupply cadence"),
            Segment("Oral appliances & hypoglossal-nerve stimulation",
                    "growing PAP alternatives",
                    "INDUSTRY · device & procedure trackers"),
        ],
        growth_drivers=[
            "OSA prevalence rising with obesity and aging",
            "Large undiagnosed pool entering testing (HSAT lowers the barrier)",
            "HSAT expanding total tested volume at lower price per study",
            "CPAP resupply adherence programs compounding the installed base",
            "Inspire / oral-appliance alternatives expanding treated population",
            "GLP-1 weight-loss drugs — a two-sided demand factor",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Medicare / MA": 0.45,
            "Commercial": 0.45,
            "Medicaid / self-pay": 0.10,
        },
        rate_mechanics=[
            "Medicare Physician Fee Schedule (+ commercial equivalents) for the "
            "study — separate professional (interpretation) and technical "
            "components; the HOPD / IDTF / office site changes the facility "
            "payment.",
            "Payer site-of-service steerage — coverage policies increasingly "
            "require an HSAT before authorizing an attended in-lab PSG, "
            "compressing lab reimbursement.",
            "CPAP National Coverage Determination — coverage requires a "
            "qualifying AHI/RDI plus a 90-day adherence demonstration "
            "(objective usage, commonly ≥4 hrs/night on ≥70% of nights) to "
            "continue payment.",
            "DME capped-rental — PAP devices paid monthly for ~13 months then "
            "transfer to the patient; resupply of masks/consumables is billed "
            "on a schedule with medical-necessity/adherence documentation.",
            "Prior authorization & DMEPOS competitive bidding — pressure PAP "
            "and resupply margins and add administrative friction.",
        ],
        reimbursement_risk=(
            "The diagnostic side faces a structural price cut as payers force "
            "volume from the in-lab PSG to the home study — a lab priced on "
            "bed-nights is exposed. The therapy side lives or dies on adherence "
            "documentation: Medicare and commercial payers will not continue to "
            "pay for a CPAP the patient isn't using, so failed adherence "
            "converts to denied and recouped revenue. Add DME competitive "
            "bidding and prior-authorization friction, and the durable margin "
            "sits with operators who can prove adherence at scale — not with "
            "the testing asset itself."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("CMS CPAP/PAP National Coverage Determination (NCD 240.4)",
                 "Sets the AHI threshold and the 90-day adherence rule that "
                 "gate CPAP coverage — the single most important reimbursement "
                 "rule in the sector.",
                 "https://www.cms.gov/medicare-coverage-database/"),
            Rule("Medicare IDTF supplier standards",
                 "Freestanding sleep-testing facilities must meet Independent "
                 "Diagnostic Testing Facility enrollment and performance "
                 "standards to bill Medicare.",
                 "https://www.cms.gov/"),
            Rule("Stark Law & Anti-Kickback Statute",
                 "Physician self-referral and referral-for-DME prohibitions; "
                 "the test → interpret → dispense integration is exactly the "
                 "fact pattern these target.",
                 "https://oig.hhs.gov/"),
            Rule("AASM accreditation (facility & HSAT)",
                 "The American Academy of Sleep Medicine's accreditation is the "
                 "de facto quality standard many payers require to reimburse "
                 "studies.",
                 "https://aasm.org/"),
            Rule("FDA device regulation & the Philips Respironics recall",
                 "PAP and HSAT devices are 510(k) medical devices; the 2021 "
                 "Philips recall reshaped supply and left a replacement/"
                 "adherence overhang.",
                 "https://www.fda.gov/medical-devices"),
        ],
        policy_watch=[
            "Continued payer HSAT-first mandates compressing in-lab revenue",
            "DMEPOS competitive-bidding rounds on PAP and resupply",
            "Scrutiny of sleep-DME self-referral (Stark/AKS)",
            "GLP-1 coverage & OSA-indication developments (tirzepatide)",
            "Telehealth prescribing of PAP and resupply audit activity",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "The provider layer is fragmented — hospital sleep programs, "
            "independent labs/IDTFs, and sleep-physician practices — even as "
            "the device layer (ResMed/Philips) and, increasingly, the "
            "DME/telehealth distribution layer concentrate. In-lab capacity is "
            "oversupplied relative to a shrinking attended-study volume."),
        hhi_or_share=(
            "No dominant national sleep-services operator; concentration lives "
            "upstream in devices (ResMed + Philips) rather than in testing. No "
            "public lab census (AASM accreditation lists aren't vendored), so "
            "provider share is honestly unquantified."),
        consolidation=(
            "Consolidation follows the money downstream: DME/resupply roll-ups "
            "and vertically-integrated 'test-to-therapy' platforms, plus "
            "digital adherence managers. Freestanding-lab roll-ups have faded "
            "with in-lab volume; the durable platform owns the resupply annuity "
            "and the adherence data."),
        pe_activity=(
            "PE interest has migrated from bricks-and-mortar labs toward DME "
            "resupply, telehealth-enabled diagnosis-to-therapy models, and "
            "value-based sleep management paid for adherence/outcomes. Inspire "
            "Medical built a large public franchise on the PAP-intolerant "
            "segment via hypoglossal-nerve stimulation."),
        notable_players=[
            "ResMed", "Philips Respironics", "Inspire Medical Systems",
            "Lincare (DME)", "Hospital sleep programs", "Nox Medical (HSAT)",
            "Digital / value-based sleep-management platforms",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("In-lab bed utilization (studies/bed/week)", "under pressure",
                "Under-utilization is the melting-lab problem — reverse "
                "operating leverage on a fixed bed/tech cost base."),
            Kpi("HSAT mix (% of studies home vs in-lab)", "rising",
                "The site-shift indicator — higher HSAT means lower revenue per "
                "study but higher volume."),
            Kpi("Resupply revenue mix & pull-through", "the annuity",
                "Share of revenue that is recurring DME resupply, and how many "
                "diagnoses convert to a monitored therapy patient."),
            Kpi("Adherence / compliance rate (90-day rule)", "the payment gate",
                "The percentage of patients meeting the objective-usage "
                "threshold — it directly gates continued payment."),
            Kpi("Denial / prior-auth rate (studies & DME)", "RCM friction",
                "Where gated reimbursement is won or lost operationally."),
            Kpi("Revenue per study (blended PSG vs HSAT)", "compressing",
                "The price the mix shift is grinding down on the diagnostic "
                "side."),
        ],
        margin_profile=(
            "A pure in-lab testing business carries high fixed cost (beds, "
            "techs, real estate) against a shrinking attended-study volume — "
            "operating leverage running in reverse. The attractive economics "
            "are downstream: CPAP resupply is high-gross-margin, recurring, and "
            "scales with the installed base rather than bed-nights. Integrated "
            "operators that convert a diagnosis into a monitored, adherent "
            "therapy patient earn the annuity; standalone labs are squeezed "
            "between HSAT pricing and fixed cost. Ranges are ILLUSTRATIVE — "
            "confirm against the target's own financials."),
    ),
    risks=[
        Risk("In-lab volume decline (HSAT site-shift)", "High",
             "Payer steerage structurally cuts the higher-revenue attended "
             "study; a bed-heavy P&L is a melting ice cube."),
        Risk("Adherence-gated denial / recoupment", "High",
             "CPAP payment stops without documented use; failed adherence is "
             "lost and recouped revenue."),
        Risk("Stark / AKS on test-to-DME integration", "High",
             "The value play is the exact self-referral fact pattern "
             "regulators target."),
        Risk("DME competitive bidding & prior auth", "Medium",
             "Compresses PAP/resupply margins and adds administrative "
             "friction."),
        Risk("Philips recall supply / adherence overhang", "Medium",
             "Device availability and replacement dynamics are still "
             "normalizing across the channel."),
        Risk("GLP-1 long-run OSA prevalence erosion", "Medium",
             "Broad weight loss could shrink the severe-OSA pool over a long "
             "hold — a genuine two-sided factor."),
    ],
    diligence_questions=[
        "What is the in-lab vs HSAT study mix and its trend, and how much "
        "revenue is tied to attended in-lab beds?",
        "What share of revenue is recurring DME resupply, and what is the pull-"
        "through from new diagnoses to therapy?",
        "What is the documented adherence rate, and how are 90-day compliance "
        "and resupply medical-necessity handled operationally?",
        "How is the test → interpret → dispense chain structured against "
        "Stark/AKS (who orders, who profits from the DME)?",
        "What is the payer mix and the prior-authorization / denial rate on "
        "studies and on DME?",
        "What is the device-supply exposure (Philips vs ResMed) and any recall-"
        "related replacement liability?",
        "How would broad GLP-1 adoption change severe-OSA testing and therapy "
        "volumes over the hold?",
    ],
    insider_lens=[
        "The study is a loss-leader; the CPAP resupply is the business. A "
        "diagnosis happens once; masks and consumables reorder forever — but "
        "only for adherent patients. The asset's quality is the resupply "
        "annuity and the adherence data behind it, not the number of beds.",
        "Payers are deliberately killing the in-lab polysomnogram. Home-test-"
        "first policies are a permanent price cut on the sector's historically "
        "highest-revenue study; a lab-heavy P&L is a melting ice cube.",
        "Adherence is reimbursement. Medicare literally stops paying for a CPAP "
        "the patient doesn't use (the 90-day rule). Operators that "
        "industrialize adherence coaching and data capture keep the revenue; "
        "those that dispense and forget lose it to denials.",
        "The integration everyone wants — test, read, and sell the CPAP under "
        "one roof — is also the textbook Stark/AKS problem. The economics and "
        "the compliance risk are the same transaction; the structure is the "
        "diligence.",
        "The Philips recall rewired the channel. It handed share to ResMed, "
        "created replacement demand, and left adherence gaps; anyone touching "
        "sleep DME still has to reconcile device supply and recall exposure.",
        "Watch GLP-1s both ways. They expand screening today (obese patients in "
        "the funnel) but could shrink the severe-OSA pool that fills beds and "
        "moves CPAPs over a long enough hold.",
    ],
    connections=default_connections(
        "sleep",
        deals_sector="sleep",
        connectors=[
            ("cms_open_data_mup_physician_by_provider_service",
             "CMS Physician & Other Practitioners — sleep-study volumes (95810/95811/G0399)"),
            ("cms_open_data_mup_dme_by_supplier_service",
             "CMS DME by Supplier & Service — PAP devices & resupply utilization"),
            ("npi_provider",
             "NPI Registry — sleep-medicine physicians & testing facilities"),
            ("openfda_device_510k",
             "openFDA 510(k) — HSAT & PAP device clearances (supply / recall context)"),
            ("open_payments_general_payments_2024",
             "CMS Open Payments — sleep-device maker payments to physicians"),
        ],
    ),
    sources=[
        Source("CMS Medicare Coverage Database — NCD 240.4, CPAP for "
               "obstructive sleep apnea", "GOV",
               "https://www.cms.gov/medicare-coverage-database/"),
        Source("CMS Medicare Physician Fee Schedule & DMEPOS capped-rental "
               "policy", "GOV",
               "https://www.cms.gov/medicare/payment/fee-schedules"),
        Source("American Academy of Sleep Medicine — accreditation standards & "
               "clinical practice guidelines", "INDUSTRY", "https://aasm.org/"),
        Source("FDA — Philips Respironics ventilator/CPAP recall & PAP device "
               "regulation", "GOV", "https://www.fda.gov/medical-devices"),
        Source("Benjafield et al., 'Estimation of the global prevalence and "
               "burden of obstructive sleep apnoea', Lancet Respir Med 2019",
               "ACADEMIC", "https://pubmed.ncbi.nlm.nih.gov/31300334/"),
        Source("PE Desk industry deep-dive (sleep medicine) + realized-deal "
               "corpus", "INTERNAL", "/diligence/tam-sam?template=sleep"),
    ],
    live_figures=live_figures_from_dive("sleep"),
    trends=(
        "The economics of sleep have inverted over the last decade. The "
        "attended in-lab polysomnogram — long the sector's revenue anchor — is "
        "being deliberately displaced by home sleep apnea testing as Medicare "
        "and commercial payers mandate the cheaper home study first; in-lab bed "
        "volume and revenue are in structural decline. The value has migrated "
        "downstream to CPAP therapy and, above all, to recurring DME resupply, "
        "which scales with the installed patient base and is gated by "
        "documented adherence. The 2021 Philips Respironics recall jolted "
        "device supply, shifted share to ResMed, and left an adherence-and-"
        "replacement overhang still working through the channel. Two forces "
        "shape the next chapter: vertical integration of test-to-therapy-to-"
        "resupply (colliding with Stark/AKS), and GLP-1 weight-loss drugs as a "
        "two-sided wildcard that expands screening today but could erode the "
        "severe-OSA population over a long hold. The durable platform owns the "
        "adherence data and the resupply annuity, not the beds."),
    growth_levers=[
        GrowthLever(
            "OSA under-diagnosis closure",
            "A large undiagnosed obese/aging population enters testing as "
            "screening and HSAT access expand — the primary volume engine.",
            "primary volume", "ACADEMIC"),
        GrowthLever(
            "HSAT access expansion",
            "Cheaper, home-based testing lifts total tested volume while "
            "cutting revenue per study — volume up, price down.",
            "+ volume / − price", "GOV"),
        GrowthLever(
            "CPAP resupply annuity",
            "Recurring masks and consumables scale with the installed base and "
            "adherence programs — the durable margin.",
            "recurring", "ILLUSTRATIVE"),
        GrowthLever(
            "Therapy alternatives (Inspire HGNS, oral appliances)",
            "Expand treatment of the PAP-intolerant population beyond the "
            "device.",
            "adjacent", "ILLUSTRATIVE"),
        GrowthLever(
            "GLP-1 two-sided effect",
            "Expands screening now (obese funnel), may shrink severe-OSA "
            "prevalence later — a long-run swing factor.",
            "± long-run", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Untreated obstructive sleep apnea prevalence (obesity + aging)",
        analysis=(
            "The demand base is a large, under-diagnosed OSA population — peer-"
            "reviewed estimates (Benjafield et al., 2019) put nearly a billion "
            "adults globally with at least mild OSA, tightly correlated with "
            "obesity and aging, both rising in the US. Most remain undiagnosed, "
            "so the near-term driver is diagnosis-rate closure via easier home "
            "testing rather than new incidence. That cuts both ways for "
            "revenue: more patients tested and treated, but at a lower price "
            "per (home) study, so volume growth outpaces revenue growth on the "
            "diagnostic side while the therapy/resupply base compounds with the "
            "installed population. GLP-1 weight loss is the credible long-run "
            "offset to severe-OSA prevalence."),
        basis="ACADEMIC"),
    cost_drivers=[
        CostDriver(
            "Clinical & technical labor (techs, scoring, RTs, physician reads)",
            "~35-45% of cost",
            "The fixed cost of running beds; reverse operating leverage as in-"
            "lab volume falls.",
            "ILLUSTRATIVE"),
        CostDriver(
            "DME product COGS (devices, masks, consumables)",
            "~25-35% of cost",
            "The resupply annuity's cost of goods — scales with the installed "
            "base, and where vendor pricing (ResMed/Philips) is margin.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Facility & beds (real estate, IDTF setup)",
            "~10-15% of cost",
            "The melting-ice-cube fixed cost of the in-lab model.",
            "ILLUSTRATIVE"),
        CostDriver(
            "Billing / prior-auth / adherence operations (RCM)",
            "~10-15% of cost",
            "The friction cost of gated reimbursement — also where denials are "
            "won or lost.",
            "ILLUSTRATIVE"),
        CostDriver(
            "G&A & compliance (incl. Stark/AKS structuring)",
            "~5-10% of cost",
            "Management overhead plus the cost of defending an integrated "
            "test-to-DME structure.",
            "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No national sleep-lab census is vendored (AASM accreditation lists are "
        "proprietary), so geography is not fabricated here. Directionally, "
        "testing and therapy demand track obesity prevalence and age structure "
        "(a Southeast / Appalachia skew) and payer mix, while supply "
        "concentrates where hospital sleep programs and DME distribution are "
        "dense. The honest read is the CMS procedure-volume and DME connectors "
        "plus the deal history below, not a facility map."),
)

register(REPORT)
