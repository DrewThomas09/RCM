"""Dental Labs — custom dental-prosthetic manufacturing.

Deals-only deep-dive (no vendored facility file): a fragmented B2B device-
manufacturing trade (crowns, bridges, dentures, implant components, aligners)
being reshaped by digital CAD/CAM, offshoring, and DSO in-sourcing. The lab is
a device manufacturer, not a care provider — insulated from dental insurance but
exposed to its dentist/DSO customers. Live figures come from the deals corpus
(the ``dental`` token adjacency); geography (NADL rosters aren't public) is
honestly omitted, so ``cms_trend`` and ``state_breakdown`` are unset.
"""
from __future__ import annotations

from .. import (
    Competition, CostDriver, GrowthLever, HowItWorks, Kpi, MarketReport,
    MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment, Source,
    TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="dental_labs",
    name="Dental Labs",
    care_setting="Other services",
    naics="339116",
    one_line_def=(
        "Custom manufacturers of dental prosthetics and restorations — crowns, "
        "bridges, dentures, implant components, night guards, and orthodontic / "
        "aligner appliances — made to a dentist's prescription; a fragmented "
        "B2B device trade being reshaped by digital CAD/CAM, offshoring, and "
        "DSO in-sourcing."),
    tam_headline=TamHeadline(
        value=4.5, unit="$B", growth_pct=4.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "Dental labs are not Medicare-paid, so there is no CMS figure. The "
            "~$4-5B US dental-laboratory market is an industry estimate (NADL / "
            "IBISWorld NAICS 33911a); growth is the modeled composite of "
            "implant and aligner demand, aging/edentulism, and CAD/CAM "
            "productivity, net of offshoring price pressure."),
    ),
    executive_summary=[
        "Dental labs are B2B device manufacturers, not care providers. The "
        "customer is the dentist/DSO, the product is a custom crown, denture, "
        "or aligner, and payment is a per-unit price list — the lab is "
        "insulated from dental insurance but fully exposed to its customer's "
        "volume and price sensitivity.",
        "The trade is being digitized out of its old shape. Intraoral scanners "
        "plus CAD/CAM milling and 3D printing collapse the model-and-wax "
        "handcraft into a digital workflow, favoring scaled labs with capital "
        "equipment and squeezing the small bench lab — the classic "
        "automation-driven consolidation setup.",
        "Offshoring is the standing margin threat. A large share of US crowns "
        "are fabricated overseas (China and others) at far lower cost; the "
        "domestic lab competes on turnaround, chairside/clinical support, "
        "remakes, and 'made in USA' quality positioning — not on price.",
        "DSO in-sourcing changes the customer. As dental groups consolidate, "
        "they build central/in-house labs or negotiate captive-lab pricing — "
        "the lab's largest accounts can become its competitor, so DSO "
        "relationships cut both ways.",
        "Aligners re-drew the map. Clear-aligner manufacturing is a "
        "higher-growth, IP-driven, more consolidated device segment adjacent to "
        "the lab — a different business than pouring dentures, and mispricing "
        "it misprices both the opportunity and the competition.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Dentist diagnoses and preps the tooth/arch",
            "Physical impression OR intraoral scan + prescription (Rx)",
            "Lab design (CAD) — margin, occlusion, shade",
            "Fabrication — mill / print / cast / layer (zirconia, PFM, acrylic)",
            "QC + finishing, staining, and glaze",
            "Ship to the practice",
            "Seat and adjust chairside; remake if the fit fails",
        ],
        sites_of_care=[
            "Full-service dental laboratory",
            "Specialized lab (crown & bridge / removables / implant / aligner)",
            "DSO central / in-house lab (the in-sourcing substitute)",
            "Offshore fabrication partner; chairside in-office mill (the "
            "disintermediating substitute)",
        ],
        money_flow=(
            "The lab bills the dental practice a per-unit price for each "
            "restoration — a crown, a denture, an aligner set — set by a "
            "published price list negotiated with volume accounts. The lab is "
            "not a healthcare-payer counterparty: it does not bill insurance. "
            "The practice collects from the patient and the dental plan, then "
            "pays the lab out of that. Turnaround time, remake rate, and "
            "clinical/chairside support are the real competitive currency; "
            "offshore fabrication and chairside milling set the price ceiling. "
            "The lab's exposure to reimbursement is one step removed — it rides "
            "on the dentist's volume and fee pressure, not on a claim."),
        key_players=(
            "A very long tail of small independent bench labs under a few "
            "scaled players and the aligner/implant device majors: Glidewell "
            "(the vertically-integrated leader), National Dentex (NDX, a "
            "buy-and-build platform), and Modern Dental Group (Hong "
            "Kong-listed, large offshore capacity), plus Align Technology "
            "(Invisalign) and implant/ortho device firms adjacent to the "
            "trade. DSO central labs increasingly in-source the work."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("Crown & bridge (fixed restorations)",
                    "the largest category",
                    "ILLUSTRATIVE · NADL / industry estimate"),
            Segment("Removables (dentures / partials)",
                    "aging-demand core",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("Implant components / abutments",
                    "higher-value, growing",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("Clear aligners & orthodontic appliances",
                    "the fastest-growing segment",
                    "ILLUSTRATIVE · industry estimate"),
            Segment("Offshore-fabricated share of US units",
                    "the price ceiling",
                    "ILLUSTRATIVE · trade estimate"),
        ],
        growth_drivers=[
            "Aging population / edentulism — dentures and removables",
            "Dental-implant adoption — higher-value units",
            "Clear-aligner and cosmetic demand",
            "CAD/CAM productivity and digital workflow adoption",
            "DSO consolidation (a channel shift, cutting both ways)",
            "Offshoring price pressure — a persistent margin drag",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial dental (PPO / DHMO)": 0.45,
            "Patient out-of-pocket": 0.43,
            "Medicaid / CHIP (largely pediatric, variable adult)": 0.12,
        },
        rate_mechanics=[
            "Per-unit lab price list — the lab is paid a fixed price per "
            "restoration by the practice, not a claim; volume accounts "
            "negotiate discounts.",
            "No third-party payer for the lab — dental insurance pays the "
            "dentist, not the lab; the lab's exposure is one step removed.",
            "Downstream dental reimbursement — the practice's economics ride on "
            "commercial dental PPO fee schedules, DHMO capitation, high patient "
            "cost-share, and limited/variable Medicaid adult dental coverage; "
            "that determines how much lab work gets prescribed.",
            "Offshore price arbitrage — overseas fabrication sets a hard price "
            "ceiling on commodity crowns.",
            "Digital-workflow pricing — scanned/CAD cases and DSO in-house labs "
            "shift the value split between the dentist and the lab.",
        ],
        reimbursement_risk=(
            "The lab has no payer-denial risk — but it inherits its customers' "
            "pricing power in reverse. Dentists, and especially DSOs, squeezed "
            "by flat dental-PPO fees and high patient cost-share, push lab "
            "prices down and shop offshore for commodity units. Adult Medicaid "
            "dental coverage is politically volatile — states add and cut it — "
            "swinging denture and removables volume. The structural risks are "
            "offshoring (a persistent price ceiling), chairside milling and DSO "
            "in-sourcing (disintermediation), and commoditization of the "
            "crown; the domestic lab must defend on turnaround, remake rate, "
            "and clinical complexity, not price. Shares shown are the "
            "downstream funding mix and are ILLUSTRATIVE."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("FDA establishment registration & device listing (21 CFR 807)",
                 "Dental labs are device manufacturers/establishments; custom "
                 "restorations are listed devices subject to registration and "
                 "listing — a baseline compliance obligation many small labs "
                 "underappreciate.",
                 "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807"),
            Rule("FDA dental-device classification (21 CFR 872)",
                 "Classifies crowns, dentures, implants, and aligners "
                 "(Class I/II) — the framework that governs which products need "
                 "clearance and controls.",
                 "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-872"),
            Rule("Quality System / QMSR (21 CFR 820)",
                 "GMP for device manufacturers — most binding on scaled and "
                 "aligner/3D-printing labs; the compliance bar rises with "
                 "automation and volume.",
                 "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820"),
            Rule("Import regulation & country-of-origin / material disclosure",
                 "Offshore-fabricated restorations must meet FDA import rules; "
                 "several states require disclosure of foreign fabrication and "
                 "material content to the patient/dentist.",
                 None),
            Rule("State dental-lab certification & material-disclosure laws "
                 "(NADL CDL/CDT)",
                 "Voluntary certification signals quality; state disclosure "
                 "laws on material content and point of origin bound the "
                 "offshore commodity trade.",
                 None),
        ],
        policy_watch=[
            "Expansion or contraction of adult Medicaid dental benefits by state",
            "FDA scrutiny of 3D-printed and clear-aligner devices (incl. DTC)",
            "Import / tariff policy on overseas restorations",
            "State material-content and point-of-origin disclosure laws",
            "DSO corporate-practice structures and captive-lab arrangements",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "One of the most fragmented device trades — thousands of small "
            "bench labs (owner-technicians) under a handful of scaled players "
            "and offshore majors. Digital capital requirements are "
            "consolidating the tail. NADL membership rosters aren't public, so "
            "a precise HHI is honestly omitted."),
        hhi_or_share=(
            "Highly fragmented with a few scaled leaders (Glidewell, NDX, "
            "Modern Dental) and separate aligner/implant device majors; no "
            "public roster, so a precise HHI is omitted rather than fabricated."),
        consolidation=(
            "Active roll-up — Glidewell scaling organically with vertical "
            "integration, National Dentex/NDX buying and building, Modern "
            "Dental scaling offshore, plus regional consolidators. Aligners and "
            "implants consolidated separately around IP."),
        pe_activity=(
            "PE-backed buy-and-build across regional labs, chasing CAD/CAM "
            "scale economies, DSO contracts, and offshore cost. The thesis is "
            "automation plus purchasing scale plus DSO account capture; the "
            "risk is offshoring and in-sourcing eroding the very accounts you "
            "buy, and having to digitize acquired analog labs."),
        notable_players=[
            "Glidewell", "National Dentex (NDX)", "Modern Dental Group",
            "Align Technology (Invisalign, adjacent)", "Dandy (digital-first)",
            "DSO central labs",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Revenue per unit (crown)",
                "$80-180 domestic; far less offshore",
                "Category, digital workflow, and country of origin drive it."),
            Kpi("Remake rate", "2-6%",
                "Fit/quality failures; remakes are pure margin loss and "
                "relationship risk — the lab's core quality metric."),
            Kpi("Turnaround time", "days",
                "The domestic lab's central competitive edge against offshore "
                "fabrication."),
            Kpi("Digital (scan) case share", "rising",
                "CAD/CAM productivity and margin; the leading indicator of a "
                "lab's competitiveness."),
            Kpi("Technician productivity (units / tech / day)", "labor-bound",
                "Skilled-technician labor is the dominant cost and the capacity "
                "ceiling."),
            Kpi("Top-account (DSO) concentration", "often high",
                "Customer power and in-sourcing risk concentrated in a few "
                "accounts."),
        ],
        margin_profile=(
            "Lab EBITDA margins are labor- and remake-sensitive. Scaled digital "
            "labs earn more via CAD/CAM automation and purchasing power, while "
            "small bench labs are squeezed between skilled-technician wage "
            "inflation and offshore price ceilings. Aligner and implant device "
            "margins are structurally higher (IP, branding). The swing factors "
            "are digital adoption, remake rate, and account mix; ranges are "
            "ILLUSTRATIVE."),
    ),
    risks=[
        Risk("Offshoring price ceiling", "High",
             "Overseas fabrication caps commodity-crown pricing and erodes the "
             "domestic lab's margin on standard units."),
        Risk("DSO in-sourcing / chairside milling", "High",
             "The largest customers build central labs or use CEREC — "
             "disintermediating the independent lab."),
        Risk("Skilled-technician labor shortage", "High",
             "An aging technician workforce with a thin apprenticeship pipeline "
             "caps capacity; a retirement wave can vaporize acquired output."),
        Risk("Digital capex & obsolescence", "Medium",
             "Scanners, mills, and printers require continual capital; laggards "
             "lose accounts to digital-first competitors."),
        Risk("Medicaid adult-dental volatility", "Medium",
             "Denture/removables volume swings with state coverage decisions."),
        Risk("Customer concentration", "Medium",
             "DSO accounts wield pricing power and can leave or in-source."),
    ],
    diligence_questions=[
        "What is the account concentration, and what is the DSO exposure and "
        "in-sourcing risk?",
        "What is the domestic-versus-offshore fabrication mix, and how is it "
        "trending?",
        "What is the remake rate and the warranty/redo cost?",
        "What is the digital/scan case share, and what is the CAD/CAM capex "
        "plan?",
        "What is the technician headcount, age profile, and turnover?",
        "What is the category mix (crown / removable / implant / aligner) and "
        "its growth?",
        "How does unit pricing compare to the offshore benchmark?",
        "What is the FDA registration/QSR compliance posture and the recall "
        "history?",
    ],
    insider_lens=[
        "The lab lives or dies on turnaround and remakes, not price — it "
        "already can't win on price against China. A one-day-faster, low-remake "
        "lab keeps the dentist; a cheap slow one loses the chair. Underwrite "
        "remake rate and turnaround time, not headline gross margin.",
        "Your biggest customer is your biggest threat. Win a DSO account and "
        "it's great — until the DSO builds a central lab or dangles the book to "
        "force price. DSO concentration is a double-edged asset; model the "
        "in-sourcing scenario explicitly.",
        "Digital is a capex treadmill that consolidates the trade. Scanners, "
        "mills, and printers raise productivity but demand continual "
        "reinvestment; the small bench lab can't keep up — which is the "
        "roll-up thesis and the integration risk if you buy analog labs.",
        "The technician is the scarce input. Skilled ceramists and denture "
        "techs are aging out with a thin apprenticeship pipeline; capacity is "
        "labor-bound, and a retirement wave at an acquired lab can vaporize the "
        "output you paid for.",
        "Aligners aren't dentures with a new coat. Clear-aligner manufacturing "
        "is a higher-growth, IP-driven, more consolidated device business "
        "adjacent to the lab — treating it as 'just another lab product' "
        "misprices both the opportunity and Align's competitive moat.",
    ],
    connections=default_connections(
        "dental_labs",
        deals_sector="dental_labs",
        connectors=[
            ("openfda_device_510k",
             "openFDA 510(k) — dental device clearances (product-code map)"),
            ("openfda_device_classification",
             "openFDA device classification — dental product codes (21 CFR 872)"),
            ("bls_qcew_industry_area",
             "BLS QCEW — Dental Laboratories (NAICS 339116) establishments & wages"),
            ("hrsa_data_hpsa_dental",
             "HRSA — dental HPSAs (downstream dental-demand proxy)"),
        ],
    ),
    sources=[
        Source("FDA — Dental Devices classification (21 CFR 872)", "GOV",
               "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-872"),
        Source("FDA — Establishment Registration & Device Listing (21 CFR 807)",
               "GOV",
               "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-807"),
        Source("FDA — Quality System Regulation / QMSR (21 CFR 820)", "GOV",
               "https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-820"),
        Source("National Association of Dental Laboratories (NADL) — trade "
               "statistics & CDL/CDT certification", "INDUSTRY",
               "https://nadl.org/"),
        Source("IBISWorld — US Dental Laboratories industry report "
               "(NAICS 33911a)", "INDUSTRY", "https://www.ibisworld.com/"),
        Source("PE Desk industry deep-dive (deals-only; dental-trade "
               "adjacency) + realized-deal corpus", "INTERNAL",
               "/diligence/tam-sam?template=dental_labs"),
    ],
    live_figures=live_figures_from_dive("dental_labs"),
    trends=(
        "The dental-lab trade is being reshaped by three converging forces. "
        "Digital first: intraoral scanning, CAD design, milling, and 3D "
        "printing have collapsed the century-old model-and-wax handcraft into a "
        "capital-intensive digital workflow, rewarding scaled labs and "
        "squeezing the small bench operator — the automation-driven "
        "consolidation setup. Offshoring second: a large share of commodity "
        "crowns are now fabricated overseas at a fraction of domestic cost, "
        "setting a hard price ceiling and forcing the US lab to compete on "
        "turnaround, remakes, and clinical support. DSO consolidation third: as "
        "dental groups scale, they build central labs or extract captive-lab "
        "pricing, turning the lab's biggest accounts into its competitors. "
        "Around all of it, clear aligners have grown into a separate, "
        "higher-growth, IP-driven device segment. The result is a fragmented "
        "trade consolidating toward digital scale, where the durable question "
        "is whether a lab can defend turnaround and remake rate against a "
        "structural offshore price floor."),
    growth_levers=[
        GrowthLever(
            "Dental-implant & cosmetic demand",
            "Implant components and cosmetic restorations are higher-value "
            "units than commodity crowns.",
            "value per unit", "ILLUSTRATIVE"),
        GrowthLever(
            "Clear-aligner / orthodontic growth",
            "The fastest-growing adjacent segment — IP-driven and structurally "
            "higher-margin.",
            "fastest segment", "ILLUSTRATIVE"),
        GrowthLever(
            "CAD/CAM automation & purchasing scale",
            "Digital fabrication and volume purchasing raise productivity and "
            "spread capital cost — the core scale lever.",
            "margin / productivity", "ILLUSTRATIVE"),
        GrowthLever(
            "DSO account capture",
            "Winning large DSO contracts adds volume — but the same account can "
            "in-source, so it cuts both ways.",
            "volume (double-edged)", "ILLUSTRATIVE"),
        GrowthLever(
            "Offshoring price pressure",
            "Overseas fabrication compresses pricing on commodity units — the "
            "standing headwind against domestic growth.",
            "price headwind", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Restorative & prosthetic procedure volume prescribed by "
               "dentists and DSOs",
        analysis=(
            "The lab's volume is derived demand: it is a function of how many "
            "crowns, bridges, dentures, implants, and appliances dentists "
            "prescribe, which in turn tracks dental-visit volume, an aging and "
            "increasingly dentate population keeping more teeth to restore, "
            "rising implant and cosmetic adoption, and — critically — the "
            "downstream reimbursement that determines whether a patient accepts "
            "treatment. Because the lab does not touch the patient or the "
            "payer, its demand is one derivative removed: it grows with "
            "procedure mix (a shift toward implants and aligners raises value "
            "per case faster than case count) and shrinks when patient "
            "cost-share or Medicaid adult-dental cuts suppress elective "
            "restorative work. The offsetting substitution is chairside milling "
            "and DSO in-house labs, which capture procedure volume without ever "
            "reaching the independent lab."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Technician & production labor", "~40-50% of cost",
            "The dominant cost and the capacity ceiling; skilled ceramists and "
            "denture techs are scarce and aging out.", "ILLUSTRATIVE"),
        CostDriver(
            "Materials (zirconia, alloys, resins, ceramics)", "~20-30% of cost",
            "Restorative materials — exposed to metal and specialty-ceramic "
            "price swings.", "ILLUSTRATIVE"),
        CostDriver(
            "CAD/CAM & 3D-print capital + software", "digital capex",
            "Scanners, mills, printers, and design software — a continual "
            "reinvestment treadmill that consolidates the trade.", "ILLUSTRATIVE"),
        CostDriver(
            "Remakes & warranty", "margin leak",
            "Redone units for fit/quality failures — pure margin loss plus "
            "relationship damage.", "ILLUSTRATIVE"),
        CostDriver(
            "Shipping & logistics (turnaround)", "delivery cost",
            "Fast, reliable shipping is the domestic lab's edge over offshore — "
            "and a real cost line.", "ILLUSTRATIVE"),
    ],
)

register(REPORT)
