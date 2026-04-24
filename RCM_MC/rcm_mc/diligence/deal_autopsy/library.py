"""Curated library of historical PE healthcare deals.

Each deal is reduced to a 9-dimension signature taken at (or near)
entry, plus a narrative record of what actually happened. The
signatures are the matchable surface; the narratives are the story
a partner reads after a match surfaces.

The 9 dimensions (each in [0.0, 1.0], higher = more risk):
    1. lease_intensity         — annual lease / revenue, capped 0.20
    2. ebitdar_stress          — 0.0 when coverage >= 2.5x, 1.0 when <= 1.0x
    3. medicare_mix            — Medicare + MA share of revenue
    4. payer_concentration     — top-1 payer share of revenue
    5. denial_rate             — baseline claim-level denial rate
    6. dar_stress              — days-in-AR / 120, capped
    7. regulatory_exposure     — composite (CPOM + NSA RED + V28 + antitrust)
    8. physician_concentration — top-10% RVU share
    9. oon_revenue_share       — out-of-network revenue share (NSA trigger)

Why these nine: every dimension is directly observable from the
CCD + counterfactual + Steward Score + V28 + cyber outputs we
already compute. No new data pipeline required.

Outcomes tracked:
    - BANKRUPTCY         terminal Chapter 7 or closure
    - CHAPTER_11         reorganization (often wiping out sponsors)
    - DISTRESSED_SALE    forced asset sale below cost basis
    - DELISTED           public delisting under financial duress
    - STRONG_EXIT        sponsor realised MOIC > 2.0x
    - STRONG_PUBLIC      IPO'd and trading above entry multiple

Source: public reporting (SEC filings, bankruptcy dockets,
trade press, landlord REIT disclosures). Signatures are
best-efforts reconstructions — the directional story is what the
matcher is built on, not decimal-precision replay.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


OUTCOME_BANKRUPTCY = "BANKRUPTCY"
OUTCOME_CHAPTER_11 = "CHAPTER_11"
OUTCOME_DISTRESSED_SALE = "DISTRESSED_SALE"
OUTCOME_DELISTED = "DELISTED"
OUTCOME_STRONG_EXIT = "STRONG_EXIT"
OUTCOME_STRONG_PUBLIC = "STRONG_PUBLIC"

OUTCOMES: Tuple[str, ...] = (
    OUTCOME_BANKRUPTCY,
    OUTCOME_CHAPTER_11,
    OUTCOME_DISTRESSED_SALE,
    OUTCOME_DELISTED,
    OUTCOME_STRONG_EXIT,
    OUTCOME_STRONG_PUBLIC,
)


_NEGATIVE_OUTCOMES = {
    OUTCOME_BANKRUPTCY, OUTCOME_CHAPTER_11,
    OUTCOME_DISTRESSED_SALE, OUTCOME_DELISTED,
}


@dataclass(frozen=True)
class DealAutopsy:
    """Narrative record of how a historical deal ended."""

    outcome: str
    outcome_year: int
    primary_killer: str
    early_warning_signs: Tuple[str, ...]
    partner_lesson: str
    partner_quote: str

    @property
    def is_negative(self) -> bool:
        return self.outcome in _NEGATIVE_OUTCOMES


@dataclass(frozen=True)
class HistoricalDeal:
    """A historical PE healthcare deal with entry signature + autopsy."""

    deal_id: str
    name: str
    sponsor: str
    sector: str               # HOSPITAL_SYSTEM / PHYSICIAN_STAFFING / ASC / SNF / OTHER
    entry_year: int
    # The 9-dim signature. Dimensions documented at module top.
    signature: Tuple[float, float, float, float, float, float,
                     float, float, float]
    autopsy: DealAutopsy
    sources: Tuple[str, ...] = field(default_factory=tuple)


# ────────────────────────────────────────────────────────────────────
# The Library — 12 curated deals across sector × outcome.
# Eight negative outcomes + four survivors. Signatures are
# directional reconstructions from public reporting, not point
# estimates.
# ────────────────────────────────────────────────────────────────────

_LIBRARY: Tuple[HistoricalDeal, ...] = (
    HistoricalDeal(
        deal_id="steward_2010",
        name="Steward Health Care",
        sponsor="Cerberus Capital Management",
        sector="HOSPITAL_SYSTEM",
        entry_year=2010,
        #          lease  ebitdar  medicare  payer  denial  dar    reg    physconc  oon
        signature=(0.90,  0.85,    0.55,     0.35,  0.14,   0.62,  0.58,  0.30,     0.08),
        autopsy=DealAutopsy(
            outcome=OUTCOME_BANKRUPTCY,
            outcome_year=2024,
            primary_killer="sale-leaseback_to_mpt_crushed_ebitdar_coverage",
            early_warning_signs=(
                "Master lease with MPT at 3.5% annual escalator signed in 2016 converted owned real estate into a liability indexed above inflation.",
                "EBITDAR coverage fell below 1.2x within 3 years of the sale-leaseback.",
                "Expansion into Texas (NSA-RED) and Malta concentrated regulatory exposure across jurisdictions with incompatible reform timelines.",
                "Physician attrition in flagship MA hospitals went unaddressed for 4+ quarters before partner-level action.",
            ),
            partner_lesson="If the sale-leaseback PV savings evaporate within 5 years of lease escalators, the whole deal is an unhedged rates trade. Model escalator caps on day one.",
            partner_quote="We mistook a one-time liquidity event for a sustainable EBITDAR profile.",
        ),
        sources=(
            "Boston Globe 2024 bankruptcy coverage",
            "MPT Q4 2023 10-K tenant disclosures",
            "HHS hospital cost reports 2010-2023",
        ),
    ),
    HistoricalDeal(
        deal_id="envision_2018",
        name="Envision Healthcare",
        sponsor="KKR",
        sector="PHYSICIAN_STAFFING",
        entry_year=2018,
        signature=(0.15,  0.55,    0.35,     0.42,  0.19,   0.48,  0.78,  0.65,     0.58),
        autopsy=DealAutopsy(
            outcome=OUTCOME_CHAPTER_11,
            outcome_year=2023,
            primary_killer="no_surprises_act_killed_oon_billing_model",
            early_warning_signs=(
                "58% of revenue came from out-of-network billing — the single largest business-model-level legal-regulatory risk in the sector.",
                "UnitedHealth contract dispute signalled the in-network counterparties' willingness to exit.",
                "NSA was already in legislative draft at underwrite; the sponsor priced as if it would be blocked.",
                "Physician-comp concentration in ER/anesthesia subspecialties meant comp couldn't be rationalized without provider walkouts.",
            ),
            partner_lesson="If a proposed federal bill kills >30% of revenue overnight, the deal is a regulatory trade dressed as a staffing thesis. Stress the thesis with the bill in force.",
            partner_quote="The playbook assumed the lobbying would hold. The lobbying did not hold.",
        ),
        sources=(
            "Envision Ch 11 docket (S.D. Tex 2023)",
            "UnitedHealth 2022 contract termination press release",
            "No Surprises Act congressional record",
        ),
    ),
    HistoricalDeal(
        deal_id="manorcare_2007",
        name="HCR ManorCare",
        sponsor="Carlyle Group",
        sector="SNF",
        entry_year=2007,
        signature=(0.85,  0.75,    0.72,     0.55,  0.16,   0.55,  0.62,  0.20,     0.05),
        autopsy=DealAutopsy(
            outcome=OUTCOME_CHAPTER_11,
            outcome_year=2018,
            primary_killer="reit_lease_plus_doj_false_claims_plus_wage_inflation",
            early_warning_signs=(
                "6.1B sale-leaseback to HCP (now Welltower) in 2011 inverted the cost structure.",
                "DOJ False Claims Act intervention on therapy billing became a material ongoing expense.",
                "SNF wage inflation accelerated after 2013, eroding the operating leverage the deal underwrote.",
                "Medicare bundled-payment transition disproportionately hit the high-acuity skilled-nursing mix.",
            ),
            partner_lesson="SNFs plus a REIT landlord plus unresolved DOJ exposure is three reinforcing negatives. Clear the FCA docket before the sale-leaseback.",
            partner_quote="We were right on the SNF thesis and wrong on the cost structure.",
        ),
        sources=(
            "HCR ManorCare Ch 11 docket (2018)",
            "Welltower/HCP tenant disclosures",
            "DOJ press release on settled FCA claims",
        ),
    ),
    HistoricalDeal(
        deal_id="prospect_2010",
        name="Prospect Medical Holdings",
        sponsor="Leonard Green & Partners",
        sector="HOSPITAL_SYSTEM",
        entry_year=2010,
        signature=(0.78,  0.80,    0.48,     0.50,  0.18,   0.72,  0.65,  0.40,     0.12),
        autopsy=DealAutopsy(
            outcome=OUTCOME_DISTRESSED_SALE,
            outcome_year=2023,
            primary_killer="dividend_recap_plus_mpt_sale_leaseback_plus_capex_starvation",
            early_warning_signs=(
                "Dividend recap totaling ~$700M extracted most of the value pre-exit.",
                "MPT sale-leaseback overlapped with the dividend recap, leaving the operating entity structurally stressed.",
                "Capex deferral manifested as JCAHO and state survey failures at multiple hospitals.",
                "Yale-New Haven walked away from the CT hospital acquisition, signalling unlevered buyers wouldn't clear the cost basis.",
            ),
            partner_lesson="A dividend recap plus an MPT sale-leaseback is a double-strip of equity. Markets can see this; your exit buyer will see it.",
            partner_quote="We kept extracting. The operating company kept absorbing. Then it stopped absorbing.",
        ),
        sources=(
            "Connecticut Attorney General investigative filings 2023",
            "MPT tenant concentration disclosures",
            "Bloomberg 2022-2023 Prospect reporting",
        ),
    ),
    HistoricalDeal(
        deal_id="adeptus_2014",
        name="Adeptus Health",
        sponsor="Sterling Partners (pre-IPO); IPO 2014",
        sector="OTHER",
        entry_year=2014,
        signature=(0.40,  0.70,    0.18,     0.32,  0.21,   0.65,  0.72,  0.55,     0.75),
        autopsy=DealAutopsy(
            outcome=OUTCOME_CHAPTER_11,
            outcome_year=2017,
            primary_killer="freestanding_er_oon_billing_collided_with_payer_pushback",
            early_warning_signs=(
                "75% out-of-network revenue share inside a facility model targeting commercial payers.",
                "Aggressive growth plan of 30-50 facilities a year outran the payer-contract pipeline.",
                "BCBS-TX declared Adeptus facilities out-of-network in 2016, collapsing same-store revenue.",
                "USAP-style antitrust/regulatory overhang was foreseeable but unmodeled.",
            ),
            partner_lesson="Any facility model earning >50% of revenue OON is living on a single payer's tolerance. Underwrite the loss of that tolerance.",
            partner_quote="We confused a billing arbitrage for an operating thesis.",
        ),
        sources=(
            "Adeptus S-1 and subsequent 10-Ks",
            "BCBS-TX 2016 network notice",
            "Ch 11 filing D. Delaware 2017",
        ),
    ),
    HistoricalDeal(
        deal_id="genesis_2007",
        name="Genesis HealthCare",
        sponsor="Formation Capital / JER Partners",
        sector="SNF",
        entry_year=2007,
        signature=(0.82,  0.75,    0.75,     0.58,  0.15,   0.52,  0.58,  0.18,     0.04),
        autopsy=DealAutopsy(
            outcome=OUTCOME_DELISTED,
            outcome_year=2021,
            primary_killer="reit_lease_plus_medicare_bundle_plus_wage_inflation",
            early_warning_signs=(
                "Multi-REIT lease stack with cross-defaults constrained any single-asset sale.",
                "Medicare bundled-payment policy shift reduced reimbursement for the high-acuity SNF census.",
                "Nurse wage inflation after 2018 compressed contribution margin below 3% system-wide.",
                "Dividend eliminations and going-concern language in annual report preceded the delisting by ~24 months.",
            ),
            partner_lesson="SNFs with a multi-REIT lease stack have no real-estate optionality. The first bad quarter is the whole thesis.",
            partner_quote="Every lever we needed was a landlord's lever.",
        ),
        sources=(
            "Genesis 10-Ks 2015-2020",
            "Welltower / Omega tenant disclosures",
            "OTC delisting notice 2021",
        ),
    ),
    HistoricalDeal(
        deal_id="quorum_2016",
        name="Quorum Health",
        sponsor="CHS spin (2016)",
        sector="HOSPITAL_SYSTEM",
        entry_year=2016,
        signature=(0.55,  0.82,    0.58,     0.38,  0.19,   0.78,  0.55,  0.35,     0.08),
        autopsy=DealAutopsy(
            outcome=OUTCOME_CHAPTER_11,
            outcome_year=2020,
            primary_killer="rural_hospital_economics_plus_spinco_leverage",
            early_warning_signs=(
                "Rural hospital portfolio with systemically declining admissions.",
                "Spin-off left Quorum with $1.2B of debt and minimal operating cash.",
                "Days in AR rose from 50 to 78 in the first 18 months post-spin.",
                "Divestiture program exceeded 40% of facilities — portfolio was unsellable as a whole.",
            ),
            partner_lesson="A spin-off loaded with the parent's weakest hospitals plus the parent's debt is not an investable thesis. Treat SpinCo leverage-mix as a red flag.",
            partner_quote="The spin was a liquidity event for the parent, not a strategy for us.",
        ),
        sources=(
            "Quorum Health 10-K 2016-2019",
            "Ch 11 docket D. Delaware 2020",
        ),
    ),
    HistoricalDeal(
        deal_id="air_methods_2017",
        name="Air Methods",
        sponsor="American Securities",
        sector="OTHER",
        entry_year=2017,
        signature=(0.22,  0.60,    0.28,     0.40,  0.23,   0.55,  0.85,  0.45,     0.82),
        autopsy=DealAutopsy(
            outcome=OUTCOME_CHAPTER_11,
            outcome_year=2023,
            primary_killer="no_surprises_act_eliminated_oon_air_ambulance_billing",
            early_warning_signs=(
                "82% of commercial revenue billed out-of-network at high unit prices.",
                "NSA final rule extended to air ambulance in 2022 — directly invalidated the unit economics.",
                "IDR arbitration under NSA yielded awards far below the billed rates Air Methods had underwritten.",
                "Patient-balance-billing news cycles (Vox 'surprise bill' coverage) signalled political endgame.",
            ),
            partner_lesson="Air ambulance is the strongest example of a sub-sector killed by NSA. If your target has any meaningful NSA air-ambulance analog, stress the thesis with IDR awards at CMS-qualified rate.",
            partner_quote="We priced a franchise. We bought a regulatory bet.",
        ),
        sources=(
            "Air Methods Ch 11 docket 2023",
            "Vox 'surprise air ambulance bill' 2019",
            "CMS IDR award disclosures 2023",
        ),
    ),
    # ─── Survivors ────────────────────────────────────────────────
    HistoricalDeal(
        deal_id="hca_2006",
        name="HCA Healthcare",
        sponsor="Bain + KKR + MLGPE",
        sector="HOSPITAL_SYSTEM",
        entry_year=2006,
        signature=(0.12,  0.28,    0.42,     0.22,  0.08,   0.38,  0.30,  0.18,     0.04),
        autopsy=DealAutopsy(
            outcome=OUTCOME_STRONG_EXIT,
            outcome_year=2011,
            primary_killer="",
            early_warning_signs=(
                "Scale: 170+ hospitals with nationwide payer contract leverage.",
                "In-network discipline kept OON exposure under 5% across the system.",
                "Employed-physician model rather than contracted staffing — insulated against NSA precursors.",
                "Owned most real estate outright — sale-leaseback was never forced.",
            ),
            partner_lesson="Scale + in-network discipline + owned real estate is the survivor pattern. When all three hold, the deal absorbs shocks that kill roll-ups.",
            partner_quote="Size was the risk hedge we paid up for.",
        ),
        sources=(
            "HCA S-1 2011",
            "Bain/KKR LP disclosures",
        ),
    ),
    HistoricalDeal(
        deal_id="usps_2015",
        name="USPI (United Surgical Partners International)",
        sponsor="Welsh Carson → Tenet",
        sector="ASC",
        entry_year=2015,
        signature=(0.18,  0.32,    0.25,     0.28,  0.10,   0.42,  0.35,  0.25,     0.12),
        autopsy=DealAutopsy(
            outcome=OUTCOME_STRONG_EXIT,
            outcome_year=2022,
            primary_killer="",
            early_warning_signs=(
                "ASC tailwind from site-neutral payment and outpatient migration.",
                "Physician-owned joint ventures aligned incentives without triggering antitrust.",
                "Commercial payer contracts in-network by default; Medicare ASC rate growth stable.",
                "Geographic diversification across 20+ states limited state-level regulatory tail risk.",
            ),
            partner_lesson="ASCs with JV ownership and in-network commercial contracts are a demographic tailwind play with limited regulatory tail. The sector-rotation thesis wins.",
            partner_quote="We bet on where care was moving, not on who was paying.",
        ),
        sources=(
            "Tenet 10-Ks 2015-2022",
            "Welsh Carson LP disclosures",
        ),
    ),
    HistoricalDeal(
        deal_id="lhc_2018",
        name="LHC Group",
        sponsor="Public-market roll-up → UHG 2023",
        sector="OTHER",
        entry_year=2018,
        signature=(0.14,  0.38,    0.68,     0.35,  0.11,   0.48,  0.42,  0.20,     0.05),
        autopsy=DealAutopsy(
            outcome=OUTCOME_STRONG_EXIT,
            outcome_year=2023,
            primary_killer="",
            early_warning_signs=(
                "Home-health tailwind from site-neutral payment + aging demographic.",
                "Low OON exposure — Medicare traditional dominated revenue.",
                "Joint-venture strategy with hospital systems aligned referral flow.",
                "Clean M&A track record without goodwill impairments.",
            ),
            partner_lesson="Home health with clean referrals and high Medicare mix is defensible. UHG paid a strategic multiple on top of the organic growth.",
            partner_quote="We sold into the strategic, not the financial, buyer.",
        ),
        sources=(
            "LHC 10-Ks 2018-2022",
            "UHG acquisition 8-K 2023",
        ),
    ),
    HistoricalDeal(
        deal_id="surgery_partners_2017",
        name="Surgery Partners",
        sponsor="Bain Capital",
        sector="ASC",
        entry_year=2017,
        signature=(0.20,  0.42,    0.22,     0.32,  0.12,   0.45,  0.38,  0.28,     0.15),
        autopsy=DealAutopsy(
            outcome=OUTCOME_STRONG_PUBLIC,
            outcome_year=2024,
            primary_killer="",
            early_warning_signs=(
                "ASC + outpatient migration demographic tailwind.",
                "Physician-partner JV model kept comp aligned without FTC exposure.",
                "Low OON — predominantly in-network commercial plus Medicare ASC rates.",
                "Deleveraging cadence kept covenant headroom through 2020 COVID dislocation.",
            ),
            partner_lesson="ASC ownership plus in-network discipline plus deleveraging covenant headroom — the defensible configuration.",
            partner_quote="Nothing exotic. Right sector, right payer mix, disciplined capital structure.",
        ),
        sources=(
            "Surgery Partners 10-Ks 2018-2023",
            "Bain Capital LP disclosures",
        ),
    ),
)


def historical_library() -> Tuple[HistoricalDeal, ...]:
    """Return the full library (tuple — immutable)."""
    return _LIBRARY


def get_deal_by_id(deal_id: str) -> HistoricalDeal:
    """Lookup a single deal by id. Raises KeyError if missing."""
    for d in _LIBRARY:
        if d.deal_id == deal_id:
            return d
    raise KeyError(f"unknown historical deal: {deal_id!r}")


def outcomes_summary() -> Dict[str, int]:
    """Counts of deals per outcome — useful for UI."""
    counts: Dict[str, int] = {o: 0 for o in OUTCOMES}
    for d in _LIBRARY:
        counts[d.autopsy.outcome] += 1
    return counts
