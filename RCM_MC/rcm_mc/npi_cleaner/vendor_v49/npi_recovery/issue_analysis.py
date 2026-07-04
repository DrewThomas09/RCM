"""
issue_analysis.py  (v45)
========================

Analysis for the problems, not just a count of them. A screen that returns 800
MUE violations is a flag; the diligence question is whether those 800 are three
J-codes and two billers worth 2 million dollars (systematic, likely a real
practice pattern) or a thin scatter across the book (random noise). This module
takes any screen's flagged rows and produces that read:

  magnitude          rows flagged, and share of the relevant denominator
  dollar_exposure    allowed dollars on the flagged rows, and share of total
  concentration      how concentrated the issue is by drug, payer, and provider
                     (top offenders and an HHI-style concentration score)
  systematic_signal  a verdict: is the issue concentrated enough to look
                     systematic, or diffuse enough to look like random error

The point is to turn each data-quality finding into something an analyst can size
and act on: chase the systematic ones (they change the deal read), note the random
ones (they are cleanup). Deterministic and offline.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def _col(std, mapping, canonical, fallbacks=()):
    if mapping and mapping.get(canonical) and mapping[canonical] in std.columns:
        return mapping[canonical]
    if canonical in std.columns:
        return canonical
    for f in fallbacks:
        if f in std.columns:
            return f
    return None


def _hhi(shares):
    """Herfindahl on a set of dollar shares (0..1). 1 = one entity owns it all."""
    s = np.asarray(shares, dtype=float)
    return round(float(np.sum(s ** 2)), 3) if len(s) else 0.0


def _concentration(std, rows, dim_col, amt):
    """Top offenders and an HHI on the flagged dollars, along a dimension."""
    if dim_col is None or dim_col not in std.columns:
        return pd.DataFrame(), 0.0
    d = pd.DataFrame({"k": std.loc[rows, dim_col].astype(str).to_numpy(),
                      "amt": amt})
    g = d.groupby("k")["amt"].sum().sort_values(ascending=False)
    tot = float(g.sum()) or 1.0
    shares = (g / tot).to_numpy()
    top = g.head(5).reset_index()
    top.columns = [dim_col, "flagged_dollars"]
    top["share_pct"] = (100.0 * top["flagged_dollars"] / tot).round(1)
    return top, _hhi(shares)


def analyze_issue(flagged: pd.DataFrame, std: pd.DataFrame, issue_name: str,
                  mapping=None, denom_rows=None) -> dict:
    """Full analysis of one issue. flagged carries a 'row' column indexing std."""
    if flagged is None or flagged.empty or "row" not in flagged.columns:
        return {"issue": issue_name, "status": "no_rows"}
    rows = flagged["row"].to_numpy()
    acol = _col(std, mapping, "allowed_amt")
    amt = (pd.to_numeric(std.loc[rows, acol], errors="coerce").fillna(0.0).clip(lower=0).to_numpy()
           if acol else np.ones(len(rows)))
    total_amt = (float(pd.to_numeric(std[acol], errors="coerce").fillna(0).clip(lower=0).sum())
                 if acol else float(len(std)))
    n_denom = denom_rows if denom_rows is not None else len(std)

    hcpcs_c = _col(std, mapping, "hcpcs", ("hcpcs_cpt", "code"))
    payer_c = _col(std, mapping, "payer")
    prov_c = _col(std, mapping, "billing_npi", ("npi",))

    top_drug, hhi_drug = _concentration(std, rows, hcpcs_c, amt)
    top_payer, hhi_payer = _concentration(std, rows, payer_c, amt)
    top_prov, hhi_prov = _concentration(std, rows, prov_c, amt)

    # systematic vs random: concentrated dollars in few drugs/providers looks
    # systematic; diffuse looks random. Use the max of the drug/provider HHIs.
    conc = max(hhi_drug, hhi_prov)
    if conc >= 0.30:
        signal = "systematic (concentrated in few drugs/providers; likely a real pattern)"
    elif conc >= 0.15:
        signal = "mixed (some concentration; worth a look)"
    else:
        signal = "diffuse (spread thin; looks like random error)"

    return {
        "issue": issue_name, "status": "ok",
        "rows_flagged": int(len(rows)),
        "pct_rows": round(100.0 * len(rows) / n_denom, 2) if n_denom else 0.0,
        "dollar_exposure": round(float(amt.sum()), 2),
        "pct_dollars": round(100.0 * float(amt.sum()) / total_amt, 2) if total_amt else 0.0,
        "hhi_drug": hhi_drug, "hhi_payer": hhi_payer, "hhi_provider": hhi_prov,
        "systematic_signal": signal,
        "top_drugs": top_drug, "top_payers": top_payer, "top_providers": top_prov,
    }


def issue_summary_frame(analyses: list) -> pd.DataFrame:
    """One row per issue: the sizing and the systematic verdict, for the readout."""
    rows = []
    for a in analyses:
        if a.get("status") != "ok":
            continue
        rows.append({
            "issue": a["issue"], "rows_flagged": a["rows_flagged"],
            "pct_rows": a["pct_rows"], "dollar_exposure": a["dollar_exposure"],
            "pct_dollars": a["pct_dollars"],
            "hhi_drug": a["hhi_drug"], "hhi_provider": a["hhi_provider"],
            "systematic_signal": a["systematic_signal"],
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out = out.sort_values("dollar_exposure", ascending=False).reset_index(drop=True)
    sysd = out[out["systematic_signal"].str.startswith("systematic")]["dollar_exposure"].sum()
    tot = out["dollar_exposure"].sum() or 1.0
    out.attrs["note"] = (
        f"{len(out)} issue types analyzed. ${sysd:,.0f} of ${tot:,.0f} flagged "
        f"exposure ({round(100.0*sysd/tot,1)}%) looks systematic (concentrated in few "
        f"drugs or providers), which is where the diligence signal is. The rest looks "
        f"like random error to clean up, not a pattern to price.")
    return out


def analyze_all(screen_results: dict, std: pd.DataFrame, mapping=None) -> tuple:
    """Analyze every screen result. Returns (summary_frame, {issue: detail_dict})."""
    analyses = []
    details = {}
    for key, res in (screen_results or {}).items():
        if not isinstance(res, pd.DataFrame) or res.empty or "row" not in res.columns:
            continue
        a = analyze_issue(res, std, key, mapping=mapping)
        if a.get("status") == "ok":
            analyses.append(a)
            details[key] = a
    return issue_summary_frame(analyses), details
