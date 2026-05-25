"""Snapshot CMS Open Payments (staged) → industry-payments aggregates.

Source: CMS Open Payments pre-aggregated summary (by reporting entity × nature
of payment), public. BUILD-TIME: fetch the small summary file and commit two
PII-free aggregates — a national total and top reporting entities
(manufacturers/GPOs) by total payments. The multi-GB detail file is NOT
ingested (see docs/data_profiles/OPEN_PAYMENTS_SOURCE_PROFILE.md for the staged
full-ingest plan). Nature-of-payment is code-only in the summary; labels are a
documented follow-up (not guessed).

Run: python scripts/ingest_open_payments.py
"""
from __future__ import annotations
import io, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

_OUT = Path(__file__).resolve().parent.parent / "rcm_mc" / "data" / "vendor" / "open_payments"
_URL = ("https://download.cms.gov/openpayments/SMRY_RPTS_P01232026_01102026/"
        "PBLCTN_SMRY_BY_AMGPO_BY_NTR_OF_PYMT_PGYR2023_P01232026_01102026.csv")
_YEAR = 2023


def main(argv=None) -> int:
    _OUT.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(["curl", "-sS", "-m", "120", _URL],
                         capture_output=True, check=True)
    df = pd.read_csv(io.BytesIO(res.stdout), dtype=str, encoding="latin-1")
    df.columns = [c.strip().strip('"') for c in df.columns]
    df["Total_Amount"] = pd.to_numeric(df["Total_Amount"], errors="coerce")
    df["Number_of_Transaction"] = pd.to_numeric(df["Number_of_Transaction"], errors="coerce")

    by_mfr = (df.groupby("AMGPO_Name")
              .agg(total_amount=("Total_Amount", "sum"),
                   transactions=("Number_of_Transaction", "sum"))
              .reset_index().sort_values("total_amount", ascending=False))
    by_mfr["year"] = _YEAR
    by_mfr.head(100).to_csv(_OUT / "open_payments_top_entities.csv", index=False)

    total_amt = float(df["Total_Amount"].sum())
    total_txn = int(df["Number_of_Transaction"].sum())
    (_OUT / "open_payments_report.json").write_text(json.dumps({
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "program_year": _YEAR,
        "total_payments_usd": round(total_amt, 2),
        "total_transactions": total_txn,
        "reporting_entities": int(df["AMGPO_Name"].nunique()),
        "source": "CMS Open Payments summary (by entity x nature); public; "
                  "detail/nature-labels deferred (see source profile)",
    }, indent=2))
    print(f"Wrote top {min(100, len(by_mfr))} entities; national ${total_amt/1e9:.2f}bn, "
          f"{total_txn:,} txns, {df['AMGPO_Name'].nunique()} entities → {_OUT}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
