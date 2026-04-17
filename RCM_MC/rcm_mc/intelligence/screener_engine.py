"""Hospital screener: filter 17,000+ hospitals by any metric combination.

The Seeking Alpha stock screener equivalent. Analysts build custom
queries with operator/value filters and save them for reuse.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class Filter:
    field: str
    operator: str  # "=", "!=", ">", "<", ">=", "<=", "between", "in"
    value: Any
    value2: Any = None  # for "between"

    def to_dict(self) -> Dict[str, Any]:
        d = {"field": self.field, "operator": self.operator, "value": self.value}
        if self.value2 is not None:
            d["value2"] = self.value2
        return d


@dataclass
class Screen:
    name: str
    filters: List[Filter]
    created_by: str = "system"
    is_predefined: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "filters": [f.to_dict() for f in self.filters],
            "created_by": self.created_by,
            "is_predefined": self.is_predefined,
        }


@dataclass
class ScreenResult:
    screen_name: str
    total_hospitals: int
    matching_hospitals: int
    matches: List[Dict[str, Any]]
    summary_stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screen_name": self.screen_name,
            "total_hospitals": self.total_hospitals,
            "matching_hospitals": self.matching_hospitals,
            "matches": self.matches[:200],
            "summary_stats": self.summary_stats,
        }


PREDEFINED_SCREENS = [
    Screen(
        name="Acquisition Targets in Fragmented Markets",
        filters=[
            Filter("beds", ">=", 100),
            Filter("beds", "<=", 400),
            Filter("net_patient_revenue", ">", 100e6),
        ],
        is_predefined=True,
    ),
    Screen(
        name="High-Margin Hospitals",
        filters=[
            Filter("operating_margin", ">", 0.08),
            Filter("net_patient_revenue", ">", 50e6),
        ],
        is_predefined=True,
    ),
    Screen(
        name="Distressed (Negative Margin)",
        filters=[
            Filter("operating_margin", "<", 0),
            Filter("beds", ">=", 50),
        ],
        is_predefined=True,
    ),
    Screen(
        name="Large Academic Centers",
        filters=[
            Filter("beds", ">=", 400),
            Filter("net_patient_revenue", ">", 500e6),
        ],
        is_predefined=True,
    ),
    Screen(
        name="Medicare-Heavy (>40%)",
        filters=[
            Filter("medicare_day_pct", ">", 0.40),
        ],
        is_predefined=True,
    ),
]


def _apply_filter(df: pd.DataFrame, f: Filter) -> pd.DataFrame:
    if f.field not in df.columns:
        return df
    col = df[f.field]
    try:
        if f.operator == "=":
            return df[col == f.value]
        if f.operator == "!=":
            return df[col != f.value]
        if f.operator == ">":
            return df[col.astype(float) > float(f.value)]
        if f.operator == ">=":
            return df[col.astype(float) >= float(f.value)]
        if f.operator == "<":
            return df[col.astype(float) < float(f.value)]
        if f.operator == "<=":
            return df[col.astype(float) <= float(f.value)]
        if f.operator == "between" and f.value2 is not None:
            return df[col.astype(float).between(float(f.value), float(f.value2))]
        if f.operator == "in" and isinstance(f.value, list):
            return df[col.isin(f.value)]
    except (TypeError, ValueError):
        pass
    return df


def run_screen(
    screen: Screen,
    hcris_df: Optional[pd.DataFrame] = None,
    limit: int = 200,
) -> ScreenResult:
    """Run a screen against the HCRIS dataset."""
    if hcris_df is None:
        from ..data.hcris import _get_latest_per_ccn
        hcris_df = _get_latest_per_ccn()

    df = hcris_df.copy()
    total = len(df)

    # Add computed columns
    if "net_patient_revenue" in df.columns and "operating_expenses" in df.columns:
        rev = df["net_patient_revenue"].fillna(0)
        opex = df["operating_expenses"].fillna(0)
        df["operating_margin"] = ((rev - opex) / rev.replace(0, np.nan)).clip(-1.0, 1.0)

    for f in screen.filters:
        df = _apply_filter(df, f)

    matching = len(df)
    df = df.head(limit)

    matches = []
    for _, row in df.iterrows():
        r = {}
        for col in ["ccn", "name", "city", "state", "beds",
                     "net_patient_revenue", "operating_expenses",
                     "net_income", "medicare_day_pct", "medicaid_day_pct"]:
            if col in row.index:
                v = row[col]
                if hasattr(v, "item"):
                    v = v.item()
                r[col] = v
        if "operating_margin" in row.index:
            om = row["operating_margin"]
            r["operating_margin"] = round(float(om), 4) if pd.notna(om) else None
        matches.append(r)

    stats = {}
    if matching > 0:
        num_cols = df.select_dtypes(include=[np.number])
        for c in ["beds", "net_patient_revenue", "operating_margin"]:
            if c in num_cols.columns:
                vals = num_cols[c].dropna()
                if len(vals) > 0:
                    stats[c] = {
                        "median": round(float(vals.median()), 2),
                        "mean": round(float(vals.mean()), 2),
                        "min": round(float(vals.min()), 2),
                        "max": round(float(vals.max()), 2),
                    }
        if "state" in df.columns:
            stats["top_states"] = df["state"].value_counts().head(5).to_dict()

    return ScreenResult(
        screen_name=screen.name,
        total_hospitals=total,
        matching_hospitals=matching,
        matches=matches,
        summary_stats=stats,
    )


def run_screen_from_filters(
    filters_json: List[Dict[str, Any]],
    screen_name: str = "Custom Screen",
    limit: int = 200,
) -> ScreenResult:
    """Run a screen from a JSON filter list."""
    filters = [
        Filter(
            field=f["field"],
            operator=f.get("operator", ">="),
            value=f["value"],
            value2=f.get("value2"),
        )
        for f in filters_json
    ]
    return run_screen(Screen(name=screen_name, filters=filters), limit=limit)
