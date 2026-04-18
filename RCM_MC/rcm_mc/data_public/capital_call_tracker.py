"""Capital Call / LP Communication Tracker.

Tracks capital calls, distributions, quarterly reporting, LP requests,
and treasury movements across GP-LP relationships.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CapitalCall:
    fund: str
    call_date: str
    call_number: int
    amount_m: float
    purpose: str
    unfunded_before_m: float
    unfunded_after_m: float
    ltm_called_m: float
    defaulted_lp: bool


@dataclass
class DistributionEvent:
    fund: str
    dist_date: str
    dist_number: int
    amount_m: float
    type: str
    source: str
    ltm_distributed_m: float
    net_to_lps_m: float


@dataclass
class FundCashflow:
    fund: str
    vintage: int
    committed_m: float
    called_m: float
    distributed_m: float
    nav_m: float
    dpi: float
    tvpi: float
    unfunded_m: float
    next_call_estimate: str


@dataclass
class LPCommunication:
    lp_name: str
    commitment_m: float
    communication_type: str
    date: str
    subject: str
    response_due: str
    status: str


@dataclass
class ReportingSchedule:
    fund: str
    quarter: str
    report_type: str
    due_date: str
    completion_status: str
    pages: int
    owner: str


@dataclass
class TreasuryMovement:
    fund: str
    movement_type: str
    date: str
    amount_m: float
    from_entity: str
    to_entity: str
    bank: str
    status: str


@dataclass
class CapCallResult:
    total_funds: int
    total_committed_b: float
    total_called_b: float
    total_distributed_b: float
    ltm_calls_m: float
    ltm_distributions_m: float
    net_ltm_m: float
    calls: List[CapitalCall]
    distributions: List[DistributionEvent]
    cashflows: List[FundCashflow]
    lp_comms: List[LPCommunication]
    reporting: List[ReportingSchedule]
    treasury: List[TreasuryMovement]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_calls() -> List[CapitalCall]:
    return [
        CapitalCall("WCAS Healthcare XV", "2026-03-15", 7, 485.0, "Project Azalea initial equity",
                    2450.0, 1965.0, 1285.0, False),
        CapitalCall("WCAS Healthcare XV", "2026-04-10", 8, 125.0, "Working capital + fees",
                    1965.0, 1840.0, 1285.0, False),
        CapitalCall("Bain Life Sciences IV", "2026-03-22", 9, 420.0, "Project Sierra platform equity",
                    1620.0, 1200.0, 985.0, False),
        CapitalCall("Apollo Healthcare II", "2026-02-28", 6, 385.0, "Project Tundra equity",
                    1980.0, 1595.0, 780.0, False),
        CapitalCall("KKR Healthcare III", "2026-02-15", 10, 525.0, "Project Ridge equity",
                    2265.0, 1740.0, 1195.0, False),
        CapitalCall("TPG Healthcare II", "2026-03-01", 5, 295.0, "Project Meridian equity + WC",
                    2285.0, 1990.0, 565.0, False),
        CapitalCall("Silver Lake HC Tech III", "2026-03-20", 8, 415.0, "Project Terra equity",
                    1350.0, 935.0, 925.0, False),
        CapitalCall("Carlyle Healthcare III", "2026-02-18", 7, 245.0, "Project Quartz equity",
                    1180.0, 935.0, 585.0, False),
        CapitalCall("Warburg XIV HC", "2026-04-05", 6, 385.0, "Project Horizon equity",
                    1725.0, 1340.0, 695.0, False),
        CapitalCall("Summit Growth XIII", "2026-03-08", 4, 185.0, "Project Vista equity",
                    1620.0, 1435.0, 350.0, False),
        CapitalCall("Advent XI HC Allocation", "2026-03-25", 5, 315.0, "Project Aurora equity",
                    2385.0, 2070.0, 765.0, False),
        CapitalCall("L Catterton GP IV", "2026-02-22", 3, 165.0, "Project Tide equity",
                    875.0, 710.0, 285.0, False),
    ]


def _build_distributions() -> List[DistributionEvent]:
    return [
        DistributionEvent("WCAS Healthcare XIII", "2026-03-20", 18, 485.0, "return of capital + gain",
                          "Project Fern (vision) exit", 1125.0, 460.0),
        DistributionEvent("KKR Healthcare II", "2026-02-28", 15, 380.0, "return of capital + gain",
                          "Project Pine (MSK) SBO exit", 985.0, 355.0),
        DistributionEvent("Bain Life Sciences III", "2026-03-15", 14, 425.0, "gain + carry cross-over",
                          "Project Oak (lab) strategic sale", 1085.0, 400.0),
        DistributionEvent("Apollo Healthcare I", "2026-02-18", 11, 185.0, "dividend recap",
                          "USAP dividend recap", 640.0, 175.0),
        DistributionEvent("Advent GPE X HC Allocation", "2026-03-25", 16, 485.0, "gain + carry",
                          "Home Health exit Q4 2025", 1265.0, 460.0),
        DistributionEvent("Silver Lake HC Tech II", "2026-03-05", 13, 545.0, "IPO secondary",
                          "Cohere Health IPO", 1485.0, 515.0),
        DistributionEvent("Carlyle Healthcare II", "2026-02-22", 12, 225.0, "return of capital + gain",
                          "Anatomic Path SBO", 685.0, 210.0),
        DistributionEvent("Summit Growth XII", "2026-03-10", 11, 185.0, "return of capital + gain",
                          "DSO strategic sale", 550.0, 172.0),
        DistributionEvent("L Catterton III", "2026-01-28", 10, 125.0, "continuation vehicle proceeds",
                          "Fertility partial CV", 485.0, 118.0),
        DistributionEvent("TPG Healthcare Partners", "2026-03-28", 8, 195.0, "SBO proceeds",
                          "Cardiology SBO", 465.0, 182.0),
    ]


def _build_cashflows() -> List[FundCashflow]:
    return [
        FundCashflow("WCAS Healthcare XIII", 2018, 4100.0, 4100.0, 5945.0, 3775.0, 1.45, 2.37, 0.0, "n/a (fully called)"),
        FundCashflow("WCAS Healthcare XIV", 2021, 5200.0, 4265.0, 1065.0, 6485.0, 0.25, 1.77, 935.0, "2026-Q3"),
        FundCashflow("WCAS Healthcare XV", 2024, 6500.0, 2275.0, 0.0, 2455.0, 0.0, 1.08, 4225.0, "2026-Q2"),
        FundCashflow("KKR Healthcare II", 2019, 4000.0, 3800.0, 4864.0, 3980.0, 1.28, 2.33, 200.0, "2026-Q3 (final)"),
        FundCashflow("KKR Healthcare III", 2022, 5800.0, 3770.0, 680.0, 4970.0, 0.18, 1.50, 2030.0, "2026-Q2"),
        FundCashflow("Bain Life Sciences III", 2019, 3200.0, 2944.0, 4863.0, 2720.0, 1.52, 2.37, 256.0, "2026-Q4 (final)"),
        FundCashflow("Bain Life Sciences IV", 2022, 4500.0, 2610.0, 324.0, 3165.0, 0.12, 1.37, 1890.0, "2026-Q3"),
        FundCashflow("Apollo Healthcare I", 2020, 3500.0, 3080.0, 3265.0, 3922.0, 0.95, 2.10, 420.0, "2026-Q3 (topping off)"),
        FundCashflow("Apollo Healthcare II", 2023, 5000.0, 2250.0, 250.0, 2460.0, 0.05, 1.20, 2750.0, "2026-Q3"),
        FundCashflow("Advent GPE X HC", 2018, 4500.0, 4455.0, 7258.0, 3217.0, 1.62, 2.34, 45.0, "2026-Q4 (final)"),
        FundCashflow("Advent GPE XI HC", 2021, 5500.0, 4290.0, 1210.0, 6705.0, 0.22, 1.60, 1210.0, "2026-Q3"),
        FundCashflow("Silver Lake HC Tech II", 2019, 3500.0, 3360.0, 6370.0, 3162.0, 1.85, 2.77, 140.0, "2026-Q4 (final)"),
    ]


def _build_lp_comms() -> List[LPCommunication]:
    return [
        LPCommunication("CalPERS", 850.0, "Capital Call Notice", "2026-03-15", "WCAS XV Call #7 — $485M", "2026-03-29", "paid"),
        LPCommunication("CPPIB", 925.0, "Capital Call Notice", "2026-03-15", "WCAS XV Call #7 — $485M", "2026-03-29", "paid"),
        LPCommunication("Texas Teachers", 710.0, "Distribution Notice", "2026-03-20", "WCAS XIII Dist #18 — $485M", "2026-04-05", "distributed"),
        LPCommunication("HOOPP", 420.0, "Capital Call Notice", "2026-02-28", "Apollo HC II Call #6", "2026-03-14", "paid"),
        LPCommunication("Temasek", 1150.0, "Side Letter Request", "2026-03-01", "RADV exposure disclosure", "2026-03-15", "responded"),
        LPCommunication("GIC (Singapore)", 985.0, "GP Extension Request", "2026-02-22", "WCAS XIII 1-year extension approval", "2026-03-22", "approved"),
        LPCommunication("ADIA", 780.0, "Valuation Review", "2026-02-18", "Portfolio mark review", "2026-03-18", "responded"),
        LPCommunication("NBIM (Norway)", 685.0, "ESG Reporting", "2026-03-10", "Annual ESG scorecard", "2026-04-10", "in progress"),
        LPCommunication("Harvard Management", 285.0, "Co-Invest Offer", "2026-03-05", "Project Azalea co-invest", "2026-03-20", "declined (conflict)"),
        LPCommunication("Yale Investments", 325.0, "Co-Invest Offer", "2026-03-05", "Project Azalea co-invest", "2026-03-20", "accepted ($18M)"),
        LPCommunication("CPPIB", 925.0, "Co-Invest Offer", "2026-03-05", "Project Azalea co-invest", "2026-03-20", "accepted ($65M)"),
        LPCommunication("Ford Foundation", 165.0, "LP Request", "2026-02-28", "Exit sequencing review", "2026-04-15", "in progress"),
        LPCommunication("Northwestern Mutual", 295.0, "Quarterly Report", "2026-03-31", "Q4 2025 report", "2026-04-14", "distributed"),
        LPCommunication("Adams Street", 465.0, "Secondary Inquiry", "2026-02-25", "LP secondary bid on WCAS XIII", "2026-03-25", "discussing"),
        LPCommunication("HarbourVest", 585.0, "Side-Car Proposal", "2026-03-15", "Project Willow fertility side-car", "2026-04-05", "in review"),
    ]


def _build_reporting() -> List[ReportingSchedule]:
    return [
        ReportingSchedule("WCAS Healthcare XV", "Q4 2025", "Annual Report", "2026-03-31", "distributed", 185, "CFO / Controller"),
        ReportingSchedule("WCAS Healthcare XIV", "Q4 2025", "Annual Report", "2026-03-31", "distributed", 165, "CFO / Controller"),
        ReportingSchedule("WCAS Healthcare XIII", "Q4 2025", "Annual Report", "2026-03-31", "distributed", 145, "CFO / Controller"),
        ReportingSchedule("Apollo Healthcare II", "Q1 2026", "Quarterly Report", "2026-04-30", "in progress", 85, "Fund Accountant"),
        ReportingSchedule("KKR Healthcare III", "Q1 2026", "Quarterly Report", "2026-04-30", "in progress", 92, "Fund Accountant"),
        ReportingSchedule("Bain Life Sciences IV", "Q1 2026", "Quarterly Report", "2026-04-30", "in progress", 88, "Fund Accountant"),
        ReportingSchedule("Silver Lake HC Tech III", "Q4 2025", "Annual Report", "2026-03-31", "distributed", 105, "Fund Accountant"),
        ReportingSchedule("All Funds", "2025-YE", "Audited Financials", "2026-05-15", "draft complete", 485, "PwC / KPMG"),
        ReportingSchedule("WCAS Healthcare XIII", "Q1 2026", "Quarterly Report", "2026-04-30", "in progress", 78, "Fund Accountant"),
        ReportingSchedule("Advent XI HC", "Q1 2026", "Quarterly Report", "2026-04-30", "in progress", 82, "Fund Accountant"),
        ReportingSchedule("All Funds — LPAs", "2026-03-31", "ILPA Template Update", "2026-04-15", "drafting", 35, "Investor Relations"),
        ReportingSchedule("All Funds — ESG", "2025-YE", "PRI / Annual ESG", "2026-05-31", "drafting", 115, "ESG Officer"),
    ]


def _build_treasury() -> List[TreasuryMovement]:
    return [
        TreasuryMovement("WCAS Healthcare XV", "Capital Call Receipt", "2026-03-15", 485.0, "LPs", "Fund Account", "JPMorgan Chase", "received"),
        TreasuryMovement("WCAS Healthcare XV", "Equity Deployment", "2026-03-18", 465.0, "Fund Account", "Project Azalea SPV", "JPMorgan Chase", "wired"),
        TreasuryMovement("Apollo Healthcare II", "Capital Call Receipt", "2026-02-28", 385.0, "LPs", "Fund Account", "Citi", "received"),
        TreasuryMovement("Apollo Healthcare II", "Equity Deployment", "2026-03-04", 375.0, "Fund Account", "Project Tundra SPV", "Citi", "wired"),
        TreasuryMovement("KKR Healthcare III", "Capital Call Receipt", "2026-02-15", 525.0, "LPs", "Fund Account", "Bank of America", "received"),
        TreasuryMovement("KKR Healthcare III", "Equity Deployment", "2026-02-20", 510.0, "Fund Account", "Project Ridge SPV", "Bank of America", "wired"),
        TreasuryMovement("WCAS Healthcare XIII", "Distribution", "2026-03-20", 485.0, "Fund Account", "LPs", "JPMorgan Chase", "sent"),
        TreasuryMovement("KKR Healthcare II", "Distribution", "2026-02-28", 380.0, "Fund Account", "LPs", "Bank of America", "sent"),
        TreasuryMovement("Bain Life Sciences III", "Distribution", "2026-03-15", 425.0, "Fund Account", "LPs", "Goldman Sachs", "sent"),
        TreasuryMovement("Apollo Healthcare I", "Dividend Recap", "2026-02-18", 185.0, "USAP Holdco", "Fund Account", "Citi", "received"),
        TreasuryMovement("Apollo Healthcare I", "Distribution", "2026-02-22", 175.0, "Fund Account", "LPs", "Citi", "sent"),
        TreasuryMovement("Silver Lake HC Tech II", "IPO Secondary", "2026-03-05", 545.0, "Cohere Health IPO", "Fund Account", "Morgan Stanley", "received"),
    ]


def compute_capital_call_tracker() -> CapCallResult:
    corpus = _load_corpus()
    calls = _build_calls()
    distributions = _build_distributions()
    cashflows = _build_cashflows()
    lp_comms = _build_lp_comms()
    reporting = _build_reporting()
    treasury = _build_treasury()

    total_committed = sum(c.committed_m for c in cashflows) / 1000.0
    total_called = sum(c.called_m for c in cashflows) / 1000.0
    total_distributed = sum(c.distributed_m for c in cashflows) / 1000.0
    ltm_calls = sum(c.amount_m for c in calls)
    ltm_dist = sum(d.amount_m for d in distributions)

    return CapCallResult(
        total_funds=len(cashflows),
        total_committed_b=round(total_committed, 2),
        total_called_b=round(total_called, 2),
        total_distributed_b=round(total_distributed, 2),
        ltm_calls_m=round(ltm_calls, 1),
        ltm_distributions_m=round(ltm_dist, 1),
        net_ltm_m=round(ltm_dist - ltm_calls, 1),
        calls=calls,
        distributions=distributions,
        cashflows=cashflows,
        lp_comms=lp_comms,
        reporting=reporting,
        treasury=treasury,
        corpus_deal_count=len(corpus),
    )
