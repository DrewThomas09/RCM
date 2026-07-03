"""
npi_channel.py  (v31)
=====================

Answers the transcript question, verbatim: "the government claims are built
through their own pharmacies, which have unique NPIs ... which NPIs in this file
are the government-billing ones?"

The approach uses two independent, defensible signals and never guesses from one
alone:

  1. Payer-type mix per billing NPI. Every claim's payer name is classified
     (config.classify_payer_type) into medicare / medicaid / military_va /
     commercial / unknown, then rolled up by NPI to a government dollar share.

  2. NPPES taxonomy of the billing NPI. A pharmacy-model supplier NPI
     (taxonomy 3335*/3336*/333600000X, plus 332B* DME infusion suppliers) is
     exactly the "their own pharmacies" channel the team described. Taxonomy is
     optional; when it is absent the payer mix still drives the call.

From those two signals each NPI gets one channel label:

  GOVERNMENT_PHARMACY   pharmacy-supplier taxonomy AND a government-heavy book
  COMMERCIAL_MEDICAL    non-supplier taxonomy AND a commercial-heavy book
  MIXED                 has a payer signal but fits neither clean bucket
                        (government-through-a-non-pharmacy, commercial-through-a
                        -pharmacy, or a genuine blend)
  UNKNOWN               no payer signal and no taxonomy to classify on

and one boolean, is_government_billing, which is the direct answer to the
question.

If the client hands over their own list of government-billing NPIs, the second
tab reconciles the panel against that list so nothing is taken on faith:

  CONFIRMED_GOV                 in the client list and the panel agrees
  CLIENT_GOV_LOW_PANEL_SIGNAL   in the client list but the panel book looks
                                commercial (government book may run off-panel)
  PANEL_GOV_NOT_IN_CLIENT_LIST  panel says government-billing, client list did
                                not include it (a candidate they may have missed)
  CLIENT_LIST_NOT_IN_PANEL      in the client list but that NPI never appears in
                                this panel

Everything is additive and offline-safe: no rows are dropped, taxonomy and the
client list are both optional, and with neither supplied the module still emits
an honest payer-mix-only classification.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import config


# Pharmacy / supplier taxonomy families. 3335 = nuclear pharmacy, 3336 = the
# pharmacy families (infusion, home-infusion, specialty, retail, clinic),
# 333600000X = generic pharmacy. 332B* = DME suppliers that carry the external
# pump / SCIG home channel. These are the "supplier"/pharmacy-model NPIs.
_PHARMACY_PREFIXES = ("3335", "3336")
_DME_PREFIXES = ("332B",)


def _digits(x) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    return "".join(ch for ch in str(x) if ch.isdigit())


def supplier_class(taxonomy_code) -> str:
    """PHARMACY | DME | NONE for a NUCC taxonomy code."""
    c = ("" if taxonomy_code is None else str(taxonomy_code)).strip().upper()
    if not c:
        return "NONE"
    if c == "333600000X" or c.startswith(_PHARMACY_PREFIXES):
        return "PHARMACY"
    if c.startswith(_DME_PREFIXES):
        return "DME"
    return "NONE"


def load_gov_npi_list(path_or_ref=None):
    """Load a client-provided list of government-billing NPIs.

    Accepts an explicit file path, or a reference directory in which the first
    file matching *gov*npi*.csv (that is not the shipped *_example.csv) is used.
    The file needs an NPI column (npi / billing_npi / provider_npi / number);
    all digit-strings found there are returned as a set. Missing file -> empty
    set (module then runs panel-only, no reconciliation)."""
    if path_or_ref is None:
        return set()
    p = Path(path_or_ref)
    target = None
    if p.is_file():
        target = p
    elif p.is_dir():
        cands = [f for f in sorted(p.glob("*gov*npi*.csv"))
                 if not f.name.endswith("_example.csv")]
        target = cands[0] if cands else None
    if target is None or not target.exists():
        return set()
    try:
        df = pd.read_csv(target, dtype=str)
    except Exception:
        return set()
    npi_col = None
    for cand in ("npi", "billing_npi", "provider_npi", "number", "npi_number"):
        for col in df.columns:
            if col.strip().lower() == cand:
                npi_col = col
                break
        if npi_col:
            break
    if npi_col is None:
        # fall back to the first column that looks like 10-digit NPIs
        for col in df.columns:
            s = df[col].map(_digits)
            if (s.str.len() == 10).mean() > 0.5:
                npi_col = col
                break
    if npi_col is None:
        return set()
    return {d for d in df[npi_col].map(_digits) if len(d) == 10}


def _payer_type_series(std: pd.DataFrame) -> pd.Series:
    if "payer" in std.columns:
        return std["payer"].map(config.classify_payer_type)
    return pd.Series("unknown", index=std.index)


def classify_npi_channels(std: pd.DataFrame, *, allowed=None, taxonomy_of=None,
                          gov_frac_threshold: float = 0.50,
                          commercial_frac_threshold: float = 0.20,
                          gov_pharmacy_floor: float = 0.35) -> pd.DataFrame:
    """One row per billing NPI with its payer-type mix, supplier class, channel
    label, and the is_government_billing boolean. `allowed` is an optional dollar
    Series aligned to std; when omitted every claim counts as 1 (claim-count
    weighting). `taxonomy_of` is an optional {npi: taxonomy_code} dict."""
    if "billing_npi" not in std.columns:
        return pd.DataFrame({"note": ["no billing_npi column present; channel classification skipped"]})

    n = len(std)
    npi = std["billing_npi"].map(_digits)
    a = (pd.to_numeric(allowed, errors="coerce").fillna(0.0).values
         if allowed is not None else np.ones(n, dtype=float))
    ptype = _payer_type_series(std).astype(str).values
    taxmap = {_digits(k): str(v) for k, v in (taxonomy_of or {}).items()}

    work = pd.DataFrame({"npi": npi.values, "allowed": a, "ptype": ptype})
    work = work[work["npi"].str.len() > 0]
    if work.empty:
        return pd.DataFrame({"note": ["no usable billing NPIs after digit-cleaning"]})

    rows = []
    gov_types = config.GOVERNMENT_PAYER_TYPES
    for code, g in work.groupby("npi", sort=False):
        tot = float(g["allowed"].sum())
        claims = int(len(g))
        by_type = g.groupby("ptype")["allowed"].sum()
        share = {t: (float(by_type.get(t, 0.0)) / tot if tot > 0 else 0.0)
                 for t in ("medicare", "medicaid", "military_va", "commercial", "unknown")}
        gov_share = share["medicare"] + share["medicaid"] + share["military_va"]
        com_share = share["commercial"]
        known = gov_share + com_share
        # renormalize the gov/commercial split over the KNOWN (non-unknown) book
        gov_of_known = gov_share / known if known > 0 else np.nan

        tax_code = taxmap.get(code, "")
        sclass = supplier_class(tax_code)
        is_pharm = sclass == "PHARMACY"

        # direct answer: government-billing if the book is government-heavy, or a
        # pharmacy-supplier NPI carrying a materially government book.
        is_gov = (gov_share >= gov_frac_threshold) or (is_pharm and gov_share >= gov_pharmacy_floor)

        if is_pharm and gov_share >= gov_pharmacy_floor:
            channel = "GOVERNMENT_PHARMACY"
        elif (not is_pharm) and gov_share <= commercial_frac_threshold and known > 0:
            channel = "COMMERCIAL_MEDICAL"
        elif known == 0:
            channel = "UNKNOWN"
        else:
            channel = "MIXED"

        top_type = max(share, key=share.get) if tot > 0 else "unknown"
        rows.append({
            "billing_npi": code,
            "channel": channel,
            "is_government_billing": bool(is_gov),
            "n_claims": claims,
            "allowed": round(tot, 2),
            "gov_payer_share_pct": round(gov_share * 100, 1),
            "commercial_share_pct": round(com_share * 100, 1),
            "unknown_payer_share_pct": round(share["unknown"] * 100, 1),
            "gov_share_of_known_pct": (round(gov_of_known * 100, 1)
                                       if not np.isnan(gov_of_known) else np.nan),
            "supplier_class": sclass,
            "taxonomy_code": tax_code,
            "top_payer_type": top_type,
            "medicare_pct": round(share["medicare"] * 100, 1),
            "medicaid_pct": round(share["medicaid"] * 100, 1),
            "military_va_pct": round(share["military_va"] * 100, 1),
        })

    out = pd.DataFrame(rows).sort_values(
        ["is_government_billing", "allowed"], ascending=[False, False]
    ).reset_index(drop=True)
    out.attrs["note"] = (
        "Government-billing = government payer share >= {:.0%}, or a pharmacy-supplier "
        "NPI (taxonomy 3335*/3336*/333600000X) carrying >= {:.0%} government. "
        "Pass taxonomy_of to enable the pharmacy-channel test; without it the call is "
        "payer-mix-only. unknown_payer rows are excluded from the gov/commercial "
        "split (see gov_share_of_known_pct)."
    ).format(gov_frac_threshold, gov_pharmacy_floor)
    return out


def government_reconciliation(channel_df: pd.DataFrame, client_gov_npis=None) -> pd.DataFrame:
    """Reconcile the panel's government-billing NPIs against a client-supplied
    list. Returns a per-NPI status table with a summary block on top. When no
    client list is supplied, returns an honest note instead of a fake match."""
    if channel_df is None or "billing_npi" not in getattr(channel_df, "columns", []):
        return pd.DataFrame({"note": ["channel classification unavailable; reconciliation skipped"]})

    client = {(_digits(x)) for x in (client_gov_npis or set())}
    client = {x for x in client if len(x) == 10}
    if not client:
        return pd.DataFrame({"note": [
            "no client government-NPI list supplied. Pass --gov-npi-list (or drop a "
            "*gov*npi*.csv into reference/) to reconcile the panel against the client's "
            "own government-billing NPIs."]})

    panel = channel_df[["billing_npi", "is_government_billing", "channel",
                        "allowed", "gov_payer_share_pct", "supplier_class"]].copy()
    panel_npis = set(panel["billing_npi"])
    panel_gov = set(panel.loc[panel["is_government_billing"], "billing_npi"])

    def _status(row):
        code = row["billing_npi"]
        in_client = code in client
        if in_client and row["is_government_billing"]:
            return "CONFIRMED_GOV"
        if in_client and not row["is_government_billing"]:
            return "CLIENT_GOV_LOW_PANEL_SIGNAL"
        if (not in_client) and row["is_government_billing"]:
            return "PANEL_GOV_NOT_IN_CLIENT_LIST"
        return "COMMERCIAL_NOT_FLAGGED"

    panel["reconciliation"] = panel.apply(_status, axis=1)

    # client-listed NPIs that never appear in the panel at all
    missing = sorted(client - panel_npis)
    extra_rows = [{
        "billing_npi": code, "is_government_billing": False,
        "channel": "NOT_IN_PANEL", "allowed": 0.0, "gov_payer_share_pct": np.nan,
        "supplier_class": "", "reconciliation": "CLIENT_LIST_NOT_IN_PANEL"
    } for code in missing]

    detail = pd.concat([panel, pd.DataFrame(extra_rows)], ignore_index=True) if extra_rows else panel

    # keep the reconciliation-relevant rows (drop the plain commercial ones from
    # the detail view, they are not part of the government reconciliation)
    detail = detail[detail["reconciliation"] != "COMMERCIAL_NOT_FLAGGED"].copy()
    detail = detail.sort_values(["reconciliation", "allowed"],
                                ascending=[True, False]).reset_index(drop=True)

    # summary block
    order = ["CONFIRMED_GOV", "PANEL_GOV_NOT_IN_CLIENT_LIST",
             "CLIENT_GOV_LOW_PANEL_SIGNAL", "CLIENT_LIST_NOT_IN_PANEL"]
    summ = []
    for st in order:
        d = detail[detail["reconciliation"] == st]
        summ.append({"billing_npi": f"== {st}", "channel": "",
                     "reconciliation": "", "n_npis": int(len(d)),
                     "allowed": round(float(d["allowed"].sum()), 2)})
    summ.append({"billing_npi": "== client list size", "channel": "",
                 "reconciliation": "", "n_npis": len(client), "allowed": np.nan})
    summ.append({"billing_npi": "== panel government NPIs", "channel": "",
                 "reconciliation": "", "n_npis": len(panel_gov), "allowed": np.nan})
    summ_df = pd.DataFrame(summ)

    out = pd.concat([summ_df, detail], ignore_index=True)
    out.attrs["note"] = (
        "CONFIRMED_GOV: in client list and panel agrees. PANEL_GOV_NOT_IN_CLIENT_LIST: "
        "panel flags government-billing, absent from client list (candidate to add). "
        "CLIENT_GOV_LOW_PANEL_SIGNAL: client-listed but the panel book reads commercial "
        "(government book may run off-panel). CLIENT_LIST_NOT_IN_PANEL: client-listed NPI "
        "not present in this panel.")
    return out
