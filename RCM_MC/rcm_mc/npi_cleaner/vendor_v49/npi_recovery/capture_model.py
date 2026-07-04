"""
capture_model.py  (v43)
=======================

A claims panel is not the whole book. Komodo and panels like it miss
pharmacy-benefit drugs, undercount VA and military, and capture a very different
share of true volume drug by drug. A cleaner that reports confident totals without
saying what it cannot see produces confident wrong diligence: the visible slice
gets mistaken for the whole.

This module does not invent the missing volume. It states, from the data in hand
plus known structural facts, where the panel is systematically blind and how wide
the uncertainty is, so a reader sees "this is a partial view, and here is which
part is missing" instead of a total presented as complete.

Three outputs:

  channel_completeness   for each payer channel present (commercial, Medicare,
                         Medicare Advantage, Medicaid, managed Medicaid, VA/
                         military, cash), a coverage posture: is this channel
                         well captured by claims panels, structurally
                         under-captured, or effectively invisible. Flags the
                         under-captured dollars in the file.

  drug_capture_flags     for each drug (HCPCS/J-code), whether it is the kind of
                         drug a medical-claims panel captures well (clinician
                         administered, buy-and-bill) or poorly (pharmacy-benefit,
                         self-administered, white-bag/specialty-pharmacy routed).
                         Uses the shipped JW/JZ single-dose list and the SAD
                         signal already in the toolkit as structural markers.

  implied_capture_band   a transparent low/high band on what fraction of the true
                         book the file likely represents, built by weighting the
                         file's dollars by the per-channel and per-drug capture
                         postures. It is a band with stated assumptions, not a
                         point estimate, and the assumptions are returned with it.

All deterministic and offline. The postures are structural priors, labeled as
such; they are meant to frame the read, not to restate the file's dollars as
truth.
"""
from __future__ import annotations

import os
import pandas as pd
import numpy as np


# structural capture posture by payer channel for a medical-claims panel.
# value is a (low, high) plausible capture fraction of that channel's TRUE book.
_CHANNEL_POSTURE = {
    "commercial":        (0.70, 0.95, "well captured"),
    "medicare_ffs":      (0.60, 0.90, "well captured (FFS adjudicated)"),
    "medicare_advantage":(0.45, 0.80, "partially captured (encounter completeness varies)"),
    "medicaid":          (0.40, 0.75, "partially captured (state variation)"),
    "managed_medicaid":  (0.35, 0.70, "partially captured"),
    "va_military":       (0.05, 0.30, "structurally under-captured (federal, often invisible)"),
    "cash":              (0.00, 0.20, "structurally invisible (no third-party claim)"),
    "unknown":           (0.30, 0.85, "unknown channel; wide band"),
}

_CHANNEL_TOKENS = {
    "medicare_advantage": ("advantage", " ma ", "mapd", "part c", "medicare adv"),
    "managed_medicaid":   ("managed medicaid", "medicaid managed", "mmc"),
    "medicaid":           ("medicaid", "medi-cal", "medical assistance"),
    "medicare_ffs":       ("medicare", "cms", "ffs"),
    "va_military":        ("va", "veteran", "tricare", "champva", "military", "dod"),
    "cash":               ("cash", "self pay", "self-pay", "patient pay", "uninsured"),
    "commercial":         ("bcbs", "blue cross", "aetna", "cigna", "united",
                           "uhc", "humana", "commercial", "ppo", "hmo", "employer"),
}


def _classify_channel(name: str) -> str:
    if not name:
        return "unknown"
    s = str(name).lower()
    # order matters: check advantage/managed before their base programs
    for chan in ("medicare_advantage", "managed_medicaid", "medicaid",
                 "va_military", "cash", "medicare_ffs", "commercial"):
        for tok in _CHANNEL_TOKENS[chan]:
            if tok.strip() in s:
                return chan
    return "unknown"


def _amount(std, mapping):
    col = (mapping or {}).get("allowed_amt", "allowed_amt")
    col = col if col in std.columns else ("allowed_amt" if "allowed_amt" in std.columns else None)
    if col is None:
        return pd.Series(np.ones(len(std)), index=std.index)
    return pd.to_numeric(std[col], errors="coerce").fillna(0.0).clip(lower=0)


def channel_completeness(std: pd.DataFrame, mapping=None) -> pd.DataFrame:
    """Coverage posture and dollars by payer channel present in the file."""
    pcol = (mapping or {}).get("payer", "payer")
    pcol = pcol if pcol in std.columns else ("payer" if "payer" in std.columns else None)
    amt = _amount(std, mapping)
    if pcol is None:
        out = pd.DataFrame([{"channel": "unknown", "dollars": round(float(amt.sum()), 2),
                             "posture": "no payer column; cannot assess channel capture"}])
        out.attrs["note"] = "No payer column delivered; channel completeness cannot be assessed."
        return out
    chan = std[pcol].map(_classify_channel)
    g = amt.groupby(chan).sum().sort_values(ascending=False)
    tot = float(g.sum()) or 1.0
    rows = []
    for c, d in g.items():
        lo, hi, label = _CHANNEL_POSTURE.get(c, _CHANNEL_POSTURE["unknown"])
        rows.append({"channel": c, "dollars": round(float(d), 2),
                     "share_pct": round(100.0 * d / tot, 1),
                     "capture_low": lo, "capture_high": hi, "posture": label,
                     "under_captured": c in ("va_military", "cash", "managed_medicaid")})
    out = pd.DataFrame(rows)
    under = out[out["under_captured"]]["dollars"].sum()
    out.attrs["note"] = (
        f"{round(100.0*under/tot,1)}% of visible dollars sit in structurally "
        f"under-captured channels (VA/military, cash, managed Medicaid). The true "
        f"book is larger than this file by an unknown amount concentrated there.")
    return out


