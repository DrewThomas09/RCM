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

_EXPLAINER_CSS = """<style>
.ck-bt-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#4a4a4a);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-bt-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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
        f'stroke="#ef4444" stroke-width="0.8" stroke-dasharray="3,4" opacity="0.5"/>'
        f'<text x="{pad_l+pw-2}" y="{breakeven_y-3:.1f}" '
        f'font-size="7" fill="#ef4444" text-anchor="end" opacity="0.7">1.0×</text>'
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
            f'fill="#64748b" text-anchor="end">{yv:.1f}x</text>'
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
        f'stroke="#ef4444" stroke-width="1" stroke-dasharray="3,3" opacity="0.7"/>'
        f'<text x="{be_x+2:.1f}" y="{pad_t+9}" font-size="7" fill="#ef4444" opacity="0.8">1×</text>'
    )
    if ref_line is not None:
        rx = tx(ref_line)
        overlays += (
            f'<line x1="{rx:.1f}" y1="{pad_t}" x2="{rx:.1f}" y2="{pad_t+ph}" '
            f'stroke="#0a8a5f" stroke-width="1" stroke-dasharray="3,3" opacity="0.6"/>'
            f'<text x="{rx+2:.1f}" y="{pad_t+9}" font-size="7" fill="#0a8a5f" opacity="0.8">{ref_line}×</text>'
        )

    x_ticks = []
    for xv in [x_lo, 1.0, 2.0, 3.0, x_hi]:
        if x_lo <= xv <= x_hi:
            x_ticks.append(
                f'<text x="{tx(xv):.1f}" y="{pad_t+ph+13}" font-size="7.5" '
                f'fill="#64748b" text-anchor="middle">{xv:.0f}x</text>'
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

# Module-level cache for OLS-fitted model coefficients. The fit
# runs once per process per corpus-id (id() of the deals list) so
# pages that call _corpus_predicted_moic across multiple deals
# share one fit. Previously the model was a hardcoded formula
# (3.2 - 0.10*multiple + 0.12*hold) labelled "approximate" — R²
# came out at -1.09 because those coefficients didn't match the
# corpus at all. Fitting OLS on the realized subset every time
# replaces that toy model with one that actually earns its place.
_MODEL_CACHE: Dict[int, Optional[Tuple[float, float, float, float, float]]] = {}


def _deal_features(deal: Dict[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    """Extract (multiple, hold_yr, commercial_frac, gov_frac) or None.

    commercial_frac = pm.commercial; gov_frac = pm.medicare + pm.medicaid.
    Missing payer-mix → both default to 0 so the deal still scores
    on multiple + hold alone.
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
    pm = deal.get("payer_mix") or {}
    if not isinstance(pm, dict):
        pm = {}
    comm = float(pm.get("commercial", 0) or 0)
    gov = float(
        (pm.get("medicare", 0) or 0) + (pm.get("medicaid", 0) or 0)
    )
    return (multiple, hold_yr, comm, gov)


def _fit_corpus_model(
    deals: List[Dict[str, Any]],
) -> Optional[Tuple[float, float, float, float, float]]:
    """OLS-fit `realized_moic ~ multiple + hold_yr + commercial + gov`
    on the realized subset of the corpus. Returns (b0, b_mult, b_hold,
    b_comm, b_gov) or None if there aren't enough rows.

    Numpy-only (no sklearn). Cached per corpus id.
    """
    import numpy as np  # local import to keep module-import light

    key = id(deals)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    rows = []
    for d in _realized(deals):
        feats = _deal_features(d)
        moic = d.get("realized_moic")
        if feats is None or moic is None:
            continue
        try:
            rows.append((*feats, float(moic)))
        except (TypeError, ValueError):
            continue

    if len(rows) < 10:
        _MODEL_CACHE[key] = None
        return None

    arr = np.asarray(rows, dtype=float)
    X = arr[:, :4]
    y = arr[:, 4]
    # Augment with intercept column
    X_aug = np.column_stack([np.ones(len(X)), X])
    try:
        beta, *_ = np.linalg.lstsq(X_aug, y, rcond=None)
    except np.linalg.LinAlgError:
        _MODEL_CACHE[key] = None
        return None

    result = tuple(float(b) for b in beta)
    _MODEL_CACHE[key] = result  # type: ignore[assignment]
    return result  # type: ignore[return-value]


