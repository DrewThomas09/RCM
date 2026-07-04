"""Step 7: coverage gross-up.

For blank rows we deliberately do NOT name a biller for — self-administered
(Part D) drugs, unresolved NOC codes, codes with no Part-B presence anywhere,
and rows where no candidate matched — size the magnitude by drug so the gap is
quantified rather than guessed. Dollars come from the panel itself (commercial
$ are already on the row); CMS dollars are FFS and do not transfer, so this is
drug-level attribution of volume, not biller attribution."""

import pandas as pd

GROSSUP_REASONS = {"sad", "noc", "no_partb_presence", "no_candidate"}


def build_grossup(std, recovery, route_map):
    """recovery: DataFrame aligned to blanks with columns incl. 'reason', 'tier',
    'recovered_npi', 'blank_allowed'. Returns a per-drug magnitude table."""
    bp = recovery.copy()
    gu = bp[bp["reason"].isin(GROSSUP_REASONS) | bp["recovered_npi"].isna()]
    if gu.empty:
        return pd.DataFrame(columns=["hcpcs", "drug_name", "reason", "rows",
                                     "units", "dollars", "track"])
    drug_lookup = (std.dropna(subset=["hcpcs"])
                   .groupby("hcpcs")["drug_name"]
                   .agg(lambda s: next((x for x in s if pd.notna(x) and str(x).strip()), ""))
                   .to_dict())
    gu = gu.copy()
    gu["drug_name"] = gu["hcpcs"].map(drug_lookup).fillna("")
    gu["units"] = pd.to_numeric(gu.get("blank_units", 0), errors="coerce").fillna(0)
    gu["dollars"] = pd.to_numeric(gu.get("blank_allowed", 0), errors="coerce").fillna(0)
    track = {"sad": "Part D (pharmacy benefit)", "noc": "Resolve NDC then re-run",
             "no_partb_presence": "No Medicare Part-B billers — likely pharmacy/commercial-only",
             "no_candidate": "No candidate match — distributional only"}
    out = (gu.groupby(["hcpcs", "drug_name", "reason"])
           .agg(rows=("hcpcs", "size"), units=("units", "sum"), dollars=("dollars", "sum"))
           .reset_index()
           .sort_values("dollars", ascending=False))
    out["track"] = out["reason"].map(track).fillna(out["reason"])
    return out
