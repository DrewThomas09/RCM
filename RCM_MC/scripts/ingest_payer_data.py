#!/usr/bin/env python3
"""Ingest the Colorado CIVHC / CO-APCD public-use files into normalized CSVs.

Source: Center for Improving Value in Health Care (CIVHC), the Colorado
All-Payer Claims Database administrator — PUBLIC-USE files (redistributable,
like the CMS public data already vendored in this repo). The normalized CSVs
are committed under rcm_mc/data/vendor/payer_data/ so the loaders work in
production with no runtime network calls.

Honesty rules (same as the Deal Library pipeline): missing stays empty/NaN,
never 0; nothing inferred from a blank; every output carries source_id +
the files enter rcm_mc/data/vendor/source_registry.csv.

Run (offline / build-time only)::

    python scripts/ingest_payer_data.py --in "<folder with the 3 .xlsx>"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "payer_data"

# header row (0-based) per source sheet, and the canonical column renames.
_COST_TOTAL_REN = {
    "Year": "year", "Payer Type": "payer_type", "Category": "category",
    "Division of Insurance (DOI) Region": "doi_region", "Claim Type": "claim_type",
    "Total Spend": "total_spend", "Total Member Months": "member_months",
    "Per Person Per Year (PPPY)": "pppy",
}
_COST_OUT_REN = {
    "Outpatient Category": "outpatient_category", "Year": "year",
    "Payer Type": "payer_type", "Division of Insurance (DOI) Region": "doi_region",
    "Total Spending": "total_spend", "Total Member Months": "member_months",
    "Per Person Per Year (PPPY)": "pppy",
}
_APM_REN = {
    "Payer Type": "payer_type", "Year": "year", "Metric": "metric",
    "Integrated Payer/Provider Systems Included?": "integrated_systems",
    "Value-Based Payments": "value_based_payments", "Total Spend": "total_spend",
    "Fee for Service Spending": "ffs_spend", "APM Spending": "apm_spend",
    "% Fee For Service": "pct_ffs", "% APM": "pct_apm",
}
_RBP_REN = {
    "Organization Name": "organization_name", "Claim Type": "claim_type",
    "Year": "year", "County": "county", "Urban/Rural": "urban_rural",
    "DOI Region": "doi_region", "CAH Flag": "cah_flag", "AMB Flag": "amb_flag",
    "Hospital % Medicare": "hospital_pct_medicare", "Claims ": "claims",
    "URF % Medicare": "urf_pct_medicare", "Payer Minimum": "payer_min",
    "Payer Median": "payer_median", "Payer Maximum": "payer_max",
}


def _read(path: Path, sheet: str, header: int, ren: Dict[str, str],
          source_id: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet, header=header, engine="openpyxl")
    df = df.dropna(how="all")
    # keep only mapped columns that are present
    cols = {k: v for k, v in ren.items() if k in df.columns}
    df = df[list(cols)].rename(columns=cols)
    # drop rows with no key (first canonical col empty)
    first = list(cols.values())[0]
    df = df[df[first].notna()]
    df["source_id"] = source_id
    return df


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="indir", required=True,
                    help="folder containing the 3 CIVHC .xlsx files")
    args = ap.parse_args(argv)
    base = Path(args.indir)
    _OUT.mkdir(parents=True, exist_ok=True)

    cost_f = base / "FY23_Public Data_Cost of Care.xlsx"
    apm_f = base / "FY26_APM_Public Excel File.xlsx"
    rbp_f = base / "FY26_Medicare Reference Based Pricing_Public Excel File.xlsx"

    report: Dict[str, object] = {"outputs": {}, "missingness_pct": {}}

    def emit(df: pd.DataFrame, name: str) -> None:
        out = _OUT / name
        df.to_csv(out, index=False)
        report["outputs"][name] = len(df)
        report["missingness_pct"][name] = {
            c: round(100 * df[c].isna().mean(), 1)
            for c in df.columns if df[c].isna().any()}
        print(f"  {name}: {len(df)} rows", file=sys.stderr)

    if cost_f.exists():
        emit(_read(cost_f, "Total Spending", 3, _COST_TOTAL_REN, "civhc_coc_fy23_total"),
             "cost_of_care_total.csv")
        emit(_read(cost_f, "Outpatient Spending Details", 3, _COST_OUT_REN, "civhc_coc_fy23_outpatient"),
             "cost_of_care_outpatient.csv")
    if apm_f.exists():
        emit(_read(apm_f, "Data", 11, _APM_REN, "civhc_apm_fy26"), "apm_public.csv")
    if rbp_f.exists():
        emit(_read(rbp_f, "RBP Final Dataset FY2026", 11, _RBP_REN, "civhc_rbp_fy26"),
             "reference_based_pricing.csv")

    (_OUT / "payer_data_ingest_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote {len(report['outputs'])} normalized CSVs → {_OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