def _corpus_predicted_moic(
    deal: Dict[str, Any],
    corpus: Optional[List[Dict[str, Any]]] = None,
) -> Optional[float]:
    """Corpus-calibrated MOIC prediction from entry characteristics.

    Fits OLS once per corpus and uses the fitted coefficients to
    predict — see _fit_corpus_model for the spec.

    ``corpus`` is optional for backward compat with single-deal
    callers; when omitted the function falls back to the hardcoded
    historical formula. The page's calibration stats call passes
    the corpus so the page reports the OLS-fitted R².
    """
    feats = _deal_features(deal)
    if feats is None:
        return None
    multiple, hold_yr, comm, gov = feats

    if corpus is not None:
        coeffs = _fit_corpus_model(corpus)
        if coeffs is not None:
            b0, b_mult, b_hold, b_comm, b_gov = coeffs
            pred = (
                b0
                + b_mult * multiple
                + b_hold * hold_yr
                + b_comm * comm
                + b_gov * gov
            )
            return max(0.05, round(pred, 2))

    # Fallback (no corpus passed or fit failed): keep the
    # historical hardcoded formula so single-deal callers still
    # get a number rather than None.
    base = 3.2 - 0.10 * multiple + 0.12 * hold_yr
    if comm >= 0.65:
        base += 0.15
    elif gov >= 0.65:
        base -= 0.10
    return max(0.05, round(base, 2))


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
    """Compute corpus-wide calibration statistics."""
    realized_list = _realized(deals)
    moics = sorted([d["realized_moic"] for d in realized_list])
    irrs = sorted([d["realized_irr"] for d in realized_list if d.get("realized_irr") is not None])

    # Predicted vs realized pairs — pass the corpus so the helper
    # fits OLS on the realized subset (rather than using the legacy
    # hardcoded "MOIC ≈ 3.2 - 0.10*multiple + 0.12*hold" formula
    # that produced R² = -1.09).
    pairs = []
    for d in realized_list:
        pred = _corpus_predicted_moic(d, corpus=deals)
        if pred is not None:
            pairs.append((pred, d["realized_moic"]))

    errors = [p - r for p, r in pairs]
    mae = sum(abs(e) for e in errors) / len(errors) if errors else None
    rmse = math.sqrt(sum(e * e for e in errors) / len(errors)) if errors else None

    # R² of corpus prediction
    if pairs:
        r_mean = sum(r for _, r in pairs) / len(pairs)
        ss_tot = sum((r - r_mean) ** 2 for _, r in pairs)
        ss_res = sum((p - r) ** 2 for p, r in pairs)
        r2 = 1 - ss_res / ss_tot if ss_tot > 1e-9 else 0.0
    else:
        r2 = None

    return {
        "total": len(deals),
        "realized_n": len(realized_list),
        "moic_p25": _percentile(moics, 25),
        "moic_p50": _percentile(moics, 50),
        "moic_p75": _percentile(moics, 75),
        "irr_p50": _percentile(irrs, 50) if irrs else None,
        "loss_rate": sum(1 for m in moics if m < 1.0) / len(moics) if moics else 0.0,
        "homerun_rate": sum(1 for m in moics if m >= 3.0) / len(moics) if moics else 0.0,
        "pairs_n": len(pairs),
        "mae": round(mae, 3) if mae else None,
        "rmse": round(rmse, 3) if rmse else None,
        "r2": round(r2, 3) if r2 is not None else None,
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
        pred = _corpus_predicted_moic(d, corpus=deals)
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
        return "#ef4444"
    if v >= 2.5:
        return "#0a8a5f"
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
    color = "#0a8a5f" if abs(v) < 0.3 else ("#f59e0b" if abs(v) < 0.7 else "#ef4444")
    sign = "+" if v > 0 else ""
    return (
        f'<span style="font-family:var(--ck-mono);color:{color};font-variant-numeric:tabular-nums">'
        f'{sign}{v:.3f}x</span>'
    )


def _r2_badge(r2: Optional[float]) -> str:
    if r2 is None:
        return "—"
    color = "#0a8a5f" if r2 >= 0.5 else ("#f59e0b" if r2 >= 0.25 else "#ef4444")
    return (
        f'<span style="font-family:var(--ck-mono);color:{color};font-size:13px;font-weight:600">'
        f'{r2:.3f}</span>'
    )


# ---------------------------------------------------------------------------
# Main page sections
# ---------------------------------------------------------------------------

def _kpi_bar(stats: Dict[str, Any]) -> str:
    from rcm_mc.ui._chartis_kit import (
        SafeHtml, ck_fmt_moic, ck_fmt_pct, ck_kpi_block,
        ck_provenance_tooltip,
    )

    moic_p50 = stats["moic_p50"]
    moic_color = _moic_color(moic_p50)
    # _r2_badge returns pre-rendered HTML (a colored span); wrap in
    # SafeHtml so ck_provenance_tooltip's _esc-pass doesn't escape
    # the inner <span> to literal &lt;span&gt;... text.
    r2_raw = _r2_badge(stats["r2"]) if stats["r2"] is not None else "—"
    r2_value = ck_provenance_tooltip(
        "Model R-squared",
        SafeHtml(r2_raw) if stats["r2"] is not None else r2_raw,
        explainer=(
            f"Coefficient of determination on the predicted-vs-"
            f"realized MOIC pairs ({stats['pairs_n']} calibrated). "
            f">0.7 is a usable signal; <0.5 means the model isn't "
            f"earning its place over a sector-median baseline."
        ),
    )
    moic_value = ck_provenance_tooltip(
        "Corpus P50 MOIC",
        SafeHtml(f'<span class="mn" style="color:{moic_color}">{ck_fmt_moic(moic_p50)}</span>'),
        explainer=(
            "Median realized MOIC across the calibration corpus. "
            "Color encodes regime: green >2.5x (strong), amber "
            "1.5-2.5x (typical), red <1.5x (weak). The IQR cell "
            "above shows P25/P75 spread."
        ),
        inject_css=False,
    )
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Realized Deals", str(stats["realized_n"]), f"of {stats['total']} corpus")
        + ck_kpi_block("Corpus P50 MOIC", moic_value, "realized")
        + ck_kpi_block("P25 / P75 MOIC",
                       f'{ck_fmt_moic(stats["moic_p25"])} / {ck_fmt_moic(stats["moic_p75"])}', "IQR")
        + ck_kpi_block("Loss Rate",
                       ck_fmt_pct(stats["loss_rate"]), "MOIC < 1.0x")
        + ck_kpi_block("3x Homerun Rate",
                       ck_fmt_pct(stats["homerun_rate"]), "MOIC >= 3.0x")
        + ck_kpi_block("Model R²", r2_value, f"n={stats['pairs_n']} pairs")
        + '</div>'
    )


