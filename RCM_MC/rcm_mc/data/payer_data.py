"""Colorado CIVHC / CO-APCD public payer datasets — loaders + summaries.

Reads the normalized public-use CSVs vendored under
``rcm_mc/data/vendor/payer_data/`` (produced offline by
``scripts/ingest_payer_data.py``). These are PUBLIC, redistributable CIVHC
files — committed to the repo like the CMS public data, so the loaders work in
production with no runtime network calls.

Honesty: missing values stay NaN (never 0); summaries report sample size and
never fabricate. Every dataset is registered in
``rcm_mc/data/vendor/source_registry.csv``.

Datasets:
  - cost_of_care_total / _outpatient — CO spending by year × payer × region ×
    claim/outpatient-category → total spend, member months, per-person-per-year.
  - apm_public — CO alternative-payment-model adoption by payer × year × metric
    → %FFS / %APM and LAN-category breakdown.
  - reference_based_pricing — provider-level (CO hospitals/ASCs) reimbursement
    as a % of Medicare, by county/region/claim type/year.
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_DIR = Path(__file__).resolve().parent / "vendor" / "payer_data"


def _load(name: str) -> pd.DataFrame:
    p = _DIR / name
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


@functools.lru_cache(maxsize=None)
def load_cost_of_care(detail: str = "total") -> pd.DataFrame:
    """CO cost-of-care spending. ``detail='total'`` (by claim type) or
    ``detail='outpatient'`` (by outpatient category)."""
    return _load("cost_of_care_total.csv" if detail == "total"
                 else "cost_of_care_outpatient.csv").copy()


@functools.lru_cache(maxsize=None)
def load_apm_public() -> pd.DataFrame:
    """CO APM adoption (%FFS / %APM, LAN categories) by payer × year × metric."""
    return _load("apm_public.csv").copy()


@functools.lru_cache(maxsize=None)
def load_reference_based_pricing() -> pd.DataFrame:
    """Provider-level CO reimbursement as a % of Medicare (RBP)."""
    return _load("reference_based_pricing.csv").copy()


def payer_data_summary() -> Dict[str, Any]:
    """Row counts + coverage (years, payer types, regions) per dataset."""
    coc = load_cost_of_care("total")
    apm = load_apm_public()
    rbp = load_reference_based_pricing()
    def yrs(df):
        return sorted(str(y) for y in df["year"].dropna().unique()) if "year" in df else []
    return {
        "cost_of_care_total": {"rows": len(coc), "years": yrs(coc),
            "payer_types": sorted(coc["payer_type"].dropna().unique().tolist()) if len(coc) else [],
            "regions": sorted(coc["doi_region"].dropna().unique().tolist()) if len(coc) else []},
        "apm_public": {"rows": len(apm), "years": yrs(apm),
            "metrics": sorted(apm["metric"].dropna().unique().tolist()) if len(apm) else []},
        "reference_based_pricing": {"rows": len(rbp), "years": yrs(rbp),
            "providers": int(rbp["organization_name"].nunique()) if len(rbp) else 0,
            "counties": int(rbp["county"].nunique()) if len(rbp) else 0},
    }


def payer_data_missingness() -> Dict[str, Dict[str, float]]:
    """Percent-missing per field per dataset (so sparsity is never hidden)."""
    out = {}
    for name, df in (("cost_of_care_total", load_cost_of_care("total")),
                     ("cost_of_care_outpatient", load_cost_of_care("outpatient")),
                     ("apm_public", load_apm_public()),
                     ("reference_based_pricing", load_reference_based_pricing())):
        if len(df):
            out[name] = {c: round(100 * df[c].isna().mean(), 1)
                         for c in df.columns if df[c].isna().any()}
    return out


def _apply(df: pd.DataFrame, col: str, val: str) -> pd.DataFrame:
    """Equality filter, but treat 'All' as no-op when the column has no literal
    'All' aggregate row (some dimensions, e.g. claim_type, have no All total)."""
    if val == "All" and "All" not in df[col].astype(str).values:
        return df
    return df[df[col].astype(str) == str(val)]


def payer_cost_by_service(year: str = "All", payer_type: str = "All",
                          region: str = "All") -> pd.DataFrame:
    """Outpatient per-person-per-year spend by service category, filtered."""
    df = load_cost_of_care("outpatient")
    if not len(df):
        return df
    for col, val in (("year", year), ("payer_type", payer_type), ("doi_region", region)):
        df = _apply(df, col, val)
    return df[["outpatient_category", "pppy", "total_spend", "member_months"]] \
        .sort_values("pppy", ascending=False)


def payer_cost_by_geography(year: str = "All", payer_type: str = "All",
                            claim_type: str = "All") -> pd.DataFrame:
    """Per-person-per-year total spend by DOI region, filtered."""
    df = load_cost_of_care("total")
    if not len(df):
        return df
    for col, val in (("year", year), ("payer_type", payer_type), ("claim_type", claim_type)):
        df = _apply(df, col, val)
    return df[["doi_region", "pppy", "total_spend", "member_months", "claim_type"]] \
        .sort_values("pppy", ascending=False)


def apm_summary_by_model(year: str = "2024") -> pd.DataFrame:
    """%APM vs %FFS by payer type for a year (Total Spending metric where
    present), so a deal team sees Colorado's value-based-care penetration."""
    df = load_apm_public()
    if not len(df):
        return df
    df = df[df["year"].astype(str) == str(year)]
    keep = [c for c in ["payer_type", "metric", "pct_apm", "pct_ffs",
                        "apm_spend", "ffs_spend", "total_spend"] if c in df.columns]
    return df[keep].sort_values("pct_apm", ascending=False, na_position="last")


