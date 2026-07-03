"""Step 6.7 (v29): site-of-care reclassification.

The problem the readout surfaced: place-of-service (POS) on a J-code line cannot
separate an ambulatory infusion center (AIC) from a physician office — both bill
POS 11 — and cannot separate the AIC chair from the AIS (home-infusion pharmacy)
model. Many true infusion centers (the Ocrevus proof point) come through the
panel flagged "office", so the as-billed office share is overstated and the AIC
share understated. This module corrects that without inventing certainty.

How it decides a row's true site, strongest signal first:
  1. POS home (12/32/34)                              -> Home   (trust the flag)
  2. A home-infusion code anywhere in the same claim  -> Home   (S9325-S9504,
     99601/99602, G0068-G0090 are home-only by definition; presence overrides a
     mis-stamped office POS — this is the reattribution Kyle's IQVIA gap needs)
  3. Billing-provider taxonomy = infusion clinic      -> AIC
  4. Billing-provider taxonomy = infusion/home pharmacy or DME supplier -> AIS
  5. Billing-provider taxonomy = home health/hospice  -> Home
  6. POS office + an in-clinic administration code in the claim (96360-96549)
     + a learned office->AIC propensity over threshold -> AIC (likely)
  7. otherwise                                        -> Office (as billed)

For the residual office bucket that step 6 cannot resolve on a hard signal, a
HAND-ROLLED logistic (numpy; ridge-penalised; no sklearn/scipy — the toolkit's
standing rule) learns P(AIC) from the rows that DID resolve to office vs AIC and
scores the ambiguous ones. The per-row label is only flipped above a confidence
threshold; the trend totals additionally carry a probability-weighted
("expected") office->AIC reattribution so the headline is graded, not asserted.

Honesty: when the extract carries no administration codes (today's J-code-only
pull), steps 2 and 6 cannot fire on codes and the reattribution rests on
taxonomy + drug propensity only; the summary says so and points at the
extract-expansion the readout called for. AIS is reported as its own bucket so
an operator that bills AIS (Option Care) is no longer compared apples-to-oranges
against AIC-only competitors.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

try:
    from .repair import POS_CANON
except Exception:                       # pragma: no cover
    POS_CANON = {"11": "11", "12": "12", "22": "22"}

_HOME_POS = {"12", "32", "34"}
_OFFICE_POS = {"11", "49", "50", "71", "72"}
_HOPD_POS = {"22", "19"}
_INPT_POS = {"21", "23"}

# learned-propensity gate: an ambiguous office row is only relabelled AIC-likely
# when the logistic clears this. Mirrors the pipeline's point-attribution gates.
AIC_PROPENSITY_GATE = 0.60
# minimum labelled rows on EACH class before the logistic is trusted; below this
# the office bucket is left as-billed (no propensity reattribution).
PROPENSITY_MIN_PER_CLASS = 40


# --------------------------------------------------------------------------- #
# reference loaders
# --------------------------------------------------------------------------- #
def load_admin_codes(ref_dir=None):
    """code(upper) -> {'site_signal','strength','description'} for the 9xxxx /
    Sxxxx / Gxxxx administration, home-infusion, and oversight codes."""
    path = (ref_dir or config.REF_DIR) / "admin_oversight_codes.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    out = {}
    for _, r in df.iterrows():
        code = str(r["code"]).strip().upper()
        if not code:
            continue
        try:
            strength = float(r.get("strength", "") or 0.0)
        except Exception:
            strength = 0.0
        out[code] = {"site_signal": str(r.get("site_signal", "")).strip(),
                     "strength": strength,
                     "description": str(r.get("description", "")).strip()}
    return out


def load_taxonomies(ref_dir=None):
    """taxonomy_code(upper) -> {'site_class','label'} for AIC / AIS / Home / Office."""
    path = (ref_dir or config.REF_DIR) / "infusion_taxonomies.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str).fillna("")
    out = {}
    for _, r in df.iterrows():
        tx = str(r["taxonomy_code"]).strip().upper()
        if not tx:
            continue
        out[tx] = {"site_class": str(r.get("site_class", "")).strip(),
                   "label": str(r.get("label", "")).strip()}
    return out


def _canon_pos(pos: pd.Series) -> pd.Series:
    return (pos.astype("string").str.strip().str.upper()
            .map(lambda v: POS_CANON.get(v, v) if v is not None else v))


def _pos_site(tok: str) -> str:
    if tok in _HOME_POS:
        return "Home"
    if tok in _OFFICE_POS:
        return "Office"          # NB: as-billed office still hides AIC
    if tok in _HOPD_POS:
        return "Outpatient hospital"
    if tok in _INPT_POS:
        return "Inpatient"
    return "Other / unknown"


# --------------------------------------------------------------------------- #
# claim-cluster code signals (the "nine codes" attached to each J-code line)
# --------------------------------------------------------------------------- #
def cluster_code_signals(std: pd.DataFrame, admin_codes: dict):
    """For every row, look at the OTHER codes billed in the same claim cluster
    (claim_id when present, else patient_id+date) and return, per row:
      home_strength      : max strength of any home-infusion signal in the cluster
      inclinic_strength  : max strength of any in-clinic administration signal
      oversight_home     : max strength of any home/hospice oversight signal
      n_inclinic         : count of distinct in-clinic admin codes in the cluster
    Rows whose OWN hcpcs is itself an admin/home code are support rows; they are
    flagged so the drug-volume cuts can drop them (a per-diem line is not a drug).
    """
    n = len(std)
    zero = pd.Series(0.0, index=std.index)
    res = {"home_strength": zero.copy(), "inclinic_strength": zero.copy(),
           "oversight_home_strength": zero.copy(),
           "n_inclinic": pd.Series(0, index=std.index, dtype="int64"),
           "is_support_code": pd.Series(False, index=std.index)}
    if "hcpcs" not in std.columns or not admin_codes:
        return res

    hc = std["hcpcs"].astype("string").str.upper().fillna("")
    sig = hc.map(lambda c: admin_codes.get(c))
    res["is_support_code"] = sig.map(lambda d: bool(d)).astype(bool)

    # cluster key
    if "claim_id" in std.columns and std["claim_id"].notna().any():
        key = std["claim_id"].astype("string").fillna("")
    else:
        pid = (std["patient_id"].astype("string").fillna("")
               if "patient_id" in std.columns else pd.Series("", index=std.index))
        dt = (pd.to_datetime(std["date"], errors="coerce").dt.strftime("%Y%m%d").fillna("")
              if "date" in std.columns else pd.Series("", index=std.index))
        key = (pid + "|" + dt)
    # rows with an empty key cannot be clustered -> treat each as its own cluster
    empty = key.eq("") | key.eq("|")
    key = key.where(~empty, other=pd.Series([f"_solo{i}" for i in range(n)], index=std.index))

    home_s = sig.map(lambda d: d["strength"] if d and d["site_signal"] == "home" else 0.0)
    incl_s = sig.map(lambda d: d["strength"] if d and d["site_signal"] == "in_clinic" else 0.0)
    ovh_s = sig.map(lambda d: d["strength"] if d and d["site_signal"] in ("oversight_home",) else 0.0)
    incl_flag = sig.map(lambda d: 1 if d and d["site_signal"] == "in_clinic" else 0)

    work = pd.DataFrame({"key": key.values, "home": home_s.values, "incl": incl_s.values,
                         "ovh": ovh_s.values, "incln": incl_flag.values}, index=std.index)
    g = work.groupby("key")
    res["home_strength"] = g["home"].transform("max").astype(float)
    res["inclinic_strength"] = g["incl"].transform("max").astype(float)
    res["oversight_home_strength"] = g["ovh"].transform("max").astype(float)
    res["n_inclinic"] = g["incln"].transform("sum").astype("int64")
    return res


# --------------------------------------------------------------------------- #
# hand-rolled ridge-penalised logistic (no sklearn / scipy) for office->AIC
# --------------------------------------------------------------------------- #
def _standardize(X):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd, mu, sd


def _logistic_fit(X, y, l2=1.0, iters=400, lr=0.3):
    """Batch gradient descent on the ridge-penalised log-loss. Returns weights
    on the STANDARDISED design (intercept first). Deterministic; converges fast
    on the small feature set used here."""
    n, p = X.shape
    Xs, mu, sd = _standardize(X)
    Xd = np.hstack([np.ones((n, 1)), Xs])
    w = np.zeros(Xd.shape[1])
    yv = y.astype(float)
    for _ in range(iters):
        z = Xd @ w
        # numerically stable sigmoid
        pos = z >= 0
        ph = np.empty_like(z)
        ph[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
        ez = np.exp(z[~pos])
        ph[~pos] = ez / (1.0 + ez)
        grad = Xd.T @ (ph - yv) / n
        reg = np.r_[0.0, l2 * w[1:] / n]      # no penalty on intercept
        w -= lr * (grad + reg)
    return w, mu, sd


def _logistic_predict(w, mu, sd, X):
    Xs = (X - mu) / sd
    Xd = np.hstack([np.ones((Xs.shape[0], 1)), Xs])
    z = Xd @ w
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


# --------------------------------------------------------------------------- #
# main reclassifier
# --------------------------------------------------------------------------- #
def reclassify(std: pd.DataFrame, *, taxonomy_of: dict | None = None,
               drug_label: pd.Series | None = None, ref_dir=None):
    """Return a DataFrame aligned to std with columns:
        site_as_billed, site_reclassified, site_confidence, site_basis,
        is_support_code, aic_propensity (NaN where not scored), and
        site_expected_weight columns for the probability-weighted view.
    Plus a small diagnostics dict.
    """
    admin_codes = load_admin_codes(ref_dir)
    tax = load_taxonomies(ref_dir)
    taxmap = {str(k): str(v) for k, v in (taxonomy_of or {}).items()}

    n = len(std)
    idx = std.index
    pos_tok = (_canon_pos(std["pos"]) if "pos" in std.columns
               else pd.Series(pd.NA, index=idx, dtype="string"))
    site_billed = pos_tok.map(lambda t: _pos_site(t) if t is not None else "Other / unknown").fillna("Other / unknown")

    cs = cluster_code_signals(std, admin_codes)
    home_strength = cs["home_strength"]
    inclinic_strength = cs["inclinic_strength"]
    is_support = cs["is_support_code"]
    n_inclinic = cs["n_inclinic"]

    # billing-provider taxonomy class per row (from enriched NPPES; optional)
    def _row_npi(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return ""
        return "".join(ch for ch in str(x) if ch.isdigit())
    if "billing_npi" in std.columns:
        bnpi = std["billing_npi"].map(_row_npi)
    else:
        bnpi = pd.Series("", index=idx)
    tx_code = bnpi.map(lambda d: taxmap.get(d, "")).str.upper()
    tx_class = tx_code.map(lambda c: (tax.get(c, {}) or {}).get("site_class", ""))

    site = pd.Series("Office", index=idx, dtype="object")
    conf = pd.Series(0.5, index=idx, dtype=float)
    basis = pd.Series("POS as-billed", index=idx, dtype="object")

    # start from POS as-billed for the non-office buckets we trust
    for b in ("Home", "Outpatient hospital", "Inpatient", "Other / unknown"):
        m = site_billed.eq(b)
        site[m] = b
        conf[m] = 0.9 if b in ("Outpatient hospital", "Inpatient") else (0.95 if b == "Home" else 0.4)
        basis[m] = f"POS {b.lower()}"
    office_or_other = site_billed.eq("Office") | site_billed.eq("Other / unknown")

    # (2) home-infusion code anywhere in the claim -> Home (overrides office POS)
    m_home_code = (home_strength > 0) & office_or_other
    site[m_home_code] = "Home"
    conf[m_home_code] = np.maximum(0.85, home_strength[m_home_code]).clip(upper=0.99)
    basis[m_home_code] = "home-infusion code in claim (Sxxxx/99601/G00xx)"

    # taxonomy-driven (only on rows not already pinned Home by a code/POS)
    open_mask = ~m_home_code & (site_billed.ne("Home"))
    m_aic_tax = open_mask & tx_class.eq("AIC")
    site[m_aic_tax] = "AIC"
    conf[m_aic_tax] = 0.9
    basis[m_aic_tax] = "billing taxonomy = infusion clinic"

    m_ais_tax = open_mask & tx_class.eq("AIS")
    site[m_ais_tax] = "AIS"
    conf[m_ais_tax] = 0.85
    basis[m_ais_tax] = "billing taxonomy = infusion/home pharmacy or DME supplier"

    m_home_tax = open_mask & tx_class.eq("Home")
    site[m_home_tax] = "Home"
    conf[m_home_tax] = 0.85
    basis[m_home_tax] = "billing taxonomy = home health/hospice"

    # rows still sitting at "Office" after the hard signals = the ambiguous bucket
    resolved_office = site.eq("Office") & basis.eq("billing taxonomy = infusion clinic")  # none; placeholder
    ambiguous = site.eq("Office")

    # ---- learn office->AIC propensity from the rows that DID resolve --------
    aic_prop = pd.Series(np.nan, index=idx, dtype=float)
    diagnostics = {"admin_codes_present": bool((inclinic_strength > 0).any() or (home_strength > 0).any()),
                   "labelled_aic": int((site.eq("AIC")).sum()),
                   "labelled_office": int(ambiguous.sum()),
                   "propensity_trained": False}

    # features: log allowed, log units, in-clinic strength, n in-clinic, top-drug one-hots
    allowed = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0).clip(lower=0.0)
    units = pd.to_numeric(std.get("units"), errors="coerce").fillna(0.0).clip(lower=0.0)
    feats = {"log_allowed": np.log1p(allowed.values),
             "log_units": np.log1p(units.values),
             "inclinic_strength": inclinic_strength.values.astype(float),
             "n_inclinic": n_inclinic.values.astype(float)}
    dl = (drug_label if drug_label is not None
          else (std["drug_name"] if "drug_name" in std.columns else pd.Series("", index=idx)))
    dl = dl.astype("string").fillna("").str.upper()
    top_drugs = [d for d, _ in dl[dl.ne("")].value_counts().head(8).items()]
    for d in top_drugs:
        feats[f"drug::{d[:24]}"] = (dl.eq(d)).astype(float).values
    Xall = np.column_stack([feats[k] for k in feats])

    # labelled set: AIC (1) vs hard-resolved office (0). A row is a "hard office"
    # if POS office AND taxonomy says Office (a known physician practice).
    hard_office = site_billed.eq("Office") & tx_class.eq("Office")
    lab_mask = (site.eq("AIC")) | hard_office
    y = (site.eq("AIC")).astype(int).values
    if (int((y[lab_mask.values] == 1).sum()) >= PROPENSITY_MIN_PER_CLASS and
            int((y[lab_mask.values] == 0).sum()) >= PROPENSITY_MIN_PER_CLASS):
        w, mu, sd = _logistic_fit(Xall[lab_mask.values], y[lab_mask.values])
        p_amb = _logistic_predict(w, mu, sd, Xall[ambiguous.values])
        aic_prop.loc[ambiguous] = p_amb
        diagnostics["propensity_trained"] = True
        # hard relabel above the gate
        flip = ambiguous.copy()
        flip.loc[ambiguous] = p_amb >= AIC_PROPENSITY_GATE
        site[flip] = "AIC"
        conf[flip] = pd.Series(np.clip(p_amb[p_amb >= AIC_PROPENSITY_GATE], 0.6, 0.85),
                               index=site.index[flip])
        basis[flip] = "office POS reattributed to AIC (learned propensity)"

    # ---- probability-weighted (expected) view for the totals ---------------
    # For every still-Office ambiguous row, split its dollars Office/AIC by P(AIC).
    exp_aic_w = pd.Series(0.0, index=idx, dtype=float)
    exp_off_w = pd.Series(0.0, index=idx, dtype=float)
    still_amb = site.eq("Office")
    exp_off_w[still_amb] = 1.0
    if diagnostics["propensity_trained"]:
        p_here = aic_prop[still_amb].fillna(0.0).values
        exp_aic_w.loc[still_amb] = p_here
        exp_off_w.loc[still_amb] = 1.0 - p_here

    out = pd.DataFrame({
        "site_as_billed": site_billed.values,
        "site_reclassified": site.values,
        "site_confidence": conf.round(3).values,
        "site_basis": basis.values,
        "is_support_code": is_support.values,
        "aic_propensity": aic_prop.round(3).values,
        "_exp_w_aic": exp_aic_w.values,
        "_exp_w_office": exp_off_w.values,
    }, index=idx)
    return out, diagnostics


# --------------------------------------------------------------------------- #
# readout tabs
# --------------------------------------------------------------------------- #
def _share(series_sum):
    tot = float(series_sum.sum())
    return (series_sum / tot * 100.0) if tot > 0 else series_sum * 0.0


def site_reclassification_summary(std, sc: pd.DataFrame, diagnostics: dict):
    """As-billed vs reclassified site mix on drug dollars (support/per-diem and
    reversal rows excluded), plus the probability-weighted office->AIC view."""
    allowed = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
    # drug volume only: drop support (per-diem/admin) rows and reversals (<0)
    keep = (~sc["is_support_code"].values) & (allowed.values >= 0)
    a = allowed[keep]
    billed = sc.loc[keep, "site_as_billed"]
    recl = sc.loc[keep, "site_reclassified"]

    order = ["Office", "AIC", "AIS", "Home", "Outpatient hospital", "Inpatient", "Other / unknown"]
    bill_by = a.groupby(billed).sum()
    recl_by = a.groupby(recl).sum()
    bill_sh = _share(bill_by)
    recl_sh = _share(recl_by)

    rows = []
    for s in order:
        b = float(bill_by.get(s, 0.0))
        r = float(recl_by.get(s, 0.0))
        rows.append({
            "site_of_care": s,
            "as_billed_allowed": round(b, 0),
            "as_billed_share_pct": round(float(bill_sh.get(s, 0.0)), 1),
            "reclassified_allowed": round(r, 0),
            "reclassified_share_pct": round(float(recl_sh.get(s, 0.0)), 1),
            "reclassified_minus_billed_pp": round(float(recl_sh.get(s, 0.0)) - float(bill_sh.get(s, 0.0)), 1),
        })
    out = pd.DataFrame(rows)

    # probability-weighted expected office->AIC migration (graded headline)
    exp_aic = float((a.values * sc.loc[keep, "_exp_w_aic"].values).sum())
    note = []
    if not diagnostics.get("admin_codes_present"):
        note.append("Extract carries NO administration codes (9xxxx/Sxxxx/Gxxxx). "
                     "Home-code and in-clinic-code signals could not fire; reattribution "
                     "rests on billing taxonomy + drug propensity only. Expand the extract "
                     "to all codes on claims that include the J-codes (per the readout) to "
                     "enable code-anchored site inference.")
    if not diagnostics.get("propensity_trained"):
        note.append("Office->AIC propensity model not trained (too few hard-labelled rows). "
                    "Office shown as-billed; supply billing taxonomy and/or admin codes to enable it.")
    out = pd.concat([out, pd.DataFrame([{
        "site_of_care": "— office reattributed to AIC (expected, prob-weighted)",
        "as_billed_allowed": "",
        "as_billed_share_pct": "",
        "reclassified_allowed": round(exp_aic, 0),
        "reclassified_share_pct": round(100 * exp_aic / float(a.sum()), 1) if float(a.sum()) > 0 else "",
        "reclassified_minus_billed_pp": "",
    }])], ignore_index=True)
    if note:
        out = pd.concat([out, pd.DataFrame([{"site_of_care": "NOTE", "as_billed_allowed": "",
                                             "as_billed_share_pct": "", "reclassified_allowed": "",
                                             "reclassified_share_pct": "",
                                             "reclassified_minus_billed_pp": " | ".join(note)}])],
                        ignore_index=True)
    return out


def site_proof_point(std, sc: pd.DataFrame, drug_label: pd.Series, *,
                     anchor_keywords=("ocrelizumab", "ocrevus", "j2350")):
    """The Ocrevus-style check: for an anchor drug known to be AIC-heavy, show the
    as-billed office vs AIC split and how much reclassification moves to AIC. This
    is the 'the volume we have is paltry vs what AICs actually do' validation."""
    dl = drug_label.astype("string").fillna("").str.lower()
    hc = (std["hcpcs"].astype("string").str.upper().fillna("")
          if "hcpcs" in std.columns else pd.Series("", index=std.index))
    mask = pd.Series(False, index=std.index)
    for kw in anchor_keywords:
        k = kw.lower()
        mask = mask | dl.str.contains(k, regex=False) | hc.str.contains(k.upper(), regex=False)
    if not mask.any():
        return pd.DataFrame({"note": [f"anchor drug not found in panel (keywords: {', '.join(anchor_keywords)})"]})
    allowed = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
    keep = mask & (~sc["is_support_code"]) & (allowed >= 0)
    a = allowed[keep]
    billed = sc.loc[keep, "site_as_billed"]
    recl = sc.loc[keep, "site_reclassified"]
    bb = a.groupby(billed).sum()
    rr = a.groupby(recl).sum()
    tot = float(a.sum()) or 1.0
    rows = []
    for s in ["Office", "AIC", "AIS", "Home", "Outpatient hospital", "Other / unknown"]:
        rows.append({"site_of_care": s,
                     "as_billed_allowed": round(float(bb.get(s, 0.0)), 0),
                     "as_billed_share_pct": round(100 * float(bb.get(s, 0.0)) / tot, 1),
                     "reclassified_allowed": round(float(rr.get(s, 0.0)), 0),
                     "reclassified_share_pct": round(100 * float(rr.get(s, 0.0)) / tot, 1)})
    out = pd.DataFrame(rows)
    moved = float(rr.get("AIC", 0.0) - bb.get("AIC", 0.0))
    out = pd.concat([out, pd.DataFrame([{
        "site_of_care": "ANCHOR: office->AIC reattributed",
        "as_billed_allowed": "", "as_billed_share_pct": "",
        "reclassified_allowed": round(moved, 0),
        "reclassified_share_pct": round(100 * moved / tot, 1)}])], ignore_index=True)
    return out
