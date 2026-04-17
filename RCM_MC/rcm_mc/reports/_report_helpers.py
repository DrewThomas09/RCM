"""Standalone helpers used by the HTML report generator.

These were previously inlined at the top of html_report.py.
"""
from __future__ import annotations

import base64
import json
import os
from html import escape as html_escape
from typing import Any, Dict, List, Optional

import pandas as pd

from .reporting import METRIC_LABELS, pretty_money


# Industry benchmark references (HFMA MAP, AHA, Kodiak, Fierce, AKASA)
_BENCHMARK_REFERENCES = {
    "idr_commercial": {"industry_avg": "13.9%", "top_decile": "~11–12%", "source": "AHA market scan"},
    "idr_ma": {"industry_avg": "15.7%", "top_decile": "~12–14%", "source": "AHA"},
    "idr_medicaid": {"industry_avg": "15–17%", "top_decile": "~14–15%", "source": "Fierce Healthcare"},
    "idr_medicare_ffs": {"industry_avg": "8–9%", "top_decile": "~7–8%", "source": "Fierce Healthcare"},
    "fwr_npsr": {"industry_avg": "2.8% of NPSR", "top_decile": "2.2% of NPSR", "source": "Kodiak/HealthLeaders"},
    "dar_days": {"industry_avg": "56.9 days", "top_decile": "43.6 days", "source": "Kodiak/HealthLeaders"},
    "ctc_pct": {"industry_avg": "3.68%", "top_decile": "~3.5%", "source": "AKASA/HFMA"},
    "ar_over_90": {"industry_avg": "35.9%", "best_practice": "<15%", "source": "PMC, Kodiak"},
}


