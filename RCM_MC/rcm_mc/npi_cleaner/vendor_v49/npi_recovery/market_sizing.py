"""Step 6b (v26): VRDC-free market sizing by bottom-up payer-segment build.

VRDC was never received. Its job was to gross the Komodo commercial subset up to
a full all-payer market. We replace that census with a triangulated estimate
whose two LARGEST segments are MEASURED, not assumed:

  * Commercial      -> measured from the Komodo panel (this state).
  * Medicare FFS    -> measured from CMS Physician-by-Geography (state level).
                       This is real fee-for-service utilization, not a candidate
                       universe.
  * Medicare Adv.   -> estimated = Medicare FFS x MA-to-FFS ratio (stated, adjustable).
  * Medicaid/other  -> estimated = a small residual multiplier (stated, adjustable).

The output always reports what share of the total is MEASURED versus grossed up,
so it is never mistaken for a census. Every multiplier is shown on a method
sheet and is a parameter, not a magic number.

Two honest cross-checks are emitted:
  * panel-capture-vs-Medicare: if the panel carries any Medicare rows for a drug,
    the ratio of panel-Medicare to CMS-actual-Medicare is that drug's rough
    capture rate -- a yardstick for how complete the panel is (the CIM showed
    capture swings 0-111% by drug, so this is shown per drug, not averaged away).
  * site-of-care: CMS office vs hospital-outpatient split for the same code.

Connector-bound: needs the CMS client. If a code's CMS pull fails, that row
falls back to the measured commercial figure plus a note, never a fabricated
number. This whole module is deterministic arithmetic over real pulls -- no
model, no LLM.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Default gross-up multipliers. These are TRANSPARENT, ADJUSTABLE assumptions,
# not measured for this market. They are deliberately conservative national-ish
# anchors; override per engagement as better local mix becomes known.
DEFAULTS = dict(
    ma_to_ffs_ratio=1.15,        # Medicare Advantage allowed relative to FFS (MA now > half of Medicare)
    medicaid_residual=0.06,      # Medicaid + other public, as a fraction of the commercial+Medicare base
    commercial_completeness=1.0, # set <1.0 to gross the panel up if a capture rate is known
)

_STATE_NAME = {
    "TX": "Texas", "NY": "New York", "CA": "California", "FL": "Florida",
    "IL": "Illinois", "PA": "Pennsylvania", "OH": "Ohio", "GA": "Georgia",
    "NC": "North Carolina", "MI": "Michigan", "NJ": "New Jersey", "AZ": "Arizona",
    "WA": "Washington", "MA": "Massachusetts", "TN": "Tennessee", "IN": "Indiana",
    "MO": "Missouri", "MD": "Maryland", "WI": "Wisconsin", "CO": "Colorado",
    "MN": "Minnesota", "VA": "Virginia", "AL": "Alabama", "LA": "Louisiana",
    "KY": "Kentucky", "OR": "Oregon", "OK": "Oklahoma", "CT": "Connecticut",
    "SC": "South Carolina", "UT": "Utah", "NV": "Nevada", "KS": "Kansas",
}


def _commercial_by_hcpcs(std, top_n=40):
    """Measured commercial allowed $ and claims per HCPCS from the panel, plus a
    representative drug label. Returns a DataFrame keyed on hcpcs."""
    if "hcpcs" not in std.columns:
        return pd.DataFrame()
    allowed = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
    dn = std["drug_name"].astype("string") if "drug_name" in std.columns else pd.Series("", index=std.index)
    df = pd.DataFrame({"hcpcs": std["hcpcs"].astype("string"),
                       "drug_name": dn, "allowed": allowed.values})
    df = df[df["hcpcs"].notna() & (df["hcpcs"].astype(str).str.len() > 0)]
    if df.empty:
        return df
    g = (df.groupby("hcpcs")
           .agg(commercial_panel_claims=("allowed", "size"),
                commercial_panel_allowed=("allowed", "sum"),
                drug_name=("drug_name", lambda s: s.dropna().mode().iloc[0] if not s.dropna().mode().empty else ""))
           .reset_index())
    return g.sort_values("commercial_panel_allowed", ascending=False).head(top_n)


def build_market_size(std, cms, *, state="TX", top_hcpcs=25,
                      multipliers=None, panel_medicare_by_hcpcs=None, progress=None):
    """Bottom-up payer-segment market size for one state.

    cms: a CMS client exposing geography_benchmark_state(hcpcs, state_name) and
         psps_site_of_care(hcpcs). panel_medicare_by_hcpcs: optional dict
         {hcpcs: panel_medicare_allowed} for the capture cross-check.

    Returns (estimate_df, method_df). Never raises.
    """
    progress = progress or (lambda *_: None)
    mult = dict(DEFAULTS); mult.update(multipliers or {})
    state_name = _STATE_NAME.get(str(state).upper(), str(state))
    pm_med = panel_medicare_by_hcpcs or {}

    comm = _commercial_by_hcpcs(std, top_n=top_hcpcs)
    if comm.empty or cms is None:
        return (pd.DataFrame({"note": ["no HCPCS commercial rows, or CMS client unavailable"]}),
                _method_df(mult, state_name))

    rows = []
    n = len(comm)
    for i, r in enumerate(comm.itertuples(index=False)):
        hc = str(r.hcpcs)
        progress(f"sizing {hc}", (i + 1) / max(n, 1))
        ffs_allowed = None; ffs_services = None; ffs_benes = None
        pct_office = None; note = ""
        try:
            geo = cms.geography_benchmark_state(hc, state_name) or {}
            ffs_allowed = geo.get("ffs_allowed_total")
            ffs_services = geo.get("ffs_services")
            ffs_benes = geo.get("ffs_benes")
        except Exception as e:
            note = f"CMS geo pull failed ({type(e).__name__})"
        try:
            soc = cms.psps_site_of_care(hc) or {}
            pct_office = soc.get("pct_office_services")
        except Exception:
            pass

        commercial = float(r.commercial_panel_allowed) * float(mult["commercial_completeness"])
        ffs = float(ffs_allowed) if ffs_allowed else 0.0
        ma = ffs * float(mult["ma_to_ffs_ratio"]) if ffs else 0.0
        base = commercial + ffs + ma
        medicaid = base * float(mult["medicaid_residual"])
        total = base + medicaid

        measured = commercial + ffs          # the two segments we did not gross up
        measured_share = round(100 * measured / total, 1) if total > 0 else None

        capture = None
        if hc in pm_med and ffs:
            capture = round(100 * float(pm_med[hc]) / ffs, 1)

        rows.append({
            "hcpcs": hc,
            "drug_name": r.drug_name,
            "commercial_panel_allowed__measured": round(commercial, 0),
            "medicare_ffs_allowed__measured": round(ffs, 0),
            "medicare_ffs_services__measured": ffs_services,
            "medicare_ffs_benes__measured": ffs_benes,
            "medicare_adv_allowed__estimate": round(ma, 0),
            "medicaid_other_allowed__estimate": round(medicaid, 0),
            "est_all_payer_allowed": round(total, 0),
            "measured_share_of_estimate_pct": measured_share,
            "panel_capture_vs_medicare_pct": capture,
            "pct_office_of_medicare_services": pct_office,
            "note": note,
        })
    est = pd.DataFrame(rows)

    # total row
    if not est.empty:
        num_cols = ["commercial_panel_allowed__measured", "medicare_ffs_allowed__measured",
                    "medicare_adv_allowed__estimate", "medicaid_other_allowed__estimate",
                    "est_all_payer_allowed"]
        tot = {c: round(float(est[c].fillna(0).sum()), 0) for c in num_cols}
        meas = tot["commercial_panel_allowed__measured"] + tot["medicare_ffs_allowed__measured"]
        tot.update({
            "hcpcs": "TOTAL", "drug_name": f"{state_name} estimated market (top {len(est)} codes)",
            "measured_share_of_estimate_pct": (round(100 * meas / tot["est_all_payer_allowed"], 1)
                                               if tot["est_all_payer_allowed"] > 0 else None),
            "note": "Sum of measured segments + grossed-up MA/Medicaid. Estimate, not a census.",
        })
        est = pd.concat([est, pd.DataFrame([tot])], ignore_index=True)
    return est, _method_df(mult, state_name)


def _num(v):
    """Parse a CMS string like '$291,095,650.01' or '11.06%' or '2,394,063'."""
    import re
    if v is None:
        return np.nan
    s = re.sub(r"[,$%\s]", "", str(v))
    try:
        return float(s)
    except Exception:
        return np.nan


def build_market_attractiveness(cms, states, hcpcs_list, *, weights=None, progress=None):
    """Cross-state market-attractiveness model (the national-model ask, Phase 2),
    anchored on REAL Medicare infusion drug spend.

    For each state and each of the deal's top infusion HCPCS, pulls actual
    Medicare fee-for-service allowed $ and provider counts from CMS
    Physician-by-Geography (state level). State size = summed infusion allowed $
    (real). Competition = mean providers per code (real). Score 0-100 blends size
    and headroom (fewer providers = more room). Bounded: len(states) x
    len(hcpcs_list) cached calls.

    HONESTY: Medicare fee-for-service, infusion codes only. Commercial volume is
    not in free public data, so this is a first-pass infusion-demand screen by
    state, not a commercial market size. Labeled as such. No model, no LLM.
    """
    progress = progress or (lambda *_: None)
    w = dict(size=0.70, headroom=0.30); w.update(weights or {})
    states = list(dict.fromkeys([str(s).upper() for s in (states or []) if s]))
    codes = [str(c) for c in (hcpcs_list or []) if c][:8]
    if not states or not codes or cms is None:
        return (pd.DataFrame({"note": ["need states, infusion HCPCS, and a CMS client"]}),
                _attract_method(w))
    rows = []
    for i, st in enumerate(states):
        progress(f"attractiveness {st}", (i + 1) / max(len(states), 1))
        st_name = _STATE_NAME.get(st, st)
        tot_allowed = 0.0; prov_counts = []; svc = 0.0; got = 0
        for hc in codes:
            try:
                g = cms.geography_benchmark_state(hc, st_name) or {}
            except Exception:
                g = {}
            if g.get("ffs_allowed_total"):
                tot_allowed += float(g["ffs_allowed_total"]); got += 1
            if g.get("ffs_services"):
                svc += float(g["ffs_services"])
            if g.get("ffs_providers"):
                prov_counts.append(float(g["ffs_providers"]))
        rows.append({
            "state": st,
            "medicare_infusion_allowed__measured": round(tot_allowed, 0) if got else np.nan,
            "medicare_infusion_services__measured": round(svc, 0) if svc else np.nan,
            "avg_providers_per_code__measured": round(float(np.mean(prov_counts)), 0) if prov_counts else np.nan,
            "codes_found": got,
        })
    out = pd.DataFrame(rows)
    have = out[out["medicare_infusion_allowed__measured"].notna()]
    if len(have) >= 2:
        size_n = have["medicare_infusion_allowed__measured"].rank(pct=True)
        head_n = (1 - have["avg_providers_per_code__measured"].rank(pct=True)).fillna(0.5)
        out.loc[have.index, "attractiveness_score"] = (
            100 * (w["size"] * size_n + w["headroom"] * head_n)).round(0)
        out = out.sort_values("attractiveness_score", ascending=False, na_position="last")
    out["basis"] = ("real Medicare infusion $ (size " + str(w["size"]) +
                    ") + provider headroom (" + str(w["headroom"]) + "); codes: " + ", ".join(codes))
    return out.reset_index(drop=True), _attract_method(w, codes)


def _attract_method(w, codes=None):
    return pd.DataFrame([
        {"item": "Approach", "value": "Cross-state attractiveness on REAL Medicare infusion spend",
         "detail": "Per state x infusion HCPCS, actual CMS Physician-by-Geography allowed $ and providers."},
        {"item": "Size", "value": f"weight {w['size']}",
         "detail": "Summed Medicare FFS allowed $ for the deal's top infusion codes (measured)."},
        {"item": "Headroom", "value": f"weight {w['headroom']}",
         "detail": "Inverse of average providers per code: fewer providers = more room (measured)."},
        {"item": "Codes used", "value": ", ".join(codes) if codes else "(top panel codes)",
         "detail": "The infusion HCPCS the score is built on."},
        {"item": "What this is NOT", "value": "Not commercial market size",
         "detail": "Medicare fee-for-service, infusion codes only. A first-pass geographic screen for Phase 2, "
                   "not a commercial TAM. Refine with commercial data where available."},
    ])


# Curated medical<->pharmacy channel map for the deal's dual-channel infusion
# drugs. medical_hcpcs bill on the MEDICAL benefit (in the Komodo panel);
# pharmacy_brands are the Part D brands for the same molecule's SC / self-admin
# form (the PHARMACY benefit, invisible to the panel). channel: 'dual' = both
# meaningful (gross-up reliable); 'pharmacy_dominant' = medical base ~0 so a
# multiplier is unreliable (size from Part D directly). Reference-sourced.
_PHARMACY_CHANNEL = [
    dict(cls="Immune globulin (IVIG + SCIG)",
         medical_hcpcs=["J1569", "J1561", "J1459", "J1568", "J1572", "J1566"],
         pharmacy_brands=["Hizentra", "Cuvitru", "Xembify", "Cutaquig", "Gammagard Liquid", "Gammaked"],
         channel="dual"),
    dict(cls="Vedolizumab (Entyvio)", medical_hcpcs=["J3380"],
         pharmacy_brands=["Entyvio"], channel="dual"),
    dict(cls="Efgartigimod (Vyvgart)", medical_hcpcs=["J9332", "J9334"],
         pharmacy_brands=["Vyvgart Hytrulo"], channel="dual"),
    dict(cls="Ocrelizumab (Ocrevus)", medical_hcpcs=["J2350"],
         pharmacy_brands=["Ocrevus Zunovo"], channel="dual"),
    dict(cls="Ustekinumab (Stelara)", medical_hcpcs=["J3358"],
         pharmacy_brands=["Stelara"], channel="pharmacy_dominant"),
]


def _partb_total(cms, hc):
    try:
        g = cms.geography_benchmark(hc) or {}
    except Exception:
        return 0.0
    s = g.get("natl_services"); a = g.get("avg_allowed_unit")
    return float(s * a) if (s and a) else 0.0


def _partd_total(cms, brand):
    from . import config as _cfg
    try:
        df = cms.pull(_cfg.DATASET_TITLES["partd_provider"],
                      filters={"Brnd_Name": brand}, max_rows=6000)
    except Exception:
        return 0.0
    if df is None or df.empty or "Tot_Drug_Cst" not in df:
        return 0.0
    return float(pd.to_numeric(df["Tot_Drug_Cst"], errors="coerce").fillna(0).sum())


def build_pharmacy_benefit_grossup(cms, std, *, commercial_adj=1.0,
                                   channel_map=None, pharmacy_observed_by_hcpcs=None,
                                   progress=None):
    """Estimate the PHARMACY-BENEFIT section the medical panel cannot see, using
    a CMS Part D (pharmacy) vs Part B (medical) analog.

    Per dual-channel drug: ratio = Medicare Part D $ / Part B $ (real CMS).
    commercial pharmacy estimate = commercial MEDICAL $ from the panel (matched
    by HCPCS) x ratio x commercial_adj.

    v29: if pharmacy_observed_by_hcpcs is supplied (a real Komodo pharmacy pull,
    {hcpcs: allowed $}), the MEASURED pharmacy dollars for a drug class supersede
    the estimate for that class and are labelled MEASURED — the toolkit's standing
    rule that the evidence beats the prior. Classes without observed dollars stay
    on the Part-D-analog estimate.

    HONESTY: the estimate is a LOWER BOUND. It grosses up the pharmacy tail of
    drugs that appear in the medical panel; purely pharmacy-benefit drugs
    (channel='pharmacy_dominant', medical base ~0) are flagged to size from the
    pharmacy pull / data room, not grossed up. The ratio is a Medicare analog;
    commercial_adj is the knob for the commercial gap.
    """
    progress = progress or (lambda *_: None)
    cmap = channel_map or _PHARMACY_CHANNEL
    obs = {str(k).upper(): float(v) for k, v in (pharmacy_observed_by_hcpcs or {}).items()}
    if cms is None or std is None or "hcpcs" not in std.columns:
        return (pd.DataFrame({"note": ["need a CMS client and a panel with HCPCS"]}),
                _pharm_method(commercial_adj))
    allowed = pd.to_numeric(std.get("allowed_amt"), errors="coerce").fillna(0.0)
    hc_ser = std["hcpcs"].astype("string")
    rows = []
    for i, d in enumerate(cmap):
        progress(f"pharmacy gross-up {d['cls']}", (i + 1) / max(len(cmap), 1))
        partb = sum(_partb_total(cms, hc) for hc in d["medical_hcpcs"])
        partd = sum(_partd_total(cms, b) for b in d["pharmacy_brands"])
        ratio = (partd / partb) if partb > 0 else np.nan
        comm_med = float(allowed[hc_ser.isin(d["medical_hcpcs"])].sum())
        observed = sum(obs.get(str(hc).upper(), 0.0) for hc in d["medical_hcpcs"])
        pharm_source = "estimate (Part D analog)"
        if observed > 0:
            pharm_est = observed
            pharm_source = "MEASURED (pharmacy feed)"
            note = "measured from the supplied pharmacy pull; estimate superseded"
        elif d["channel"] == "dual" and partb > 0:
            pharm_est = comm_med * ratio * float(commercial_adj); note = ""
        else:
            pharm_est = np.nan
            note = "pharmacy-dominant: medical base ~0, size from Part D / data room (not grossed up)"
        rows.append({
            "drug_class": d["cls"], "channel": d["channel"],
            "commercial_medical_allowed__measured": round(comm_med, 0),
            "medicare_partB_medical__ref": round(partb, 0),
            "medicare_partD_pharmacy__ref": round(partd, 0),
            "pharmacy_to_medical_ratio__ref": round(ratio, 2) if pd.notna(ratio) else np.nan,
            "pharmacy_share_pct__ref": round(100 * partd / (partd + partb), 0) if (partb + partd) > 0 else np.nan,
            "commercial_pharmacy_estimate": round(pharm_est, 0) if pd.notna(pharm_est) else np.nan,
            "pharmacy_source": pharm_source,
            "note": note,
        })
    est = pd.DataFrame(rows)
    dual = est[est["channel"] == "dual"]
    tot_med = float(dual["commercial_medical_allowed__measured"].sum())
    tot_ph = float(dual["commercial_pharmacy_estimate"].dropna().sum())
    est = pd.concat([est, pd.DataFrame([{
        "drug_class": "TOTAL (dual-channel drugs only)", "channel": "",
        "commercial_medical_allowed__measured": round(tot_med, 0),
        "commercial_pharmacy_estimate": round(tot_ph, 0),
        "pharmacy_to_medical_ratio__ref": round(tot_ph / tot_med, 2) if tot_med > 0 else np.nan,
        "note": "Blended gross-up across dual-channel drugs. Lower bound; excludes pharmacy-only drugs.",
    }])], ignore_index=True)
    return est, _pharm_method(commercial_adj)


def _pharm_method(commercial_adj):
    return pd.DataFrame([
        {"item": "Approach", "value": "Pharmacy-benefit gross-up via CMS Part D analog",
         "detail": "Per drug, Medicare Part D (pharmacy) / Part B (medical) ratio applied to the commercial medical panel."},
        {"item": "Ratio source", "value": "MEASURED (CMS)",
         "detail": "Part D total drug cost and Part B allowed are real CMS pulls, national Medicare."},
        {"item": "Commercial adjustment", "value": f"x{commercial_adj}",
         "detail": "Knob for the Medicare-to-commercial gap. White-bag-barred states argue for <1 (more stays medical)."},
        {"item": "Immune globulin", "value": "~1.36x (58% pharmacy)",
         "detail": "IVIG in the medical panel is only ~42% of total IG; the rest is SCIG / home IG on the pharmacy benefit."},
        {"item": "Lower bound", "value": "Excludes pharmacy-only drugs",
         "detail": "Drugs absent from the medical panel (e.g. Stelara, pure SCIG) cannot be grossed up from it; size those from the pharmacy pull or data room."},
        {"item": "What this is NOT", "value": "Not a commercial pharmacy census",
         "detail": "A Medicare-anchored estimate of the pharmacy tail of dual-channel drugs. Confirm with the Komodo pharmacy pull or the data room."},
    ])


def _method_df(mult, state_name):
    return pd.DataFrame([
        {"item": "Approach", "value": "Bottom-up payer-segment build (VRDC stand-in)",
         "detail": "Sum measured segments, gross up only MA and Medicaid with stated multipliers."},
        {"item": "State", "value": state_name, "detail": "Sizing scope."},
        {"item": "Commercial segment", "value": "MEASURED",
         "detail": "Komodo panel allowed $ by HCPCS (this state). A sample of commercial; "
                   "set commercial_completeness < 1.0 to gross up if a capture rate is known."},
        {"item": "Medicare FFS segment", "value": "MEASURED",
         "detail": "CMS Physician-by-Geography, state level. Actual fee-for-service allowed $, "
                   "services, beneficiaries -- not a candidate universe."},
        {"item": "Medicare Advantage", "value": f"ESTIMATE x{mult['ma_to_ffs_ratio']}",
         "detail": "MA allowed approximated as FFS x ma_to_ffs_ratio. Adjustable per engagement."},
        {"item": "Medicaid / other", "value": f"ESTIMATE x{mult['medicaid_residual']}",
         "detail": "Residual public payers as a fraction of the commercial+Medicare base. Adjustable."},
        {"item": "Honesty metric", "value": "measured_share_of_estimate_pct",
         "detail": "Share of each estimate that is measured rather than grossed up. Lead with this."},
        {"item": "Capture cross-check", "value": "panel_capture_vs_medicare_pct",
         "detail": "Panel Medicare $ / CMS actual Medicare $ for a drug = rough panel completeness. "
                   "Shown per drug because capture varies widely by drug."},
        {"item": "What this is NOT", "value": "Not VRDC, not a census",
         "detail": "A triangulated estimate with stated assumptions. Use as the working market size "
                   "for this project; refine if VRDC ever lands."},
    ])
