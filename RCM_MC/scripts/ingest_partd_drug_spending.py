#!/usr/bin/env python3
"""Build-time ingest for CMS Medicare Part D Spending by Drug.

Downloads the public CMS "Medicare Part D Spending by Drug" file and writes
a compact, PII-free committed aggregate under
``rcm_mc/data/vendor/partd_drug/``:

  • ``partd_drug_top.csv``     — top drugs by 2023 spend + price-inflation
  • ``partd_drug_summary.json``— national totals + extract metadata

Drug-level public spending — no PII. Build-time download only; production
reads the committed aggregate (no runtime network). Public CMS data.
The per-dosage-unit price + its 2019-2023 CAGR is the real drug-price-
inflation signal that drives 340B / drug-cost economics.

Run manually to refresh: ``python scripts/ingest_partd_drug_spending.py``.
"""
from __future__ import annotations

import io
import json
import subprocess
from datetime import date
from pathlib import Path

import pandas as pd

DY = "2023"
URL = ("https://data.cms.gov/sites/default/files/2025-05/"
       "56d95a8b-138c-4b60-84a5-613fbab7197f/DSD_PTD_RY25_P04_V10_DY23_BGM.csv")
OUT_DIR = Path(__file__).resolve().parents[1] / "rcm_mc" / "data" / "vendor" / "partd_drug"


def _download() -> pd.DataFrame:
    print("downloading CMS Part D Spending by Drug ...")
    res = subprocess.run(["curl", "-s", "-L", "-m", "240", URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), encoding="latin-1", low_memory=False)
    print(f"  {len(df):,} rows, {len(df.columns)} cols")
    return df


def main() -> None:
    df = _download()
    # one row per drug = the "Overall" manufacturer roll-up (avoid double count).
    if "Mftr_Name" in df.columns:
        df = df[df["Mftr_Name"].astype(str).str.strip().str.lower() == "overall"]
    spend = pd.to_numeric(df["Tot_Spndng_2023"], errors="coerce")
    clms = pd.to_numeric(df["Tot_Clms_2023"], errors="coerce")
    benes = pd.to_numeric(df["Tot_Benes_2023"], errors="coerce")
    ppu = pd.to_numeric(df["Avg_Spnd_Per_Dsg_Unt_Wghtd_2023"], errors="coerce")
    cagr = pd.to_numeric(df["CAGR_Avg_Spnd_Per_Dsg_Unt_19_23"], errors="coerce")
    chg = pd.to_numeric(df["Chg_Avg_Spnd_Per_Dsg_Unt_22_23"], errors="coerce")
    df = df.assign(spv=spend, clv=clms, bnv=benes, ppv=ppu, cgv=cagr, chv=chg)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    def _rows(frame: pd.DataFrame, n: int) -> list:
        out = []
        for r in frame.head(n).itertuples():
            out.append({
                "brand": str(r.Brnd_Name), "generic": str(r.Gnrc_Name),
                "spend_2023": round(float(r.spv), 0) if r.spv == r.spv else None,
                "claims_2023": int(r.clv) if r.clv == r.clv else None,
                "price_per_unit_2023": round(float(r.ppv), 4) if r.ppv == r.ppv else None,
                "price_cagr_19_23": round(float(r.cgv), 4) if r.cgv == r.cgv else None,
            })
        return out

    top_spend = _rows(df.sort_values("spv", ascending=False), 12)
    # price inflation among drugs with non-trivial spend (>$10M) to avoid noise
    infl = df[df["spv"] > 1e7].sort_values("cgv", ascending=False)
    top_inflation = _rows(infl, 12)
    pd.DataFrame(top_spend).to_csv(OUT_DIR / "partd_drug_top_spend.csv", index=False)
    pd.DataFrame(top_inflation).to_csv(OUT_DIR / "partd_drug_top_inflation.csv", index=False)

    cagr_valid = cagr.dropna()
    summary = {
        "data_year": DY,
        "source": "CMS Medicare Part D Spending by Drug",
        "extract_date": date.today().isoformat(),
        "drugs": int(len(df)),
        "total_spending_2023": round(float(spend.sum()), 0),
        "total_claims_2023": int(clms.sum()),
        "total_beneficiaries_2023": int(benes.sum()),
        "median_price_cagr_19_23": round(float(cagr_valid.median()), 4) if len(cagr_valid) else None,
        "drugs_price_up_over_10pct_cagr": int((cagr_valid > 0.10).sum()),
        "top_spend": top_spend,
        "top_inflation": top_inflation,
    }
    (OUT_DIR / "partd_drug_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"  drugs {summary['drugs']:,}, 2023 spend ${summary['total_spending_2023']/1e9:,.1f}B, "
          f"median price CAGR {summary['median_price_cagr_19_23']}")
    print(f"  wrote partd_drug_summary.json + top_spend/top_inflation csvs")


if __name__ == "__main__":
    main()
