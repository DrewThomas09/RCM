"""Retail Clinics — pharmacy/big-box-embedded convenience clinics.

Deals-only deep-dive, and effectively a failure autopsy: the standalone retail-
clinic thesis largely collapsed (Walmart Health closed all clinics in 2024;
Walgreens wrote down VillageMD), leaving CVS MinuteClinic as the pharmacy- and
payer-integrated survivor. The qualitative sections are authored around the
central truth that the clinic is a strategic loss-leader — its return is script
capture, immunizations, and health-plan engagement, not visit margin. The
corpus carries no realized retail-clinic deals, so ``live_figures`` is honestly
empty and the analysis leans on the qualitative frame.
"""
from __future__ import annotations

from .. import (
    Competition, Connection, CostDriver, GrowthLever, HowItWorks, Kpi,
    MarketReport, MarketSize, Regulatory, Reimbursement, Risk, Rule, Segment,
    Source, TamHeadline, UnitEconomics, VolumeDriver,
    default_connections, live_figures_from_dive, register,
)

REPORT = MarketReport(
    slug="retail_clinics",
    name="Retail Clinics",
    care_setting="Ambulatory",
    naics="621498",
    one_line_def=(
        "Small, nurse-practitioner-staffed clinics embedded inside pharmacies "
        "and big-box/grocery stores (CVS MinuteClinic and peers) that treat a "
        "narrow protocol menu of minor acute conditions, vaccinations, and "
        "screenings — convenience-first, low-acuity, and owned by retail/"
        "pharmacy corporations rather than physicians."),
    tam_headline=TamHeadline(
        value=3.0, unit="$B", growth_pct=1.5, basis_label="ILLUSTRATIVE",
        basis_note=(
            "US retail-clinic services revenue is a small, contracting segment "
            "(no single published figure); ~$3B is the modeled composite of "
            "the surviving footprint × thin per-visit revenue. Growth is "
            "modeled and near-flat — the standalone format is in retreat "
            "(Walmart Health closed 2024) even as immunization volume "
            "persists."),
    ),
    executive_summary=[
        "Retail clinics are a strategic loss-leader, not a standalone "
        "business. They exist to drive pharmacy foot traffic, script capture, "
        "immunizations, and (for integrated owners) health-plan engagement — "
        "the clinic P&L itself rarely stands alone, and that is the single "
        "most important thing to understand.",
        "The standalone thesis failed publicly. Walmart Health shut all its "
        "clinics in 2024, Walgreens wrote down and retrenched VillageMD, and "
        "the survivors are pharmacy-integrated (CVS MinuteClinic, ~1,100 "
        "sites). Read any retail-clinic deal as a failure autopsy: what killed "
        "the economics?",
        "The model is NP-staffed, protocol-driven, and narrow-menu — a fixed "
        "list of minor acute complaints, vaccinations, physicals, and "
        "screenings at transparent cash/commercial prices. Labor is the whole "
        "cost, volume is thin and seasonal, and there is no facility fee.",
        "Ownership is corporate-retail, not physician — CVS, Walgreens, Kroger, "
        "grocery. The acquirable pool for a traditional healthcare sponsor is "
        "thin; the real action is inside the pharmacy/payer strategy "
        "(MinuteClinic feeding CVS Health/Aetna and the value-based front "
        "door).",
        "Reimbursement is thin E/M plus immunization administration — low per-"
        "visit revenue, high substitution risk from telehealth and urgent "
        "care. The durable value is the pharmacy/traffic/data flywheel and the "
        "flu-shot franchise, not the sick-visit margin.",
    ],
    how_it_works=HowItWorks(
        value_chain=[
            "Customer already in the store → self-serve kiosk / queue",
            "NP/PA visit against a fixed protocol menu",
            "Point-of-care test or vaccination administered",
            "Prescription routed to the co-located pharmacy",
            "Transparent cash price or commercial / pharmacy-benefit claim",
            "Pharmacy script capture + retail basket lift (the real return)",
        ],
        sites_of_care=[
            "Pharmacy-embedded clinic (CVS MinuteClinic — the survivor)",
            "Grocery / big-box clinic (Kroger Little Clinic; Walmart, closed)",
            "Standalone retail-adjacent clinic",
            "Telehealth-integrated virtual + in-store hybrid",
        ],
        money_flow=(
            "The clinic bills low-level E/M office codes and immunization-"
            "administration codes for a narrow protocol menu, at transparent "
            "cash prices or commercial rates, with no facility fee — per-visit "
            "revenue is low (~$70-150). But the clinic's economic purpose sits "
            "upstream and downstream of the visit: it drives pharmacy "
            "prescription capture, retail traffic and basket size, "
            "immunization volume (flu shots are a major pharmacy line), and — "
            "for a vertically-integrated owner like CVS Health — engagement "
            "that supports the Aetna insurance and value-based-care strategy. "
            "The clinic is a customer-acquisition and retention asset whose ROI "
            "is measured across the store and the health plan, not on the "
            "clinic's own claims."),
        key_players=(
            "CVS MinuteClinic is the clear survivor and leader (~1,100 clinics "
            "inside CVS pharmacies, tied to CVS Health/Aetna). Historically "
            "Walgreens (Healthcare Clinic, then the VillageMD primary-care "
            "pivot), Walmart Health (closed 2024), and Kroger's The Little "
            "Clinic. The field has consolidated toward pharmacy-integrated "
            "survivors as the pure-retail-health experiments closed."),
    ),
    market_size=MarketSize(
        segments=[
            Segment("CVS MinuteClinic footprint", "~1,100 clinics",
                    "INDUSTRY · CVS Health disclosures"),
            Segment("Walmart Health", "closed all clinics (2024)",
                    "INDUSTRY · directional (segment contraction)"),
            Segment("Net revenue / visit", "~$70-150",
                    "ILLUSTRATIVE · modeled low-acuity E/M + immunization"),
            Segment("Immunization / vaccination", "the largest recurring line",
                    "ILLUSTRATIVE · directional (flu/COVID/shingles)"),
            Segment("Standalone clinic profitability",
                    "rarely positive on its own P&L",
                    "ILLUSTRATIVE · directional (repeated market exits)"),
        ],
        growth_drivers=[
            "Pharmacy-traffic + script-capture flywheel (the real driver)",
            "Immunization volume (flu, COVID, shingles, travel)",
            "Value-based-care front-door strategy for integrated owners",
            "Consumer convenience for the narrowest acute menu",
            "Offsets: standalone-economics failure, telehealth/urgent-care "
            "substitution, retrenchment",
        ],
    ),
    reimbursement=Reimbursement(
        payer_mix={
            "Commercial": 0.48,
            "Medicare / MA": 0.22,
            "Self-pay / cash": 0.18,
            "Medicaid": 0.12,
        },
        rate_mechanics=[
            "Low-level E/M office codes (99202-99213) for a narrow protocol "
            "menu — no facility fee, thin per-visit revenue.",
            "Immunization administration + vaccine product codes — flu, COVID, "
            "shingles, travel — often the largest, most recurring line, "
            "frequently billed through the pharmacy benefit.",
            "Transparent cash / retail pricing — a flat posted price for common "
            "visits; a meaningful self-pay share.",
            "Pharmacy benefit (Part D) integration — vaccines and some services "
            "flow through the pharmacy claim, not medical — a structural "
            "advantage of the co-located model.",
            "Payer clinical-network contracts — some payers steer members to "
            "retail clinics as the lowest-cost site of care.",
            "Value-based-care attribution (integrated owners) — for CVS/Aetna-"
            "type owners, engagement feeds capitation/quality economics "
            "upstream of the clinic claim.",
        ],
        reimbursement_risk=(
            "The visit itself is a thin-margin, low-acuity E/M that competes "
            "directly with telehealth (often cheaper) and urgent care (broader "
            "menu), so per-visit reimbursement is structurally weak and "
            "substitution risk is high. Immunization is the more durable line "
            "but is seasonal (flu) and was distorted by COVID vaccination "
            "volume that has since collapsed. Because the standalone clinic "
            "rarely clears its own labor cost, the real 'reimbursement' is the "
            "pharmacy script capture and — for integrated owners — the plan-"
            "side value, neither of which shows up on the clinic's own claims. "
            "A sponsor underwriting retail-clinic visit revenue in isolation is "
            "underwriting the wrong number."),
    ),
    regulatory=Regulatory(
        rules=[
            Rule("Scope-of-practice / NP-PA independent-practice laws (state)",
                 "The entire staffing model depends on NP practice authority; "
                 "restrictive-supervision states make the clinic uneconomic.",
                 None),
            Rule("Pharmacy immunization authority (state) + CDC/ACIP schedules",
                 "Governs which vaccines the clinic/pharmacy may administer and "
                 "to whom — the durable revenue line.",
                 "https://www.cdc.gov/vaccines/hcp/imz-schedules/"),
            Rule("CLIA certification for point-of-care testing",
                 "Required to run the rapid strep/flu/COVID tests that support "
                 "the acute-visit menu.",
                 "https://www.cms.gov/medicare/quality/clinical-laboratory-improvement-amendments"),
            Rule("Corporate Practice of Medicine (CPOM) (state)",
                 "Retail corporations must structure the clinical entity via "
                 "MSO / friendly-PC arrangements where CPOM applies.",
                 None),
            Rule("Telehealth licensure & parity (state/federal)",
                 "The hybrid virtual-plus-in-store model rides on evolving "
                 "telehealth licensure — both an enabler and a substitute.",
                 None),
        ],
        policy_watch=[
            "Scope-of-practice expansion (independent NP practice) — the swing "
            "factor for clinic economics",
            "Pharmacy-based-care and immunization authority expansion (PREP Act "
            "legacy)",
            "Telehealth parity — both a substitute and an enabler of the hybrid "
            "model",
            "Value-based-care / Medicare Advantage strategy of integrated "
            "pharmacy owners",
            "Continued retail-health retrenchment (post-Walmart / Walgreens)",
        ],
    ),
    competition=Competition(
        fragmentation=(
            "Not fragmented at the operator level — a handful of national "
            "retail/pharmacy corporations own essentially the whole segment, "
            "led by CVS MinuteClinic. It is concentrated ownership over a thin, "
            "shrinking footprint, the opposite of the fragmented physician-"
            "owned verticals; there is no independent long tail to acquire."),
        hhi_or_share=(
            "Highly concentrated by owner — CVS MinuteClinic is the dominant "
            "survivor after Walmart and others exited. No independent "
            "acquirable pool exists, so the usual fragmentation-arbitrage "
            "thesis does not apply here."),
        consolidation=(
            "The story is de-consolidation by exit, not roll-up: Walmart Health "
            "closed (2024), Walgreens wrote down VillageMD and pulled back, and "
            "the standalone retail-clinic experiment largely ended. CVS "
            "integrated MinuteClinic deeper into CVS Health/Aetna. The "
            "survivors are pharmacy- or payer-owned, not sponsor-owned."),
        pe_activity=(
            "Minimal direct PE ownership — retail clinics sit inside strategic "
            "retail/pharmacy/payer balance sheets, not sponsor portfolios. PE "
            "interest in the adjacent space runs through primary-care and "
            "value-based-care platforms (the VillageMD/Oak Street/CityBlock "
            "lineage), not the retail-clinic format itself, which has proven "
            "hard to make money on as a standalone."),
        notable_players=[
            "CVS MinuteClinic", "Walgreens (Healthcare Clinic / VillageMD)",
            "Kroger The Little Clinic", "Walmart Health (closed 2024)",
            "Grocery / regional retail clinics",
        ],
    ),
    unit_economics=UnitEconomics(
        kpis=[
            Kpi("Visits / clinic / day", "10-25",
                "Thin and highly seasonal — immunization-driven peaks, quiet "
                "shoulder seasons."),
            Kpi("Net revenue / visit", "$70-150",
                "Low-acuity E/M plus immunization admin; no facility fee to "
                "lift it."),
            Kpi("Labor as % of clinic cost", "55-70%",
                "The NP/PA and support staff are essentially the whole cost "
                "against thin volume."),
            Kpi("Standalone clinic EBITDA", "near / below breakeven",
                "The reason the format keeps retrenching — it rarely clears "
                "its own cost."),
            Kpi("Immunization share of visits", "30-50% seasonally",
                "The most durable, pharmacy-linked line — the franchise worth "
                "underwriting."),
            Kpi("Script-capture / basket lift per visit", "the real ROI",
                "Measured off-clinic in pharmacy scripts and retail traffic — "
                "where the return actually lands."),
        ],
        margin_profile=(
            "On its own P&L a retail clinic is a marginal-to-loss-making box — "
            "thin, seasonal visit volume against fixed NP labor and in-store "
            "space, no facility fee, and low per-visit reimbursement. That is "
            "precisely why Walmart and others exited. The format only makes "
            "sense as a strategic asset: it drives pharmacy prescription "
            "capture, immunization volume, retail traffic, and (for integrated "
            "owners) health-plan engagement — returns that accrue to the store "
            "and the plan, not the clinic. Any valuation that treats the clinic "
            "as a standalone EBITDA generator is mispricing it; the honest "
            "frame is contribution to the pharmacy/payer flywheel."),
    ),
    risks=[
        Risk("Standalone-economics failure", "High",
             "The format repeatedly fails to clear its own cost; Walmart's "
             "2024 exit is the proof point."),
        Risk("Telehealth + urgent-care substitution", "High",
             "Cheaper virtual visits and broader-menu urgent care take the "
             "same low-acuity demand."),
        Risk("Dependence on the strategic/pharmacy owner's strategy", "High",
             "The clinic's fate rides on the parent's retail/payer priorities, "
             "not on clinic performance."),
        Risk("Immunization seasonality + COVID-volume reversal", "Medium",
             "The most durable revenue line is seasonal and was inflated by "
             "COVID vaccination that has since gone."),
        Risk("Scope-of-practice restrictiveness", "Medium",
             "States limiting NP practice make the staffing model uneconomic."),
        Risk("Thin acquirable pool / strategic-only ownership", "Medium",
             "Little for a traditional sponsor to buy — the segment sits on "
             "strategic balance sheets."),
    ],
    diligence_questions=[
        "Is the clinic valued on its own P&L, or on its contribution to "
        "pharmacy script capture, immunizations, and retail traffic — and "
        "which of those is actually real and measured?",
        "What is the visit and immunization volume seasonality, and how much "
        "of trailing revenue was COVID vaccination that has since gone?",
        "What is the standalone clinic-level EBITDA, and how many sites are "
        "below breakeven?",
        "How does clinic engagement convert to downstream pharmacy scripts and "
        "(if integrated) plan value — is that link quantified?",
        "What are the state scope-of-practice constraints across the "
        "footprint, and how do they affect staffing cost?",
        "What is the substitution exposure to telehealth and urgent care in "
        "each market?",
        "Is there any durable payer contract steering members to the clinic, "
        "or is volume purely cash/convenience-dependent?",
    ],
    insider_lens=[
        "The clinic is a loss-leader by design. It exists to pull customers "
        "into the pharmacy and lift the basket — the visit rarely pays for "
        "itself, and pretending otherwise is how Walmart Health ended up "
        "closing all of its clinics.",
        "The most durable revenue is the flu shot, not the sick visit. "
        "Immunization is pharmacy-linked, recurring, and high-margin; the "
        "acute-visit menu is thin and squeezed by telehealth. Underwrite the "
        "immunization franchise, discount the visit.",
        "Retail health is a graveyard of standalone theses. Walmart Health, "
        "Haven, and the pure-play retail-clinic model all struggled or closed "
        "— the survivors (MinuteClinic) are the ones welded to a pharmacy and "
        "a health plan.",
        "The real strategic buyer is the payer-pharmacy stack. CVS's "
        "MinuteClinic matters because it feeds Aetna and the value-based front "
        "door — the clinic's value is a function of the vertical integration "
        "around it, not the format itself.",
        "There is almost nothing here for a classic PE roll-up. Ownership is "
        "concentrated in strategics; the sponsor money in this neighborhood "
        "went into primary-care/VBC platforms (VillageMD, Oak Street) — which "
        "themselves proved the economics are brutally hard.",
    ],
    connections=default_connections(
        "retail_clinics",
        deals_sector="retail_clinics",
        extra_pages=[
            ("/industry/retail_clinics",
             "Industry deep-dive — retail-clinic failure autopsy"),
        ],
        connectors=[
            ("npi_provider_taxonomy",
             "NPI taxonomy — retail-clinic / NP footprint"),
            ("census_acs_cbsa_profile",
             "Census ACS — store-catchment demographics"),
            ("hrsa_data_hpsa_primary_care",
             "HRSA HPSA — primary-care shortage markets the format targets"),
            ("cms_open_data_medicare_telehealth_trends",
             "CMS Medicare Telehealth Trends — the format's main substitution "
             "threat"),
            ("cms_open_data_mup_partd_prescriber_by_geo_drug",
             "Medicare Part D prescribing by geography — the pharmacy script-"
             "capture flywheel"),
        ],
    ),
    sources=[
        Source("CVS Health — MinuteClinic disclosures / investor materials",
               "INDUSTRY", "https://www.cvshealth.com/"),
        Source("Convenient Care Association — retail-clinic industry data",
               "INDUSTRY", "https://www.ccaclinics.org/"),
        Source("Health Affairs / RAND — research on retail-clinic utilization, "
               "cost, and care substitution", "ACADEMIC",
               "https://www.healthaffairs.org/"),
        Source("CDC / ACIP — immunization schedules (the durable revenue "
               "line)", "GOV", "https://www.cdc.gov/vaccines/hcp/imz-schedules/"),
        Source("CMS — Medicare Telehealth Trends (utilization substitution)",
               "GOV",
               "https://www.cms.gov/data-research/statistics-trends-reports/medicare-telehealth-trends"),
        Source("Company announcements — Walmart Health closure (2024); "
               "Walgreens / VillageMD retrenchment", "INDUSTRY", None),
        Source("PE Desk industry deep-dive (retail clinics) + realized-deal "
               "corpus", "INTERNAL",
               "/diligence/tam-sam?template=retail_clinics"),
    ],
    live_figures=live_figures_from_dive("retail_clinics"),
    trends=(
        "The retail-clinic story is a cautionary one. The format scaled in the "
        "2000s-2010s on a convenience thesis — NP-staffed, protocol-driven "
        "clinics inside pharmacies and big-box stores — and peaked as a "
        "strategic experiment when CVS, Walgreens, Walmart, and Amazon all bet "
        "on owning the primary-care/retail-health front door. That bet largely "
        "failed on the standalone economics: Walmart Health closed all its "
        "clinics in 2024, Walgreens wrote down and retrenched its VillageMD "
        "stake, and the pure-play retail-clinic model proved unable to clear "
        "its own labor cost. The survivor is CVS MinuteClinic, which persists "
        "because it is welded to a pharmacy and a health plan (Aetna) — "
        "monetizing through script capture, immunizations, and value-based "
        "engagement rather than visit margin. The forward trajectory is not a "
        "growth story but a repositioning one: retail health is consolidating "
        "into pharmacy-integrated, telehealth-hybrid, VBC-oriented formats, "
        "with the standalone convenience clinic in structural retreat. Read "
        "any deal here as a question about what the clinic contributes to the "
        "flywheel, because on its own it usually does not pay."),
    growth_levers=[
        GrowthLever(
            "Pharmacy script-capture + retail-traffic flywheel",
            "The clinic pulls customers into the store and captures "
            "prescriptions — the real return sits off the clinic P&L.",
            "primary", "ILLUSTRATIVE"),
        GrowthLever(
            "Immunization / vaccination volume",
            "Flu, shingles, and travel vaccines are recurring, pharmacy-linked, "
            "and the most durable revenue line.",
            "+ recurring", "ILLUSTRATIVE"),
        GrowthLever(
            "Value-based-care front-door (integrated owners)",
            "For CVS/Aetna-type owners, clinic engagement feeds plan quality "
            "and capitation economics upstream.",
            "+ plan value", "ILLUSTRATIVE"),
        GrowthLever(
            "Telehealth-hybrid repositioning",
            "Virtual-plus-in-store models extend engagement, but also cannibalize "
            "the in-person convenience visit.",
            "+ engagement", "ILLUSTRATIVE"),
        GrowthLever(
            "Standalone-economics failure + substitution drag",
            "The format cannot clear its own cost and loses low-acuity volume "
            "to telehealth and urgent care — driving repeated exits.",
            "− structural", "ILLUSTRATIVE"),
    ],
    volume_growth_driver=VolumeDriver(
        driver="Convenience demand for a narrow acute/immunization menu × the "
               "parent's store footprint",
        analysis=(
            "The dominant driver is convenience-seeking demand for the "
            "narrowest band of low-acuity care — minor acute complaints, "
            "vaccinations, physicals, and screenings — from consumers already "
            "in the store. Unlike urgent care, the retail clinic serves an "
            "intentionally narrow protocol menu, so its addressable volume is "
            "thin and heavily seasonal, peaking with flu and immunization "
            "season. Crucially, the clinic does not primarily grow its own "
            "revenue; it grows the pharmacy and retail business around it by "
            "pulling customers in and capturing scripts. That makes the real "
            "volume driver the parent's retail and pharmacy footprint and its "
            "immunization franchise, not independent clinic demand. The offsets "
            "are severe and structural: telehealth undercuts the convenience "
            "visit on price, urgent care offers a broader menu, and the "
            "standalone economics have driven repeated market exits. Underwrite "
            "the immunization and script-capture volume; discount the acute-"
            "visit growth."),
        basis="ILLUSTRATIVE"),
    cost_drivers=[
        CostDriver(
            "Clinical labor (NP/PA + support)", "~55-70% of cost",
            "The whole variable cost against thin volume — the reason the "
            "standalone format struggles.", "ILLUSTRATIVE"),
        CostDriver(
            "In-store space / occupancy allocation", "~10-20% of cost",
            "The retail footprint the clinic occupies, often an internal "
            "transfer priced by the parent.", "ILLUSTRATIVE"),
        CostDriver(
            "Point-of-care testing, vaccines & supplies", "~10-20% of cost",
            "Rapid tests plus vaccine product and administration inventory — "
            "the immunization line's cost of goods.", "ILLUSTRATIVE"),
        CostDriver(
            "Technology, protocols & compliance (CLIA, scope)",
            "~5-10% of cost",
            "The protocol/EHR/telehealth backbone and clinical governance the "
            "model requires.", "ILLUSTRATIVE"),
        CostDriver(
            "G&A allocated from the retail parent", "variable",
            "Corporate overhead the clinic bears as one line inside a much "
            "larger retail/pharmacy enterprise.", "ILLUSTRATIVE"),
    ],
    state_breakdown=(
        "No public retail-clinic facility roll is vendored, and ownership is "
        "concentrated in a few national retail/pharmacy corporations, so state "
        "geography is omitted rather than fabricated. Qualitatively, the "
        "footprint tracks the parent chains' store networks and — decisively — "
        "state scope-of-practice law: independent-NP-practice states (much of "
        "the West and Northeast) support the staffing model, while restrictive-"
        "supervision states make clinics uneconomic and thin the map. The NPI-"
        "taxonomy and Census ACS connectors below support a real footprint-and-"
        "catchment read; the honest headline is a shrinking, strategically-"
        "owned base, not a fragmented acquirable one."),
)

register(REPORT)
