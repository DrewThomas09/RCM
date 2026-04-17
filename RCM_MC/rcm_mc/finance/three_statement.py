"""Three-statement financial model: Income Statement + Balance Sheet + Cash Flow.

Reconstructs estimated financials from HCRIS public data + deal profile
inputs. Where data is missing, uses healthcare industry benchmarks.

This is NOT audited — it's the associate's starting model before they
get the seller's actuals. Every assumption is labeled so the IC can
see what's real data vs estimated.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np


# ── Healthcare industry benchmarks (median acute-care hospital) ──

_BENCHMARKS = {
    "gross_to_net_ratio": 0.55,
    "bad_debt_pct_npr": 0.03,
    "salary_pct_opex": 0.55,
    "supply_pct_opex": 0.18,
    "depreciation_pct_revenue": 0.04,
    "interest_pct_revenue": 0.02,
    "current_ratio": 1.8,
    "days_cash_on_hand": 45,
    "ar_days": 50,
    "ap_days": 40,
    "inventory_days": 15,
    "ppe_to_revenue": 0.60,
    "capex_pct_revenue": 0.04,
    "debt_to_ebitda": 3.5,
}


@dataclass
class LineItem:
    """One line in a financial statement."""
    label: str
    value: float
    source: str
    pct_revenue: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"label": self.label, "value": round(self.value, 2), "source": self.source}
        if self.pct_revenue is not None:
            d["pct_revenue"] = round(self.pct_revenue, 4)
        return d


@dataclass
class IncomeStatement:
    """Estimated P&L."""
    gross_patient_revenue: LineItem = field(default_factory=lambda: LineItem("Gross Patient Revenue", 0, "unknown"))
    contractual_allowances: LineItem = field(default_factory=lambda: LineItem("Contractual Allowances", 0, "unknown"))
    net_patient_revenue: LineItem = field(default_factory=lambda: LineItem("Net Patient Revenue", 0, "unknown"))
    bad_debt: LineItem = field(default_factory=lambda: LineItem("Bad Debt Expense", 0, "unknown"))
    total_operating_revenue: LineItem = field(default_factory=lambda: LineItem("Total Operating Revenue", 0, "unknown"))
    salaries_and_wages: LineItem = field(default_factory=lambda: LineItem("Salaries & Wages", 0, "unknown"))
    supplies: LineItem = field(default_factory=lambda: LineItem("Supplies", 0, "unknown"))
    other_operating: LineItem = field(default_factory=lambda: LineItem("Other Operating Expenses", 0, "unknown"))
    total_operating_expenses: LineItem = field(default_factory=lambda: LineItem("Total Operating Expenses", 0, "unknown"))
    ebitda: LineItem = field(default_factory=lambda: LineItem("EBITDA", 0, "unknown"))
    depreciation: LineItem = field(default_factory=lambda: LineItem("Depreciation & Amortization", 0, "unknown"))
    ebit: LineItem = field(default_factory=lambda: LineItem("EBIT", 0, "unknown"))
    interest: LineItem = field(default_factory=lambda: LineItem("Interest Expense", 0, "unknown"))
    ebt: LineItem = field(default_factory=lambda: LineItem("Earnings Before Tax", 0, "unknown"))
    taxes: LineItem = field(default_factory=lambda: LineItem("Income Tax", 0, "unknown"))
    net_income: LineItem = field(default_factory=lambda: LineItem("Net Income", 0, "unknown"))
    ebitda_margin: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        items = []
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if isinstance(val, LineItem):
                items.append(val.to_dict())
        return {"line_items": items, "ebitda_margin": round(self.ebitda_margin, 4)}


@dataclass
class BalanceSheet:
    """Estimated balance sheet."""
    cash: LineItem = field(default_factory=lambda: LineItem("Cash & Equivalents", 0, "estimated"))
    accounts_receivable: LineItem = field(default_factory=lambda: LineItem("Accounts Receivable", 0, "estimated"))
    inventory: LineItem = field(default_factory=lambda: LineItem("Inventory", 0, "estimated"))
    other_current: LineItem = field(default_factory=lambda: LineItem("Other Current Assets", 0, "estimated"))
    total_current_assets: LineItem = field(default_factory=lambda: LineItem("Total Current Assets", 0, "estimated"))
    ppe_net: LineItem = field(default_factory=lambda: LineItem("PP&E (Net)", 0, "estimated"))
    other_assets: LineItem = field(default_factory=lambda: LineItem("Other Assets", 0, "estimated"))
    total_assets: LineItem = field(default_factory=lambda: LineItem("Total Assets", 0, "estimated"))
    accounts_payable: LineItem = field(default_factory=lambda: LineItem("Accounts Payable", 0, "estimated"))
    accrued_liabilities: LineItem = field(default_factory=lambda: LineItem("Accrued Liabilities", 0, "estimated"))
    current_debt: LineItem = field(default_factory=lambda: LineItem("Current Portion of Debt", 0, "estimated"))
    total_current_liabilities: LineItem = field(default_factory=lambda: LineItem("Total Current Liabilities", 0, "estimated"))
    long_term_debt: LineItem = field(default_factory=lambda: LineItem("Long-Term Debt", 0, "estimated"))
    total_liabilities: LineItem = field(default_factory=lambda: LineItem("Total Liabilities", 0, "estimated"))
    equity: LineItem = field(default_factory=lambda: LineItem("Total Equity", 0, "estimated"))
    total_liabilities_equity: LineItem = field(default_factory=lambda: LineItem("Total Liab + Equity", 0, "estimated"))

    def to_dict(self) -> Dict[str, Any]:
        items = []
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if isinstance(val, LineItem):
                items.append(val.to_dict())
        return {"line_items": items}


@dataclass
class CashFlowStatement:
    """Estimated cash flow statement."""
    net_income: LineItem = field(default_factory=lambda: LineItem("Net Income", 0, "computed"))
    depreciation_add_back: LineItem = field(default_factory=lambda: LineItem("+ Depreciation", 0, "computed"))
    change_in_ar: LineItem = field(default_factory=lambda: LineItem("Change in A/R", 0, "estimated"))
    change_in_inventory: LineItem = field(default_factory=lambda: LineItem("Change in Inventory", 0, "estimated"))
    change_in_ap: LineItem = field(default_factory=lambda: LineItem("Change in A/P", 0, "estimated"))
    cash_from_operations: LineItem = field(default_factory=lambda: LineItem("Cash from Operations", 0, "computed"))
    capex: LineItem = field(default_factory=lambda: LineItem("Capital Expenditures", 0, "estimated"))
    cash_from_investing: LineItem = field(default_factory=lambda: LineItem("Cash from Investing", 0, "computed"))
    debt_repayment: LineItem = field(default_factory=lambda: LineItem("Debt Repayment", 0, "estimated"))
    cash_from_financing: LineItem = field(default_factory=lambda: LineItem("Cash from Financing", 0, "estimated"))
    net_change_in_cash: LineItem = field(default_factory=lambda: LineItem("Net Change in Cash", 0, "computed"))
    free_cash_flow: LineItem = field(default_factory=lambda: LineItem("Free Cash Flow", 0, "computed"))

    def to_dict(self) -> Dict[str, Any]:
        items = []
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if isinstance(val, LineItem):
                items.append(val.to_dict())
        return {"line_items": items}


@dataclass
class ThreeStatementModel:
    """Complete 3-statement model."""
    deal_id: str
    deal_name: str
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlowStatement
    assumptions_used: Dict[str, str]
    data_quality: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "deal_name": self.deal_name,
            "income_statement": self.income_statement.to_dict(),
            "balance_sheet": self.balance_sheet.to_dict(),
            "cash_flow": self.cash_flow.to_dict(),
            "assumptions_used": self.assumptions_used,
            "data_quality": self.data_quality,
        }


def _li(label: str, value: float, source: str, revenue: float = 0) -> LineItem:
    pct = value / revenue if revenue > 0 else None
    return LineItem(label=label, value=value, source=source, pct_revenue=pct)


def build_three_statement(
    profile: Dict[str, Any],
    hcris_row: Optional[Dict[str, Any]] = None,
) -> ThreeStatementModel:
    """Build a 3-statement model from deal profile + optional HCRIS data."""
    deal_id = str(profile.get("deal_id") or "")
    deal_name = str(profile.get("name") or deal_id)
    assumptions: Dict[str, str] = {}
    h = hcris_row or {}

    # ── Income Statement ──
    gpr = float(h.get("gross_patient_revenue") or profile.get("gross_revenue") or 0)
    ca = float(h.get("contractual_allowances") or 0)
    npr = float(h.get("net_patient_revenue") or profile.get("net_revenue") or 0)

    if gpr > 0 and ca > 0 and npr == 0:
        npr = gpr - ca
        assumptions["net_patient_revenue"] = "computed: gross - contractual"
    elif npr > 0 and gpr == 0:
        gpr = npr / (1 - _BENCHMARKS["gross_to_net_ratio"])
        ca = gpr - npr
        assumptions["gross_patient_revenue"] = "estimated from NPR using 55% allowance benchmark"
    elif gpr == 0 and npr == 0:
        npr = float(profile.get("revenue") or 200e6)
        gpr = npr / (1 - _BENCHMARKS["gross_to_net_ratio"])
        ca = gpr - npr
        assumptions["net_patient_revenue"] = "default $200M"

    gpr_src = "HCRIS" if h.get("gross_patient_revenue") else "estimated"
    npr_src = "HCRIS" if h.get("net_patient_revenue") else (
        "deal_profile" if profile.get("net_revenue") else "estimated"
    )

    opex = float(h.get("operating_expenses") or 0)
    ni = float(h.get("net_income") or 0)
    opex_src = "HCRIS" if h.get("operating_expenses") else "estimated"

    bad_debt = npr * _BENCHMARKS["bad_debt_pct_npr"]
    total_rev = npr - bad_debt

    if opex == 0:
        opex = npr * 0.92
        assumptions["operating_expenses"] = "estimated at 92% of NPR"

    salaries = opex * _BENCHMARKS["salary_pct_opex"]
    supplies = opex * _BENCHMARKS["supply_pct_opex"]
    other_opex = opex - salaries - supplies

    ebitda = total_rev - opex
    da = npr * _BENCHMARKS["depreciation_pct_revenue"]
    ebit = ebitda - da
    interest = npr * _BENCHMARKS["interest_pct_revenue"]
    ebt = ebit - interest
    taxes = max(ebt * 0.25, 0)
    if ni == 0:
        ni = ebt - taxes
        assumptions["net_income"] = "computed from estimated P&L"
    ni_src = "HCRIS" if h.get("net_income") else "computed"

    ebitda_margin = ebitda / npr if npr > 0 else 0

    inc = IncomeStatement(
        gross_patient_revenue=_li("Gross Patient Revenue", gpr, gpr_src, npr),
        contractual_allowances=_li("Contractual Allowances", -ca, gpr_src, npr),
        net_patient_revenue=_li("Net Patient Revenue", npr, npr_src, npr),
        bad_debt=_li("Bad Debt Expense", -bad_debt, "benchmark 3%", npr),
        total_operating_revenue=_li("Total Operating Revenue", total_rev, "computed", npr),
        salaries_and_wages=_li("Salaries & Wages", -salaries, "benchmark 55% opex", npr),
        supplies=_li("Supplies", -supplies, "benchmark 18% opex", npr),
        other_operating=_li("Other Operating", -other_opex, "residual", npr),
        total_operating_expenses=_li("Total Operating Expenses", -opex, opex_src, npr),
        ebitda=_li("EBITDA", ebitda, "computed", npr),
        depreciation=_li("D&A", -da, "benchmark 4% NPR", npr),
        ebit=_li("EBIT", ebit, "computed", npr),
        interest=_li("Interest", -interest, "benchmark 2% NPR", npr),
        ebt=_li("EBT", ebt, "computed", npr),
        taxes=_li("Taxes", -taxes, "25% rate", npr),
        net_income=_li("Net Income", ni, ni_src, npr),
        ebitda_margin=ebitda_margin,
    )

    # ── Balance Sheet ──
    daily_rev = npr / 365
    ar = daily_rev * float(profile.get("days_in_ar") or _BENCHMARKS["ar_days"])
    ar_src = "deal_profile" if profile.get("days_in_ar") else "benchmark"
    cash = daily_rev * _BENCHMARKS["days_cash_on_hand"]
    inventory = daily_rev * _BENCHMARKS["inventory_days"]
    other_ca = npr * 0.02
    total_ca = cash + ar + inventory + other_ca

    ppe = npr * _BENCHMARKS["ppe_to_revenue"]
    other_a = npr * 0.05
    total_a = total_ca + ppe + other_a

    daily_opex = opex / 365
    ap = daily_opex * _BENCHMARKS["ap_days"]
    accrued = opex * 0.06
    current_debt = ebitda * _BENCHMARKS["debt_to_ebitda"] * 0.05
    total_cl = ap + accrued + current_debt

    lt_debt = ebitda * _BENCHMARKS["debt_to_ebitda"] - current_debt
    total_l = total_cl + lt_debt
    equity_val = total_a - total_l
    total_le = total_a

    bs = BalanceSheet(
        cash=_li("Cash", cash, "benchmark 45 days", npr),
        accounts_receivable=_li("A/R", ar, ar_src, npr),
        inventory=_li("Inventory", inventory, "benchmark 15 days", npr),
        other_current=_li("Other Current", other_ca, "benchmark 2%", npr),
        total_current_assets=_li("Total Current Assets", total_ca, "computed", npr),
        ppe_net=_li("PP&E Net", ppe, "benchmark 60% NPR", npr),
        other_assets=_li("Other Assets", other_a, "benchmark 5%", npr),
        total_assets=_li("Total Assets", total_a, "computed", npr),
        accounts_payable=_li("A/P", ap, "benchmark 40 days", npr),
        accrued_liabilities=_li("Accrued Liab", accrued, "benchmark 6% opex", npr),
        current_debt=_li("Current Debt", current_debt, "benchmark 5% total debt", npr),
        total_current_liabilities=_li("Total Current Liab", total_cl, "computed", npr),
        long_term_debt=_li("LT Debt", lt_debt, "benchmark 3.5x EBITDA", npr),
        total_liabilities=_li("Total Liabilities", total_l, "computed", npr),
        equity=_li("Total Equity", equity_val, "plug (A - L)", npr),
        total_liabilities_equity=_li("Total L + E", total_le, "computed", npr),
    )

    # ── Cash Flow ──
    capex = npr * _BENCHMARKS["capex_pct_revenue"]
    cfo = ni + da - (ar * 0.03) - (inventory * 0.02) + (ap * 0.02)
    cfi = -capex
    debt_repay = -lt_debt * 0.05
    cff = debt_repay
    net_cash = cfo + cfi + cff
    fcf = cfo - capex

    cf = CashFlowStatement(
        net_income=_li("Net Income", ni, ni_src, npr),
        depreciation_add_back=_li("+ D&A", da, "from IS", npr),
        change_in_ar=_li("Change in A/R", -(ar * 0.03), "3% growth", npr),
        change_in_inventory=_li("Change in Inventory", -(inventory * 0.02), "2% growth", npr),
        change_in_ap=_li("Change in A/P", ap * 0.02, "2% growth", npr),
        cash_from_operations=_li("CFO", cfo, "computed", npr),
        capex=_li("CapEx", -capex, "benchmark 4% NPR", npr),
        cash_from_investing=_li("CFI", cfi, "computed", npr),
        debt_repayment=_li("Debt Repayment", debt_repay, "5% of LT debt", npr),
        cash_from_financing=_li("CFF", cff, "computed", npr),
        net_change_in_cash=_li("Net Change", net_cash, "computed", npr),
        free_cash_flow=_li("FCF", fcf, "CFO - CapEx", npr),
    )

    has_hcris = bool(h.get("net_patient_revenue"))
    has_profile = bool(profile.get("net_revenue"))
    quality = "high" if has_hcris else ("moderate" if has_profile else "low")

    return ThreeStatementModel(
        deal_id=deal_id, deal_name=deal_name,
        income_statement=inc, balance_sheet=bs, cash_flow=cf,
        assumptions_used=assumptions, data_quality=quality,
    )