def _extract_payer_params(cfg: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Extract IDR, FWR, DAR means by payer from config."""
    out: Dict[str, Dict[str, float]] = {}
    payers = cfg.get("payers") or {}
    for payer, p in payers.items():
        d: Dict[str, float] = {}
        if "denials" in p and p["denials"]:
            idr = p["denials"].get("idr")
            fwr = p["denials"].get("fwr")
            if isinstance(idr, dict) and "mean" in idr:
                d["idr"] = float(idr["mean"])
            if isinstance(fwr, dict) and "mean" in fwr:
                d["fwr"] = float(fwr["mean"])
        dar = p.get("dar_clean_days")
        if isinstance(dar, dict) and "mean" in dar:
            d["dar"] = float(dar["mean"])
        if d:
            out[payer] = d
    return out


def _build_benchmark_gap_table(
    actual_cfg: Optional[Dict[str, Any]],
    benchmark_cfg: Optional[Dict[str, Any]],
) -> str:
    """Build benchmark gap table: Target (actual) vs industry avg vs top-decile (benchmark)."""
    if not actual_cfg or not benchmark_cfg:
        return ""
    a = _extract_payer_params(actual_cfg)
    b = _extract_payer_params(benchmark_cfg)
    def _gap_badge(val_a: float, val_b: float, fmt: str = "pct") -> str:
        """Color-coded gap badge: red if target is worse, green if better."""
        diff = val_a - val_b
        if fmt == "pct":
            txt = f"+{diff*100:.1f}pp" if diff > 0 else f"{diff*100:.1f}pp"
        else:
            txt = f"+{diff:.0f}" if diff > 0 else f"{diff:.0f}"
        if diff > 0.001:
            return f"<span class='badge badge-red'>{txt}</span>"
        elif diff < -0.001:
            return f"<span class='badge badge-green'>{txt}</span>"
        return f"<span class='badge badge-amber'>0</span>"

    rows = []
    for payer in ("Medicare", "Medicaid", "Commercial"):
        if payer not in a or payer not in b:
            continue
        aa, bb = a[payer], b[payer]
        ref_key = "idr_medicaid" if payer == "Medicaid" else ("idr_ma" if payer == "Medicare" else "idr_commercial")
        ref = _BENCHMARK_REFERENCES.get(ref_key, {})
        idr_a = aa.get("idr")
        idr_b = bb.get("idr")
        if idr_a is not None and idr_b is not None:
            rows.append(
                f"<tr><td>Initial Denial Rate ({payer})</td><td class='num'>{idr_a*100:.1f}%</td>"
                f"<td class='num'>{ref.get('industry_avg', '—')}</td>"
                f"<td class='num'>{idr_b*100:.1f}%</td>"
                f"<td class='num'>{_gap_badge(idr_a, idr_b)}</td>"
                f"<td>{ref.get('source', '')}</td></tr>"
            )
        fwr_a, fwr_b = aa.get("fwr"), bb.get("fwr")
        if fwr_a is not None and fwr_b is not None:
            ref_fwr = _BENCHMARK_REFERENCES.get("fwr_npsr", {})
            rows.append(
                f"<tr><td>Write-Off Rate ({payer})</td><td class='num'>{fwr_a*100:.1f}%</td>"
                f"<td class='num'>{ref_fwr.get('industry_avg', '—')}</td>"
                f"<td class='num'>{fwr_b*100:.1f}%</td>"
                f"<td class='num'>{_gap_badge(fwr_a, fwr_b)}</td>"
                f"<td>{ref_fwr.get('source', '')}</td></tr>"
            )
        dar_a, dar_b = aa.get("dar"), bb.get("dar")
        if dar_a is not None and dar_b is not None:
            ref_dar = _BENCHMARK_REFERENCES.get("dar_days", {})
            rows.append(
                f"<tr><td>A/R Days ({payer})</td><td class='num'>{dar_a:.0f}</td>"
                f"<td class='num'>{ref_dar.get('industry_avg', '—')}</td>"
                f"<td class='num'>{dar_b:.0f}</td>"
                f"<td class='num'>{_gap_badge(dar_a, dar_b, 'days')}</td>"
                f"<td>{ref_dar.get('source', '')}</td></tr>"
            )
    if not rows:
        return ""
    return """
    <div class="card" id="benchmark-gap-table">
      <h3>Benchmark Gap Analysis</h3>
      <p class='section-desc'>How the target hospital compares to industry averages and top-decile performers. HFMA definitions; sources: AHA, Kodiak, Fierce, AKASA. See <a href="#data-sources">Data Sources</a>.</p>
      <table><tr><th>Metric</th><th>Target Hospital</th><th>Industry Average</th><th>Best Practice (Benchmark)</th><th>Gap</th><th>Source</th></tr>
      """ + "\n      ".join(rows) + """
      </table>
      <p class='section-desc'><em>Final Write-Off and A/R benchmarks: Kodiak top-10 performers (2.2% write-off rate, 43.6 A/R days). Cost to Collect: HFMA/AKASA average of 3.68%.</em></p>
    </div>"""


def _build_provenance_methodology_section(outdir: str) -> str:
    """Render Metric methodology card from provenance.json (written by cli per run)."""
    path = os.path.join(outdir, "provenance.json")
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ""
    run = doc.get("run") or {}
    metrics = doc.get("metrics") or []
    rows: List[str] = []
    for m in metrics:
        raw_name = str(m.get("metric", ""))
        display_name = METRIC_LABELS.get(raw_name, raw_name.replace("_", " ").title())
        name = html_escape(display_name)
        formula = html_escape(str(m.get("formula", ""))[:800])
        raw_keys = m.get("config_keys") or []
        keys = html_escape(", ".join(raw_keys)[:400])
        caveats = m.get("caveats") or []
        ctext = html_escape("; ".join(str(c) for c in caveats)[:500])
        agg = m.get("aggregations") or {}
        mean_v = agg.get("mean")
        if mean_v is not None and isinstance(mean_v, (int, float)):
            fv = float(mean_v)
            if abs(fv) >= 1e6:
                mean_s = pretty_money(fv)
            else:
                mean_s = html_escape(f"{fv:.4g}")
        else:
            mean_s = "—"
        rows.append(
            f"<tr><td>{name}</td><td class='num'>{mean_s}</td>"
            f"<td>{formula}</td><td>{keys}</td><td>{ctext}</td></tr>"
        )
    meta = html_escape(str(run.get("generated_at_utc", "")))
    n = html_escape(str(run.get("n_sims", "")))
    seed = html_escape(str(run.get("seed", "")))
    align = html_escape(str(run.get("align_profile", "")))
    git = html_escape(str(run.get("git_revision") or "n/a"))
    inp = run.get("inputs") or {}
    sha_a = str(inp.get("actual_config_sha256") or "—")
    sha_b = str(inp.get("benchmark_config_sha256") or "—")
    pre_a = html_escape(sha_a[:12] + ("…" if len(sha_a) > 12 else ""))
    pre_b = html_escape(sha_b[:12] + ("…" if len(sha_b) > 12 else ""))
    trace_note = ""
    tpath = os.path.join(outdir, "simulation_trace.json")
    if os.path.isfile(tpath):
        trace_note = (
            "<p class='section-desc'>Single-draw audit: <code>simulation_trace.json</code> "
            "(pre-scrub engine; use with scrubbed <code>simulations.csv</code> for full picture).</p>"
        )
    return f"""
    <div class="card" id="metric-methodology">
      <h2>Metric Definitions and Methodology</h2>
      <p class='section-desc'><strong>Why this matters:</strong> Full transparency on how every number is computed. Each metric links back to its formula, the configuration inputs that drive it, and known caveats. This supports audit-grade traceability for investment committee review.</p>
      <p class='section-desc'>Run: <em>{meta}</em> | Simulations: {n} | Seed: {seed} | Profile Alignment: {align} | Code Version: {git}</p>
      <p class='section-desc'>Configuration Fingerprint: Actual <code>{pre_a}</code> | Benchmark <code>{pre_b}</code></p>
      {trace_note}
      <table><tr><th>Metric</th><th>Mean Value</th><th>Formula / Definition</th><th>Configuration Drivers</th><th>Caveats</th></tr>
      {"".join(rows)}
      </table>
    </div>"""


def _build_data_confidence(calibration_path: str, out_path: str) -> str:
    """
    Read calibration_actual_report.csv and write data_confidence.csv with payer, sample metrics,
    calibrated means, and confidence label. Returns out_path.
    """
    df = pd.read_csv(calibration_path)
    rows = []
    for _, r in df.iterrows():
        payer = str(r.get("payer", ""))
        n_val = r.get("denial_cases_observed", 0)
        n = int(n_val) if pd.notna(n_val) and str(n_val).strip() != "" else 0
        if n < 0:
            n = 0
        if n < 30:
            conf = "Low"
        elif n < 100:
            conf = "Medium"
        else:
            conf = "High"
        idr_obs = r.get("idr_observed", "")
        fwr_obs = r.get("fwr_observed", "")
        idr_cal = r.get("idr_calibrated_mean", "")
        fwr_cal = r.get("fwr_calibrated_mean", "")
        idr_obs_str = f"{float(idr_obs):.3f}" if pd.notna(idr_obs) and str(idr_obs).strip() != "" else ""
        fwr_obs_str = f"{float(fwr_obs):.3f}" if pd.notna(fwr_obs) and str(fwr_obs).strip() != "" else ""
        calibrated_str = ""
        if pd.notna(idr_cal) and str(idr_cal).strip() != "" and pd.notna(fwr_cal) and str(fwr_cal).strip() != "":
            calibrated_str = f"IDR={float(idr_cal):.3f}, FWR={float(fwr_cal):.3f}"
        elif pd.notna(idr_cal) and str(idr_cal).strip() != "":
            calibrated_str = f"IDR={float(idr_cal):.3f}"
        elif pd.notna(fwr_cal) and str(fwr_cal).strip() != "":
            calibrated_str = f"FWR={float(fwr_cal):.3f}"
        rows.append({
            "payer": payer,
            "denial_cases_observed": n,
            "idr_observed": idr_obs_str,
            "fwr_observed": fwr_obs_str,
            "calibrated_means": calibrated_str,
            "confidence": conf,
        })
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False)
    return out_path


def _read_csv_if_exists(path: str, **kwargs) -> Optional[pd.DataFrame]:
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, **kwargs)


def _img_tag(path: str, alt: str) -> str:
    if not os.path.exists(path):
        return f"<p><em>Image not available: {alt}</em></p>"
    with open(path, "rb") as f:
        b = base64.b64encode(f.read()).decode("ascii")
    ext = os.path.splitext(path)[1].lower().replace(".", "")
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"<img src='data:{mime};base64,{b}' alt='{alt}' style='max-width: 100%; height: auto; border: 1px solid #e5e7eb; border-radius: 8px;'>"


def _fmt_metric_row(metric: str, row: pd.Series) -> str:
    """Format a summary row with separate columns and color-coded values."""
    label = METRIC_LABELS.get(metric, metric.replace("_", " ").title())
    if "dar" in metric:
        mean_v = f"{float(row['mean']):.1f} days"
        p10_v = f"{float(row['p10']):.1f} days"
        p90_v = f"{float(row['p90']):.1f} days"
    else:
        mean_v = pretty_money(float(row["mean"]))
        p10_v = pretty_money(float(row["p10"]))
        p90_v = pretty_money(float(row["p90"]))
    return (
        f"<tr><td>{label}</td>"
        f"<td class='num' style='font-weight:600;'>{mean_v}</td>"
        f"<td class='num' style='color:var(--green);'>{p10_v}</td>"
        f"<td class='num' style='color:var(--red);'>{p90_v}</td></tr>"
    )


def _format_money_cols(df: pd.DataFrame, money_cols: list) -> pd.DataFrame:
    """Format numeric columns as $X.XM for display. Returns copy."""
    out = df.copy()
    for c in money_cols:
        if c not in out.columns:
            continue
        def _fmt(v):
            if pd.isna(v):
                return ""
            x = float(v)
            if abs(x) < 1:
                return f"{x:.2f}"
            return pretty_money(x)
        out[c] = out[c].apply(_fmt)
    return out