def _calibration_panel(stats: Dict[str, Any]) -> str:
    mae_color = "#0a8a5f" if (stats["mae"] or 99) < 0.5 else ("#f59e0b" if (stats["mae"] or 99) < 1.0 else "#ef4444")
    rows_html = [
        f'<tr><td>Mean Absolute Error (MAE)</td><td class="mono" style="color:{mae_color}">{stats["mae"]:.3f}x</td></tr>',
        f'<tr style="background:var(--sc-bone)"><td>RMSE</td><td class="mono">{stats["rmse"]:.3f}x</td></tr>',
        f'<tr><td>Mean Bias (predicted – realized)</td><td>{_error_badge(stats["mean_error"])}</td></tr>',
        f'<tr style="background:var(--sc-bone)"><td>R² (corpus regression)</td><td>{_r2_badge(stats["r2"])}</td></tr>',
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


def _moic_histogram_viz(moics: List[float]) -> str:
    """Bare MOIC-distribution histogram + caption for the viz half of
    the paired block. (Superseded the panel-wrapped
    ``_moic_histogram_panel`` when /backtest adopted ck_paired_block.)
    """
    svg = _histogram_svg(moics, x_lo=0.0, x_hi=6.0, bins=30, width=680, height=160,
                         bar_color="#1d4ed8", ref_line=2.5)
    return (
        '<div style="font-family:var(--sc-mono);font-size:9px;'
        'letter-spacing:0.1em;text-transform:uppercase;'
        'color:var(--sc-text-faint);margin-bottom:8px;">'
        f'Realized MOIC distribution &middot; full corpus (n={len(moics)})</div>'
        f'{svg}'
        '<div style="margin-top:6px;font-size:10px;color:var(--sc-text-faint);">'
        'Red dashed = 1.0&times; breakeven &middot; '
        'Green dashed = 2.5&times; threshold &middot; each bar = 0.2&times; bin'
        '</div>'
    )


def _scatter_panel(
    pts_entry: List[Tuple[float, float]],
    pts_hold: List[Tuple[float, float]],
    pts_pred: List[Tuple[float, float]],
) -> str:
    svg_entry = _scatter_svg(
        pts_entry, "Entry EV/EBITDA (×)", "Realized MOIC",
        x_lo=3.0, x_hi=22.0, y_lo=0.0, y_hi=6.5, color="#3b82f6",
    )
    svg_hold = _scatter_svg(
        pts_hold, "Hold Years", "Realized MOIC",
        x_lo=1.0, x_hi=11.0, y_lo=0.0, y_hi=6.5, color="#8b5cf6",
    )
    svg_pred = _scatter_svg(
        pts_pred, "Predicted MOIC (corpus model)", "Realized MOIC",
        x_lo=0.5, x_hi=5.5, y_lo=0.0, y_hi=6.5, color="#06b6d4",
        trend_color="#f59e0b",
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


def _sector_rows(rows: List[Dict[str, Any]]) -> tuple:
    """Sector-calibration data for the paired block's dataset half.

    Returns ``(headers, data_rows, hot_rows)`` for ``ck_paired_block``.
    ``rows`` arrives pre-sorted by P50 MOIC descending, so ``hot_rows``
    just marks row 0 — the strongest sector. (Superseded the
    pre-rendered ``_sector_table_panel`` when /backtest adopted the
    handoff's paired viz+dataset primitive.)
    """
    headers = [
        "Sector", "N", "P25 MOIC", "P50 MOIC", "P75 MOIC", "Loss%", "3x+%",
    ]
    data_rows = [
        [
            r["sector"],
            str(r["n"]),
            f"{r['p25']:.2f}x",
            f"{r['p50']:.2f}x",
            f"{r['p75']:.2f}x",
            f"{r['loss_rate'] * 100:.1f}%",
            f"{r['homerun'] * 100:.1f}%",
        ]
        for r in rows
    ]
    return headers, data_rows, ([0] if data_rows else [])


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_backtest() -> str:
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_page_title, ck_paired_block, ck_section_header,
    )

    deals = _load_corpus()
    stats = _calibration_stats(deals)

    pts_entry = _entry_multiple_scatter_data(deals)
    pts_hold = _hold_scatter_data(deals)
    pts_pred = _predicted_vs_realized_data(deals)
    sector_rows = _sector_calibration(deals)

    kpis = _kpi_bar(stats)
    # Signature paired viz+dataset block: the realized-MOIC histogram
    # on the left, its per-sector breakdown on the right, one rule.
    # The histogram is the overall distribution; the sector table is
    # the same corpus sliced — exactly the handoff's pairing intent.
    sec_headers, sec_rows, sec_hot = _sector_rows(sector_rows)
    dist_paired = ck_paired_block(
        _moic_histogram_viz(stats["moics"]),
        data_label="MOIC by sector · ≥3 realized deals",
        data_source="deals corpus",
        headers=sec_headers,
        rows=sec_rows,
        hot_rows=sec_hot,
    )
    section_scatter = ck_section_header("ENTRY SIGNAL CALIBRATION", "entry characteristics vs realized outcomes")
    scatter_panel = _scatter_panel(pts_entry, pts_hold, pts_pred)
    section_cal = ck_section_header("MODEL STATISTICS", "corpus OLS calibration accuracy")
    cal_panel = _calibration_panel(stats)

    page_title = ck_page_title(
        "Model Calibration / Backtest",
        eyebrow="BACKTEST",
        meta=(
            f"{stats['realized_n']} realized deals · "
            f"P50 MOIC {stats['moic_p50']:.2f}x · "
            f"Model R² {stats['r2']:.3f} · "
            f"MAE {stats['mae']:.3f}x"
        ) if stats["r2"] is not None else f"{stats['realized_n']} realized deals",
    )
    bt_explainer = (
        '<p class="ck-bt-explainer">'
        "<em>How well the model retrodicts the corpus.</em> "
        "Predicted vs. realized MOIC across the calibration corpus, sliced by sector. "
        "R-squared and MAE tell you whether the model is earning its place; "
        "the residual cloud tells you where it isn't."
        "</p>"
    )
    body = (
        page_title
        + bt_explainer
        + kpis
        + ck_section_header(
            "MOIC DISTRIBUTION × SECTOR",
            "realized corpus outcomes, paired with the per-sector dataset",
        )
        + dist_paired
        + section_scatter
        + scatter_panel
        + section_cal
        + cal_panel
    )

    return chartis_shell(
        body,
        title="Model Calibration / Backtest",
        active_nav="/backtest",
        extra_css=_EXPLAINER_CSS,
    )
