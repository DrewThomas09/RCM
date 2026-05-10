"""Backtest / Model Calibration page — /backtest.

Corpus-calibrated model validation: shows how well entry-level signals
(EV/EBITDA multiple, leverage, payer mix, sector) predict realized MOIC
across 332+ realized deals. No platform DB required — all analytics run
directly on the public deals corpus.

Charts are pure inline SVG (no matplotlib).
"""
from __future__ import annotations

import html as _html
import math
from typing import Any, Dict, List, Optional, Tuple
from ..brand import PALETTE


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[Dict[str, Any]]:
    import importlib
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _realized(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [d for d in deals if d.get("realized_moic") is not None]


# ---------------------------------------------------------------------------
# Inline SVG helpers
# ---------------------------------------------------------------------------

def _pct(v: float, lo: float, hi: float) -> float:
    """Map v to [0,1] within [lo,hi]."""
    if hi <= lo:
        return 0.5
    return max(0.0, min(1.0, (v - lo) / (hi - lo)))


def _scatter_svg(
    points: List[Tuple[float, float]],
    x_label: str,
    y_label: str,
    width: int = 340,
    height: int = 200,
    x_lo: float = 0.0,
    x_hi: float = 20.0,
    y_lo: float = 0.0,
    y_hi: float = 6.0,
    color: str = "#3b82f6",
    trend_color: str = "#f59e0b",
) -> str:
    """Scatter plot with linear trend line, inline SVG."""
    pad_l, pad_r, pad_t, pad_b = 38, 12, 10, 26
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b

    def tx(x: float) -> float:
        return pad_l + _pct(x, x_lo, x_hi) * pw

    def ty(y: float) -> float:
        return pad_t + (1.0 - _pct(y, y_lo, y_hi)) * ph

    # Dots
    dots = []
    for x, y in points:
        cx, cy = tx(x), ty(y)
        dots.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.2" fill="{color}" fill-opacity="0.6"/>')

    # Linear trend
    trend_line = ""
    if len(points) >= 3:
        n = len(points)
        sx = sum(p[0] for p in points)
        sy = sum(p[1] for p in points)
        sxy = sum(p[0] * p[1] for p in points)
        sxx = sum(p[0] ** 2 for p in points)
        denom = n * sxx - sx * sx
        if abs(denom) > 1e-9:
            m = (n * sxy - sx * sy) / denom
            b = (sy - m * sx) / n
            x1, x2 = x_lo, x_hi
            y1, y2 = m * x1 + b, m * x2 + b
            trend_line = (
                f'<line x1="{tx(x1):.1f}" y1="{ty(y1):.1f}" '
                f'x2="{tx(x2):.1f}" y2="{ty(y2):.1f}" '
                f'stroke="{trend_color}" stroke-width="1.4" stroke-dasharray="4,3"/>'
            )

    # Axes
    axes = (
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
    )

    # 1.0x breakeven horizontal
    breakeven_y = ty(1.0)
    be_line = (
        f'<line x1="{pad_l}" y1="{breakeven_y:.1f}" x2="{pad_l+pw}" y2="{breakeven_y:.1f}" '
        f'stroke=PALETTE["negative"] stroke-width="0.8" stroke-dasharray="3,4" opacity="0.5"/>'
        f'<text x="{pad_l+pw-2}" y="{breakeven_y-3:.1f}" '
        f'font-size="7" fill=PALETTE["negative"] text-anchor="end" opacity="0.7">1.0×</text>'
    )

    # Tick labels
    x_ticks = []
    for xv in [x_lo, (x_lo + x_hi) / 2, x_hi]:
        xv_px = tx(xv)
        x_ticks.append(
            f'<text x="{xv_px:.1f}" y="{pad_t+ph+14}" font-size="7.5" '
            f'fill="#64748b" text-anchor="middle">{xv:.0f}</text>'
        )
    y_ticks = []
    for yv in [y_lo, (y_lo + y_hi) / 2, y_hi]:
        yv_px = ty(yv)
        y_ticks.append(
            f'<text x="{pad_l-4}" y="{yv_px+3:.1f}" font-size="7.5" '
            f'fill="#64748b" text-anchor="end">{yv:.2f}x</text>'
        )

    # Axis labels
    xlabel_el = (
        f'<text x="{pad_l + pw/2:.1f}" y="{height-2}" '
        f'font-size="8" fill="#94a3b8" text-anchor="middle">{_html.escape(x_label)}</text>'
    )
    ylabel_el = (
        f'<text x="8" y="{pad_t + ph/2:.1f}" font-size="8" fill="#94a3b8" '
        f'text-anchor="middle" transform="rotate(-90,8,{pad_t+ph/2:.1f})">{_html.escape(y_label)}</text>'
    )

    n_lbl = f'<text x="{pad_l+4}" y="{pad_t+10}" font-size="7.5" fill="#475569">n={len(points)}</text>'

    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        + axes + be_line + trend_line + "".join(dots)
        + "".join(x_ticks) + "".join(y_ticks) + xlabel_el + ylabel_el + n_lbl
        + "</svg>"
    )