def payer_cost_trend(region: str = "All") -> pd.DataFrame:
    """Real Colorado payer cost trend: total per-person-per-year spend by payer
    type × year (summed across claim types), with % change first→last year.
    Excludes the 'All' year aggregate. One row per payer with year columns +
    pct_change. Returns empty if data is absent."""
    df = load_cost_of_care("total")
    if not len(df):
        return df
    df = df[df["doi_region"].astype(str) == str(region)]
    df = df[df["year"].astype(str) != "All"]
    if not len(df):
        return df.head(0)
    grp = (df.groupby(["payer_type", "year"])["pppy"].sum()
           .reset_index())
    pivot = grp.pivot(index="payer_type", columns="year", values="pppy")
    years = sorted(c for c in pivot.columns)
    if len(years) >= 2:
        first, last = years[0], years[-1]
        pivot["pct_change"] = ((pivot[last] - pivot[first]) / pivot[first]) * 100
    pivot = pivot.reset_index().rename_axis(None, axis=1)
    return pivot


def apm_adoption_by_payer(metric: str = "Total Medical Spending") -> pd.DataFrame:
    """Clean Colorado APM-adoption slice: %APM / %FFS by payer × year for one
    metric, fixed to the integrated-systems-included / value-based-included
    variant so each payer×year appears once. Payer label keeps CIVHC's leading
    sort digit stripped for display. NaN preserved (Unknown payer has no value).
    """
    df = load_apm_public()
    if not len(df):
        return df
    sl = df[(df["metric"] == metric)
            & (df["integrated_systems"] == "Yes")
            & (df["value_based_payments"] == "Included")].copy()
    sl["payer"] = sl["payer_type"].astype(str).str.replace(r"^\d+\s+", "", regex=True)
    keep = ["payer", "year", "pct_apm", "pct_ffs", "apm_spend", "ffs_spend",
            "total_spend"]
    return sl[[c for c in keep if c in sl.columns]].sort_values(["payer", "year"])


def reference_pricing_summary(claim_type: str = "All") -> pd.DataFrame:
    """Provider RBP (% of Medicare) — per organization, optionally by claim
    type. Sorted by hospital_pct_medicare desc; NaN last."""
    df = load_reference_based_pricing()
    if not len(df):
        return df
    if claim_type != "All":
        df = df[df["claim_type"].astype(str) == str(claim_type)]
    keep = [c for c in ["organization_name", "claim_type", "year", "county",
                        "doi_region", "hospital_pct_medicare", "claims",
                        "urf_pct_medicare"] if c in df.columns]
    return df[keep].sort_values("hospital_pct_medicare", ascending=False,
                                na_position="last")


def payer_data_sources() -> List[Dict[str, str]]:
    """Provenance rows from the source registry for the payer datasets."""
    reg = _DIR.parent / "source_registry.csv"
    if not reg.exists():
        return []
    df = pd.read_csv(reg)
    df = df[df["source_id"].astype(str).str.startswith("civhc_")]
    return df.to_dict("records")
