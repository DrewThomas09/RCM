"""Ground-ambulance unit economics — the cited benchmark layer.

Replaces the suite's fabricated per-leg P&L (rev $600–1,300 vs cost $1,040,
none of it filed) with what is actually published, each figure carrying its
source. Three layers:

  1. The Medicare FEE LADDER — CY2025 conversion factor × the AFS relative
     value units = national unadjusted base rates by HCPCS (GOV inputs,
     DERIVED arithmetic, equation shown).
  2. The GADCS BENCHMARKS — mean cost + mean reimbursement per transport,
     labor share, unpaid share, from the first federal ambulance cost
     collection (RAND/CMS; figures captured from trade coverage of the
     report → needs_reverify until the PDFs are re-pulled).
  3. The PAYER ECONOMICS — commercial-vs-Medicare multiples and OON shares
     (HCCI / FAIR Health / Peterson-KFF / Health Affairs / JAMA, several
     PubMed-verbatim).

The honest bottom line this module encodes: GADCS MEAN economics are
negative (readiness-heavy 911 books drag the mean); a scheduled IFT
specialist's thesis is the spread it earns via unit-hour utilization and
payer selection — a diligence request against MMT's actuals, not a public
number. No fabricated margin is published here.

Research pull 2026-07-10. Degrade — never raise.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# ── 1. Medicare fee ladder (CY2025) ─────────────────────────────────────────
# Conversion factor: captured as $278.98 (MedPAC Payment Basics 2025 / CMS
# PUF via search synthesis — re-verify against the PUF before circulation).
# RVUs are the long-standing AFS relative values (CMS Claims Processing
# Manual ch.15). Base rate = CF × RVU (national, unadjusted, before GPCI on
# the 70% labor share and the +2%/+3%/+22.6% urban/rural/super-rural
# add-ons, which run through 2027 under CAA 2026 §6203).
CY2025_CONVERSION_FACTOR = 278.98
CF_BASIS = ("GOV (re-verify) · CY2025 AFS conversion factor $278.98 — "
            "MedPAC Payment Basics 2025 / CMS AFS PUF; AIF CY2025 +2.4%, "
            "CY2026 +2.0%")

@dataclass(frozen=True)
class FeeRung:
    hcpcs: str
    label: str
    rvu: float
    note: str = ""

    @property
    def national_base(self) -> float:
        return round(CY2025_CONVERSION_FACTOR * self.rvu, 2)


FEE_LADDER: Tuple[FeeRung, ...] = (
    FeeRung("A0428", "BLS non-emergency", 1.00,
            "The scheduled-IFT workhorse. ESRD dialysis-related BLS "
            "non-emergency pays fee schedule −23% (42 CFR 414, since "
            "Oct 2018)."),
    FeeRung("A0429", "BLS emergency", 1.60),
    FeeRung("A0426", "ALS1 non-emergency", 1.20),
    FeeRung("A0427", "ALS1 emergency", 1.90),
    FeeRung("A0433", "ALS2", 2.75),
    FeeRung("A0434", "Specialty care transport (SCT)", 3.25,
            "RVU standard per the manual; not excerpt-confirmed in "
            "tonight's pull — flagged."),
)

MILEAGE_NOTE = ("Loaded mileage (A0425): Medicare ≈$8/mile vs commercial "
                "ESI ≈$17/mile in 2022 (HCCI); exact CY2025 rate sits in "
                "the blocked CMS PUF — re-verify.")


# ── 2. GADCS benchmarks ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class EconBenchmark:
    key: str
    figure: str
    value: str
    basis: str
    source: str
    url: str
    quote: str = ""
    verbatim: bool = False
    needs_reverify: bool = True


_B = EconBenchmark

BENCHMARKS: Tuple[EconBenchmark, ...] = (
    _B("gadcs_cost_mean",
       "Mean cost to complete an ambulance transport (2022–23, all payers, "
       "readiness included)",
       "$2,673 all agencies · $3,127 governmental · $1,778 private "
       "for-profit",
       "SOURCED",
       "CMS/RAND GADCS Report, Year 1–2 cohort (Dec 2024), via EMS|MC "
       "coverage",
       "https://www.cms.gov/files/document/medicare-ground-ambulance-data-"
       "collection-system-gadcs-report-year-1-and-year-2-cohort-analysis."
       "pdf",
       "The mean cost to complete an ambulance transport was $2,673."),
    _B("gadcs_reimb_mean",
       "Mean reimbursement per ambulance transport (all provider + payer "
       "types)",
       "$1,147",
       "SOURCED",
       "CMS/RAND GADCS Report, Year 1–2 cohort, via EMS|MC coverage",
       "https://emsmc.com/in-the-news/takeaways-from-the-first-cms-data-"
       "collection-report-on-ambulance-services-and-what-we-need-to-do-"
       "about-it/",
       "Across all provider and payer types, the mean reimbursement per "
       "ambulance transport is $1,147."),
    _B("gadcs_labor_share",
       "Labor share of total ambulance cost",
       "69% (Y1–2) → 70.7% (Y1–4 appendix, Dec 2025)",
       "SOURCED",
       "GADCS reports via AIMHI/EMS1 + AAA coverage",
       "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/",
       "labor (including wages and benefits) represents 69% of the cost "
       "of ambulance service delivery."),
    _B("gadcs_unpaid",
       "Share of ambulance transports that go entirely unpaid",
       "19.7% (up from 18.8% in the first cohort)",
       "SOURCED",
       "GADCS Year 1–4 appendix (Dec 2025) via AAA coverage",
       "https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/",
       "19.7% of ambulance transports go unpaid, up from 18.8% in the "
       "initial cohort."),
    _B("gadcs_medicare_revshare",
       "Medicare + Medicare Advantage share of transport revenue",
       "42% (MA share of revenue grew >30% across cohorts)",
       "SOURCED",
       "GADCS reports via EMS|MC / AAA coverage",
       "https://emsmc.com/in-the-news/takeaways-from-the-first-cms-data-"
       "collection-report-on-ambulance-services-and-what-we-need-to-do-"
       "about-it/",
       "Medicare and Medicare Advantage brought in 42% of total transport "
       "revenue."),
    _B("medicare_avg_payment",
       "Medicare FFS average payment per ground transport (incl. mileage)",
       "$469 = $5.3B / 11.3M transports (2024)",
       "DERIVED",
       "MedPAC Ambulance Payment Basics, Oct 2024 (both inputs GOV)",
       "https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_"
       "Basics_24_ambulance_FINAL_SEC.pdf",
       "", verbatim=True, needs_reverify=False),
    _B("volume_cost_curve",
       "Volume-cost relationship",
       "Strong INVERSE relationship between response volume and cost per "
       "response — scale is the cost lever",
       "SOURCED",
       "MedPAC assessment of GADCS data (Dec 2025) via coverage",
       "https://www.medpac.gov/wp-content/uploads/2025/01/Tab-M-Ambulance-"
       "Dec-2025.pdf",
       "a strong inverse relationship between ambulance response volume "
       "and cost per response."),
    _B("gao_2010",
       "Historical anchor: median cost per transport + Medicare margin "
       "(2010)",
       "$429 median (range $224–$2,204); Medicare margin +2% with "
       "add-ons, −1% without",
       "GOV",
       "GAO-13-6, 'Ambulance Providers: Costs and Medicare Margins Varied "
       "Widely' (Oct 2012)",
       "https://www.gao.gov/products/gao-13-6",
       "The median cost per transport for ground ambulance providers in "
       "GAO's 2010 sample was $429, ranging from $224 to $2,204."),
    _B("uhu_benchmarks",
       "Unit-hour utilization benchmarks",
       "911 systems target ~0.30–0.50; AIMHI survey mean 0.508; "
       "non-emergency/IFT providers target HIGHER (no published consensus "
       "IFT number)",
       "SOURCED",
       "AIMHI benchmarking / EMS1 UHU explainers",
       "https://aimhi.mobi/benchmarking-resources/",
       "911-only agencies typically target between 0.30 and 0.50 UHU."),
)


# ── 3. Payer economics ───────────────────────────────────────────────────────
PAYER_FACTS: Tuple[EconBenchmark, ...] = (
    _B("hcci_multiple",
       "Commercial (ESI) base-rate price vs Medicare, ground ambulance",
       "2.0x in 2022 ($718 vs $365); 1.8x in 2016; mileage 2.1x "
       "($17 vs $8)",
       "SOURCED",
       "Health Care Cost Institute, 'Commercial Prices for Ground "
       "Ambulance are Double Medicare Rates'",
       "https://healthcostinstitute.org/all-hcci-reports/commercial-"
       "prices-for-ground-ambulance-are-double-medicare-rates/",
       "In 2022, the ESI base rate price ($718) was 2.0 times the "
       "Medicare rate ($365)."),
    _B("fairhealth_allowed",
       "In-network commercial allowed amounts vs Medicare (excl. mileage)",
       "ALS-E $758 vs $463 (~1.64x, 2020); BLS $522 vs $390 (~1.34x)",
       "SOURCED",
       "FAIR Health ground-ambulance white paper (2022) + brief (2023)",
       "https://www.fairhealth.org/article/nearly-60-percent-of-ground-"
       "ambulance-rides-were-out-of-network-in-2022-according-to-new-fair-"
       "health-study"),
    _B("ma_hpc_multiple",
       "Median commercial vs Medicare, Massachusetts (2019)",
       "2.7x ($1,185 vs $501); 4.6x MassHealth (Medicaid)",
       "SOURCED",
       "Massachusetts HPC/CHIA emergency ground ambulance chartpack",
       "https://www.mass.gov/doc/emergency-ground-ambulance-utilization-"
       "and-payment-rates-in-massachusetts-chartpack/download"),
    _B("oon_shares",
       "Out-of-network shares, ground ambulance",
       "~60% of rides OON in 2022 (FAIR Health); 51% emergency / 39% "
       "non-emergency rides carried an OON charge (Peterson-KFF 2021); "
       "54.8% of 2.03M MarketScan services billed OON 2015–20",
       "ACADEMIC",
       "FAIR Health 2023; Peterson-KFF 2021; Gong et al., JAMA Network "
       "Open 2024",
       "https://doi.org/10.1001/jamanetworkopen.2024.0118",
       "1,113,676 (54.8%) were billed OON", verbatim=True,
       needs_reverify=False),
    _B("ownership_prices",
       "Ownership structure moves prices",
       "Private-sector transports carry substantially higher allowed "
       "amounts + surprise-bill exposure; PE-/public-owned higher still; "
       "28% of commercial emergency transports 2014–17 = potential "
       "surprise bill",
       "ACADEMIC",
       "Adler et al., Health Affairs 2023 (USC-Brookings)",
       "https://doi.org/10.1377/hlthaff.2022.00738",
       "28 percent of commercially insured emergency ground ambulance "
       "transports during the period 2014-17 resulted in a potential "
       "surprise bill", verbatim=True, needs_reverify=False),
    _B("medicare_mix_proxy",
       "Medicare share of payer mix (proxy)",
       "~40% of a typical agency's payer mix (AIMHI); GADCS transport-"
       "level payer-mix table not extractable from coverage — flagged "
       "diligence request",
       "SOURCED",
       "AIMHI 'The true cost of a 911 call' (EMS1)",
       "https://www.ems1.com/ems-management/the-true-cost-of-a-911-call-"
       "breaking-down-ems-economics",
       "the average Medicare reimbursement for an emergency ambulance "
       "call is $480, and Medicare typically represents about 40% of an "
       "EMS agency's payer mix."),
)

THE_HONEST_BOTTOM_LINE = (
    "GADCS mean economics are negative — mean cost $2,673 vs mean "
    "reimbursement $1,147 — because the mean carries readiness-heavy "
    "municipal 911 books. The IFT specialist thesis is precisely the "
    "spread against that mean: a scheduled book runs unit-hour "
    "utilization above the 0.30–0.50 911 band, a private for-profit "
    "cost base ($1,778 GADCS mean) rather than a governmental one "
    "($3,127), and a payer-selected mix where commercial pays ~2.0x "
    "Medicare. MMT's actual per-leg P&L is a diligence request against "
    "company data — no public figure exists, and this page does not "
    "invent one."
)


def fee_ladder() -> Tuple[FeeRung, ...]:
    return FEE_LADDER


def benchmark(key: str) -> Optional[EconBenchmark]:
    for b in BENCHMARKS + PAYER_FACTS:
        if b.key == key:
            return b
    return None


def all_benchmarks() -> Tuple[EconBenchmark, ...]:
    return BENCHMARKS + PAYER_FACTS