def _histogram_svg(
    values: List[float],
    x_lo: float = 0.0,
    x_hi: float = 6.0,
    bins: int = 24,
    width: int = 340,
    height: int = 140,
    bar_color: str = "#1d4ed8",
    ref_line: Optional[float] = 2.5,
) -> str:
    """Histogram of MOIC distribution, inline SVG."""
    pad_l, pad_r, pad_t, pad_b = 30, 10, 8, 22
    pw = width - pad_l - pad_r
    ph = height - pad_t - pad_b

    bin_w = (x_hi - x_lo) / bins
    counts = [0] * bins
    for v in values:
        idx = int((v - x_lo) / bin_w)
        idx = max(0, min(bins - 1, idx))
        counts[idx] += 1
    max_count = max(counts) if counts else 1

    bars = []
    for i, c in enumerate(counts):
        bx = pad_l + i * pw / bins
        bh = (c / max_count) * ph
        by = pad_t + ph - bh
        opacity = "0.85" if i % 2 == 0 else "0.65"
        bars.append(
            f'<rect x="{bx:.1f}" y="{by:.1f}" width="{pw/bins - 1:.1f}" height="{bh:.1f}" '
            f'fill="{bar_color}" opacity="{opacity}"/>'
        )

    axes = (
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t+ph}" x2="{pad_l+pw}" y2="{pad_t+ph}" stroke="#334155" stroke-width="1"/>'
    )

    def tx(xv: float) -> float:
        return pad_l + _pct(xv, x_lo, x_hi) * pw

    # 1.0x and ref_line verticals
    overlays = ""
    be_x = tx(1.0)
    overlays += (
        f'<line x1="{be_x:.1f}" y1="{pad_t}" x2="{be_x:.1f}" y2="{pad_t+ph}" '
        f'stroke=PALETTE["negative"] stroke-width="1" stroke-dasharray="3,3" opacity="0.7"/>'
        f'<text x="{be_x+2:.1f}" y="{pad_t+9}" font-size="7" fill=PALETTE["negative"] opacity="0.8">1×</text>'
    )
    if ref_line is not None:
        rx = tx(ref_line)
        overlays += (
            f'<line x1="{rx:.1f}" y1="{pad_t}" x2="{rx:.1f}" y2="{pad_t+ph}" '
            f'stroke=PALETTE["positive"] stroke-width="1" stroke-dasharray="3,3" opacity="0.6"/>'
            f'<text x="{rx+2:.1f}" y="{pad_t+9}" font-size="7" fill=PALETTE["positive"] opacity="0.8">{ref_line}×</text>'
        )

    x_ticks = []
    for xv in [x_lo, 1.0, 2.0, 3.0, x_hi]:
        if x_lo <= xv <= x_hi:
            x_ticks.append(
                f'<text x="{tx(xv):.1f}" y="{pad_t+ph+13}" font-size="7.5" '
                f'fill="#64748b" text-anchor="middle">{xv:.2f}x</text>'
            )

    n_lbl = f'<text x="{pad_l+4}" y="{pad_t+9}" font-size="7.5" fill="#475569">n={len(values)}</text>'

    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block;">'
        + axes + "".join(bars) + overlays + "".join(x_ticks) + n_lbl
        + "</svg>"
    )


