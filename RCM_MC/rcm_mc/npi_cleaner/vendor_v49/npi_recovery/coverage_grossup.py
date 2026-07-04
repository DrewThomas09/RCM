"""
coverage_grossup.py  (v32)
==========================

The Komodo pivot resolves the morning's problem, and Kyle's gross-up is, in the
report's words, the whole ballgame, because the arithmetic is brutal at these
ratios. A 14.1% coverage ratio is a 7.1x multiplier, and two points of ratio
error move the MA market estimate by roughly fifteen to seventeen percent. This
module makes the multiplier, its sensitivity, and its definitional traps explicit
so nothing gets charted on a number the team does not yet understand.

What it does:

  grossup_estimate      captured / ratio, with the multiplier, and the basis
                        (lives or dollars) surfaced rather than assumed.
  grossup_sensitivity   the estimate at the ratio and at +/- a few points, with
                        the percent swing, so the fragility is on the page.
  grossup_panel         the multi-channel view: observed Part D and Medicaid
                        dollars carried at face, MA grossed up, each line tagged
                        with its stability and its referent question.

Three honesty rails from the report are built in as flags, not footnotes:

  * lives vs dollars: a ratio computed on lives applied to dollars silently
    assumes Komodo's captured payers carry the market's drug mix. Flagged.
  * referent ambiguity: whether a figure is target-attributed or universe-wide
    observed spend changes what the gross-up means. Asked on every line.
  * Medicaid asterisk: managed-Medicaid capture varies enormously by state, so
    that gross-up is the least stable number on the page.

Deterministic and offline. Confirm-or-deny framing: it states the multiplier and
the swing and lets the fragility decide, rather than presenting a point estimate
as settled.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _mult(ratio):
    r = float(ratio)
    if r <= 0:
        return np.nan
    return 1.0 / r


def grossup_estimate(*, captured, coverage_ratio, channel_label: str = "MA",
                     basis: str = "lives", referent: str = "unspecified") -> pd.DataFrame:
    """Gross up a captured figure to a market estimate: estimate = captured / ratio.
    basis is 'lives' or 'dollars'; referent is 'target_attributed' or
    'universe_observed' or 'unspecified'. Both are surfaced because they change
    what the number means."""
    cap = float(captured or 0.0)
    m = _mult(coverage_ratio)
    est = cap * m if not np.isnan(m) else np.nan
    rows = [
        {"line": f"captured ({channel_label})", "value": round(cap, 2)},
        {"line": "coverage ratio", "value": round(float(coverage_ratio), 4)},
        {"line": "gross-up multiplier (1 / ratio)", "value": (round(m, 3) if not np.isnan(m) else np.nan)},
        {"line": f"grossed-up market estimate ({channel_label})", "value": (round(est, 2) if not np.isnan(est) else np.nan)},
        {"line": "ratio basis", "value": basis},
        {"line": "captured referent", "value": referent},
    ]
    out = pd.DataFrame(rows)
    flags = []
    if basis == "lives":
        flags.append("ratio is on LIVES but applied to DOLLARS: assumes captured payers carry "
                     "the market drug mix; verify against a dollar-based coverage ratio")
    if referent == "unspecified":
        flags.append("captured referent unspecified: confirm target-attributed vs universe-wide "
                     "observed before charting")
    out.attrs["flags"] = flags
    out.attrs["note"] = (
        "estimate = captured / coverage_ratio. At low ratios the multiplier is large and the "
        "estimate is highly sensitive to ratio error (see grossup_sensitivity).")
    return out


def grossup_sensitivity(*, captured, coverage_ratio, delta_points=2.0,
                        channel_label: str = "MA") -> pd.DataFrame:
    """Show how much a few points of ratio error move the estimate. Because the
    multiplier is 1/ratio (convex), the swing is large and asymmetric at low
    ratios: this is the 7.1x / fifteen-to-seventeen-percent point made concrete."""
    cap = float(captured or 0.0)
    r0 = float(coverage_ratio)
    d = float(delta_points) / 100.0
    base = cap * _mult(r0)

    rows = []
    for label, r in (("ratio - {:.0f}pts".format(delta_points), r0 - d),
                     ("stated ratio", r0),
                     ("ratio + {:.0f}pts".format(delta_points), r0 + d)):
        if r <= 0:
            rows.append({"scenario": label, "coverage_ratio": round(r, 4),
                         "multiplier": np.nan, "estimate": np.nan, "pct_vs_stated": np.nan})
            continue
        est = cap * (1.0 / r)
        rows.append({"scenario": label, "coverage_ratio": round(r, 4),
                     "multiplier": round(1.0 / r, 3), "estimate": round(est, 2),
                     "pct_vs_stated": (round((est / base - 1.0) * 100, 1) if base else np.nan)})
    out = pd.DataFrame(rows)
    swings = [abs(v) for v in out["pct_vs_stated"].tolist() if isinstance(v, (int, float)) and not np.isnan(v) and v != 0.0]
    max_swing = max(swings) if swings else np.nan
    out.attrs["max_abs_swing_pct"] = (round(max_swing, 1) if not np.isnan(max_swing) else None)
    out.attrs["note"] = (
        "A {:.0f}-point ratio error moves the {} estimate by up to {} percent. The multiplier is "
        "1/ratio, so the swing is asymmetric: an equal drop in the ratio moves the estimate more "
        "than an equal rise. Pin the ratio before charting.".format(
            delta_points, channel_label, out.attrs["max_abs_swing_pct"]))
    return out


def grossup_panel(*, part_d_observed=None, medicaid_observed=None,
                  ma_captured=None, ma_coverage_ratio=None,
                  ma_basis: str = "lives") -> pd.DataFrame:
    """The government-book view as one table. Observed Part D and Medicaid dollars
    are carried at face (they are census-complete or directly observed); MA is
    grossed up. Every line carries a stability tag and a referent question."""
    rows = []
    if part_d_observed is not None:
        rows.append({"channel": "Part D (observed)", "input": round(float(part_d_observed), 2),
                     "multiplier": 1.0, "estimate": round(float(part_d_observed), 2),
                     "stability": "census-complete (PDE incl. MA-PD)",
                     "referent_question": "target-attributed vs universe-wide observed?"})
    if medicaid_observed is not None:
        rows.append({"channel": "Medicaid (observed)", "input": round(float(medicaid_observed), 2),
                     "multiplier": 1.0, "estimate": round(float(medicaid_observed), 2),
                     "stability": "LEAST STABLE: managed-Medicaid capture varies enormously by state",
                     "referent_question": "target-attributed vs universe-wide observed?"})
    if ma_captured is not None and ma_coverage_ratio is not None:
        m = _mult(ma_coverage_ratio)
        rows.append({"channel": "MA (grossed up)", "input": round(float(ma_captured), 2),
                     "multiplier": (round(m, 3) if not np.isnan(m) else np.nan),
                     "estimate": (round(float(ma_captured) * m, 2) if not np.isnan(m) else np.nan),
                     "stability": ("HIGH SENSITIVITY: {:.1f}x multiplier; small ratio error swings "
                                   "the estimate".format(m) if not np.isnan(m) else "invalid ratio"),
                     "referent_question": "ratio on lives applied to dollars: does captured mix = market mix?"})
    if not rows:
        return pd.DataFrame({"note": ["no channel inputs supplied to gross-up panel"]})
    out = pd.DataFrame(rows)
    out.attrs["note"] = (
        "Observed channels are carried at face; only MA is grossed up. The Medicaid line is the "
        "least stable number on the page, and the MA line is the most sensitive. Confirm the "
        "referent of every input before it is charted.")
    return out


# --------------------------------------------------------------------------- #
# v33 hardening: Kyle's verification burden made computable. The 14.1 is only
# chartable once it decomposes, the mix parity holds, and the Medicaid state
# variation is scored rather than asterisked.
# --------------------------------------------------------------------------- #

def ratio_decomposition(components, stated_blend, *, tolerance_pts: float = 0.5) -> pd.DataFrame:
    """components: per payer class, captured and universe dollars (a frame/CSV with
    columns like payer_class, captured, universe, or a dict of dicts). The implied
    blend is sum(captured)/sum(universe); if it does not reproduce the stated
    blend within tolerance, the stated ratio is flagged as not yet understood."""
    rows_in = []
    if isinstance(components, dict):
        for k, v in components.items():
            rows_in.append({"payer_class": str(k),
                            "captured": float(v.get("captured", 0.0)),
                            "universe": float(v.get("universe", 0.0))})
    else:
        df = components
        if not isinstance(df, pd.DataFrame):
            from pathlib import Path as _P
            p = _P(str(components))
            df = pd.read_csv(p) if p.exists() else None
        if df is None or df.empty:
            return pd.DataFrame({"note": ["supply ratio components (payer_class, captured, "
                                          "universe) to decompose the stated blend"]})
        cols = {c.strip().lower(): c for c in df.columns}
        kc = cols.get("payer_class", cols.get("class", df.columns[0]))
        cc = cols.get("captured")
        uc = cols.get("universe")
        if cc is None or uc is None:
            return pd.DataFrame({"note": ["ratio components need captured and universe columns"]})
        for _, r in df.iterrows():
            rows_in.append({"payer_class": str(r[kc]),
                            "captured": float(pd.to_numeric(pd.Series([r[cc]]), errors="coerce").iloc[0] or 0),
                            "universe": float(pd.to_numeric(pd.Series([r[uc]]), errors="coerce").iloc[0] or 0)})
    rows = []
    for r in rows_in:
        ratio = (r["captured"] / r["universe"]) if r["universe"] > 0 else np.nan
        rows.append({**{k: round(v, 2) if isinstance(v, float) else v for k, v in r.items()},
                     "class_ratio": (round(ratio, 4) if not np.isnan(ratio) else np.nan)})
    tot_c = sum(r["captured"] for r in rows_in)
    tot_u = sum(r["universe"] for r in rows_in)
    implied = (tot_c / tot_u) if tot_u > 0 else np.nan
    delta = (implied - float(stated_blend)) * 100 if not np.isnan(implied) else np.nan
    rows.append({"payer_class": "IMPLIED BLEND", "captured": round(tot_c, 2),
                 "universe": round(tot_u, 2),
                 "class_ratio": (round(implied, 4) if not np.isnan(implied) else np.nan)})
    out = pd.DataFrame(rows)
    reproduced = bool(not np.isnan(delta) and abs(delta) <= tolerance_pts)
    out.attrs["implied_blend"] = (round(implied, 4) if not np.isnan(implied) else None)
    out.attrs["delta_pts_vs_stated"] = (round(delta, 2) if not np.isnan(delta) else None)
    out.attrs["verdict"] = ("REPRODUCED: components reproduce the stated blend ({:+.2f} pts)".format(delta)
                            if reproduced else
                            "NOT REPRODUCED ({:+.2f} pts vs stated): the stated ratio is not yet "
                            "understood; do not chart on it".format(delta if not np.isnan(delta) else 0.0))
    out.attrs["note"] = out.attrs["verdict"]
    return out


def mix_parity(captured_mix, census_mix, *, tolerance: float = 0.15) -> pd.DataFrame:
    """The direct test of the lives-applied-to-dollars assumption: does the
    captured drug mix match the census drug mix? Per drug, an index of captured
    share over census share; the spend-weighted mean absolute deviation from 1.0
    is the parity score. Inputs are drug-to-dollars maps."""
    from .calibration import load_kv_csv as _kv
    cap = _kv(captured_mix)
    cen = _kv(census_mix)
    if not cap or not cen:
        return pd.DataFrame({"note": ["supply captured and census drug mixes to test the "
                                      "lives-vs-dollars assumption"]})
    tc, tn = sum(cap.values()), sum(cen.values())
    drugs = sorted(set(cap) | set(cen))
    rows, dev_w = [], 0.0
    for d in drugs:
        cs = cap.get(d, 0.0) / tc if tc > 0 else 0.0
        ns = cen.get(d, 0.0) / tn if tn > 0 else 0.0
        idx = (cs / ns) if ns > 0 else np.nan
        rows.append({"drug": d, "captured_share_pct": round(cs * 100, 2),
                     "census_share_pct": round(ns * 100, 2),
                     "parity_index": (round(idx, 3) if not np.isnan(idx) else np.nan)})
        if not np.isnan(idx):
            dev_w += ns * abs(idx - 1.0)
    out = pd.DataFrame(rows).sort_values("census_share_pct", ascending=False).reset_index(drop=True)
    out.attrs["parity_score"] = round(dev_w, 3)
    holds = bool(dev_w <= tolerance)
    out.attrs["verdict"] = ("MIX MATCHES (weighted deviation {:.3f}): the lives-based ratio is "
                            "usable on dollars".format(dev_w) if holds else
                            "MIX DIVERGES (weighted deviation {:.3f}): a lives-based ratio "
                            "misprices the dollar gross-up; use per-drug ratios".format(dev_w))
    out.attrs["note"] = out.attrs["verdict"]
    return out


def medicaid_state_grossup(state_ratios, captured_by_state=None) -> pd.DataFrame:
    """The Medicaid asterisk made numeric: per-state coverage ratios (and optional
    captured dollars), with the dispersion scored. High dispersion means the
    single Medicaid gross-up is the least stable number on the page, now with a
    coefficient instead of a footnote."""
    from .calibration import load_kv_csv as _kv
    ratios = _kv(state_ratios)
    caps = _kv(captured_by_state) if captured_by_state is not None else {}
    if not ratios:
        return pd.DataFrame({"note": ["supply per-state Medicaid coverage ratios to score the "
                                      "state-variation instability"]})
    rows = []
    for st, r in sorted(ratios.items()):
        row = {"state": st, "coverage_ratio": round(float(r), 4),
               "multiplier": (round(1.0 / float(r), 3) if float(r) > 0 else np.nan)}
        if st in caps:
            row["captured"] = round(caps[st], 2)
            row["state_estimate"] = (round(caps[st] / float(r), 2) if float(r) > 0 else np.nan)
        rows.append(row)
    vals = np.array([float(v) for v in ratios.values() if float(v) > 0])
    cv = float(vals.std() / vals.mean()) if len(vals) and vals.mean() > 0 else np.nan
    stability = ("HIGH" if cv < 0.15 else ("MEDIUM" if cv < 0.30 else "LOW")) if not np.isnan(cv) else "UNKNOWN"
    out = pd.DataFrame(rows)
    out.attrs["ratio_cv"] = (round(cv, 3) if not np.isnan(cv) else None)
    out.attrs["stability"] = stability
    out.attrs["note"] = (
        "Coefficient of variation across state ratios: {} (stability {}). LOW stability means "
        "one blended Medicaid gross-up should not be charted; gross up state by state or carry "
        "a range.".format(out.attrs["ratio_cv"], stability))
    return out
