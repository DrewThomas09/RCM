"""Revenue-cycle & claims-transaction infrastructure reference data (Group D).

Sourced reference figures: US RCM market-size estimates (shown as a range
because software-only vs services-inclusive definitions diverge widely),
the HIPAA EDI transaction set (ANSI X12 v5010), clearinghouse transaction
volumes, RCM KPI benchmarks, and the Feb-2024 Change Healthcare cyberattack.
Public, named-source figures — NOT this portfolio — disclosed with a research
source/purpose header. RCM operating red-flags for a deal live on
/rcm-red-flags.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


VINTAGE = "2024 market estimates; HDA / CAQH; HIPAA X12 v5010"


@dataclass
class MarketEstimate:
    source: str
    us_market_b: float
    note: str


@dataclass
class EDITransaction:
    code: str
    function: str


@dataclass
class Clearinghouse:
    name: str
    annual_transactions_b: float
    note: str


@dataclass
class KPIBenchmark:
    metric: str
    target: str


@dataclass
class RCMInfraResult:
    vintage: str
    market_low_b: float
    market_high_b: float
    services_share_low_pct: float
    services_share_high_pct: float
    inhouse_low_pct: float
    inhouse_high_pct: float
    change_transactions_b: float
    estimates: List[MarketEstimate] = field(default_factory=list)
    edi: List[EDITransaction] = field(default_factory=list)
    clearinghouses: List[Clearinghouse] = field(default_factory=list)
    kpis: List[KPIBenchmark] = field(default_factory=list)


def compute_rcm_infrastructure() -> RCMInfraResult:
    estimates = [
        MarketEstimate("Market Data Forecast", 56.8, "Software-leaning definition"),
        MarketEstimate("Precedence", 58.5, "Software + core services"),
        MarketEstimate("Arizton", 141.6, "Services-inclusive definition"),
        MarketEstimate("Grand View", 172.2, "Broadest services-inclusive definition"),
    ]
    edi = [
        EDITransaction("837 (I/P/D)", "Claim submission"),
        EDITransaction("835", "Remittance / ERA (payment)"),
        EDITransaction("270 / 271", "Eligibility inquiry / response"),
        EDITransaction("276 / 277", "Claim status inquiry / response"),
        EDITransaction("278", "Prior authorization (~35% electronic, 2024)"),
        EDITransaction("834", "Enrollment"),
        EDITransaction("999 / 277CA", "Acknowledgment / claim acknowledgment"),
    ]
    clearinghouses = [
        Clearinghouse("Change Healthcare (Optum)", 15.0, "Largest US clearinghouse; ~1 in 3 patient records"),
        Clearinghouse("Availity", 13.0, "Connects to ~every payer; 95+ direct payer connections"),
        Clearinghouse("TriZetto Provider Solutions", 3.4, "8,000+ payer connections; 98% acceptance"),
        Clearinghouse("Waystar", 6.0, "IPO 2024"),
    ]
    kpis = [
        KPIBenchmark("Clean claim rate", ">95%"),
        KPIBenchmark("Initial denial rate", "~10%+ (rising)"),
        KPIBenchmark("Days in A/R", "<40–50"),
        KPIBenchmark("Cost-to-collect", "~2–4% of net patient revenue"),
        KPIBenchmark("Coder overhead (MGMA)", "~$215K / FTE / yr"),
    ]
    return RCMInfraResult(
        vintage=VINTAGE,
        market_low_b=56.8,
        market_high_b=172.2,
        services_share_low_pct=68.0,
        services_share_high_pct=77.0,
        inhouse_low_pct=62.0,
        inhouse_high_pct=71.0,
        change_transactions_b=15.0,
        estimates=estimates,
        edi=edi,
        clearinghouses=clearinghouses,
        kpis=kpis,
    )
