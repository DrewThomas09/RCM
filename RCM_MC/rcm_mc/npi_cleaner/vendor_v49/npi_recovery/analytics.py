"""Step 6 (v25): readout analytics built on the cleaned + recovered frame.

These are the deal-team cuts that came out of the pre-readout sync. They are
DETERMINISTIC group-bys over the canonical `std` frame plus the post-recovery
final billing NPI and the parent-operator roll-up. They make NO new API calls
and reuse the entity roll-up the pipeline already built, so the whole stage adds
seconds, not minutes, to a 600K-row run.

Honesty rules baked in here, because two of these cuts are easy to over-read:

  * Referral_Concentration measures CURRENT dependency and a LEADING indicator
    (is a key referrer already routing share to a competitor). It does NOT
    measure a future decline. An exclusivity that bites in 2026 is not in this
    panel yet, so this sheet is exposure, not proof of erosion.

  * Formulary_Scorecard and Benefit_Shift_Exposure lean on a small CURATED
    reference table for things claims cannot show (IRA selection, biosimilar
    status, whether an approved subcutaneous version exists). Every such column
    is suffixed/flagged as reference-sourced so it is never mistaken for a
    measured fact. Update the table as the policy landscape moves.

The VRDC gross-up is intentionally NOT done here. VRDC was never received, so a
full-market number would be fabricated. The pipeline already ships a labeled
gross-up scaffold; this stage stays on the observed Komodo subset.

Granularity is a parameter: zip3 (what the Komodo extract supports) by default,
county-ready for when VRDC arrives at county grain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from .repair import POS_CANON
except Exception:                       # pragma: no cover
    POS_CANON = {"11": "11", "12": "12", "22": "22"}


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
_SITE = {                               # canonical POS token -> readable bucket
    "11": "Office / AIC", "49": "Office / AIC", "50": "Office / AIC",
    "71": "Office / AIC", "72": "Office / AIC",
    "12": "Home", "32": "Home", "34": "Home",
    "22": "Outpatient hospital", "19": "Outpatient hospital",
    "21": "Inpatient", "23": "Inpatient",
    "F": "Facility", "60": "Other", "65": "Other",
}


def _site_of_care(pos: pd.Series) -> pd.Series:
    tok = pos.astype("string").str.strip().str.upper().map(
        lambda v: POS_CANON.get(v, v) if v is not None else v)
    return tok.map(lambda t: _SITE.get(t, "Other / unknown")).fillna("Other / unknown")


def _hhi(shares_pct: np.ndarray) -> float:
    """Herfindahl on a vector of percentage shares (0-100)."""
    if len(shares_pct) == 0:
        return float("nan")
    return float(np.round(np.sum(np.square(shares_pct)), 1))


def _year(std: pd.DataFrame) -> pd.Series:
    """Best-effort service year. Empty Series (all NA) when no date column."""
    if "date" not in std.columns or std["date"].isna().all():
        return pd.Series(pd.NA, index=std.index, dtype="Int64")
    dt = pd.to_datetime(std["date"], errors="coerce")
    return dt.dt.year.astype("Int64")


def _submarket(std: pd.DataFrame, granularity: str) -> pd.Series:
    if granularity == "county" and "county" in std.columns and not std["county"].isna().all():
        return std["county"].astype("string").fillna("(unknown)")
    z = std["zip3"] if "zip3" in std.columns else pd.Series("", index=std.index)
    return z.astype("string").replace({"": "(unknown)"}).fillna("(unknown)")


# --------------------------------------------------------------------------- #
# curated clinical reference (NOT derived from claims) -- update as policy moves
# keyed on an ingredient keyword matched against the drug label/ingredient.
# flags: bnb=buy-and-bill economics, ira=IRA-negotiation exposure,
# biosim=biosimilar erosion risk, sc=approved subcutaneous/self-admin version
# exists (the white-/brown-bag + benefit-shift vector), area=therapeutic area,
# read=the team's stance.
# --------------------------------------------------------------------------- #
_REF = [
    dict(key="immune globulin", alias="IVIG / SCIG", bnb="Strong", ira="Low",
         biosim="Low", sc="Partial (SCIG)", area="Neuro / rare disease / immunology",
         read="Core - protect"),
    dict(key="ivig", alias="IVIG / SCIG", bnb="Strong", ira="Low", biosim="Low",
         sc="Partial (SCIG)", area="Neuro / rare disease / immunology", read="Core - protect"),
    dict(key="teprotumumab", alias="Tepezza", bnb="Strong", ira="Low", biosim="Low",
         sc="No (IV)", area="Endocrine / TED", read="Favorable - concentration risk"),
    dict(key="ustekinumab", alias="Stelara", bnb="Weak (mostly SC)", ira="Selected",
         biosim="High", sc="Yes", area="Immunology / GI", read="Watch - biosimilar + IRA"),
    dict(key="ocrelizumab", alias="Ocrevus", bnb="Strong", ira="Low", biosim="Low",
         sc="Yes (Zunovo SC)", area="Neuro / MS", read="Watch - SC shift"),
    dict(key="vedolizumab", alias="Entyvio", bnb="Moderate", ira="Low", biosim="Low",
         sc="Yes (SC maintenance)", area="GI", read="Watch - GI shifting to SC"),
    dict(key="infliximab", alias="Remicade", bnb="Weak", ira="Low", biosim="High",
         sc="No", area="Rheum / GI", read="Avoid - biosimilar erosion, flat demand"),
    dict(key="efgartigimod", alias="Vyvgart", bnb="Strong", ira="Low", biosim="Low",
         sc="Yes (Hytrulo SC)", area="Neuro / gMG (FcRn)", read="Growth - watch SC"),
    dict(key="rozanolixizumab", alias="Rystiggo", bnb="Moderate", ira="Low", biosim="Low",
         sc="Yes (SC)", area="Neuro / gMG (FcRn)", read="Growth - watch SC"),
    dict(key="ravulizumab", alias="Ultomiris", bnb="Strong", ira="Low", biosim="Low",
         sc="Partial", area="Neuro / rare (complement)", read="Growth"),
    dict(key="vutrisiran", alias="Amvuttra", bnb="Moderate", ira="Low", biosim="Low",
         sc="Yes (SC)", area="Cardio / neuro rare (ATTR)", read="Promising - nascent"),
    dict(key="daptomycin", alias="Daptomycin", bnb="Strong", ira="Low", biosim="Yes (generic)",
         sc="No", area="Anti-infective / OPAT", read="Acute - stable"),
]


def _ref_lookup(label: str) -> dict | None:
    s = (label or "").lower()
    for r in _REF:
        if r["key"] in s:
            return r
    return None


def _drug_label(hcpcs, drug_name, drug_ident) -> str:
    """Best label for a drug: ingredient from drug_ident, else the drug name,
    else the bare HCPCS code."""
    di = drug_ident or {}
    rec = di.get(str(hcpcs)) if hcpcs is not None else None
    if isinstance(rec, dict):
        for k in ("ingredient", "drug_class", "name", "label"):
            if rec.get(k):
                return str(rec[k])
    if isinstance(drug_name, str) and drug_name.strip():
        return drug_name.strip()
    return str(hcpcs) if hcpcs is not None else "(unknown drug)"


def _build_drug_series(std, drug_ident):
    """Return (label_series, category_series) at row level."""
    di = drug_ident or {}
    hc = std["hcpcs"] if "hcpcs" in std.columns else pd.Series(pd.NA, index=std.index)
    dn = std["drug_name"] if "drug_name" in std.columns else pd.Series(pd.NA, index=std.index)
    labels, cats = [], []
    for h, n in zip(hc.tolist(), dn.tolist()):
        lab = _drug_label(h, n, di)
        labels.append(lab)
        rec = di.get(str(h)) if h is not None else None
        cat = rec.get("drug_class") if isinstance(rec, dict) and rec.get("drug_class") else lab
        cats.append(cat)
    return (pd.Series(labels, index=std.index, dtype="object"),
            pd.Series(cats, index=std.index, dtype="object"))


def _operator_series(final_npi: pd.Series, parent_map: dict) -> pd.Series:
    pm = parent_map or {}

    def _digits(x):
        s = "".join(ch for ch in str(x) if ch.isdigit())
        return s

    def _op(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "(unattributed)"
        d = _digits(x)
        return pm.get(d, f"NPI {d}") if d else "(unattributed)"

    return final_npi.map(_op)


# --------------------------------------------------------------------------- #
# 1. Referral concentration  (the KabaFusion / Memorial Hermann headline)
# --------------------------------------------------------------------------- #
def referral_concentration(std, operator, allowed, *, drug_cat=None,
                           drug_class_filter=None, min_allowed=0.0, top_n=400):
    """Per referring provider: how concentrated its downstream billing is, and
    which operator dominates it. This is the exposure / leading-indicator view
    behind a referral-erosion risk, NOT a measured future decline.

    drug_class_filter (e.g. 'immune globulin') restricts to one therapy so you
    can ask the IVIG-specific question directly.
    """
    if "referring_npi" not in std.columns:
        return pd.DataFrame({"note": ["no referring NPI column in source"]})
    df = pd.DataFrame({
        "referring_npi": std["referring_npi"].astype("string"),
        "referring_specialty": (std["referring_specialty"].astype("string")
                                if "referring_specialty" in std.columns else ""),
        "operator": operator.values,
        "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
    })
    if drug_class_filter is not None and drug_cat is not None:
        mask = drug_cat.astype(str).str.lower().str.contains(drug_class_filter.lower(), na=False)
        df = df[mask.values]
    df = df[df["referring_npi"].notna() & (df["referring_npi"].astype(str).str.len() > 0)]
    if df.empty:
        return pd.DataFrame({"note": ["no referring-provider rows after filtering"]})

    rows = []
    for ref, g in df.groupby("referring_npi", sort=False):
        tot = float(g["allowed"].sum())
        if tot < min_allowed:
            continue
        by_op = g.groupby("operator")["allowed"].sum().sort_values(ascending=False)
        shares = (by_op / tot * 100.0) if tot > 0 else by_op * 0
        top_op = by_op.index[0]
        top_share = float(round(shares.iloc[0], 1))
        rows.append({
            "referring_npi": ref,
            "referring_specialty": g["referring_specialty"].mode().iloc[0] if not g["referring_specialty"].mode().empty else "",
            "n_claims": int(len(g)),
            "referred_allowed": round(tot, 2),
            "n_billing_operators": int(by_op.shape[0]),
            "top_billing_operator": top_op,
            "top_operator_share_pct": top_share,
            "referral_hhi": _hhi(shares.values),
            "single_source_flag": "Y" if top_share >= 70 else "",
        })
    out = pd.DataFrame(rows).sort_values("referred_allowed", ascending=False).head(top_n)
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 2. Submarket landscape  (Corey's single-year market-landscape slide)
# --------------------------------------------------------------------------- #
def submarket_landscape(std, drug_cat, site, allowed, units, year, *,
                        granularity="zip3", latest_year_only=True):
    sub = _submarket(std, granularity)
    yr = year
    note = None
    if latest_year_only and yr.notna().any():
        latest = int(yr.dropna().max())
        keep = (yr == latest).values
        note = f"single year {latest}"
    else:
        keep = np.ones(len(std), dtype=bool)
        note = "all years (no usable date column)" if yr.isna().all() else "all years"
    df = pd.DataFrame({
        "submarket": sub.values, "drug_category": drug_cat.values,
        "site_of_care": site.values,
        "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
        "units": pd.to_numeric(units, errors="coerce").fillna(0.0).values,
    })[keep]
    if df.empty:
        return pd.DataFrame({"note": [f"no rows ({note})"]})
    g = (df.groupby(["submarket", "drug_category", "site_of_care"], sort=False)
           .agg(n_claims=("allowed", "size"), units=("units", "sum"),
                allowed=("allowed", "sum")).reset_index())
    tot_by_sub = g.groupby("submarket")["allowed"].transform("sum")
    g["allowed_share_in_submarket_pct"] = np.where(
        tot_by_sub > 0, np.round(g["allowed"] / tot_by_sub * 100.0, 1), 0.0)
    g["window"] = note
    g["allowed"] = g["allowed"].round(2)
    return g.sort_values(["submarket", "allowed"], ascending=[True, False]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 3. Submarket saturation  (build-vs-acquire; RELATIVE, no 2-per-100k benchmark)
# --------------------------------------------------------------------------- #
def submarket_saturation(std, operator, allowed, year, *, granularity="zip3"):
    sub = _submarket(std, granularity)
    df = pd.DataFrame({
        "submarket": sub.values, "operator": operator.values,
        "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
        "year": year.values,
    })
    df = df[df["operator"].astype(str).ne("(unattributed)")]
    if df.empty:
        return pd.DataFrame({"note": ["no attributed rows to assess saturation"]})

    rows = []
    has_year = df["year"].notna().any()
    for s, g in df.groupby("submarket", sort=False):
        tot = float(g["allowed"].sum())
        by_op = g.groupby("operator")["allowed"].sum()
        shares = (by_op / tot * 100.0) if tot > 0 else by_op * 0
        rec = {"submarket": s, "n_operators": int(by_op.shape[0]),
               "operator_hhi": _hhi(shares.values),
               "allowed": round(tot, 2), "n_claims": int(len(g))}
        if has_year and g["year"].notna().any():
            yy = g.dropna(subset=["year"]).groupby("year")["allowed"].sum().sort_index()
            if yy.shape[0] >= 2 and yy.iloc[-2] > 0:
                rec["yoy_growth_pct"] = round((yy.iloc[-1] / yy.iloc[-2] - 1) * 100.0, 1)
            else:
                rec["yoy_growth_pct"] = np.nan
        rows.append(rec)
    out = pd.DataFrame(rows)
    # saturation is RELATIVE across submarkets, not an absolute per-capita rule
    out["operator_density_pctile"] = (out["n_operators"].rank(pct=True) * 100).round(0)
    dense = out["operator_density_pctile"] >= 50
    if "yoy_growth_pct" in out.columns and out["yoy_growth_pct"].notna().any():
        grow = out["yoy_growth_pct"] >= out["yoy_growth_pct"].median()
        out["read"] = np.select(
            [dense & grow, dense & ~grow, ~dense & grow, ~dense & ~grow],
            ["Saturated + growing (acquire)", "Saturated + flat (avoid / acquire)",
             "Open + growing (build target)", "Open + flat (watch)"], default="")
    else:
        out["read"] = np.where(dense, "Denser than median (likely acquire)",
                               "Less dense than median (build candidate)")
    return out.sort_values("allowed", ascending=False).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 4. Referral target map  (who to target by submarket, open vs closed, org type)
# --------------------------------------------------------------------------- #
def referral_target_map(std, operator, allowed, *, granularity="zip3", min_allowed=0.0, top_per_sub=15):
    if "referring_npi" not in std.columns:
        return pd.DataFrame({"note": ["no referring NPI column in source"]})
    sub = _submarket(std, granularity)
    spec = (std["referring_specialty"].astype("string")
            if "referring_specialty" in std.columns else pd.Series("", index=std.index))
    df = pd.DataFrame({
        "submarket": sub.values,
        "referring_npi": std["referring_npi"].astype("string").values,
        "specialty": spec.values, "operator": operator.values,
        "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
    })
    df = df[df["referring_npi"].notna() & (df["referring_npi"].astype(str).str.len() > 0)]
    if df.empty:
        return pd.DataFrame({"note": ["no referring-provider rows"]})

    rows = []
    for (s, ref), g in df.groupby(["submarket", "referring_npi"], sort=False):
        tot = float(g["allowed"].sum())
        if tot < min_allowed:
            continue
        by_op = g.groupby("operator")["allowed"].sum().sort_values(ascending=False)
        top_share = float(round(by_op.iloc[0] / tot * 100.0, 1)) if tot > 0 else 0.0
        openness = ("Closed" if top_share >= 70 else
                    "Partially open" if top_share >= 40 else "Open")
        sp = (g["specialty"].mode().iloc[0] if not g["specialty"].mode().empty else "").lower()
        org = ("Health system" if any(k in sp for k in ("hospital", "health system", "medical center"))
               else "PPM / group" if any(k in sp for k in ("group", "associates", "clinic", "ppm"))
               else "Independent / unknown")
        rows.append({
            "submarket": s, "referring_npi": ref,
            "specialty": g["specialty"].mode().iloc[0] if not g["specialty"].mode().empty else "",
            "referred_allowed": round(tot, 2),
            "current_primary_operator": by_op.index[0],
            "primary_operator_share_pct": top_share,
            "openness": openness,
            "org_type_heuristic": org,
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame({"note": ["no referrers cleared the dollar floor"]})
    out["rank_in_submarket"] = (out.sort_values("referred_allowed", ascending=False)
                                .groupby("submarket").cumcount() + 1)
    out = out[out["rank_in_submarket"] <= top_per_sub]
    return out.sort_values(["submarket", "referred_allowed"], ascending=[True, False]).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 5. Benefit-shift exposure  (white/brown-bag forward risk -- Drew's analog)
# --------------------------------------------------------------------------- #
def benefit_shift_exposure(std, drug_label, allowed):
    df = pd.DataFrame({
        "drug_label": drug_label.values,
        "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
    })
    g = df.groupby("drug_label", sort=False)["allowed"].agg(["size", "sum"]).reset_index()
    g.columns = ["drug_label", "n_claims", "allowed"]
    tot = float(g["allowed"].sum()) or 1.0
    g["book_share_pct"] = (g["allowed"] / tot * 100.0).round(1)

    def _ref(lbl):
        r = _ref_lookup(lbl)
        return (r["alias"] if r else "", r["sc"] if r else "unknown",
                r["read"] if r else "") if True else None
    refd = g["drug_label"].map(lambda l: _ref_lookup(l))
    g["matched_reference_drug"] = refd.map(lambda r: r["alias"] if r else "")
    g["sc_self_admin_version__ref"] = refd.map(lambda r: r["sc"] if r else "unknown")
    g["white_bag_forward_risk__ref"] = refd.map(
        lambda r: ("High" if r and ("yes" in r["sc"].lower())
                   else "Moderate" if r and ("partial" in r["sc"].lower())
                   else "Low" if r else "unknown"))
    g["allowed"] = g["allowed"].round(2)
    g = g.sort_values("allowed", ascending=False).reset_index(drop=True)

    at_risk = g[g["white_bag_forward_risk__ref"].isin(["High", "Moderate"])]["book_share_pct"].sum()
    summary = pd.DataFrame([{
        "drug_label": "TOTAL book at forward white-bag risk (High or Moderate, reference-based)",
        "n_claims": int(g["n_claims"].sum()), "allowed": g["allowed"].sum(),
        "book_share_pct": round(float(at_risk), 1), "matched_reference_drug": "",
        "sc_self_admin_version__ref": "", "white_bag_forward_risk__ref": "<- forward exposure",
    }])
    return pd.concat([g, summary], ignore_index=True)


# --------------------------------------------------------------------------- #
# 6. Formulary scorecard  (the mix read; measured share + curated risk flags)
# --------------------------------------------------------------------------- #
def formulary_scorecard(std, drug_label, allowed, year, *, top_n=25):
    df = pd.DataFrame({
        "drug_label": drug_label.values,
        "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
        "year": year.values,
    })
    g = df.groupby("drug_label", sort=False)["allowed"].agg(["size", "sum"]).reset_index()
    g.columns = ["drug_label", "n_claims", "allowed"]
    tot = float(g["allowed"].sum()) or 1.0
    g["book_share_pct"] = (g["allowed"] / tot * 100.0).round(1)

    # measured demand trend (if a date column exists)
    if df["year"].notna().any():
        yy = (df.dropna(subset=["year"]).groupby(["drug_label", "year"])["allowed"].sum())
        trend = {}
        for lbl in g["drug_label"]:
            s = yy.get(lbl) if lbl in yy.index.get_level_values(0) else None
            try:
                s = yy.loc[lbl].sort_index()
                trend[lbl] = (round((s.iloc[-1] / s.iloc[-2] - 1) * 100.0, 1)
                              if s.shape[0] >= 2 and s.iloc[-2] > 0 else np.nan)
            except Exception:
                trend[lbl] = np.nan
        g["yoy_demand_pct__measured"] = g["drug_label"].map(trend)
    else:
        g["yoy_demand_pct__measured"] = np.nan

    refd = g["drug_label"].map(lambda l: _ref_lookup(l))
    g["matched_reference_drug"] = refd.map(lambda r: r["alias"] if r else "")
    g["therapeutic_area__ref"] = refd.map(lambda r: r["area"] if r else "")
    g["buy_and_bill__ref"] = refd.map(lambda r: r["bnb"] if r else "")
    g["ira_exposure__ref"] = refd.map(lambda r: r["ira"] if r else "")
    g["biosimilar_risk__ref"] = refd.map(lambda r: r["biosim"] if r else "")
    g["benefit_shift_sc__ref"] = refd.map(lambda r: r["sc"] if r else "")
    g["team_read__ref"] = refd.map(lambda r: r["read"] if r else "")
    g["allowed"] = g["allowed"].round(2)
    return g.sort_values("allowed", ascending=False).head(top_n).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 7. Site-of-care trend  (office -> home shift; measured + Medicare benchmark)
# --------------------------------------------------------------------------- #
def site_of_care_trend(std, site, allowed, year):
    if year.isna().all():
        return pd.DataFrame({"note": ["no usable date column for a site-of-care trend"]})
    df = pd.DataFrame({"site_of_care": site.values, "year": year.values,
                       "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values})
    df = df.dropna(subset=["year"])
    if df.empty:
        return pd.DataFrame({"note": ["no dated rows"]})
    piv = (df.pivot_table(index="year", columns="site_of_care", values="allowed",
                          aggfunc="sum", fill_value=0.0))
    shares = piv.div(piv.sum(axis=1), axis=0) * 100.0
    shares = shares.round(1).reset_index()
    shares.columns.name = None
    # add a plain-language read on the home trend if present
    if "Home" in shares.columns and len(shares) >= 2:
        delta = float(shares["Home"].iloc[-1] - shares["Home"].iloc[0])
        shares["home_share_change_pp"] = np.nan
        shares.loc[shares.index[-1], "home_share_change_pp"] = round(delta, 1)
    return shares


def payer_landscape(std, allowed, drug_cat=None, *, granularity="zip3", top_n=200):
    if "payer" not in std.columns or std["payer"].isna().all():
        return pd.DataFrame({"note": ["no payer column in source"]})
    sub = _submarket(std, granularity)
    df = pd.DataFrame({"submarket": sub.values,
                       "payer": std["payer"].astype("string").fillna("(unknown)").values,
                       "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values})
    rows = []
    for s, g in df.groupby("submarket", sort=False):
        tot = float(g["allowed"].sum())
        by_p = g.groupby("payer")["allowed"].sum().sort_values(ascending=False)
        shares = (by_p / tot * 100.0) if tot > 0 else by_p * 0
        top_share = float(round(shares.iloc[0], 1)) if len(shares) else 0.0
        rows.append({
            "submarket": s, "n_payers": int(by_p.shape[0]),
            "allowed": round(tot, 2),
            "top_payer": by_p.index[0] if len(by_p) else "",
            "top_payer_share_pct": top_share,
            "payer_hhi": _hhi(shares.values),
            "concentration_flag": "Concentrated (single-payer dependent)" if top_share >= 50 else
                                  "Moderate" if top_share >= 30 else "Diversified",
        })
    out = pd.DataFrame(rows).sort_values("allowed", ascending=False).head(top_n)
    return out.reset_index(drop=True)


# curated regulatory reference for the single-state risk slide (TX infusion).
# All reference-sourced; update as opinions/laws move.
_REG_TX = {
    "shield": "TX bars white/brown bagging on infusion-category drugs; AG opinion extends it to out-of-state PBMs.",
    "risk": "If that AG opinion is overturned, narrowed, or challenged, PBMs could circumvent it and white bagging could erode buy-and-bill.",
    "tailwinds": "Expanding reimbursement for professional services and pump-required drugs; removal of physical-presence requirements; gold carding.",
}


def regulatory_scorecard(std, drug_label, allowed):
    df = pd.DataFrame({"drug_label": drug_label.values,
                       "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values})
    g = df.groupby("drug_label", sort=False)["allowed"].sum().reset_index()
    tot = float(g["allowed"].sum()) or 1.0
    g["book_share_pct"] = (g["allowed"] / tot * 100.0).round(1)
    refd = g["drug_label"].map(lambda l: _ref_lookup(l))
    g["sc_self_admin_version__ref"] = refd.map(lambda r: r["sc"] if r else "unknown")
    g["white_bag_forward_risk__ref"] = refd.map(
        lambda r: ("High" if r and "yes" in r["sc"].lower()
                   else "Moderate" if r and "partial" in r["sc"].lower()
                   else "Low" if r else "unknown"))
    g["tx_regulatory_shield__ref"] = _REG_TX["shield"]
    g["shield_at_risk_if_overturned__ref"] = _REG_TX["risk"]
    g["allowed"] = g["allowed"].round(2)
    g = g.sort_values("allowed", ascending=False).reset_index(drop=True)
    note = pd.DataFrame([{
        "drug_label": "TAILWINDS (reference)", "allowed": "", "book_share_pct": "",
        "sc_self_admin_version__ref": "", "white_bag_forward_risk__ref": "",
        "tx_regulatory_shield__ref": _REG_TX["tailwinds"],
        "shield_at_risk_if_overturned__ref": "",
    }])
    return pd.concat([g, note], ignore_index=True)


# --------------------------------------------------------------------------- #
# 10. Growth pockets  (where to build: growing + under-served submarkets)
# --------------------------------------------------------------------------- #
def growth_pockets(std, operator, allowed, year, *, granularity="zip3", top_n=40):
    sub = _submarket(std, granularity)
    df = pd.DataFrame({"submarket": sub.values, "operator": operator.values,
                       "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values,
                       "year": year.values})
    df = df[df["operator"].astype(str).ne("(unattributed)")]
    if df.empty:
        return pd.DataFrame({"note": ["no attributed rows for growth-pocket analysis"]})
    has_year = df["year"].notna().any()
    rows = []
    for s, g in df.groupby("submarket", sort=False):
        tot = float(g["allowed"].sum())
        n_op = int(g["operator"].nunique())
        by_op = g.groupby("operator")["allowed"].sum()
        shares = (by_op / tot * 100.0) if tot > 0 else by_op * 0
        rec = {"submarket": s, "allowed": round(tot, 2), "n_operators": n_op,
               "operator_hhi": _hhi(shares.values)}
        if has_year and g["year"].notna().any():
            yy = g.dropna(subset=["year"]).groupby("year")["allowed"].sum().sort_index()
            rec["yoy_growth_pct"] = (round((yy.iloc[-1] / yy.iloc[-2] - 1) * 100.0, 1)
                                     if yy.shape[0] >= 2 and yy.iloc[-2] > 0 else np.nan)
        rows.append(rec)
    out = pd.DataFrame(rows)
    # whitespace score: reward growth and fragmentation/low density, weight by size.
    size_n = out["allowed"].rank(pct=True)
    frag_n = 1 - out["n_operators"].rank(pct=True)          # fewer operators -> more whitespace
    if "yoy_growth_pct" in out.columns and out["yoy_growth_pct"].notna().any():
        grow_n = out["yoy_growth_pct"].rank(pct=True).fillna(0.5)
        out["build_opportunity_score"] = (100 * (0.45 * grow_n + 0.35 * frag_n + 0.20 * size_n)).round(0)
        out["basis"] = "growth + whitespace + size"
    else:
        out["build_opportunity_score"] = (100 * (0.6 * frag_n + 0.4 * size_n)).round(0)
        out["basis"] = "whitespace + size (no date column for growth)"
    return out.sort_values("build_opportunity_score", ascending=False).head(top_n).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 11. Referral leakage  (BD target list: addressable volume not held by leader)
# --------------------------------------------------------------------------- #
def referral_leakage(std, operator, allowed, *, granularity="zip3", min_allowed=0.0, top_n=300):
    if "referring_npi" not in std.columns:
        return pd.DataFrame({"note": ["no referring NPI column in source"]})
    sub = _submarket(std, granularity)
    spec = (std["referring_specialty"].astype("string")
            if "referring_specialty" in std.columns else pd.Series("", index=std.index))
    df = pd.DataFrame({"submarket": sub.values,
                       "referring_npi": std["referring_npi"].astype("string").values,
                       "specialty": spec.values, "operator": operator.values,
                       "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values})
    df = df[df["referring_npi"].notna() & (df["referring_npi"].astype(str).str.len() > 0)]
    df = df[df["operator"].astype(str).ne("(unattributed)")]
    if df.empty:
        return pd.DataFrame({"note": ["no attributed referral rows"]})
    rows = []
    for ref, g in df.groupby("referring_npi", sort=False):
        tot = float(g["allowed"].sum())
        if tot < min_allowed:
            continue
        by_op = g.groupby("operator")["allowed"].sum().sort_values(ascending=False)
        leader_share = float(round(by_op.iloc[0] / tot * 100.0, 1)) if tot > 0 else 0.0
        leaked = float(round(tot - by_op.iloc[0], 2))   # volume not held by the leader = addressable
        sp = (g["specialty"].mode().iloc[0] if not g["specialty"].mode().empty else "")
        org = ("Health system" if any(k in sp.lower() for k in ("hospital", "health system", "medical center"))
               else "PPM / group" if any(k in sp.lower() for k in ("group", "associates", "clinic"))
               else "Independent / unknown")
        rows.append({
            "referring_npi": ref, "specialty": sp,
            "submarket": g["submarket"].mode().iloc[0] if not g["submarket"].mode().empty else "",
            "org_type_heuristic": org,
            "total_referred_allowed": round(tot, 2),
            "leader_operator": by_op.index[0], "leader_share_pct": leader_share,
            "n_operators_used": int(by_op.shape[0]),
            "addressable_leaked_allowed": leaked,
            "bd_priority": ("High" if leaked >= df.groupby("referring_npi")["allowed"].sum().quantile(0.9) and leader_share < 80
                            else "Medium" if leaked > 0 and leader_share < 90 else "Low"),
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame({"note": ["no referrers cleared the floor"]})
    return out.sort_values("addressable_leaked_allowed", ascending=False).head(top_n).reset_index(drop=True)


# --------------------------------------------------------------------------- #
# 12. Therapeutic adjacency  (whitespace: oncology / cardiology, present vs not)
# --------------------------------------------------------------------------- #
_ADJACENCY = {
    "Oncology": "Big opportunity but a separate business unit (own buy-and-bill, REMS, payer contracts).",
    "Cardiology": "Promising but nascent in home/AIC infusion (e.g. ATTR amyloid agents).",
}


def therapeutic_adjacency(std, drug_label, allowed):
    df = pd.DataFrame({"drug_label": drug_label.values,
                       "allowed": pd.to_numeric(allowed, errors="coerce").fillna(0.0).values})
    df["area"] = df["drug_label"].map(lambda l: (_ref_lookup(l) or {}).get("area", "Unclassified"))
    tot = float(df["allowed"].sum()) or 1.0
    g = (df.groupby("area")["allowed"].agg(["size", "sum"]).reset_index())
    g.columns = ["therapeutic_area", "n_claims", "allowed"]
    g["book_share_pct"] = (g["allowed"] / tot * 100.0).round(1)
    g["status"] = "Core / present"
    g["allowed"] = g["allowed"].round(2)
    g = g.sort_values("allowed", ascending=False).reset_index(drop=True)
    # append adjacency rows the book does not yet meaningfully serve
    present = " ".join(g["therapeutic_area"].astype(str).str.lower())
    add = []
    for area, note in _ADJACENCY.items():
        if area.lower() not in present:
            add.append({"therapeutic_area": f"{area} (adjacency)", "n_claims": 0, "allowed": 0.0,
                        "book_share_pct": 0.0, "status": f"Whitespace — {note}"})
    if add:
        g = pd.concat([g, pd.DataFrame(add)], ignore_index=True)
    return g


# --------------------------------------------------------------------------- #
# 12. Operator case mix  (allowed-per-unit: premium mix vs rate — confirm/deny)
# --------------------------------------------------------------------------- #
def operator_case_mix(std, operator, allowed, units, drug_cat, *, min_units=200.0, top_n=60):
    """THESIS: an operator's higher revenue-per-claim is RICHER DRUG MIX, not
    better unit rates. TEST: decompose each operator's allowed-per-unit into a
    mix effect (its drug composition priced at MARKET unit rates) and a rate
    effect (its actual price vs that mix-expected price). VERDICT per operator.

    This is the case-mix cut from the readout ('does Option Care deliver
    higher-value drugs than the street?') and the rate-vs-mix question behind it.
    Reversals (<0) are excluded. allowed-per-unit is a price-interested volume
    proxy, not a contracted rate.
    """
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0)
    u = pd.to_numeric(units, errors="coerce").fillna(0.0)
    keep = (a >= 0) & (u > 0)
    df = pd.DataFrame({"operator": np.asarray(operator)[keep.values],
                       "drug": np.asarray(drug_cat)[keep.values],
                       "allowed": a[keep].values, "units": u[keep].values})
    df = df[df["operator"].astype(str).ne("(unattributed)")]
    if df.empty:
        return pd.DataFrame({"note": ["no attributed rows with positive units for case-mix"]})
    # market unit price per drug (the neutral benchmark)
    mkt = df.groupby("drug").agg(mkt_allowed=("allowed", "sum"), mkt_units=("units", "sum"))
    mkt["mkt_unit_price"] = mkt["mkt_allowed"] / mkt["mkt_units"].replace(0, np.nan)
    mkt_appu = float(df["allowed"].sum()) / float(df["units"].sum())
    rows = []
    for op, g in df.groupby("operator"):
        tu = float(g["units"].sum())
        ta = float(g["allowed"].sum())
        if tu < min_units:
            continue
        appu = ta / tu
        # mix-expected: this operator's unit mix priced at market unit rates
        by_d = g.groupby("drug").agg(u=("units", "sum"))
        by_d = by_d.join(mkt["mkt_unit_price"])
        mix_expected = float((by_d["u"] * by_d["mkt_unit_price"]).sum()) / tu
        mix_index = mix_expected / mkt_appu if mkt_appu else np.nan       # >1 = richer mix
        rate_index = appu / mix_expected if mix_expected else np.nan       # >1 = pays above market for that mix
        verdict = ("premium mix" if mix_index >= 1.10 and rate_index <= 1.05 else
                   "rate premium" if rate_index >= 1.10 else
                   "commodity mix" if mix_index <= 0.92 else
                   "in line with market")
        rows.append({"operator": op, "allowed": round(ta, 0), "units": round(tu, 0),
                     "allowed_per_unit": round(appu, 2),
                     "market_allowed_per_unit": round(mkt_appu, 2),
                     "mix_index_vs_market": round(mix_index, 3) if pd.notna(mix_index) else np.nan,
                     "rate_index_vs_mix": round(rate_index, 3) if pd.notna(rate_index) else np.nan,
                     "case_mix_verdict": verdict})
    if not rows:
        return pd.DataFrame({"note": [f"no operator cleared min_units={min_units:.0f}"]})
    out = pd.DataFrame(rows).sort_values("allowed", ascending=False).head(top_n).reset_index(drop=True)
    out.attrs["read"] = ("mix_index>1 = richer (higher-value) drug book; rate_index>1 = pays above "
                         "market for the same mix. Across major commercial payers unit rates are "
                         "near-identical for a given drug, so a high allowed-per-unit is almost "
                         "always mix, not rate.")
    return out


# --------------------------------------------------------------------------- #
# 13. Share-shift markets  (top/bottom submarkets by the target's share change)
# --------------------------------------------------------------------------- #
def share_shift_markets(std, operator, allowed, year, *, granularity="zip3", top_n=10, focal=None):
    """For the FOCAL operator (default: largest by allowed — the platform under
    diligence), compute its allowed-weighted share in each submarket in the first
    vs last dated year and rank submarkets by the share-POINT change (pp). Returns
    top_n gainers and top_n decliners. Basis = patient location (submarket grain).
    This is the Richmond +16.6pp share-shift cut.
    """
    if year.isna().all():
        return pd.DataFrame({"note": ["no usable date column for a share-shift view"]})
    sub = _submarket(std, granularity)
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0).clip(lower=0.0)
    df = pd.DataFrame({"submarket": sub.values, "operator": np.asarray(operator),
                       "allowed": a.values, "year": np.asarray(year)}).dropna(subset=["year"])
    df = df[df["operator"].astype(str).ne("(unattributed)")]
    if df.empty:
        return pd.DataFrame({"note": ["no attributed dated rows for share-shift"]})
    yrs = sorted(df["year"].dropna().unique().tolist())
    if len(yrs) < 2:
        return pd.DataFrame({"note": ["need >= 2 dated years for a share shift"]})
    y0, y1 = yrs[0], yrs[-1]
    if focal is None:
        focal = df.groupby("operator")["allowed"].sum().idxmax()

    def _share(year_val):
        gg = df[df["year"] == year_val]
        tot = gg.groupby("submarket")["allowed"].sum()
        foc = gg[gg["operator"] == focal].groupby("submarket")["allowed"].sum()
        sh = (foc / tot * 100.0)
        return sh, tot

    sh0, _ = _share(y0)
    sh1, tot1 = _share(y1)
    allm = sorted(set(sh0.index) | set(sh1.index))
    rows = []
    for m in allm:
        s0 = float(sh0.get(m, 0.0))
        s1 = float(sh1.get(m, 0.0))
        rows.append({"submarket": m, "focal_operator": focal,
                     f"share_{y0}_pct": round(s0, 1), f"share_{y1}_pct": round(s1, 1),
                     "share_change_pp": round(s1 - s0, 1),
                     f"market_allowed_{y1}": round(float(tot1.get(m, 0.0)), 0)})
    full = pd.DataFrame(rows)
    # only rank submarkets with real volume in the latest year
    full = full[full[f"market_allowed_{y1}"] > 0]
    gain = full.sort_values("share_change_pp", ascending=False).head(top_n).copy()
    gain["bucket"] = "Top gainer"
    drop = full.sort_values("share_change_pp", ascending=True).head(top_n).copy()
    drop["bucket"] = "Top decliner"
    out = pd.concat([gain, drop], ignore_index=True)
    out.attrs["basis"] = f"patient-location {granularity}; share = focal allowed / submarket allowed; {y0} vs {y1}; change in pp"
    return out


# --------------------------------------------------------------------------- #
# 14. Growth reconciliation  (correct YoY vs CAGR vs cumulative; the bridge)
# --------------------------------------------------------------------------- #
def growth_reconciliation(std, allowed, year, *, membership_index=None, has_pharmacy=False):
    """Lay out the market/target growth with CAGR, year-over-year, and cumulative
    computed and LABELLED separately so a cumulative figure is never mis-read as
    an annual one (the '-11%' that was really a ~-10% cumulative / ~-5% CAGR).
    membership_index {year:factor} optionally adjusts for covered lives.
    """
    if year.isna().all():
        return pd.DataFrame({"note": ["no usable date column for a growth reconciliation"]})
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0).clip(lower=0.0)
    df = pd.DataFrame({"allowed": a.values, "year": np.asarray(year)}).dropna(subset=["year"])
    if df.empty:
        return pd.DataFrame({"note": ["no dated rows"]})
    mi = {int(k): float(v) for k, v in (membership_index or {}).items()}
    yy = df.groupby("year")["allowed"].sum().sort_index()
    adj = yy / yy.index.map(lambda y: mi.get(int(y), 1.0))
    rows = []
    yrs = list(adj.index)
    for i, y in enumerate(yrs):
        yoy = ((adj.iloc[i] / adj.iloc[i - 1] - 1.0) * 100.0) if i > 0 and adj.iloc[i - 1] > 0 else np.nan
        rows.append({"year": int(y), "allowed_membership_adj": round(float(adj.loc[y]), 0),
                     "yoy_growth_pct": round(yoy, 1) if pd.notna(yoy) else np.nan})
    out = pd.DataFrame(rows)
    n = adj.shape[0]
    cagr = ((adj.iloc[-1] / adj.iloc[0]) ** (1.0 / (n - 1)) - 1.0) * 100.0 if n >= 2 and adj.iloc[0] > 0 else np.nan
    cumulative = (adj.iloc[-1] / adj.iloc[0] - 1.0) * 100.0 if n >= 2 and adj.iloc[0] > 0 else np.nan
    summary = pd.DataFrame([
        {"year": "CAGR (annualised)", "allowed_membership_adj": "",
         "yoy_growth_pct": round(cagr, 1) if pd.notna(cagr) else np.nan},
        {"year": "Cumulative (first→last)", "allowed_membership_adj": "",
         "yoy_growth_pct": round(cumulative, 1) if pd.notna(cumulative) else np.nan},
    ])
    bridge_note = ("CAGR is the per-year rate; cumulative is the full-period change — do not report the "
                   "cumulative as an annual decline. " +
                   ("Pharmacy channel present: see Channel_Reconciliation for the medical-only vs "
                    "medical+pharmacy growth swing. " if has_pharmacy else
                    "Pharmacy channel NOT loaded here: this is medical-only (same-store). Adding the "
                    "pharmacy feed typically lifts the growth materially. ") +
                   ("Membership-adjusted." if mi else
                    "Raw allowed $ (not covered-lives-adjusted); pass membership_index to adjust."))
    summary = pd.concat([summary, pd.DataFrame([{"year": "NOTE", "allowed_membership_adj": "",
                                                 "yoy_growth_pct": bridge_note}])], ignore_index=True)
    return pd.concat([out, summary], ignore_index=True)


# --------------------------------------------------------------------------- #
# orchestrator
# --------------------------------------------------------------------------- #
def dual_channel_drug_reconciliation(std, allowed, year, *, drug_class=None, top_n=50):
    """Per drug class: medical $ vs pharmacy $ vs combined, the pharmacy share, and
    a DOUBLE-COUNT GUARD.

    A dual-benefit molecule (immune globulin, ustekinumab, vedolizumab, ...) can
    bill on BOTH the medical (J-code) feed and the pharmacy (NDC) feed. The deal
    team wants the stitched, total view per molecule — but the combined number is
    only trustworthy if the same therapy is not counted on both sides. For each
    class this counts patients present on BOTH feeds in the SAME year and estimates
    the overlapping dollars (the smaller side per patient-year), flagging classes
    where that overlap is material so it can be netted before it inflates combined.
    Reversals are excluded; class comes from drug_class_rx (consistent across feeds).
    """
    if "_claim_source" not in std.columns:
        return pd.DataFrame({"note": ["no _claim_source — union the feeds first"]})
    if drug_class is None:
        if "drug_class_rx" in std.columns:
            drug_class = std["drug_class_rx"].astype("string").fillna("UNMAPPED_RX")
        else:
            return pd.DataFrame({"note": ["no drug_class_rx — run rx_bridge.resolve_feed first"]})
    src = std["_claim_source"].astype("string").fillna("medical")
    a = pd.to_numeric(allowed, errors="coerce").fillna(0.0).clip(lower=0.0)
    pid = (std["patient_id"].astype("string").fillna("") if "patient_id" in std.columns
           else pd.Series([""] * len(std), index=std.index))
    yr = pd.to_numeric(year, errors="coerce")
    df = pd.DataFrame({"cls": np.asarray(drug_class), "src": src.values, "a": a.values,
                       "pid": pid.values, "yr": yr.values})
    rows = []
    for cls, sub in df.groupby("cls"):
        med_a = float(sub.loc[sub.src == "medical", "a"].sum())
        ph_a = float(sub.loc[sub.src == "pharmacy", "a"].sum())
        comb = med_a + ph_a
        overlap_pat, overlap_alw = 0, 0.0
        if med_a > 0 and ph_a > 0:
            g = (sub[sub.pid != ""].groupby(["pid", "yr", "src"])["a"].sum()
                 .unstack("src", fill_value=0.0))
            mcol = g["medical"] if "medical" in g.columns else pd.Series(0.0, index=g.index)
            pcol = g["pharmacy"] if "pharmacy" in g.columns else pd.Series(0.0, index=g.index)
            both = (mcol > 0) & (pcol > 0)
            if both.any():
                overlap_pat = int(g.index[both].get_level_values("pid").nunique())
                overlap_alw = float(np.minimum(mcol[both], pcol[both]).sum())
        rows.append({
            "drug_class": cls,
            "medical_allowed": round(med_a, 0),
            "pharmacy_allowed": round(ph_a, 0),
            "combined_allowed": round(comb, 0),
            "pharmacy_share_pct": round(100 * ph_a / comb, 1) if comb > 0 else np.nan,
            "both_benefit_patients": overlap_pat,
            "potential_double_count_allowed": round(overlap_alw, 0),
            "double_count_flag": "Y" if (comb > 0 and overlap_alw > 0.02 * comb) else "",
            "combined_net_of_overlap": round(comb - overlap_alw, 0),
        })
    out = (pd.DataFrame(rows).sort_values("combined_allowed", ascending=False)
           .head(top_n).reset_index(drop=True))
    # drop the unmapped bucket to the bottom but keep it visible
    if "drug_class" in out.columns and (out["drug_class"] == "UNMAPPED_RX").any():
        unm = out[out["drug_class"] == "UNMAPPED_RX"]
        out = pd.concat([out[out["drug_class"] != "UNMAPPED_RX"], unm], ignore_index=True)
    tot = {"drug_class": "TOTAL",
           "medical_allowed": round(float(df.loc[df.src == "medical", "a"].sum()), 0),
           "pharmacy_allowed": round(float(df.loc[df.src == "pharmacy", "a"].sum()), 0),
           "combined_allowed": round(float(df["a"].sum()), 0),
           "pharmacy_share_pct": round(100 * df.loc[df.src == "pharmacy", "a"].sum() / df["a"].sum(), 1) if df["a"].sum() > 0 else np.nan,
           "both_benefit_patients": int(out["both_benefit_patients"].sum()) if len(out) else 0,
           "potential_double_count_allowed": round(float(out["potential_double_count_allowed"].sum()), 0) if len(out) else 0,
           "double_count_flag": "", "combined_net_of_overlap": ""}
    out = pd.concat([pd.DataFrame([tot]), out], ignore_index=True)
    out.attrs["note"] = ("Combined stitches the medical (J-code) and pharmacy (NDC) feeds per molecule. "
                         "Where a class is flagged, the same patient appears on both benefits in a year; "
                         "net out potential_double_count_allowed before quoting combined.")
    return out


def build_analytics(std, final_npi, parent_map, drug_ident, *,
                    granularity="zip3", latest_year_only=True, progress=None,
                    taxonomy_of=None, membership_index=None,
                    crosswalk=None, ref_dir=None, rxnorm=None, asp_codes=None,
                    control_total=None, per_drug_control=None,
                    formulary=None, client_gov_npis=None,
                    expected_total=None, coverage_ratio=None,
                    spend_floor=1_000_000.0, asp_crosswalk=None, fda_ndc=None,
                    dme_fee=None, formulary_codes=None, therapy_map_path=None,
                    roster_npis=None, vrdc_suppressed=None,
                    part_d_observed=None, medicaid_observed=None, ma_captured=None,
                    surviving_roster=None, komodo_ffs=None, vrdc_census=None,
                    ma_encounters=None, ma_prices=None, asp_limits=None,
                    ratio_components=None, medicaid_state_ratios=None,
                    management_ma=None,
                    payer_aliases=None, prior_rollup=None):
    """Return an ordered dict of {sheet_name: DataFrame}. Never raises: any cut
    that lacks inputs returns a one-row note frame instead.

    v31 inputs (all optional, all offline-safe when omitted):
      crosswalk / ref_dir / rxnorm  drive common-name grouping so a molecule that
                                    bills under several J-codes is measured once.
      asp_codes                     ASP-priced HCPCS set for NDC->best-J-code.
      control_total / per_drug_control  reconcile the rebuilt total to a known
                                    control total and per-drug targets.
      formulary                     preloaded formulary spec (else seed is read).
      client_gov_npis               client list of government-billing NPIs to
                                    reconcile the panel's channel call against.

    v32 inputs (all optional, all offline-safe when omitted):
      expected_total                management / Komodo expected total, for the
                                    suppression ceiling report and deficit diagnosis.
      coverage_ratio / part_d_observed / medicaid_observed / ma_captured
                                    Komodo coverage-ratio gross-up panel inputs.
      spend_floor                   drug-grain floor for the frozen universe.
      asp_crosswalk / fda_ndc / dme_fee   top-down crosswalk reference sources.
      formulary_codes               formulary code snapshot (path or {hcpcs,ndc})
                                    for the dual-flag any-match membership.
      therapy_map_path              client three-letter therapy-code mapping.
      roster_npis                   finder-list NPIs, for enrollment JV flags.
      vrdc_suppressed               a VRDC export (path or DataFrame) with
                                    suppressed cells, for suppression reconciliation.
    """
    progress = progress or (lambda *_: None)
    out = {}
    try:
        if std is None or len(std) == 0:
            return {"Analytics_Note": pd.DataFrame({"note": ["empty input frame"]})}

        allowed = (std["allowed_amt"] if "allowed_amt" in std.columns
                   else pd.Series(0.0, index=std.index))
        units = std["units"] if "units" in std.columns else pd.Series(0.0, index=std.index)
        year = _year(std)

        # final billing NPI aligned positionally to std (rows are preserved 1:1)
        if final_npi is None:
            fn = std["billing_npi"] if "billing_npi" in std.columns else pd.Series(pd.NA, index=std.index)
        else:
            fn = pd.Series(np.asarray(final_npi), index=std.index)
        operator = _operator_series(fn, parent_map)
        drug_label, drug_cat = _build_drug_series(std, drug_ident)

        # v31: common-name grouping. A molecule that bills under several J-codes
        # (Stelara J3357/J3358/J3590, IVIG across ~15 brand codes) is collapsed to
        # one label so the per-drug cuts stop capturing only the first code. Falls
        # back to the raw per-row label on any failure, so nothing regresses.
        std_named = std
        grouped_label = drug_label
        try:
            from . import common_name as _cn
            _xwalk = crosswalk
            if _xwalk is None:
                from . import rx_bridge as _rxb
                _xwalk = _rxb.load_crosswalk(ref_dir)
            std_named = _cn.assign_common_name(
                std, crosswalk=_xwalk, drug_ident=drug_ident,
                ref_dir=ref_dir, rxnorm=rxnorm, progress=progress)
            grouped_label = _cn.grouped_label_series(std_named, fallback_label=drug_label)
        except Exception as _e:                                # pragma: no cover
            out["CommonName_Note"] = pd.DataFrame(
                {"note": [f"common-name grouping skipped: {type(_e).__name__}: {_e}"]})

        # v29: site-of-care reclassification (home-infusion codes + infusion-clinic
        # taxonomy + in-clinic admin codes + learned office->AIC propensity).
        # Replaces the POS-only bucket so AIC stops hiding inside "office" and AIS
        # is broken out from home. Falls back gracefully when signals are absent.
        try:
            from . import site_of_care as _soc
            _sc, _soc_diag = _soc.reclassify(
                std, taxonomy_of=taxonomy_of, drug_label=drug_label)
            site = pd.Series(_sc["site_reclassified"].values, index=std.index)
            out["SiteOfCare_Reclassification"] = _soc.site_reclassification_summary(std, _sc, _soc_diag)
            out["SiteOfCare_ProofPoint"] = _soc.site_proof_point(std, _sc, drug_label)
        except Exception as _e:                                # pragma: no cover
            site = (_site_of_care(std["pos"]) if "pos" in std.columns
                    else pd.Series("Other / unknown", index=std.index))
            out["SiteOfCare_Reclassification"] = pd.DataFrame(
                {"note": [f"site reclassification skipped: {type(_e).__name__}: {_e}"]})

        progress("Referral concentration", 0.1)
        out["Referral_Concentration"] = referral_concentration(std, operator, allowed, top_n=400)
        out["Referral_Concentration_IVIG"] = referral_concentration(
            std, operator, allowed, drug_cat=drug_cat, drug_class_filter="immune globulin")

        progress("Submarket landscape", 0.3)
        out["Submarket_Landscape"] = submarket_landscape(
            std, drug_cat, site, allowed, units, year,
            granularity=granularity, latest_year_only=latest_year_only)

        progress("Submarket saturation", 0.5)
        out["Submarket_Saturation"] = submarket_saturation(
            std, operator, allowed, year, granularity=granularity)

        progress("Referral target map", 0.7)
        out["Referral_Target_Map"] = referral_target_map(
            std, operator, allowed, granularity=granularity)

        progress("Benefit-shift exposure", 0.85)
        out["Benefit_Shift_Exposure"] = benefit_shift_exposure(std, grouped_label, allowed)

        progress("Site-of-care trend", 0.88)
        out["SiteOfCare_Trend"] = site_of_care_trend(std, site, allowed, year)

        progress("Payer landscape", 0.91)
        out["Payer_Landscape"] = payer_landscape(std, allowed, granularity=granularity)

        progress("Regulatory scorecard", 0.93)
        out["Regulatory_Scorecard"] = regulatory_scorecard(std, grouped_label, allowed)

        progress("Formulary scorecard", 0.95)
        out["Formulary_Scorecard"] = formulary_scorecard(std, grouped_label, allowed, year)

        progress("Growth pockets", 0.96)
        out["Growth_Pockets"] = growth_pockets(std, operator, allowed, year, granularity=granularity)

        progress("Referral leakage", 0.97)
        out["Referral_Leakage"] = referral_leakage(std, operator, allowed, granularity=granularity)

        progress("Therapeutic adjacency", 0.98)
        out["Therapeutic_Adjacency"] = therapeutic_adjacency(std, grouped_label, allowed)

        # v29: case mix (allowed-per-unit; mix vs rate), share-shift markets,
        # and a correctly-labelled growth reconciliation.
        progress("Operator case mix", 0.985)
        out["Operator_Case_Mix"] = operator_case_mix(std, operator, allowed, units, drug_cat)

        progress("Share-shift markets", 0.99)
        out["Share_Shift_Markets"] = share_shift_markets(
            std, operator, allowed, year, granularity=granularity)

        _has_pharm = ("_claim_source" in std.columns and
                      (std["_claim_source"].astype("string") == "pharmacy").any())
        progress("Growth reconciliation", 0.992)
        out["Growth_Reconciliation"] = growth_reconciliation(
            std, allowed, year, membership_index=membership_index, has_pharmacy=_has_pharm)

        # v29: medical vs pharmacy channel reconciliation (only when a pharmacy
        # feed was unioned upstream). The medical-only decline that flips when the
        # pharmacy channel is added back is the headline here.
        if _has_pharm:
            try:
                from . import pharmacy_feed as _pf
                out["Channel_Reconciliation"] = _pf.channel_reconciliation(
                    std, operator, year, membership_index=membership_index)
            except Exception as _e:                            # pragma: no cover
                out["Channel_Reconciliation"] = pd.DataFrame(
                    {"note": [f"channel reconciliation skipped: {type(_e).__name__}: {_e}"]})
            # per-molecule medical vs pharmacy stitch + double-count guard
            try:
                progress("Dual-channel drug reconciliation", 0.993)
                out["DualChannel_Drug_Reconciliation"] = dual_channel_drug_reconciliation(
                    std, allowed, year)
            except Exception as _e:                            # pragma: no cover
                out["DualChannel_Drug_Reconciliation"] = pd.DataFrame(
                    {"note": [f"dual-channel reconciliation skipped: {type(_e).__name__}: {_e}"]})

        # ------------------------------------------------------------------ #
        # v31 tabs. Each is self-contained and offline-safe: it either emits a
        # result or a one-row note, and never blocks the sheets above.
        # ------------------------------------------------------------------ #
        _split_undercount = 0.0
        try:
            from . import common_name as _cn
            progress("Common-name rollup", 0.994)
            _roll = _cn.common_name_rollup(std_named, allowed=allowed, units=units)
            out["Common_Name_Rollup"] = _roll
            if "undercount_if_first_code_only" in getattr(_roll, "columns", []):
                _split_undercount = float(pd.to_numeric(
                    _roll["undercount_if_first_code_only"], errors="coerce").fillna(0.0).sum())
        except Exception as _e:                                # pragma: no cover
            out["Common_Name_Rollup"] = pd.DataFrame(
                {"note": [f"common-name rollup skipped: {type(_e).__name__}: {_e}"]})

        try:
            from . import ndc_jcode as _nj
            progress("NDC best J-code", 0.995)
            _res = _nj.resolve_best_jcode(
                std_named, crosswalk=crosswalk, ref_dir=ref_dir,
                rxnorm=rxnorm, asp_codes=asp_codes, progress=progress)
            out["NDC_JCode_BestMatch"] = _nj.bestmatch_audit(_res, allowed, only_multi=True)
            out["NDC_NoJCode_KeptAsNDC"] = _nj.no_jcode_audit(_res, allowed)
        except Exception as _e:                                # pragma: no cover
            out["NDC_JCode_BestMatch"] = pd.DataFrame(
                {"note": [f"NDC best-J-code skipped: {type(_e).__name__}: {_e}"]})

        try:
            from . import formulary as _fm
            progress("Formulary gate", 0.996)
            _spec = formulary if formulary is not None else _fm.load_formulary(ref_dir)
            _tagged = _fm.assign_formulary_disposition(std_named, _spec, ref_dir)
            out["Formulary_Gate"] = _fm.formulary_gate_summary(_tagged, allowed)
            out["Formulary_Exclusions_Review"] = _fm.formulary_exclusions_review(_tagged, allowed)
        except Exception as _e:                                # pragma: no cover
            out["Formulary_Gate"] = pd.DataFrame(
                {"note": [f"formulary gate skipped: {type(_e).__name__}: {_e}"]})

        _gov_channel_allowed = 0.0
        try:
            from . import npi_channel as _nc
            progress("NPI channel", 0.997)
            _chan = _nc.classify_npi_channels(std, allowed=allowed, taxonomy_of=taxonomy_of)
            out["NPI_Channel_Classification"] = _chan
            if "is_government_billing" in getattr(_chan, "columns", []):
                _gov_channel_allowed = float(pd.to_numeric(
                    _chan.loc[_chan["is_government_billing"], "allowed"],
                    errors="coerce").fillna(0.0).sum())
            out["NPI_Government_Reconciliation"] = _nc.government_reconciliation(_chan, client_gov_npis)
        except Exception as _e:                                # pragma: no cover
            out["NPI_Channel_Classification"] = pd.DataFrame(
                {"note": [f"NPI channel skipped: {type(_e).__name__}: {_e}"]})

        try:
            from . import control_total as _ct
            progress("Control total", 0.998)
            _panel_total = float(pd.to_numeric(allowed, errors="coerce").fillna(0.0).sum())
            # Clean statement: the full captured panel vs the control total. The
            # split-code and government-channel dollars already sit inside the panel,
            # so they are NOT added here; they are shown as naive-rebuild exposure.
            out["Control_Total_Reconciliation"] = _ct.reconcile_control_total(
                captured=allowed, control_total=control_total,
                recovery_buckets=None, entity_label="target entity")
            out["Control_Total_Exposure"] = _ct.exposure_summary(
                panel_total=_panel_total,
                split_code_undercount=_split_undercount,
                government_channel=_gov_channel_allowed,
                control_total=control_total)
            out["Capture_By_Drug"] = _ct.capture_by_drug(
                std_named, allowed=allowed, per_drug_control=per_drug_control, units=units)
        except Exception as _e:                                # pragma: no cover
            out["Control_Total_Reconciliation"] = pd.DataFrame(
                {"note": [f"control total skipped: {type(_e).__name__}: {_e}"]})

        # ------------------------------------------------------------------ #
        # v32: the Onyx / Project Infusion comprehensive-report fixes. Built on
        # top of v31 (the grouper, formulary gate, channel call, control total),
        # NOT repeating it. Every block is offline-safe: with no new input it
        # builds from the shipped seed or emits a one-row note.
        # ------------------------------------------------------------------ #

        # (v32-1) CMS suppression ceiling: suppression hides distribution, not
        # volume. Reconcile a VRDC export against its unsuppressed aggregates and
        # separate redistributable mass from the irreducible upstream deficit.
        try:
            from . import vrdc_suppression as _supp
            _vs = vrdc_suppressed
            if isinstance(_vs, str):
                try:
                    _vs = pd.read_csv(_vs)
                except Exception:
                    _vs = None
            if _vs is not None and hasattr(_vs, "columns") and "allowed" in _vs.columns:
                _sc = [c for c in ("prov", "provider", "npi") if c in _vs.columns][:1] or [_vs.columns[0]]
                _tc = "row_total" if "row_total" in _vs.columns else None
                _cc = "benes" if "benes" in _vs.columns else None
                out["VRDC_Suppression_Reconciliation"] = _supp.reconcile_scope(
                    _vs, value_col="allowed", scope_cols=_sc, total_col=_tc, count_col=_cc)
                _recon_total = float(pd.to_numeric(
                    out["VRDC_Suppression_Reconciliation"].get("aggregate_total_ceiling", pd.Series(dtype=float)),
                    errors="coerce").fillna(0).sum())
                _vis = float(pd.to_numeric(
                    out["VRDC_Suppression_Reconciliation"].get("visible_sum", pd.Series(dtype=float)),
                    errors="coerce").fillna(0).sum())
                _resid = float(pd.to_numeric(
                    out["VRDC_Suppression_Reconciliation"].get("suppressed_residual", pd.Series(dtype=float)),
                    errors="coerce").fillna(0).sum())
                out["VRDC_Ceiling_Report"] = _supp.ceiling_report(
                    reconstructed_total=_recon_total, external_expected=expected_total,
                    visible_sum=_vis, suppressed_residual=_resid, entity_label="target")
            else:
                out["VRDC_Suppression_Reconciliation"] = pd.DataFrame({"note": [
                    "no VRDC suppressed export supplied; pass vrdc_suppressed (a frame/CSV with an "
                    "'allowed' column, optional 'row_total' and 'benes') to reconcile against the "
                    "unsuppressed aggregate ceiling"]})
        except Exception as _e:                                # pragma: no cover
            out["VRDC_Suppression_Reconciliation"] = pd.DataFrame(
                {"note": [f"suppression reconciliation skipped: {type(_e).__name__}: {_e}"]})

        # (v32-2) deficit root cause: score the four hypotheses and run the cheap
        # claim-channel coverage test that says whether the mass was ever in the
        # medical files at all.
        try:
            from . import deficit_diagnostics as _dd
            out["ClaimScope_Coverage"] = _dd.claim_scope_coverage(
                std, allowed=allowed, ref_dir=ref_dir, pull_channels=("PARTB_MEDICAL",))
            _missed = float(out["ClaimScope_Coverage"].attrs.get("missed_share_allowed", 0.0)) \
                if hasattr(out["ClaimScope_Coverage"], "attrs") else None
            if expected_total is not None:
                _captured = float(pd.to_numeric(allowed, errors="coerce").fillna(0.0).sum())
                out["Deficit_Diagnosis"] = _dd.diagnose_deficit(
                    captured_total=_captured, expected_total=expected_total,
                    claim_scope_deficit=_missed, entity_label="target")
            else:
                out["Deficit_Diagnosis"] = pd.DataFrame({"note": [
                    "supply expected_total (management/Komodo) to attribute the shortfall across "
                    "entity roster / claim-type scope / book structure / filter logic"]})
        except Exception as _e:                                # pragma: no cover
            out["ClaimScope_Coverage"] = pd.DataFrame(
                {"note": [f"claim-scope coverage skipped: {type(_e).__name__}: {_e}"]})

        # (v32-3) top-down crosswalk + dual-flag membership + NDC gap targets. The
        # complete code array per molecule that the bottom-up build lacked.
        try:
            from . import crosswalk_builder as _xb
            _cw = _xb.build_crosswalk(asp_ndc_hcpcs=asp_crosswalk, fda_ndc=fda_ndc,
                                      dme_fee=dme_fee, seed_ref_dir=ref_dir, use_example=True)
            out["Crosswalk_Coverage"] = _xb.crosswalk_coverage(_cw)
            _fc = formulary_codes
            if isinstance(_fc, str):
                _fc = _xb.load_formulary_codes(_fc)
            if isinstance(_fc, dict):
                _mem = _xb.any_match_membership(std_named, _cw, _fc)
                out["DualFlag_Membership"] = (
                    _mem.groupby(["molecule_key"], dropna=False)
                    .agg(rows=("capture_in", "size"),
                         capture_in=("capture_in", "max"),
                         code_evidence=("code_evidence", "max"),
                         noc_needs_ndc=("noc_needs_ndc", "max")).reset_index())
                out["NDC_Gap_Targets"] = _xb.ndc_gap_targets(std_named, _cw, allowed=allowed)
            else:
                out["DualFlag_Membership"] = pd.DataFrame({"note": [
                    "supply formulary_codes (path or {hcpcs,ndc}) to run the dual-flag any-match "
                    "membership; the top-down crosswalk coverage above is built regardless"]})
        except Exception as _e:                                # pragma: no cover
            out["Crosswalk_Coverage"] = pd.DataFrame(
                {"note": [f"crosswalk builder skipped: {type(_e).__name__}: {_e}"]})

        # (v32-4) granular enrollment mapping: which entities are enrolled where,
        # which CMS files each implies, and the JV / missing-entity flags.
        try:
            from . import npi_enrollment as _en
            out["NPI_Enrollment_Map"] = _en.map_enrollment_channels(
                std, allowed=allowed, taxonomy_of=taxonomy_of, ref_dir=ref_dir,
                roster_npis=roster_npis)
            out["Enrollment_File_Coverage"] = _en.enrollment_file_coverage(
                out["NPI_Enrollment_Map"], pull_files=("Carrier / Outpatient",))
        except Exception as _e:                                # pragma: no cover
            out["NPI_Enrollment_Map"] = pd.DataFrame(
                {"note": [f"enrollment mapping skipped: {type(_e).__name__}: {_e}"]})

        # (v32-5) frozen universe + spend floor + documented exclusion register.
        try:
            from . import universe as _uni
            _u = _uni.define_universe(std_named, allowed=allowed, floor=spend_floor,
                                      ref_dir=ref_dir)
            out["Drug_Universe"] = _u
            out["Excluded_Tail"] = _uni.excluded_tail_summary(_u)
            out["Exclusion_Register"] = _uni.exclusion_register(_u)
        except Exception as _e:                                # pragma: no cover
            out["Drug_Universe"] = pd.DataFrame(
                {"note": [f"universe definition skipped: {type(_e).__name__}: {_e}"]})

        # (v32-6) therapy-area mapping + the 22% acute-share band check + straddle
        # review + chronic IVIG-vs-rare/orphan subdivision.
        try:
            from . import therapy_area as _ta
            _tag = _ta.assign_therapy_area(std_named, ref_dir=ref_dir,
                                           therapy_map=_ta.load_therapy_map(ref_dir, therapy_map_path))
            out["TherapyArea_AcuteShare"] = _ta.acute_share_check(_tag, allowed=allowed)
            out["TherapyArea_StraddleReview"] = _ta.dominant_therapy_review(_tag, allowed=allowed)
            out["Chronic_Subdivision"] = _ta.chronic_subdivision(_tag, allowed=allowed)
        except Exception as _e:                                # pragma: no cover
            out["TherapyArea_AcuteShare"] = pd.DataFrame(
                {"note": [f"therapy-area mapping skipped: {type(_e).__name__}: {_e}"]})

        # (v32-7) coverage-ratio gross-up + sensitivity. Only meaningful with a
        # ratio; otherwise a one-row note.
        try:
            from . import coverage_grossup as _gu
            if coverage_ratio is not None and ma_captured is not None:
                out["Coverage_Grossup"] = _gu.grossup_panel(
                    part_d_observed=part_d_observed, medicaid_observed=medicaid_observed,
                    ma_captured=ma_captured, ma_coverage_ratio=coverage_ratio)
                out["Grossup_Sensitivity"] = _gu.grossup_sensitivity(
                    captured=ma_captured, coverage_ratio=coverage_ratio, delta_points=2.0)
            else:
                out["Coverage_Grossup"] = pd.DataFrame({"note": [
                    "supply coverage_ratio and ma_captured (optionally part_d_observed / "
                    "medicaid_observed) to build the gross-up panel and its sensitivity"]})
        except Exception as _e:                                # pragma: no cover
            out["Coverage_Grossup"] = pd.DataFrame(
                {"note": [f"coverage gross-up skipped: {type(_e).__name__}: {_e}"]})

        # ------------------------------------------------------------------ #
        # v33: close the loop, pin the ratio, protect the fallback. Built on
        # v31 and v32, not repeating them. Offline-safe throughout.
        # ------------------------------------------------------------------ #
        _filter_deficit = None
        _entity_leak = None
        _book_structure = None

        # (v33-a) filter attribution, auto-derived: the "worth an hour" unfiltered
        # recompute, run on every build from the dual-flag masks.
        try:
            from . import deficit_diagnostics as _dd33
            from . import crosswalk_builder as _xb33
            _fc33 = formulary_codes
            if isinstance(_fc33, str):
                _fc33 = _xb33.load_formulary_codes(_fc33)
            if isinstance(_fc33, dict):
                _cw33 = _xb33.build_crosswalk(asp_ndc_hcpcs=asp_crosswalk, fda_ndc=fda_ndc,
                                              dme_fee=dme_fee, seed_ref_dir=ref_dir,
                                              use_example=True)
                _mem33 = _xb33.any_match_membership(std_named, _cw33, _fc33)
                out["Filter_Attribution"] = _dd33.filter_attribution_test(
                    std_named, allowed=allowed,
                    code_level_mask=_mem33["code_evidence"],
                    drug_level_mask=_mem33["capture_in"])
                _fa = out["Filter_Attribution"]
                if "basis" in _fa.columns:
                    _sel = _fa[_fa["basis"].str.contains("self-inflicted", na=False)]
                    if len(_sel):
                        _filter_deficit = float(_sel["allowed"].iloc[0])
                # (v33-b) trend-bend audit + flicker on the same masks
                from . import trend_integrity as _ti
                out["Trend_Bend_Audit"] = _ti.inclusion_share_by_period(
                    std_named, allowed=allowed, year=year,
                    code_mask=_mem33["code_evidence"], drug_mask=_mem33["capture_in"])
                out["Trend_Bend_Decomposition"] = _ti.trend_bend_decomposition(
                    std_named, allowed=allowed, year=year,
                    code_mask=_mem33["code_evidence"], drug_mask=_mem33["capture_in"])
                out["Inclusion_Flicker_Events"] = _ti.flicker_events(std_named, year=year)
                # (v33-c) NDC attribution: the Inflectra pass, worked
                out["NDC_Attribution_Audit"] = _xb33.ndc_attribution(
                    std_named, _cw33, allowed=allowed)
            else:
                out["Filter_Attribution"] = pd.DataFrame({"note": [
                    "supply formulary_codes to auto-derive the code-level and drug-level masks "
                    "and run the unfiltered recompute (the one-hour test) on every build"]})
                from . import trend_integrity as _ti
                out["Inclusion_Flicker_Events"] = _ti.flicker_events(std_named, year=year)
        except Exception as _e:                                # pragma: no cover
            out["Filter_Attribution"] = pd.DataFrame(
                {"note": [f"filter attribution skipped: {type(_e).__name__}: {_e}"]})

        # (v33-d) cross-source harness on the claim-source tag when present
        try:
            from . import cross_source as _cs
            from . import universe as _uni33
            if "_claim_source" in std_named.columns and std_named["_claim_source"].nunique() > 1:
                _srcs = {str(s).upper(): g for s, g in std_named.groupby("_claim_source")}
                _u33 = _uni33.define_universe(std_named, allowed=allowed,
                                              floor=spend_floor, ref_dir=ref_dir)
                _keys33 = _uni33.frozen_universe_keys(_u33)
                _mx = _cs.cross_source_matrix(_srcs, universe_keys=_keys33)
                out["CrossSource_Molecule_Matrix"] = _mx
                out["Scope_Parity_Check"] = _cs.scope_parity_check(_mx)
            else:
                out["CrossSource_Molecule_Matrix"] = pd.DataFrame({"note": [
                    "single-source panel; add the pharmacy feed or a second extract and the "
                    "frozen universe is enforced across sources here"]})
        except Exception as _e:                                # pragma: no cover
            out["CrossSource_Molecule_Matrix"] = pd.DataFrame(
                {"note": [f"cross-source harness skipped: {type(_e).__name__}: {_e}"]})

        # (v33-e) roster forensics: migration, artificial growth, leakage estimate
        try:
            from . import roster_forensics as _rf
            if roster_npis:
                out["Legacy_NPI_Migration"] = _rf.legacy_npi_migration(
                    std, allowed=allowed, year=year, full_roster=roster_npis,
                    surviving_roster=(surviving_roster or roster_npis))
                out["Artificial_Growth_Test"] = _rf.artificial_growth_test(
                    out["Legacy_NPI_Migration"])
                _lk = _rf.entity_leakage_estimate(std, allowed=allowed,
                                                  full_roster=roster_npis)
                out["Entity_Leakage_Estimate"] = _lk
                _entity_leak = (_lk.attrs.get("entity_leakage_dollars")
                                if hasattr(_lk, "attrs") else None)
            else:
                out["Legacy_NPI_Migration"] = pd.DataFrame({"note": [
                    "supply roster_npis (full finder list, and optionally surviving_roster) to "
                    "quantify migration inflation and the entity-leakage ceiling"]})
        except Exception as _e:                                # pragma: no cover
            out["Legacy_NPI_Migration"] = pd.DataFrame(
                {"note": [f"roster forensics skipped: {type(_e).__name__}: {_e}"]})

        # (v33-f) VRDC-as-calibration: per-drug FFS coverage vs the census
        try:
            from . import calibration as _cal
            out["Komodo_FFS_Calibration"] = _cal.komodo_ffs_calibration(
                komodo_ffs, vrdc_census, blended_stated=coverage_ratio)
        except Exception as _e:                                # pragma: no cover
            out["Komodo_FFS_Calibration"] = pd.DataFrame(
                {"note": [f"calibration skipped: {type(_e).__name__}: {_e}"]})

        # (v33-g) MA proxy + triangulation; the median leg feeds book structure
        try:
            from . import ma_proxy as _mp
            if ma_encounters is not None and ma_prices is None:
                _px = pd.DataFrame({"note": [
                    "ma_encounters supplied without ma_prices; asp_limits is hcpcs-grain "
                    "and cannot price drug-grain encounters, so nothing was priced. "
                    "Supply --ma-prices at the drug grain."]})
            else:
                _px = _mp.ma_proxy_estimate(ma_encounters, ma_prices)
            out["MA_Proxy_Estimate"] = _px
            _ratio_est = None
            if coverage_ratio and ma_captured and float(coverage_ratio) > 0:
                _ratio_est = float(ma_captured) / float(coverage_ratio)
            _proxy_tot = (_px.attrs.get("proxy_total") if hasattr(_px, "attrs") else None)
            if _ratio_est or _proxy_tot or management_ma:
                _tri = _mp.ma_triangulation(ratio_estimate=_ratio_est,
                                            proxy_estimate=_proxy_tot,
                                            management_estimate=management_ma)
                out["MA_Triangulation"] = _tri
                _book_structure = (_tri.attrs.get("book_structure_estimate")
                                   if hasattr(_tri, "attrs") else None)
        except Exception as _e:                                # pragma: no cover
            out["MA_Proxy_Estimate"] = pd.DataFrame(
                {"note": [f"MA proxy skipped: {type(_e).__name__}: {_e}"]})

        # (v33-h) gross-up hardening: decomposition, mix parity, state Medicaid
        try:
            from . import coverage_grossup as _gu33
            if ratio_components is not None and coverage_ratio is not None:
                out["Ratio_Decomposition"] = _gu33.ratio_decomposition(
                    ratio_components, stated_blend=coverage_ratio)
            if komodo_ffs is not None and vrdc_census is not None:
                out["Mix_Parity"] = _gu33.mix_parity(komodo_ffs, vrdc_census)
            if medicaid_state_ratios is not None:
                out["Medicaid_State_Grossup"] = _gu33.medicaid_state_grossup(
                    medicaid_state_ratios)
        except Exception as _e:                                # pragma: no cover
            out["Ratio_Decomposition"] = pd.DataFrame(
                {"note": [f"gross-up hardening skipped: {type(_e).__name__}: {_e}"]})

        # (v33-i) the surviving market view: biosimilar adoption, ASP position,
        # floor sensitivity. Adoption and floor run offline always.
        try:
            from . import market_view as _mv
            out["Biosimilar_Adoption"] = _mv.biosimilar_adoption(
                std_named, allowed=allowed, year=year)
            if asp_limits is not None:
                out["ASP_Rate_Position"] = _mv.asp_rate_position(
                    std, allowed=allowed, units=units, asp_limits=asp_limits)
            out["Floor_Sensitivity"] = _mv.floor_sensitivity(
                std_named, allowed=allowed, base_floor=spend_floor, ref_dir=ref_dir)
        except Exception as _e:                                # pragma: no cover
            out["Biosimilar_Adoption"] = pd.DataFrame(
                {"note": [f"market view skipped: {type(_e).__name__}: {_e}"]})

        # (v33-j) the deficit diagnosis, self-fed: overwrite the v32 tab with the
        # fuller attribution now that filter / leakage / book-structure signals
        # exist. No hand-fed numbers.
        try:
            from . import deficit_diagnostics as _ddf
            if expected_total is not None:
                _captured33 = float(pd.to_numeric(allowed, errors="coerce").fillna(0.0).sum())
                _missed33 = None
                _csc = out.get("ClaimScope_Coverage")
                if _csc is not None and hasattr(_csc, "attrs"):
                    _missed33 = _csc.attrs.get("missed_share_allowed")
                out["Deficit_Diagnosis"] = _ddf.diagnose_deficit(
                    captured_total=_captured33, expected_total=expected_total,
                    entity_leakage=_entity_leak, claim_scope_deficit=_missed33,
                    book_structure_deficit=_book_structure,
                    filter_deficit=_filter_deficit, entity_label="target")
        except Exception as _e:                                # pragma: no cover
            pass
        # ------------------------------------------------------------------ #
        # v34: anticipate the next meeting. Integrity screens (netting, units,
        # runout), growth anatomy, payer normalization, concentration, modifier
        # economics, run-over-run restatement. All offline; all report-only.
        # ------------------------------------------------------------------ #
        try:
            from . import dedup as _dd34
            out["Netting_Audit"] = _dd34.netting_audit(std, allowed=allowed, units=units)
        except Exception as _e:                                # pragma: no cover
            out["Netting_Audit"] = pd.DataFrame(
                {"note": [f"netting audit skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import unit_integrity as _ui34
            out["Unit_Integrity_Outliers"] = _ui34.rate_outlier_screen(
                std, allowed=allowed, units=units)
            if asp_limits is not None:
                out["Unit_Basis_Check"] = _ui34.unit_basis_check(
                    std, allowed=allowed, units=units, asp_limits=asp_limits)
        except Exception as _e:                                # pragma: no cover
            out["Unit_Integrity_Outliers"] = pd.DataFrame(
                {"note": [f"unit integrity skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import runout as _ro34
            _cr34 = _ro34.completeness_report(std, allowed=allowed)
            out["Runout_Completeness"] = _cr34
            out["Restated_Trend"] = _ro34.restated_trend(_cr34)
        except Exception as _e:                                # pragma: no cover
            out["Runout_Completeness"] = pd.DataFrame(
                {"note": [f"runout check skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import growth_decomposition as _gd34
            out["Growth_PriceVolumeMix"] = _gd34.price_volume_mix(
                std_named, allowed=allowed, units=units, year=year)
        except Exception as _e:                                # pragma: no cover
            out["Growth_PriceVolumeMix"] = pd.DataFrame(
                {"note": [f"growth decomposition skipped: {type(_e).__name__}: {_e}"]})
        _parent34 = None
        try:
            from . import payer_normalizer as _pn34
            _au34 = _pn34.normalize_payers(std, allowed=allowed,
                                           aliases=payer_aliases, ref_dir=ref_dir)
            out["Payer_Normalization_Audit"] = _au34
            if "parent_series" in getattr(_au34, "attrs", {}):
                _parent34 = _au34.attrs["parent_series"]
                out["Payer_Mix_Normalized"] = _pn34.payer_mix_normalized(
                    std, allowed=allowed, aliases=payer_aliases, ref_dir=ref_dir)
        except Exception as _e:                                # pragma: no cover
            out["Payer_Normalization_Audit"] = pd.DataFrame(
                {"note": [f"payer normalization skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import concentration as _cc34
            out["Concentration_HHI"] = _cc34.concentration_table(
                std_named, allowed=allowed, payer_parent=_parent34)
            if taxonomy_of:
                out["Prescriber_Taxonomy_Mix"] = _cc34.prescriber_taxonomy_mix(
                    std, allowed=allowed, taxonomy_of=taxonomy_of)
        except Exception as _e:                                # pragma: no cover
            out["Concentration_HHI"] = pd.DataFrame(
                {"note": [f"concentration skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import modifier_economics as _me34
            out["Modifier_Economics"] = _me34.modifier_economics(std, allowed=allowed)
        except Exception as _e:                                # pragma: no cover
            out["Modifier_Economics"] = pd.DataFrame(
                {"note": [f"modifier economics skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import restatement as _rs34
            out["Restatement_Diff"] = _rs34.restatement_diff(
                prior_rollup, std_named, allowed=allowed)
        except Exception as _e:                                # pragma: no cover
            out["Restatement_Diff"] = pd.DataFrame(
                {"note": [f"restatement diff skipped: {type(_e).__name__}: {_e}"]})
        # ------------------------------------------------------------------ #
        # v35: the deep-clean report layer. Scans only; apply-mode runs in the
        # pipeline behind --deep-clean. All offline, all always-on.
        # ------------------------------------------------------------------ #
        try:
            from . import clean_pipeline as _cp35
            from . import imputation_options as _io35
            _plan35 = [("text_hygiene", "report"), ("field_validation", "report"),
                       ("row_consistency", "report"), ("distribution", "report")]
            _, _, _fnd35 = _cp35.run_cleaning(std, plan=_plan35)
            for _k35, _tab35 in (("Text_Hygiene", "Text_Hygiene"),
                                 ("Field_Validation", "Field_Validation"),
                                 ("Row_Consistency", "Row_Consistency"),
                                 ("Benford_Screen", "Benford_Screen"),
                                 ("Rounding_Pathology", "Rounding_Pathology")):
                if _k35 in _fnd35:
                    out[_tab35] = _fnd35[_k35]
            out["DQ_Scorecard"] = _cp35.dq_scorecard(std)
            _imp35 = []
            for _f35 in ("units", "state", "drug_name"):
                _c35 = _io35.compare_strategies(std, _f35, allowed=allowed)
                if "strategy" in getattr(_c35, "columns", []):
                    _c35 = _c35.copy()
                    _c35.insert(0, "field", _f35)
                    _imp35.append(_c35)
            out["Imputation_Options"] = (pd.concat(_imp35, ignore_index=True) if _imp35
                                         else pd.DataFrame({"note": [
                                             "no fillable gaps; nothing to impute"]}))
        except Exception as _e:                                # pragma: no cover
            out["DQ_Scorecard"] = pd.DataFrame(
                {"note": [f"deep-clean report layer skipped: {type(_e).__name__}: {_e}"]})

        # ------------------------------------------------------------------ #
        # v39: jurisdiction-aware SAD classification (real CMS snapshot) and
        # the consolidated missing-information resolver. All offline.
        # ------------------------------------------------------------------ #
        try:
            from . import sad_jurisdiction as _sad39
            _cls39 = _sad39.classify_frame(std, ref_dir=ref_dir, allowed=allowed)
            out["SAD_Jurisdiction"] = _cls39
            if hasattr(_cls39, "attrs") and _cls39.attrs.get("verdict_series") is not None:
                out["SAD_Ambiguous_Worklist"] = _sad39.ambiguous_lines(
                    std, _cls39, allowed=allowed)
        except Exception as _e:                                # pragma: no cover
            out["SAD_Jurisdiction"] = pd.DataFrame(
                {"note": [f"SAD classification skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import missing_resolver as _mr39
            out["Gap_Inventory"] = _mr39.gap_inventory(std, allowed=allowed, ref_dir=ref_dir)
            out["Resolution_Plan"] = _mr39.resolution_plan(std, allowed=allowed, ref_dir=ref_dir)
        except Exception as _e:                                # pragma: no cover
            out["Gap_Inventory"] = pd.DataFrame(
                {"note": [f"gap inventory skipped: {type(_e).__name__}: {_e}"]})

        # ------------------------------------------------------------------ #
        # v40: the source-of-truth behind the SAD verdicts (every excluded
        # code x MAC with its live CMS article URL), and the gap->connector
        # map showing which live source closes each remaining gap. Both offline.
        # ------------------------------------------------------------------ #
        try:
            from . import sad_jurisdiction as _sad40
            _full = _sad40.load_sad_full(ref_dir)
            if len(_full):
                out["SAD_Source_Audit"] = _full
        except Exception as _e:                                # pragma: no cover
            out["SAD_Source_Audit"] = pd.DataFrame(
                {"note": [f"SAD source audit skipped: {type(_e).__name__}: {_e}"]})
        try:
            from . import source_adapters as _sa40
            out["Source_Adapters"] = _sa40.adapter_registry_frame()
        except Exception as _e:                                # pragma: no cover
            out["Source_Adapters"] = pd.DataFrame(
                {"note": [f"connector map skipped: {type(_e).__name__}: {_e}"]})
    except Exception as e:                                  # pragma: no cover
        out["Analytics_Note"] = pd.DataFrame(
            {"note": [f"analytics stage error: {type(e).__name__}: {e}"]})
    return out