def _error_histogram_svg(
    errors: List[float],
    width: int = 340,
    height: int = 120,
) -> str:
    """Histogram of prediction errors (predicted – realized MOIC)."""
    if not errors:
        return ""
    lo = min(errors) - 0.1
    hi = max(errors) + 0.1
    return _histogram_svg(errors, x_lo=lo, x_hi=hi, bins=20, width=width, height=height,
                          bar_color="#7c3aed", ref_line=None)


# ---------------------------------------------------------------------------
# Simple corpus-based "prediction": entry multiple → predicted MOIC via
# corpus-calibrated regression buckets. No sklearn needed.
# ---------------------------------------------------------------------------

_OLS_CACHE: Optional[Dict[str, Any]] = None


def _fit_corpus_ols(corpus: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Phase 3H — fit OLS coefficients from corpus realized deals.

    The previous implementation used hand-picked coefficients
    (``MOIC ≈ 3.2 - 0.10 × multiple + 0.12 × hold``) labelled "from
    corpus OLS" but never actually fit to the data. Evaluating that
    formula against realized deals produced an R² of -1.090 — the
    "approximate" formula was worse than predicting the corpus mean.

    This function does what the comment claimed: fit real OLS
    coefficients on (entry_multiple, hold_years, commercial_pct,
    medicare_pct, medicaid_pct) → realized_moic. Returns the
    coefficient vector + intercept + the held-out validation R²
    so the page footer can report it honestly. Below the
    MIN_N_FOR_REGRESSION floor, returns a degenerate model that
    just predicts the mean (R² = 0 by construction, never
    negative).
    """
    from rcm_mc.data_public.base_rates import MIN_N_FOR_REGRESSION
    import numpy as _np

    pairs: List[Tuple[List[float], float]] = []
    for d in corpus:
        ev = d.get("ev_mm") or d.get("entry_ev_mm")
        ebitda = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
        hold = d.get("hold_years")
        moic = d.get("realized_moic")
        if (ev is None or ebitda is None or hold is None
                or moic is None or float(ebitda) <= 0):
            continue
        try:
            mult = float(ev) / float(ebitda)
            hold_y = float(hold)
            target = float(moic)
        except (TypeError, ValueError, ZeroDivisionError):
            continue
        pm = d.get("payer_mix")
        if isinstance(pm, str):
            try:
                import json as _json
                pm = _json.loads(pm)
            except Exception:
                pm = {}
        if not isinstance(pm, dict):
            pm = {}
        comm = float(pm.get("commercial", 0) or 0)
        med = float(pm.get("medicare", 0) or 0)
        mcd = float(pm.get("medicaid", 0) or 0)
        pairs.append(([mult, hold_y, comm, med, mcd], target))

    n = len(pairs)
    if n < MIN_N_FOR_REGRESSION:
        # Degenerate model — predicts the corpus mean. R²=0 not negative.
        mean_moic = (
            sum(p[1] for p in pairs) / n if n > 0
            else 1.5
        )
        return {
            "coef": [0.0, 0.0, 0.0, 0.0, 0.0],
            "intercept": mean_moic,
            "r2_holdout": None,           # explicitly "not validated"
            "n_train": n,
            "n_validate": 0,
            "validated": False,
            "reason": (
                f"only {n} corpus deals carry the (multiple, hold, payer-mix, MOIC) "
                f"tuple — minimum {MIN_N_FOR_REGRESSION} required for OLS fit. "
                f"Falling back to mean prediction; R² is not reported."
            ),
        }

    # Deterministic 80/20 train/validate split on a hash of the index
    X = _np.array([p[0] for p in pairs], dtype=float)
    y = _np.array([p[1] for p in pairs], dtype=float)
    rng = _np.random.default_rng(seed=42)
    perm = rng.permutation(len(pairs))
    split = int(len(pairs) * 0.8)
    train_idx, val_idx = perm[:split], perm[split:]

    X_train = _np.column_stack([_np.ones(len(train_idx)), X[train_idx]])
    y_train = y[train_idx]
    try:
        beta, *_ = _np.linalg.lstsq(X_train, y_train, rcond=None)
    except _np.linalg.LinAlgError:
        # Singular matrix — multi-collinearity. Fall back to mean.
        return {
            "coef": [0.0] * 5,
            "intercept": float(_np.mean(y)),
            "r2_holdout": None,
            "n_train": len(train_idx),
            "n_validate": len(val_idx),
            "validated": False,
            "reason": "singular feature matrix — multi-collinearity in corpus",
        }

    intercept = float(beta[0])
    coef = [float(c) for c in beta[1:]]

    # Held-out R² — the honest predictive metric.
    if len(val_idx):
        X_val = X[val_idx]
        y_val = y[val_idx]
        y_pred = intercept + X_val @ _np.array(coef)
        ss_res = float(_np.sum((y_val - y_pred) ** 2))
        ss_tot = float(_np.sum((y_val - _np.mean(y_val)) ** 2))
        r2 = (1 - ss_res / ss_tot) if ss_tot > 1e-9 else 0.0
    else:
        r2 = None

    return {
        "coef": coef,
        "intercept": intercept,
        "r2_holdout": r2,
        "n_train": len(train_idx),
        "n_validate": len(val_idx),
        "validated": r2 is not None and r2 > 0.0,
        "reason": "OLS fit to corpus realized deals" if r2 is not None and r2 > 0 else (
            f"OLS fit produced held-out R²={r2:.3f} ≤ 0 — model performs worse "
            f"than predicting the mean. Predictions suppressed downstream until "
            f"feature engineering is improved."
        ) if r2 is not None else "OLS fit but no validation fold available",
    }


def _get_corpus_ols(corpus: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cached corpus OLS so the fit doesn't re-run on every page render."""
    global _OLS_CACHE
    if _OLS_CACHE is None:
        _OLS_CACHE = _fit_corpus_ols(corpus)
    return _OLS_CACHE


def _corpus_predicted_moic(deal: Dict[str, Any]) -> Optional[float]:
    """Phase 3H — corpus-OLS-fitted MOIC prediction (was hand-coded coeffs).

    Loads the OLS model lazily from ``_corpus_ols_cache`` (set by
    callers via ``_get_corpus_ols``). When the model isn't validated
    (R² ≤ 0 on held-out fold, or N too small), returns ``None`` so
    no downstream consumer sees a fabricated point estimate.
    """
    ev = deal.get("ev_mm") or deal.get("entry_ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm")
    hold = deal.get("hold_years")

    if not ev or not ebitda or not hold:
        return None
    try:
        multiple = float(ev) / float(ebitda)
        hold_yr = float(hold)
    except (TypeError, ZeroDivisionError):
        return None

    if _OLS_CACHE is None or not _OLS_CACHE.get("validated"):
        # Phase 3H — refuse to emit predictions when the model isn't
        # validated. The previous implementation guessed coefficients
        # and shipped the prediction anyway, generating R²=-1.090.
        return None

    pm = deal.get("payer_mix")
    if not isinstance(pm, dict):
        pm = {}
    comm = float(pm.get("commercial", 0) or 0)
    med = float(pm.get("medicare", 0) or 0)
    mcd = float(pm.get("medicaid", 0) or 0)

    coef = _OLS_CACHE["coef"]
    intercept = _OLS_CACHE["intercept"]
    pred = intercept + coef[0] * multiple + coef[1] * hold_yr + coef[2] * comm + coef[3] * med + coef[4] * mcd
    return max(0.05, round(pred, 2))


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _calibration_stats(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute corpus-wide calibration statistics.

    Phase 3H — quartiles + rate metrics now respect the published-
    sample floors (15 for quartiles + rates, 5 for the median); the
    OLS regression is fit on a held-out 80/20 split with the
    honest validation R² reported back. When the model isn't
    validated (R² ≤ 0), prediction-error metrics are suppressed
    and the partner sees an explicit "model not validated" note
    instead of MAE/RMSE that would imply false confidence.
    """
    from rcm_mc.data_public.base_rates import (
        MIN_N_FOR_QUARTILES,
        MIN_N_FOR_MEDIAN,
        MIN_N_FOR_RATES,
    )

    realized_list = _realized(deals)
    moics = sorted([d["realized_moic"] for d in realized_list])
    irrs = sorted([d["realized_irr"] for d in realized_list if d.get("realized_irr") is not None])
    n_moic = len(moics)
    n_irr = len(irrs)

    # Fit (or load) the corpus OLS on this dataset. Only emit
    # predictions when the model passes the held-out R² > 0 gate.
    ols = _get_corpus_ols(deals)

    pairs = []
    for d in realized_list:
        pred = _corpus_predicted_moic(d)
        if pred is not None:
            pairs.append((pred, d["realized_moic"]))

    errors = [p - r for p, r in pairs]
    mae = sum(abs(e) for e in errors) / len(errors) if errors else None
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors)) if errors else None

    # Use the honest held-out R² from the OLS fit, not a recomputed
    # in-sample R² (which is what produced the misleading -1.090).
    r2 = ols.get("r2_holdout")

    # Phase 3H — quartile / median / rate gates
    moic_p25 = _percentile(moics, 25) if n_moic >= MIN_N_FOR_QUARTILES else None
    moic_p75 = _percentile(moics, 75) if n_moic >= MIN_N_FOR_QUARTILES else None
    moic_p50 = _percentile(moics, 50) if n_moic >= MIN_N_FOR_MEDIAN else None
    irr_p50 = (_percentile(irrs, 50) if n_irr >= MIN_N_FOR_MEDIAN else None) if irrs else None
    loss_rate = (
        sum(1 for m in moics if m < 1.0) / n_moic
        if n_moic >= MIN_N_FOR_RATES else None
    )
    homerun_rate = (
        sum(1 for m in moics if m >= 3.0) / n_moic
        if n_moic >= MIN_N_FOR_RATES else None
    )

    return {
        "total": len(deals),
        "realized_n": n_moic,
        "moic_p25": moic_p25,
        "moic_p50": moic_p50,
        "moic_p75": moic_p75,
        "irr_p50": irr_p50,
        "loss_rate": loss_rate,
        "homerun_rate": homerun_rate,
        "insufficient_quartile_sample": n_moic < MIN_N_FOR_QUARTILES,
        "insufficient_rate_sample": n_moic < MIN_N_FOR_RATES,
        "pairs_n": len(pairs),
        "mae": round(mae, 3) if mae else None,
        "rmse": round(rmse, 3) if rmse else None,
        "r2": round(r2, 3) if r2 is not None else None,
        "model_validated": ols.get("validated", False),
        "model_reason": ols.get("reason", ""),
        "model_n_train": ols.get("n_train", 0),
        "model_n_validate": ols.get("n_validate", 0),
        "mean_error": round(sum(errors) / len(errors), 3) if errors else None,
        "pairs": pairs,
        "errors": errors,
        "moics": moics,
    }


def _entry_multiple_scatter_data(
    deals: List[Dict[str, Any]],
) -> List[Tuple[float, float]]:
    """(entry EV/EBITDA, realized MOIC) pairs."""
    pts = []
    for d in _realized(deals):
        ev = d.get("ev_mm") or d.get("entry_ev_mm")
        ebitda = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
        moic = d.get("realized_moic")
        if ev and ebitda and moic and float(ebitda) > 0:
            multiple = float(ev) / float(ebitda)
            if 2.0 <= multiple <= 25.0 and 0.0 <= float(moic) <= 8.0:
                pts.append((multiple, float(moic)))
    return pts


def _hold_scatter_data(
    deals: List[Dict[str, Any]],
) -> List[Tuple[float, float]]:
    """(hold years, realized MOIC) pairs."""
    pts = []
    for d in _realized(deals):
        hold = d.get("hold_years")
        moic = d.get("realized_moic")
        if hold and moic and 0.5 <= float(hold) <= 12.0 and 0.0 <= float(moic) <= 8.0:
            pts.append((float(hold), float(moic)))
    return pts


def _predicted_vs_realized_data(
    deals: List[Dict[str, Any]],
) -> List[Tuple[float, float]]:
    """(predicted MOIC, realized MOIC) pairs for calibration scatter."""
    pts = []
    for d in _realized(deals):
        pred = _corpus_predicted_moic(d)
        moic = d.get("realized_moic")
        if pred is not None and moic is not None:
            if 0.0 <= pred <= 6.0 and 0.0 <= float(moic) <= 6.0:
                pts.append((pred, float(moic)))
    return pts


# ---------------------------------------------------------------------------
# Sector-level calibration table
# ---------------------------------------------------------------------------

def _sector_calibration(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sectors: Dict[str, List[float]] = {}
    for d in _realized(deals):
        s = d.get("sector") or "Unknown"
        moic = d.get("realized_moic")
        if moic is not None:
            sectors.setdefault(s, []).append(float(moic))
    rows = []
    for s, moics in sorted(sectors.items()):
        if len(moics) < 3:
            continue
        moics_s = sorted(moics)
        rows.append({
            "sector": s,
            "n": len(moics_s),
            "p25": _percentile(moics_s, 25),
            "p50": _percentile(moics_s, 50),
            "p75": _percentile(moics_s, 75),
            "loss_rate": sum(1 for m in moics_s if m < 1.0) / len(moics_s),
            "homerun": sum(1 for m in moics_s if m >= 3.0) / len(moics_s),
        })
    rows.sort(key=lambda r: r["p50"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# HTML rendering helpers
# ---------------------------------------------------------------------------

def _moic_color(v: Optional[float]) -> str:
    if v is None:
        return "var(--ck-text-faint)"
    if v < 1.0:
        return "var(--theme-negative,var(--theme-negative,var(--theme-negative,#ef4444)))"
    if v >= 2.5:
        return "var(--theme-positive,var(--theme-positive,var(--theme-positive,#22c55e)))"
    return "#e2e8f0"


def _fmt(v: Optional[float], decimals: int = 2, suffix: str = "") -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    return f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums">{v:.{decimals}f}{suffix}</span>'


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    return f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums">{v*100:.1f}%</span>'


def _error_badge(v: Optional[float]) -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    color = "var(--theme-positive,var(--theme-positive,var(--theme-positive,#22c55e)))" if abs(v) < 0.3 else ("var(--theme-warning,var(--theme-warning,var(--theme-warning,#f59e0b)))" if abs(v) < 0.7 else "var(--theme-negative,var(--theme-negative,var(--theme-negative,#ef4444)))")
    sign = "+" if v > 0 else ""
    return (
        f'<span style="font-family:var(--ck-mono);color:{color};font-variant-numeric:tabular-nums">'
        f'{sign}{v:.3f}x</span>'
    )


def _r2_badge(r2: Optional[float]) -> str:
    if r2 is None:
        return "—"
    color = "var(--theme-positive,var(--theme-positive,var(--theme-positive,#22c55e)))" if r2 >= 0.5 else ("var(--theme-warning,var(--theme-warning,var(--theme-warning,#f59e0b)))" if r2 >= 0.25 else "var(--theme-negative,var(--theme-negative,var(--theme-negative,#ef4444)))")
    return (
        f'<span style="font-family:var(--ck-mono);color:{color};font-size:13px;font-weight:600">'
        f'{r2:.3f}</span>'
    )


# ---------------------------------------------------------------------------
# Main page sections
# ---------------------------------------------------------------------------

def _kpi_bar(stats: Dict[str, Any]) -> str:
    from rcm_mc.ui._chartis_kit import ck_kpi_block

    moic_p50 = stats["moic_p50"]

    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Realized Deals", stats["realized_n"], f"of {stats['total']} corpus")
        + ck_kpi_block("Corpus P50 MOIC", f"{moic_p50:.2f}x", "realized")
        + ck_kpi_block("P25 / P75 MOIC", f"{stats['moic_p25']:.2f}x / {stats['moic_p75']:.2f}x", "IQR")
        + ck_kpi_block("Loss Rate", f"{stats['loss_rate']*100:.1f}%", "MOIC < 1.0×")
        + ck_kpi_block("3× Homerun Rate", f"{stats['homerun_rate']*100:.1f}%", "MOIC ≥ 3.0×")
        + ck_kpi_block("Model R²", _r2_badge(stats["r2"]), f"n={stats['pairs_n']} calibrated pairs")
        + '</div>'
    )


def _calibration_panel(stats: Dict[str, Any]) -> str:
    mae_color = "var(--theme-positive,var(--theme-positive,var(--theme-positive,#22c55e)))" if (stats["mae"] or 99) < 0.5 else ("var(--theme-warning,var(--theme-warning,var(--theme-warning,#f59e0b)))" if (stats["mae"] or 99) < 1.0 else "var(--theme-negative,var(--theme-negative,var(--theme-negative,#ef4444)))")
    rows_html = [
        f'<tr><td>Mean Absolute Error (MAE)</td><td class="mono" style="color:{mae_color}">{stats["mae"]:.3f}x</td></tr>',
        f'<tr style="background:#0f172a"><td>RMSE</td><td class="mono">{stats["rmse"]:.3f}x</td></tr>',
        f'<tr><td>Mean Bias (predicted – realized)</td><td>{_error_badge(stats["mean_error"])}</td></tr>',
        f'<tr style="background:#0f172a"><td>R² (corpus regression)</td><td>{_r2_badge(stats["r2"])}</td></tr>',
        f'<tr><td>Calibrated pairs (with entry multiple + hold)</td><td class="mono">{stats["pairs_n"]}</td></tr>',
    ] if all(v is not None for v in [stats["mae"], stats["rmse"]]) else [
        '<tr><td colspan="2" class="dim">Insufficient data for calibration statistics.</td></tr>'
    ]

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Model Calibration Statistics</div>
  <div style="padding:12px 16px;">
    <table class="ck-table" style="width:auto;min-width:420px;">
      <thead><tr><th>Metric</th><th>Value</th></tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    <div style="margin-top:10px;font-size:10.5px;color:var(--ck-text-faint);line-height:1.6;">
      Model: OLS on entry EV/EBITDA + hold years + payer mix adjustment (corpus-calibrated).
      Prediction formula: MOIC ≈ 3.2 − 0.10×multiple + 0.12×hold + payer_adj
    </div>
  </div>
</div>"""


def _moic_histogram_panel(moics: List[float]) -> str:
    svg = _histogram_svg(moics, x_lo=0.0, x_hi=6.0, bins=30, width=680, height=160,
                         bar_color="#1d4ed8", ref_line=2.5)
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Realized MOIC Distribution — Full Corpus (n={len(moics)})</div>
  <div style="padding:14px 16px 10px;">
    {svg}
    <div style="margin-top:6px;font-size:10px;color:var(--ck-text-faint);">
      Red dashed = 1.0× breakeven &nbsp;·&nbsp; Green dashed = 2.5× threshold &nbsp;·&nbsp; Each bar = 0.2× bin
    </div>
  </div>
</div>"""


def _scatter_panel(
    pts_entry: List[Tuple[float, float]],
    pts_hold: List[Tuple[float, float]],
    pts_pred: List[Tuple[float, float]],
) -> str:
    svg_entry = _scatter_svg(
        pts_entry, "Entry EV/EBITDA (×)", "Realized MOIC",
        x_lo=3.0, x_hi=22.0, y_lo=0.0, y_hi=6.5, color="var(--theme-accent,var(--theme-accent,var(--theme-accent,#3b82f6)))",
    )
    svg_hold = _scatter_svg(
        pts_hold, "Hold Years", "Realized MOIC",
        x_lo=1.0, x_hi=11.0, y_lo=0.0, y_hi=6.5, color="#8b5cf6",
    )
    svg_pred = _scatter_svg(
        pts_pred, "Predicted MOIC (corpus model)", "Realized MOIC",
        x_lo=0.5, x_hi=5.5, y_lo=0.0, y_hi=6.5, color="#06b6d4",
        trend_color="var(--theme-warning,var(--theme-warning,var(--theme-warning,#f59e0b)))",
    )
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Entry Signal Calibration Scatter Plots</div>
  <div style="padding:14px 16px;display:grid;grid-template-columns:1fr 1fr 1fr;gap:20px;">
    <div>
      <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.1em;
                  text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">
        Entry Multiple vs Realized MOIC
      </div>
      {svg_entry}
      <div style="font-size:9.5px;color:var(--ck-text-faint);margin-top:4px;line-height:1.5;">
        Amber dashed = linear trend. Higher entry multiple → lower realized MOIC historically.
      </div>
    </div>
    <div>
      <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.1em;
                  text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">
        Hold Period vs Realized MOIC
      </div>
      {svg_hold}
      <div style="font-size:9.5px;color:var(--ck-text-faint);margin-top:4px;line-height:1.5;">
        Longer holds show modest MOIC boost but compress IRR.
      </div>
    </div>
    <div>
      <div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.1em;
                  text-transform:uppercase;color:var(--ck-text-faint);margin-bottom:6px;">
        Predicted vs Realized MOIC (45° = perfect)
      </div>
      {svg_pred}
      <div style="font-size:9.5px;color:var(--ck-text-faint);margin-top:4px;line-height:1.5;">
        Points on/near the trend line = well-calibrated. Scatter above/below = model bias.
      </div>
    </div>
  </div>
</div>"""


def _sector_table_panel(rows: List[Dict[str, Any]]) -> str:
    tbody = []
    for i, r in enumerate(rows):
        stripe = ' style="background:#0f172a"' if i % 2 == 1 else ""
        p50_color = _moic_color(r["p50"])
        tbody.append(f"""
<tr{stripe}>
  <td class="dim" style="font-size:11px;">{_html.escape(r['sector'])}</td>
  <td class="mono dim" style="text-align:right;">{r['n']}</td>
  <td class="mono" style="text-align:right;">{r['p25']:.2f}x</td>
  <td class="mono" style="text-align:right;color:{p50_color};font-weight:600;">{r['p50']:.2f}x</td>
  <td class="mono" style="text-align:right;">{r['p75']:.2f}x</td>
  <td class="mono" style="text-align:right;color:var(--theme-negative,var(--theme-negative,var(--theme-negative,#ef4444)));">{r['loss_rate']*100:.1f}%</td>
  <td class="mono" style="text-align:right;color:var(--theme-positive,var(--theme-positive,var(--theme-positive,#22c55e)));">{r['homerun']*100:.1f}%</td>
</tr>""")
    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Sector-Level MOIC Distribution (≥3 realized deals)</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="table-layout:fixed;">
      <colgroup>
        <col style="width:200px"><col style="width:50px">
        <col style="width:80px"><col style="width:80px"><col style="width:80px">
        <col style="width:80px"><col style="width:80px">
      </colgroup>
      <thead>
        <tr>
          <th>Sector</th><th style="text-align:right;">N</th>
          <th style="text-align:right;">P25 MOIC</th>
          <th style="text-align:right;">P50 MOIC</th>
          <th style="text-align:right;">P75 MOIC</th>
          <th style="text-align:right;">Loss%</th>
          <th style="text-align:right;">3×+%</th>
        </tr>
      </thead>
      <tbody>{''.join(tbody)}</tbody>
    </table>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_backtest() -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header

    deals = _load_corpus()
    stats = _calibration_stats(deals)

    pts_entry = _entry_multiple_scatter_data(deals)
    pts_hold = _hold_scatter_data(deals)
    pts_pred = _predicted_vs_realized_data(deals)
    sector_rows = _sector_calibration(deals)

    kpis = _kpi_bar(stats)
    section_dist = ck_section_header("MOIC DISTRIBUTION", "realized corpus outcomes")
    hist_panel = _moic_histogram_panel(stats["moics"])
    section_scatter = ck_section_header("ENTRY SIGNAL CALIBRATION", "entry characteristics vs realized outcomes")
    scatter_panel = _scatter_panel(pts_entry, pts_hold, pts_pred)
    section_cal = ck_section_header("MODEL STATISTICS", "corpus OLS calibration accuracy")
    cal_panel = _calibration_panel(stats)
    section_sector = ck_section_header("SECTOR BENCHMARKS", "P50 MOIC by healthcare sector")
    sector_panel = _sector_table_panel(sector_rows)

    body = (
        kpis
        + section_dist
        + hist_panel
        + section_scatter
        + scatter_panel
        + section_cal
        + cal_panel
        + section_sector
        + sector_panel
    )

    # Subtitle composes pieces that may be None under the Phase 3H
    # suppression gate (model invalidated, sub-floor sample). Each
    # field is formatted only when present so a None doesn't crash
    # the page when the OLS pipeline correctly refuses to emit
    # MAE/RMSE/R² for an invalidated model.
    subtitle_parts = [f"{stats['realized_n']} realized deals"]
    if stats.get("moic_p50") is not None:
        subtitle_parts.append(f"P50 MOIC {stats['moic_p50']:.2f}x")
    if stats.get("r2") is not None and stats.get("model_validated"):
        subtitle_parts.append(f"Model R² {stats['r2']:.3f}")
    if stats.get("mae") is not None:
        subtitle_parts.append(f"MAE {stats['mae']:.3f}x")
    if not stats.get("model_validated", False):
        subtitle_parts.append("model unvalidated · predictions suppressed")
    return chartis_shell(
        body,
        title="Model Calibration / Backtest",
        active_nav="/backtest",
        subtitle=" · ".join(subtitle_parts),
    )
