"""Step 0.6 (v29): pharmacy / RX dual-feed.

The medical extract cannot see the pharmacy-benefit channel — the readout put a
~$20M/yr (pre-scale) Option Care figure on it that, added back, erases the
medical-only decline. v28 *estimated* that tail from a CMS Part D/Part B analog.
v29 lets the team drop the actual Komodo pharmacy pull in alongside the medical
file: it is standardised on the SAME schema and J-code reference list, every row
is stamped _Claim_Source = medical | pharmacy, the two are unioned, and obvious
cross-feed duplicates are removed (same claim id; or exact
patient+code+date+allowed) so a drug billed on both benefits is not double
counted.

Once the real pharmacy feed is present, the pharmacy slice is MEASURED, not
grossed up — the toolkit's standing principle (the holdout is evidence; evidence
beats the prior). The reconciliation tab shows, per operator and in total, the
medical-only basis vs the medical+pharmacy basis and the year-over-year growth
on each, so the analyst can see the same-store decline flip when the channel is
added back. membership_index is an optional per-year covered-lives scaling knob
(default 1.0, no adjustment) so a membership-adjusted growth read is reproducible
rather than done by hand.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import excelio, schema


PHARMACY_SOURCE = "pharmacy"
MEDICAL_SOURCE = "medical"


def read_and_standardize(path, *, overrides=None, source=PHARMACY_SOURCE,
                         rxnorm=None, ref_dir=None, crosswalk=None, progress=None):
    """Read a claims file and standardise it with the SAME column detection and
    canonicalisation the medical feed uses, then stamp _claim_source. Returns
    (std, map_report).

    v30: a real pharmacy extract is NDC-keyed (no J-code) and often reports money
    as ingredient cost + dispensing fee rather than a single allowed amount. So
    after standardising we (a) synthesise allowed_amt from ingredient_cost +
    dispensing_fee when allowed is absent, and (b) run the NDC/name -> drug-class
    bridge so the pharmacy rows fold into the same per-drug taxonomy as medical.
    """
    raw = excelio.read_claims(path)
    mapping, report = schema.detect_columns(raw, overrides=overrides)
    std = schema.standardize(raw, mapping)
    std["_claim_source"] = source

    # money: if there is no single allowed/paid column but the pharmacy split
    # (ingredient cost + dispensing fee) is present, sum it into allowed_amt.
    allowed = pd.to_numeric(std.get("allowed_amt"), errors="coerce")
    if (allowed is None) or allowed.fillna(0).abs().sum() == 0:
        ic = pd.to_numeric(std.get("ingredient_cost"), errors="coerce") if "ingredient_cost" in std.columns else None
        dfee = pd.to_numeric(std.get("dispensing_fee"), errors="coerce") if "dispensing_fee" in std.columns else None
        if ic is not None and ic.fillna(0).abs().sum() > 0:
            std["allowed_amt"] = ic.fillna(0.0) + (dfee.fillna(0.0) if dfee is not None else 0.0)

    # NDC / name -> drug class + representative J-code + unit basis
    try:
        from . import rx_bridge
        std = rx_bridge.resolve_feed(std, rxnorm=rxnorm, crosswalk=crosswalk,
                                     ref_dir=ref_dir, progress=progress)
    except Exception:
        # never fatal: the feed still unions on dollars, just without per-drug class
        if "drug_class_rx" not in std.columns:
            std["drug_class_rx"] = rx_bridge.UNMAPPED if "rx_bridge" in dir() else "UNMAPPED_RX"

    rep = pd.DataFrame(
        [{"canonical_field": k, "matched_column": (v[1] if v[1] else "(none)"),
          "match_type": v[0]} for k, v in report.items()])
    return std, rep


def union_feeds(std_medical: pd.DataFrame, std_pharmacy: pd.DataFrame):
    """Concatenate a medical and a pharmacy std frame, dedupe across feeds, and
    return (std_union, dedup_report). The medical row is kept on a collision
    because it carries the biller and site of care; the pharmacy row's dollars
    are what we want where medical has none."""
    med = std_medical.copy()
    if "_claim_source" not in med.columns:
        med["_claim_source"] = MEDICAL_SOURCE
    ph = std_pharmacy.copy()
    if "_claim_source" not in ph.columns:
        ph["_claim_source"] = PHARMACY_SOURCE

    # align columns
    cols = list(dict.fromkeys(list(med.columns) + list(ph.columns)))
    for c in cols:
        if c not in med.columns:
            med[c] = pd.NA
        if c not in ph.columns:
            ph[c] = pd.NA
    union = pd.concat([med[cols], ph[cols]], ignore_index=True)

    report_rows = [{"metric": "medical_rows", "value": int(len(med))},
                   {"metric": "pharmacy_rows", "value": int(len(ph))}]

    dropped_claimid = 0
    if "claim_id" in union.columns and union["claim_id"].notna().any():
        # A claim id can legitimately appear on MANY lines within one feed (the
        # J-code line plus its companion 9xxxx administration line share it — the
        # exact structure the readout asked the extract to carry). So we must NOT
        # collapse intra-feed multi-line claims. We only drop the PHARMACY lines of
        # a claim id that ALSO appears in the MEDICAL feed (the same adjudicated
        # claim arriving on both pulls), keeping every medical line.
        cid = union["claim_id"].astype("string")
        med_ids = set(cid[union["_claim_source"] == MEDICAL_SOURCE].dropna())
        cross = (union["_claim_source"].eq(PHARMACY_SOURCE) & cid.isin(med_ids))
        dropped_claimid = int(cross.sum())
        if dropped_claimid:
            union = union[~cross].reset_index(drop=True)
    report_rows.append({"metric": "dropped_same_claim_id", "value": dropped_claimid})

    # soft duplicate flag: exact patient+hcpcs+date+allowed across sources (not dropped)
    flagged = 0
    needed = {"patient_id", "hcpcs", "date", "allowed_amt"}
    if needed.issubset(set(union.columns)):
        key = (union["patient_id"].astype("string").fillna("") + "|" +
               union["hcpcs"].astype("string").fillna("") + "|" +
               pd.to_datetime(union["date"], errors="coerce").dt.strftime("%Y%m%d").fillna("") + "|" +
               pd.to_numeric(union["allowed_amt"], errors="coerce").round(2).astype("string").fillna(""))
        src_per_key = union.groupby(key)["_claim_source"].nunique()
        cross = set(src_per_key[src_per_key > 1].index)
        union["_possible_cross_source_dup"] = key.isin(cross) & key.ne("|||")
        flagged = int(union["_possible_cross_source_dup"].sum())
    else:
        union["_possible_cross_source_dup"] = False
    report_rows.append({"metric": "flagged_possible_cross_source_dups", "value": flagged})
    report_rows.append({"metric": "union_rows", "value": int(len(union))})

    # rebuild derived columns the rest of the pipeline expects
    if "is_blank_billing" in union.columns:
        union["is_blank_billing"] = union["billing_npi"].isna()
    union["orig_row"] = np.arange(len(union))
    return union, pd.DataFrame(report_rows)


def enrich_and_attribute(std_pharmacy, *, nppes, cms=None, provider_directory=None,
                         parent_map=None, progress=None):
    """Bring the pharmacy dispensing NPIs into the world the analytics live in.

    Two problems this solves:
      1. Site of care — a dispensing pharmacy's NPPES taxonomy is exactly what tells
         the reclassifier a row is AIS (home-infusion / specialty pharmacy) rather
         than office. The medical enrichment never saw these NPIs, so we enrich them
         here and hand back rows to append to the provider directory (-> taxonomy_of).
      2. Operator rollup — the pharmacy feed bills under the platform's pharmacy NPIs,
         which differ from its medical NPIs. We roll each pharmacy NPI up to an
         operator by its enriched organisation name: if that name matches an operator
         already known from the medical side it inherits that label (so Option Care's
         pharmacy and medical volume sit under one operator); otherwise it rolls up
         under its own organisation name (so its many NPIs still collapse to one
         operator) rather than scattering across raw NPIs.

    Returns (pharm_directory_df, extended_parent_map, attribution_coverage_df).
    Deterministic name match only (exact / contains) — no fuzzy merges, so it cannot
    fabricate a link. Never raises.
    """
    progress = progress or (lambda *_: None)
    pm = dict(parent_map or {})
    try:
        from . import enrich as _enrich, entity as _entity
    except Exception:
        return pd.DataFrame(), pm, pd.DataFrame({"note": ["enrich module unavailable"]})

    npis = sorted({"".join(ch for ch in str(n) if ch.isdigit())
                   for n in std_pharmacy.get("billing_npi", pd.Series(dtype=str)).dropna()
                   if "".join(ch for ch in str(n) if ch.isdigit())})
    if not npis:
        return pd.DataFrame(), pm, pd.DataFrame({"metric": ["pharmacy_npis"], "value": [0]})
    progress("Enriching pharmacy NPIs", 0.1)
    pharm_dir = _enrich.build_provider_directory(npis, nppes, cms=cms)

    # operator label for each medical NPI, and the set of known operator names
    name_to_op = {}
    if provider_directory is not None and len(provider_directory) and "NPI" in provider_directory.columns:
        nm_col = "Provider_Name" if "Provider_Name" in provider_directory.columns else None
        if nm_col:
            for _, r in provider_directory.iterrows():
                op = pm.get(str(r["NPI"]))
                nm = _entity._norm_name(r[nm_col]) if hasattr(_entity, "_norm_name") else _norm_org(r[nm_col])
                if op and nm:
                    name_to_op.setdefault(nm, op)
    known_ops = sorted({_norm_org(v) for v in pm.values() if isinstance(v, str)}, key=len, reverse=True)

    attributed = 0
    pharm_ops = {}
    for _, r in pharm_dir.iterrows():
        npi = str(r["NPI"]); org = _norm_org(r.get("Provider_Name", ""))
        op = None
        if org and org in name_to_op:
            op = name_to_op[org]; attributed += 1
        elif org:
            # contains-match against known operator tokens (e.g. 'option care')
            hit = next((k for k in known_ops if k and (k in org or org in k) and len(k) >= 6), None)
            if hit:
                # map to the original-cased operator label that normalises to hit
                op = next((v for v in pm.values() if isinstance(v, str) and _norm_org(v) == hit), hit)
                attributed += 1
            else:
                op = r.get("Provider_Name", "") or f"NPI {npi}"
        else:
            op = f"NPI {npi}"
        pharm_ops[npi] = op
    pm.update(pharm_ops)

    # coverage: how much pharmacy allowed rolls up to a KNOWN medical operator
    allowed = pd.to_numeric(std_pharmacy.get("allowed_amt"), errors="coerce").fillna(0.0)
    bn = std_pharmacy.get("billing_npi", pd.Series(dtype=str)).astype("string").map(
        lambda x: "".join(ch for ch in str(x) if ch.isdigit()))
    med_ops = {v for v in (parent_map or {}).values() if isinstance(v, str)}
    rolled_known = sum(float(a) for a, n in zip(allowed, bn)
                       if pharm_ops.get(str(n)) in med_ops)
    cov = pd.DataFrame([
        {"metric": "pharmacy_npis", "value": len(npis)},
        {"metric": "pharmacy_npis_found_in_nppes",
         "value": int(pharm_dir.get("Found_In_NPPES", pd.Series(dtype=bool)).sum()) if "Found_In_NPPES" in pharm_dir.columns else 0},
        {"metric": "pharmacy_npis_matched_to_a_medical_operator", "value": attributed},
        {"metric": "pharmacy_allowed_rolled_to_a_known_operator", "value": round(rolled_known, 0)},
        {"metric": "pharmacy_allowed_total", "value": round(float(allowed.sum()), 0)},
    ])
    cov.attrs["note"] = ("Pharmacy NPIs are enriched via NPPES (their taxonomy drives the AIS site "
                         "classification) and rolled up to an operator by organisation name: exact or "
                         "contains match to a known medical operator, else their own org name. "
                         "Deterministic match only — no fuzzy merges.")
    return pharm_dir, pm, cov


def _norm_org(s):
    import re as _re
    s = _re.sub(r"[^a-z0-9 ]+", " ", str(s).lower())
    s = _re.sub(r"\b(llc|inc|incorporated|corp|corporation|co|ltd|lp|pllc|pc|pa|the|"
                r"pharmacy|pharmacies|infusion|infusions|specialty|services|service|"
                r"health|healthcare|home|care|rx|company|group|holdings)\b", " ", s)
    return _re.sub(r"\s+", " ", s).strip()


def channel_reconciliation(std_union: pd.DataFrame, operator: pd.Series,
                           year: pd.Series, *, membership_index: dict | None = None,
                           top_n: int = 40):
    """Per operator (and TOTAL): medical-only vs medical+pharmacy allowed, and the
    YoY growth on each basis. The medical-only decline that flips flat/positive
    once the pharmacy channel is added is the headline this produces.

    membership_index: optional {year:int -> covered-lives scaling factor}. Applied
    to allowed $ before growth so the read is membership-adjusted; default 1.0.
    """
    if "_claim_source" not in std_union.columns:
        return pd.DataFrame({"note": ["no _claim_source column — union the feeds first"]})
    allowed = pd.to_numeric(std_union.get("allowed_amt"), errors="coerce").fillna(0.0)
    # reversals stay out of growth math
    allowed = allowed.clip(lower=0.0)
    src = std_union["_claim_source"].astype("string").fillna(MEDICAL_SOURCE)
    df = pd.DataFrame({"operator": np.asarray(operator), "src": src.values,
                       "allowed": allowed.values, "year": np.asarray(year)})
    mi = {int(k): float(v) for k, v in (membership_index or {}).items()}

    def _basis_growth(sub):
        """YoY growth (last two dated years) of membership-adjusted allowed."""
        s = sub.dropna(subset=["year"])
        if s.empty:
            return np.nan, np.nan, np.nan
        yy = s.groupby("year")["allowed"].sum()
        yy = yy / yy.index.map(lambda y: mi.get(int(y), 1.0))
        yy = yy.sort_index()
        if yy.shape[0] < 2 or yy.iloc[-2] <= 0:
            return float(yy.iloc[-1]) if len(yy) else np.nan, np.nan, np.nan
        g = (yy.iloc[-1] / yy.iloc[-2] - 1.0) * 100.0
        cagr = ((yy.iloc[-1] / yy.iloc[0]) ** (1.0 / (yy.shape[0] - 1)) - 1.0) * 100.0
        return float(yy.iloc[-1]), float(round(g, 1)), float(round(cagr, 1))

    has_year = df["year"].notna().any()
    rows = []
    ops = (df.groupby("operator")["allowed"].sum().sort_values(ascending=False)
           .head(top_n).index.tolist())
    for op in ops:
        sub = df[df["operator"] == op]
        med = sub[sub["src"] == MEDICAL_SOURCE]
        comb = sub
        med_tot = float(med["allowed"].sum())
        comb_tot = float(comb["allowed"].sum())
        rec = {"operator": op,
               "medical_only_allowed": round(med_tot, 0),
               "combined_allowed": round(comb_tot, 0),
               "pharmacy_allowed": round(comb_tot - med_tot, 0),
               "pharmacy_share_of_combined_pct": round(100 * (comb_tot - med_tot) / comb_tot, 1) if comb_tot > 0 else np.nan}
        if has_year:
            _, g_med, c_med = _basis_growth(med)
            _, g_comb, c_comb = _basis_growth(comb)
            rec["medical_only_yoy_pct"] = g_med
            rec["combined_yoy_pct"] = g_comb
            rec["yoy_swing_pp"] = round(g_comb - g_med, 1) if (pd.notna(g_med) and pd.notna(g_comb)) else np.nan
            rec["medical_only_cagr_pct"] = c_med
            rec["combined_cagr_pct"] = c_comb
        rows.append(rec)

    out = pd.DataFrame(rows)
    # TOTAL row
    med_all = df[df["src"] == MEDICAL_SOURCE]
    tot = {"operator": "TOTAL (all operators)",
           "medical_only_allowed": round(float(med_all["allowed"].sum()), 0),
           "combined_allowed": round(float(df["allowed"].sum()), 0),
           "pharmacy_allowed": round(float(df["allowed"].sum() - med_all["allowed"].sum()), 0),
           "pharmacy_share_of_combined_pct": round(100 * (df["allowed"].sum() - med_all["allowed"].sum()) / df["allowed"].sum(), 1) if df["allowed"].sum() > 0 else np.nan}
    if has_year:
        _, g_med, c_med = _basis_growth(med_all)
        _, g_comb, c_comb = _basis_growth(df)
        tot["medical_only_yoy_pct"] = g_med
        tot["combined_yoy_pct"] = g_comb
        tot["yoy_swing_pp"] = round(g_comb - g_med, 1) if (pd.notna(g_med) and pd.notna(g_comb)) else np.nan
        tot["medical_only_cagr_pct"] = c_med
        tot["combined_cagr_pct"] = c_comb
    out = pd.concat([pd.DataFrame([tot]), out], ignore_index=True)
    if not (membership_index or {}):
        out.attrs["membership_note"] = ("membership_index not supplied: growth is on raw allowed $, "
                                        "not covered-lives-adjusted. Pass membership_index={year: factor} "
                                        "to reproduce the membership-adjusted read.")
    return out
