"""Regional wage-inflation forecaster.

Pragmatic seed: MSA × role wage inflation anchors derived from BLS
QCEW / OES public aggregates (2024-2026 trend). For diligence-
grade precision, a licensed BLS pull replaces these.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


# Public-aggregate seeds. Inflation rates are annualised
# compound; the travel-nurse spike over 2021-2022 is not
# reflected here since it has largely unwound.
_DEFAULT_MSA_INFLATION = {
    "National": {
        "RN": 0.045, "LPN": 0.038, "CODER": 0.041,
        "BILLER": 0.036, "MA": 0.035,
    },
    "California (CA)": {
        "RN": 0.058, "LPN": 0.050, "CODER": 0.050,
        "BILLER": 0.045, "MA": 0.043,
    },
    "New York (NY)": {
        "RN": 0.052, "LPN": 0.044, "CODER": 0.045,
        "BILLER": 0.041, "MA": 0.040,
    },
    "Texas (TX)": {
        "RN": 0.040, "LPN": 0.034, "CODER": 0.037,
        "BILLER": 0.032, "MA": 0.031,
    },
    "Florida (FL)": {
        "RN": 0.042, "LPN": 0.036, "CODER": 0.039,
        "BILLER": 0.034, "MA": 0.033,
    },
}


@dataclass
class WageForecast:
    msa: str
    role: str
    annualized_inflation_pct: float
    projected_wage_bill_year1_usd: float
    projected_wage_bill_year3_usd: float
    projected_wage_bill_year5_usd: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def forecast_wage_inflation(
    *,
    msa: str = "National",
    role: str = "RN",
    current_wage_bill_usd: float,
    horizon_years: int = 5,
) -> WageForecast:
    """Compound the wage bill forward at the MSA × role anchor.

    Unknown MSA falls back to National. Unknown role falls back
    to the MSA's RN rate."""
    inflation_table = _DEFAULT_MSA_INFLATION.get(
        msa, _DEFAULT_MSA_INFLATION["National"],
    )
    rate = float(inflation_table.get(
        role, inflation_table.get("RN", 0.04),
    ))
    y1 = current_wage_bill_usd * (1 + rate)
    y3 = current_wage_bill_usd * ((1 + rate) ** 3)
    y5 = current_wage_bill_usd * ((1 + rate) ** 5)
    return WageForecast(
        msa=msa, role=role.upper(),
        annualized_inflation_pct=rate,
        projected_wage_bill_year1_usd=y1,
        projected_wage_bill_year3_usd=y3,
        projected_wage_bill_year5_usd=y5,
    )