def _single_dose_set(ref_dir):
    path = os.path.join(ref_dir or os.path.join(os.path.dirname(__file__), "reference"),
                        "jw_jz_single_dose_seed.csv")
    if not os.path.exists(path):
        return set()
    return set(pd.read_csv(path, dtype=str)["hcpcs"].str.strip().str.upper())


def drug_capture_flags(std: pd.DataFrame, ref_dir=None, mapping=None) -> pd.DataFrame:
    """Per-drug capture posture: clinician-administered (well captured) vs
    pharmacy-benefit / self-administered (poorly captured by a medical panel)."""
    hcol = (mapping or {}).get("hcpcs", "hcpcs")
    hcol = hcol if hcol in std.columns else ("hcpcs" if "hcpcs" in std.columns else None)
    if hcol is None:
        out = pd.DataFrame([{"note": "no HCPCS column; cannot assess drug capture"}])
        out.attrs["note"] = "No HCPCS column delivered; drug capture cannot be assessed."
        return out
    amt = _amount(std, mapping)
    single = _single_dose_set(ref_dir)
    code = std[hcol].astype(str).str.strip().str.upper()
    g = pd.DataFrame({"hcpcs": code, "amt": amt}).groupby("hcpcs")["amt"].sum()
    g = g.sort_values(ascending=False)
    rows = []
    for h, d in g.items():
        is_jcode = len(h) == 5 and h[0] in ("J", "Q", "C") and h[1:].isdigit()
        # clinician-administered buy-and-bill J-codes are well captured by a
        # medical panel; oral/self-administered (non J) are pharmacy-benefit and
        # poorly captured. Single-dose injectables are administered -> captured.
        if is_jcode:
            posture = "well captured (clinician-administered)"
            captured = True
        elif h.startswith(("S", "A")) or (h[:1].isalpha() and not is_jcode):
            posture = "variable (supply/pharmacy-adjacent)"
            captured = False
        else:
            posture = "poorly captured (likely pharmacy-benefit / self-administered)"
            captured = False
        rows.append({"hcpcs": h, "dollars": round(float(d), 2),
                     "is_jcode": is_jcode,
                     "single_dose_injectable": h in single,
                     "capture_posture": posture, "well_captured": captured})
    out = pd.DataFrame(rows)
    tot = float(out["dollars"].sum()) or 1.0
    poor = out[~out["well_captured"]]["dollars"].sum()
    out.attrs["note"] = (
        f"{round(100.0*poor/tot,1)}% of drug dollars are in codes a medical claims "
        f"panel captures poorly (pharmacy-benefit or self-administered). Those are "
        f"under-represented here relative to the true book.")
    return out


def implied_capture_band(std: pd.DataFrame, ref_dir=None, mapping=None) -> dict:
    """A transparent low/high band on what fraction of the TRUE book this file
    likely represents, by weighting visible dollars against per-channel capture
    postures. Returns the band and the assumptions behind it."""
    ch = channel_completeness(std, mapping=mapping)
    amt_total = float(_amount(std, mapping).sum()) or 1.0
    if "capture_low" not in ch.columns:
        return {"status": "insufficient", "note": ch.attrs.get("note", "")}
    # visible dollars in channel c came from a true book of visible/capture.
    # aggregate implied true book at the low and high capture bounds.
    lo_true = float((ch["dollars"] / ch["capture_high"]).sum())   # high capture -> smaller true book
    hi_true = float((ch["dollars"] / ch["capture_low"].replace(0, np.nan)).sum(min_count=1))
    if not np.isfinite(hi_true):
        # cash/invisible channels drive the true book to unbounded; cap and flag
        finite = ch[ch["capture_low"] > 0]
        hi_true = float((finite["dollars"] / finite["capture_low"]).sum())
        unbounded = True
    else:
        unbounded = False
    band_lo = round(amt_total / hi_true, 3) if hi_true > 0 else float("nan")
    band_hi = round(amt_total / lo_true, 3) if lo_true > 0 else float("nan")
    return {
        "status": "ok",
        "visible_dollars": round(amt_total, 2),
        "implied_capture_low": band_lo,
        "implied_capture_high": band_hi,
        "unbounded_from_invisible_channels": unbounded,
        "assumptions": _CHANNEL_POSTURE,
        "note": (
            f"This file likely represents roughly {int(band_lo*100)} to "
            f"{int(band_hi*100)} percent of the true book, based on the payer-"
            f"channel mix and structural capture postures for a medical claims "
            f"panel. "
            + ("A cash or federal channel is present, so the upper end is a floor: "
               "the true book could be larger still. " if unbounded else "")
            + "This is a framing band with stated assumptions, not a measured "
            "capture rate. Validate against the CIM before relying on it."),
    }


def capture_report(std: pd.DataFrame, ref_dir=None, mapping=None) -> dict:
    """Everything in one call."""
    return {
        "channel_completeness": channel_completeness(std, mapping=mapping),
        "drug_capture_flags": drug_capture_flags(std, ref_dir=ref_dir, mapping=mapping),
        "implied_capture_band": implied_capture_band(std, ref_dir=ref_dir, mapping=mapping),
    }
